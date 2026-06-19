#!/usr/bin/env python3
"""Generate deterministic public ledger snapshots from task definitions."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_NAMES = [
    "tasks.json",
    "task-graph.json",
    "public-state-summary.json",
    "task-runtime-summary.json",
]


def canonical_bytes(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def load_jsonish(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_task_definitions() -> tuple[list[dict[str, Any]], str]:
    index_path = ROOT / "ledger/task-definitions/index.yaml"
    index = load_jsonish(index_path)
    source_material: list[bytes] = [canonical_bytes(index)]
    tasks: list[dict[str, Any]] = []
    for entry in sorted(index["task_definitions"], key=lambda item: item["task_id"]):
        task_path = ROOT / entry["path"]
        task = load_jsonish(task_path)
        source_material.append(canonical_bytes(task))
        tasks.append(task)
    source_hash = sha256_bytes(b"".join(source_material))
    return tasks, source_hash


def deterministic_generated_at() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat(timespec="seconds")
    # Stable fallback for definitions-only public projection.
    return "1970-01-01T00:00:00+00:00"


def projection_task(task: dict[str, Any]) -> dict[str, Any]:
    status = task.get("status", "ready-for-ledger-review")
    return {
        "id": task["task_id"],
        "task_id": task["task_id"],
        "title": task["title"],
        "task_kind": task["task_kind"],
        "plan_rewrite_milestone": task.get("plan_rewrite_milestone"),
        "product_milestone": task.get("product_milestone"),
        "epic_id": task.get("epic_id"),
        "source_md": (task.get("source_contracts") or [None])[0],
        "source_contracts": task.get("source_contracts", []),
        "status": status,
        "decision_state": task.get("decision_state", "none"),
        "task_dependencies": task.get("dependencies", []),
        "blocked_reason": task.get("blocked_reason"),
        "required_evidence": task.get("required_evidence", []),
        "unblock_condition": task.get("unblock_condition"),
        "owner": task.get("owner"),
        "next_action": task.get("next_action"),
        "supersedes": task.get("supersedes", []),
        "evidence_status": "definitions-only",
        "workspace_state": "not-projected",
    }


def build_graph(projected: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        {
            "id": task["id"],
            "status": task["status"],
            "plan_rewrite_milestone": task.get("plan_rewrite_milestone"),
            "product_milestone": task.get("product_milestone"),
            "epic_id": task.get("epic_id"),
        }
        for task in projected
    ]
    edges = [
        {"from": dep, "to": task["id"], "kind": "task"}
        for task in projected
        for dep in task.get("task_dependencies", [])
    ]
    return {"metadata": metadata, "nodes": nodes, "edges": sorted(edges, key=lambda item: (item["from"], item["to"]))}


def counts(projected: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for task in projected:
        status = str(task.get("status"))
        result[status] = result.get(status, 0) + 1
    return dict(sorted(result.items()))


def aggregate_milestones(projected: list[dict[str, Any]]) -> dict[str, Any]:
    milestones: dict[str, dict[str, Any]] = {}
    for key in ["plan_rewrite_milestone", "product_milestone"]:
        for task in projected:
            milestone = task.get(key)
            if not milestone:
                continue
            entry = milestones.setdefault(
                milestone,
                {
                    "contract_status": "draft",
                    "implementation_status": "not-started",
                    "acceptance_status": "not-run",
                    "status_source": "definitions-only projection",
                },
            )
            if task.get("status") == "blocked":
                entry["implementation_status"] = "blocked"
    return dict(sorted(milestones.items()))


def generate(output: Path) -> dict[str, Path]:
    tasks, source_hash = load_task_definitions()
    metadata = {
        "schema_version": 1,
        "generator": "harness/generate_snapshots.py",
        "generator_version": 1,
        "generated_at": deterministic_generated_at(),
        "source_hash": source_hash,
        "projection_mode": "definitions-only",
    }
    projected = [projection_task(task) for task in tasks]
    projected.sort(key=lambda item: item["id"])
    data = {
        "tasks.json": {"metadata": metadata, "tasks": projected},
        "task-graph.json": build_graph(projected, metadata),
        "public-state-summary.json": {
            "metadata": metadata,
            "counts": {"tasks": len(projected), "status_counts": counts(projected)},
            "milestones": aggregate_milestones(projected),
        },
        "task-runtime-summary.json": {
            "metadata": metadata,
            "runtime_projection": "none",
            "status_counts": counts(projected),
            "private_inputs": {
                "runtime_events": "not-provided",
                "completion_records": "not-provided",
                "workspace_report": "not-provided",
            },
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name in SNAPSHOT_NAMES:
        path = output / name
        path.write_bytes(canonical_bytes(data[name]))
        written[name] = path
    return written


def compare_dirs(left: Path, right: Path) -> list[str]:
    diffs: list[str] = []
    for name in SNAPSHOT_NAMES:
        left_path = left / name
        right_path = right / name
        if not right_path.exists():
            diffs.append(f"{name}: missing committed snapshot")
            continue
        if not filecmp.cmp(left_path, right_path, shallow=False):
            diffs.append(f"{name}: differs from generated output")
    return diffs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--definitions-only", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--runtime-events")
    parser.add_argument("--completion-records")
    parser.add_argument("--workspace-report")
    parser.add_argument("--public-output", default="ledger/snapshots")
    args = parser.parse_args(argv)

    output = ROOT / args.public_output
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            temp_output = Path(tmp)
            generate(temp_output)
            diffs = compare_dirs(temp_output, output)
            if diffs:
                for diff in diffs:
                    print(diff, file=sys.stderr)
                return 1
            print("snapshot check passed")
            return 0
    generate(output)
    print(f"generated snapshots in {repo_relative(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
