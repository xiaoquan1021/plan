#!/usr/bin/env python3
"""Plan repository preflight gates for public CI and local private checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from projection import SNAPSHOT_NAMES, ProjectionError, build_snapshots, canonical_bytes, load_data, write_snapshots
from schema_validation import SchemaValidationError, validate_data


ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, argv: list[str]) -> dict[str, Any]:
    result = subprocess.run(argv, cwd=str(ROOT), text=True, capture_output=True)
    return {
        "name": name,
        "argv": argv,
        "exit_code": result.returncode,
        "stdout": result.stdout.strip().splitlines()[-10:],
        "stderr": result.stderr.strip().splitlines()[-10:],
    }


def public_steps() -> list[tuple[str, list[str]]]:
    py = sys.executable
    return [
        ("schema validation", [py, "harness/validate_schema.py"]),
        ("task graph validation", [py, "harness/validate_task_graph.py"]),
        ("snapshot check", [py, "harness/generate_snapshots.py", "--definitions-only", "--check"]),
        ("public contract scan", [py, "harness/validate_public_contracts.py"]),
        ("migration fixture check", [py, "harness/migrate_legacy_ledger.py", "--check"]),
    ]


def private_steps(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    return public_steps()


def validate_snapshot_privacy(path: Path) -> list[str]:
    text = "\n".join((path / name).read_text(encoding="utf-8") for name in SNAPSHOT_NAMES)
    errors: list[str] = []
    if "C:/Users/" in text or "C:\\Users\\" in text:
        errors.append("private absolute path leaked into temporary snapshot")
    for sensitive in ["patient_name", "patient_id", "raw_log", "stdout", "stderr"]:
        if sensitive in text:
            errors.append(f"sensitive field leaked into temporary snapshot: {sensitive}")
    return errors


def run_required_commit_ancestor_check(
    *,
    implementation_workspace: str | None,
    workspace_data: dict[str, Any],
    tasks: list[dict[str, Any]],
    required: bool = False,
) -> dict[str, Any]:
    if not implementation_workspace:
        if required:
            return {
                "status": "failed",
                "reason": "implementation workspace binding required for accepted Epic integration or product acceptance",
                "checked_count": 0,
                "errors": ["implementation-workspace-required"],
            }
        return {
            "status": "not-run",
            "reason": "implementation workspace binding not provided",
            "checked_count": 0,
            "errors": [],
        }
    repo = Path(implementation_workspace)
    try:
        probe = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(repo), text=True, capture_output=True)
    except OSError as exc:
        return {
            "status": "failed",
            "reason": "implementation workspace is not accessible",
            "checked_count": 0,
            "errors": [f"implementation-workspace-invalid:{exc}"],
        }
    if probe.returncode != 0:
        return {
            "status": "failed",
            "reason": "implementation workspace is not a git repository",
            "checked_count": 0,
            "errors": ["implementation-workspace-invalid"],
        }
    epic_head = workspace_data.get("epic_head_commit")
    integrated = workspace_data.get("integrated_task_commits") if isinstance(workspace_data.get("integrated_task_commits"), dict) else {}
    if not epic_head:
        return {
            "status": "failed",
            "reason": "workspace epic_head_commit missing",
            "checked_count": 0,
            "errors": ["epic-review-head-mismatch"],
        }
    required = [
        task
        for task in tasks
        if task.get("task_kind") in {"implementation", "implementation-readiness"}
        and task.get("required_for_epic")
        and (workspace_data.get("epic_id") in (None, "", task.get("epic_id")))
    ]
    errors: list[str] = []
    checked = 0
    head_exists = subprocess.run(["git", "cat-file", "-e", f"{epic_head}^{{commit}}"], cwd=str(repo), text=True, capture_output=True)
    if head_exists.returncode != 0:
        return {
            "status": "failed",
            "reason": "workspace epic_head_commit does not exist in implementation workspace",
            "checked_count": 0,
            "errors": ["epic-head-commit-missing"],
        }
    for task in required:
        task_id = str(task.get("task_id") or task.get("id"))
        commit = integrated.get(task_id)
        if not commit:
            errors.append(f"required-task-commit-missing:{task_id}")
            continue
        commit_exists = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=str(repo), text=True, capture_output=True)
        if commit_exists.returncode != 0:
            errors.append(f"required-task-commit-missing:{task_id}")
            continue
        checked += 1
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", str(commit), str(epic_head)],
            cwd=str(repo),
            text=True,
            capture_output=True,
        )
        if result.returncode == 1:
            errors.append(f"required-task-not-integrated:{task_id}")
        elif result.returncode != 0:
            errors.append(f"ancestor-check-error:{task_id}:{result.stderr.strip() or result.stdout.strip()}")
    return {
        "status": "passed" if not errors else "failed",
        "checked_count": checked,
        "errors": errors,
    }


def ancestor_check_required(workspace_data: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
    integrated = workspace_data.get("integrated_task_commits")
    if workspace_data.get("epic_head_commit") or (isinstance(integrated, dict) and bool(integrated)):
        return True
    if any(task.get("acceptance_evidence") == "codex-a-epic-review-accepted" for task in tasks):
        return True
    return False


def invalid_claimed_evidence(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    invalid: list[dict[str, Any]] = []
    for task in tasks:
        if task.get("status") == "stale-completion":
            invalid.append(task)
            continue
        if task.get("implementation_evidence") == "codex-b-gate-accepted" and task.get("stale_reasons"):
            invalid.append(task)
            continue
        if task.get("acceptance_evidence") == "codex-a-epic-review-accepted" and task.get("stale_reasons"):
            invalid.append(task)
            continue
        if task.get("plan_gate_evidence") == "stale" or task.get("plan_review_evidence") == "stale":
            invalid.append(task)
    return invalid


def run_full_projection(args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="xq-plan-full-projection-") as tmp:
        temp_output = Path(tmp)
        workspace_data = load_data(Path(args.workspace_report))
        snapshots = build_snapshots(
            runtime_events=Path(args.runtime_events),
            completion_records=Path(args.completion_records),
            workspace_report=Path(args.workspace_report),
        )
        write_snapshots(snapshots, temp_output)
        schema_errors: list[str] = []
        for name in SNAPSHOT_NAMES:
            try:
                validate_data(snapshots[name], "public-snapshot.schema.json", label=f"temporary/{name}")
            except SchemaValidationError as exc:
                schema_errors.append(str(exc))
        privacy_errors = validate_snapshot_privacy(temp_output)
        tasks = snapshots["tasks.json"]["tasks"]
        invalid_evidence = invalid_claimed_evidence(tasks)
        stale = [task for task in tasks if task.get("status") == "stale-completion"]
        ancestor_required = ancestor_check_required(workspace_data if isinstance(workspace_data, dict) else {}, tasks)
        ancestor_check = run_required_commit_ancestor_check(
            implementation_workspace=args.implementation_workspace,
            workspace_data=workspace_data if isinstance(workspace_data, dict) else {},
            tasks=tasks,
            required=ancestor_required,
        )
        ancestor_ok = ancestor_check["status"] == "passed" or (ancestor_check["status"] == "not-run" and not ancestor_required)
        report = {
            "mode": "full",
            "private_runtime_projection": "run",
            "temporary_projection_path": str(temp_output),
            "schema_validation": "passed" if not schema_errors else {"failed": schema_errors},
            "privacy_validation": "passed" if not privacy_errors else {"failed": privacy_errors},
            "ancestor_validation": ancestor_check,
            "task_count": len(tasks),
            "status_counts": snapshots["task-runtime-summary.json"]["status_counts"],
            "stale_count": len(stale),
            "invalid_evidence_count": len(invalid_evidence),
            "unknown_task_count": 0,
            "unknown_epic_count": 0,
            "overall_ok": not schema_errors and not privacy_errors and not invalid_evidence and ancestor_ok,
        }
        if args.report_output:
            report_path = Path(args.report_output)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            sanitized = dict(report)
            sanitized["temporary_projection_path"] = "temporary-private-path"
            report_path.write_bytes(canonical_bytes(sanitized))
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--runtime-events")
    parser.add_argument("--completion-records")
    parser.add_argument("--workspace-report")
    parser.add_argument("--implementation-workspace")
    parser.add_argument("--public-output", default="ledger/snapshots")
    parser.add_argument("--report-output")
    args = parser.parse_args(argv)

    if args.full:
        missing = [
            name
            for name, value in [
                ("--runtime-events", args.runtime_events),
                ("--completion-records", args.completion_records),
                ("--workspace-report", args.workspace_report),
            ]
            if not value
        ]
        if missing:
            report = {
                "schema_version": 1,
                "mode": "full",
                "ok": False,
                "private_runtime_projection": "not-run",
                "error": "full preflight requires private inputs",
                "missing": missing,
            }
            print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
            return 1

    steps = public_steps() if args.public or not args.full else private_steps(args)
    results = [run_step(name, command) for name, command in steps]
    ok = all(item["exit_code"] == 0 for item in results)
    full_report: dict[str, Any] | None = None
    if args.full and ok:
        try:
            full_report = run_full_projection(args)
            ok = bool(full_report["overall_ok"])
        except (ProjectionError, OSError, ValueError, json.JSONDecodeError) as exc:
            ok = False
            full_report = {
                "mode": "full",
                "private_runtime_projection": "not-run",
                "overall_ok": False,
                "error": str(exc),
            }
    report = {
        "schema_version": 1,
        "mode": "public" if args.public or not args.full else "full",
        "ok": ok,
        "private_runtime_projection": "not-run" if args.public or not args.full else (full_report or {}).get("private_runtime_projection", "not-run"),
        "steps": results,
    }
    if full_report:
        report["full_projection"] = full_report
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
