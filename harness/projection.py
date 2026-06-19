#!/usr/bin/env python3
"""Deterministic public snapshot projection helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - CI installs PyYAML.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_NAMES = [
    "tasks.json",
    "task-graph.json",
    "public-state-summary.json",
    "task-runtime-summary.json",
]

IMPLEMENTATION_TASK_KINDS = {"implementation", "implementation-readiness"}
ACCEPTANCE_TASK_KINDS = {"acceptance"}
PRIVATE_PATH_RE = re.compile(r"[A-Za-z]:[/\\][^\\n\\r\\t\"']*", re.IGNORECASE)
SENSITIVE_KEYS = {
    "patient_name",
    "patient_id",
    "institution",
    "institution_name",
    "operator_name",
    "raw_log",
    "stdout",
    "stderr",
}


class ProjectionError(ValueError):
    """Raised when runtime projection inputs are inconsistent."""


def canonical_bytes(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def load_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise ProjectionError("PyYAML is required to read YAML inputs")
        return yaml.safe_load(text)
    return json.loads(text)


def repo_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def normalize_for_hash(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: normalize_for_hash(data[key]) for key in sorted(data)}
    if isinstance(data, list):
        normalized_items = [normalize_for_hash(item) for item in data]
        return sorted(normalized_items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    return data


def hash_data(data: Any) -> str:
    return sha256_bytes(canonical_bytes(normalize_for_hash(data)))


def read_json_or_yaml_file(path_value: str | Path) -> Any:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return load_data(path)


def source_commit_time() -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def timestamp_from_epoch() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "0")
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat(timespec="seconds")


def latest_timestamp_from_inputs(inputs: list[Any]) -> str | None:
    candidates: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"event_time", "timestamp", "created_at", "generated_at", "completed_at", "reviewed_at"} and isinstance(item, str):
                    candidates.append(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for item in inputs:
        walk(item)
    return sorted(candidates)[-1] if candidates else None


def deterministic_generated_at(runtime_inputs: list[Any]) -> str:
    return latest_timestamp_from_inputs(runtime_inputs) or source_commit_time() or timestamp_from_epoch()


def redact_private(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: redact_private(item)
            for key, item in value.items()
            if key not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [redact_private(item) for item in value]
    if isinstance(value, str):
        return PRIVATE_PATH_RE.sub("PRIVATE_PATH_REDACTED", value)
    return value


def load_task_definitions() -> tuple[list[dict[str, Any]], str]:
    index_path = ROOT / "ledger/task-definitions/index.yaml"
    index = load_data(index_path)
    source_material: list[bytes] = [canonical_bytes(index)]
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in sorted(index["task_definitions"], key=lambda item: item["task_id"]):
        task_path = ROOT / entry["path"]
        task = load_data(task_path)
        task_id = task["task_id"]
        if task_id in seen:
            raise ProjectionError(f"duplicate task definition: {task_id}")
        seen.add(task_id)
        source_material.append(canonical_bytes(task))
        tasks.append(task)
    return tasks, sha256_bytes(b"".join(source_material))


def definition_projection(task: dict[str, Any]) -> dict[str, Any]:
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
        "source_contract_hashes": task.get("source_contract_hashes", {}),
        "status": status,
        "decision_state": task.get("decision_state", "none"),
        "task_dependencies": task.get("dependencies", []),
        "allowed_logical_scopes": task.get("allowed_logical_scopes", []),
        "claimability_rules": task.get("claimability_rules", []),
        "blocked_reason": task.get("blocked_reason"),
        "required_evidence": task.get("required_evidence", []),
        "unblock_condition": task.get("unblock_condition"),
        "owner": task.get("owner"),
        "next_action": task.get("next_action"),
        "supersedes": task.get("supersedes", []),
        "evidence_status": "definitions-only",
        "workspace_state": "not-projected",
        "runtime_projection": "none",
        "implementation_evidence": "none",
        "acceptance_evidence": "none",
        "stale_reasons": [],
    }


def list_from_projection(data: Any, key: str) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ProjectionError(f"{key} projection must be object or list")
    aliases = {
        "events": ["events", "runtime_events"],
        "task_results": ["task_results", "completion_records"],
        "gate_results": ["gate_results", "codex_b_gate_results"],
        "epic_reviews": ["epic_reviews", "codex_a_epic_reviews"],
    }
    for alias in aliases.get(key, [key]):
        value = data.get(alias)
        if value is not None:
            if not isinstance(value, list):
                raise ProjectionError(f"{key} must be a list")
            return value
    return []


def validate_known_task_ids(records: list[dict[str, Any]], known: set[str], label: str) -> None:
    for record in records:
        task_id = record.get("task_id")
        if task_id is not None and task_id not in known:
            raise ProjectionError(f"{label} references unknown task_id {task_id}")


def index_by_task(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in sorted(records, key=lambda item: (str(item.get("task_id", "")), hash_data(item))):
        task_id = record.get("task_id")
        if isinstance(task_id, str):
            indexed[task_id] = record
    return indexed


def latest_event_status(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for event in sorted(events, key=lambda item: (str(item.get("event_time") or item.get("timestamp") or ""), str(item.get("event_id") or ""))):
        task_id = event.get("task_id")
        if isinstance(task_id, str):
            latest[task_id] = event
    return latest


def status_from_event(event: dict[str, Any]) -> str | None:
    if "status" in event:
        return str(event["status"])
    return {
        "task_claimed": "claimed",
        "task_started": "in-progress",
        "task_failed": "failed-retry-ready",
        "task_blocked": "blocked",
        "task_reopened": "ready-for-ledger-review",
    }.get(str(event.get("event_type", "")))


def expected_hashes(task: dict[str, Any], workspace: dict[str, Any]) -> dict[str, Any]:
    source_hashes = task.get("source_contract_hashes") if isinstance(task.get("source_contract_hashes"), dict) else {}
    return {
        "base_commit": task.get("base_commit") or workspace.get("base_commit") or source_hashes.get("base_commit"),
        "epic_contract_sha256": task.get("epic_contract_sha256") or task.get("contract_sha256") or source_hashes.get("epic_contract_sha256") or source_hashes.get("contract_sha256"),
        "dependency_lock_sha256": task.get("dependency_lock_sha256") or workspace.get("dependency_lock_sha256") or workspace.get("implementation_dependency_lock_sha256") or source_hashes.get("dependency_lock_sha256"),
        "toolchain_manifest_sha256": task.get("toolchain_manifest_sha256") or workspace.get("toolchain_manifest_sha256") or source_hashes.get("toolchain_manifest_sha256"),
    }


def check_hashes(record: dict[str, Any] | None, expected: dict[str, Any], key_map: dict[str, str] | None = None) -> list[str]:
    if record is None:
        return []
    reasons: list[str] = []
    key_map = key_map or {}
    for key, expected_value in expected.items():
        if expected_value in (None, "", {}):
            continue
        record_key = key_map.get(key, key)
        actual = record.get(record_key)
        if actual not in (None, expected_value):
            reasons.append(f"{key}-changed")
    return reasons


def valid_task_result(task: dict[str, Any], workspace: dict[str, Any], result: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not result:
        return False, ["missing-task-result"]
    reasons: list[str] = []
    if result.get("decision") not in {"completed", "gate-required", "ready-for-gate", "passed"} and result.get("overall_status") not in {"passed", "completed"}:
        reasons.append("task-result-not-passing")
    reasons.extend(check_hashes(result, expected_hashes(task, workspace)))
    return not reasons, reasons


def valid_gate(task: dict[str, Any], workspace: dict[str, Any], gate: dict[str, Any] | None, result: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not gate:
        return False, ["missing-b-gate-result"]
    reasons: list[str] = []
    if gate.get("decision") != "accepted":
        reasons.append("b-gate-not-accepted")
    for key in ["task_pack_sha256", "base_commit", "result_commit"]:
        if not gate.get(key):
            reasons.append(f"missing-{key}")
    if result and result.get("task_pack_sha256") and gate.get("task_pack_sha256") != result.get("task_pack_sha256"):
        reasons.append("task-pack-hash-mismatch")
    reasons.extend(check_hashes(gate, expected_hashes(task, workspace)))
    return not reasons, reasons


def valid_epic_review(task: dict[str, Any], workspace: dict[str, Any], review: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not review:
        return False, ["missing-a-epic-review"]
    reasons: list[str] = []
    if review.get("decision") != "accepted":
        reasons.append("epic-review-not-accepted")
    for key in ["epic_contract_sha256", "review_base_commit", "review_head_commit"]:
        if not review.get(key):
            reasons.append(f"missing-{key}")
    expected = expected_hashes(task, workspace)
    reasons.extend(check_hashes(review, expected, {"base_commit": "review_base_commit"}))
    return not reasons, reasons


def apply_full_projection(
    projected: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
    runtime_data: Any,
    completion_data: Any,
    workspace_data: Any,
) -> None:
    known = {str(task["task_id"]) for task in definitions}
    by_task_id = {task["task_id"]: task for task in projected}
    definition_by_id = {task["task_id"]: task for task in definitions}
    events = list_from_projection(runtime_data, "events")
    task_results = list_from_projection(completion_data, "task_results")
    gate_results = list_from_projection(completion_data, "gate_results")
    epic_reviews = list_from_projection(completion_data, "epic_reviews")
    validate_known_task_ids(events, known, "runtime event")
    validate_known_task_ids(task_results, known, "task result")
    validate_known_task_ids(gate_results, known, "gate result")

    latest_events = latest_event_status(events)
    results_by_task = index_by_task(task_results)
    gates_by_task = index_by_task(gate_results)
    reviews_by_epic: dict[str, dict[str, Any]] = {}
    for review in sorted(epic_reviews, key=lambda item: (str(item.get("epic_id", "")), hash_data(item))):
        epic_id = review.get("epic_id")
        if isinstance(epic_id, str):
            reviews_by_epic[epic_id] = review

    workspace = workspace_data if isinstance(workspace_data, dict) else {}
    for task_id, task in by_task_id.items():
        definition = definition_by_id[task_id]
        task["evidence_status"] = "full-projection"
        task["runtime_projection"] = "projected"
        task["workspace_state"] = workspace.get("workspace_state", "projected")
        for key in ["base_commit", "implementation_dependency_lock_sha256", "dependency_lock_sha256", "toolchain_manifest_sha256"]:
            if workspace.get(key):
                task[key] = workspace[key]

        event = latest_events.get(task_id)
        if event:
            event_status = status_from_event(event)
            if event_status:
                task["status"] = event_status
            task["last_runtime_event"] = redact_private(event)

        result = results_by_task.get(task_id)
        gate = gates_by_task.get(task_id)
        result_ok, result_reasons = valid_task_result(definition, workspace, result)
        gate_ok, gate_reasons = valid_gate(definition, workspace, gate, result)
        review = reviews_by_epic.get(str(definition.get("epic_id"))) if definition.get("epic_id") else None
        review_ok, review_reasons = valid_epic_review(definition, workspace, review)

        stale_reasons = result_reasons + gate_reasons
        if definition.get("task_kind") in IMPLEMENTATION_TASK_KINDS:
            if result_ok and gate_ok:
                task["status"] = "completed"
                task["implementation_evidence"] = "codex-b-gate-accepted"
            else:
                task["implementation_evidence"] = "incomplete"
                if result or gate:
                    task["status"] = "stale-completion" if any("changed" in reason for reason in stale_reasons) else task["status"]
        if definition.get("task_kind") in ACCEPTANCE_TASK_KINDS or definition.get("epic_id"):
            if review_ok:
                task["acceptance_evidence"] = "codex-a-epic-review-accepted"
            else:
                task["acceptance_evidence"] = "not-passed"
                stale_reasons.extend(review_reasons)
        task["stale_reasons"] = sorted(set(stale_reasons))


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
    return {
        "metadata": metadata,
        "nodes": sorted(nodes, key=lambda item: item["id"]),
        "edges": sorted(edges, key=lambda item: (item["from"], item["to"])),
    }


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
                    "status_source": "generated from task definitions and runtime projection",
                },
            )
            status = task.get("status")
            if task.get("task_kind") in {"plan-contract", "contract-readiness", "harness"}:
                if status == "completed":
                    entry["contract_status"] = "approved"
                elif status == "blocked":
                    entry["contract_status"] = "blocked"
            if task.get("task_kind") in IMPLEMENTATION_TASK_KINDS:
                if status in {"claimed", "in-progress"} and entry["implementation_status"] != "blocked":
                    entry["implementation_status"] = "in-progress"
                elif status == "completed" and entry["implementation_status"] not in {"blocked", "stale"}:
                    entry["implementation_status"] = "completed"
                elif status == "stale-completion":
                    entry["implementation_status"] = "stale"
                elif status == "blocked":
                    entry["implementation_status"] = "blocked"
            if task.get("acceptance_evidence") == "codex-a-epic-review-accepted":
                entry["acceptance_status"] = "passed"
            elif task.get("status") == "blocked" and task.get("task_kind") in ACCEPTANCE_TASK_KINDS:
                entry["acceptance_status"] = "blocked"
    return dict(sorted(milestones.items()))


def projection_inputs_hash(definition_hash: str, runtime_data: Any | None, completion_data: Any | None, workspace_data: Any | None) -> str:
    return hash_data(
        {
            "task_definitions": definition_hash,
            "runtime_data": normalize_for_hash(runtime_data),
            "completion_data": normalize_for_hash(completion_data),
            "workspace_data": normalize_for_hash(workspace_data),
        }
    )


def build_snapshots(
    *,
    definitions_only: bool = False,
    runtime_events: Path | None = None,
    completion_records: Path | None = None,
    workspace_report: Path | None = None,
) -> dict[str, Any]:
    definitions, definition_hash = load_task_definitions()
    runtime_data = read_json_or_yaml_file(runtime_events) if runtime_events else None
    completion_data = read_json_or_yaml_file(completion_records) if completion_records else None
    workspace_data = read_json_or_yaml_file(workspace_report) if workspace_report else None
    full_projection = not definitions_only and any([runtime_events, completion_records, workspace_report])
    metadata = {
        "schema_version": 1,
        "generator": "harness/generate_snapshots.py",
        "generator_version": 2,
        "generated_at": deterministic_generated_at([item for item in [runtime_data, completion_data, workspace_data] if item is not None]),
        "source_hash": projection_inputs_hash(definition_hash, runtime_data if full_projection else None, completion_data if full_projection else None, workspace_data if full_projection else None),
        "task_definition_hash": definition_hash,
        "projection_mode": "full" if full_projection else "definitions-only",
    }
    projected = [definition_projection(task) for task in definitions]
    if full_projection:
        apply_full_projection(projected, definitions, runtime_data, completion_data, workspace_data)
    projected = redact_private(projected)
    projected.sort(key=lambda item: item["id"])
    return {
        "tasks.json": {"metadata": metadata, "tasks": projected},
        "task-graph.json": build_graph(projected, metadata),
        "public-state-summary.json": {
            "metadata": metadata,
            "counts": {"tasks": len(projected), "status_counts": counts(projected)},
            "milestones": aggregate_milestones(projected),
        },
        "task-runtime-summary.json": {
            "metadata": metadata,
            "runtime_projection": "projected" if full_projection else "none",
            "status_counts": counts(projected),
            "private_inputs": {
                "runtime_events": "provided" if runtime_events else "not-provided",
                "completion_records": "provided" if completion_records else "not-provided",
                "workspace_report": "provided" if workspace_report else "not-provided",
            },
            "note": "private runtime projection: projected from sanitized inputs" if full_projection else "private runtime projection: not run",
        },
    }


def write_snapshots(snapshots: dict[str, Any], output: Path) -> dict[str, Path]:
    output.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name in SNAPSHOT_NAMES:
        path = output / name
        path.write_bytes(canonical_bytes(snapshots[name]))
        written[name] = path
    return written
