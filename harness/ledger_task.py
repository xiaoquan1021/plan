#!/usr/bin/env python3
"""CLI for the XQ ledger executor harness."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from command_summary_validator import validate_command_summary_file, validate_command_summary_matches_evidence
from command_runner import run_harness_command
from evidence_validator import CompletionRecordError, validate_completion_record
from lease_manager import LeaseError, LeaseManager
from ledger_models import (
    DEFAULT_LEASE_SECONDS,
    EVENT_TASK_BLOCKED,
    EVENT_TASK_CLAIMED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_FAILED,
    EVENT_TASK_HEARTBEAT,
    EVENT_TASK_OVERRIDE,
    EVENT_TASK_REOPENED,
    EVENT_TASK_RELEASED,
    EVENT_TASK_STARTED,
    FAILURE_TYPES,
    ROOT,
    STATUS_BLOCKED,
    STATUS_STALE_COMPLETION,
    TASKS_FILE,
    TOOLS_DIR,
    TREE_ROOT,
    file_sha256,
)
from task_event_store import EventStore, event_type_counts, failure_count_by_type, status_counts
from task_selector import build_task_graph, dependency_violations, explain_selection


HARD_GATE_KEYS = [
    "scope_violations",
    "active_plan_kernel_violations",
    "claim_actionable",
    "deferred_needs_owner_confirmation",
    "execution_flow_items",
    "needs_hardening_documents",
    "task_event_errors",
    "missing_private_evidence_links",
    "invalid_private_evidence_files",
    "dependency_violations",
    "invalid_task_leases",
]

TASK_BLOCKING_GATE_KEYS = [
    "blocked_tasks",
    "lease_expired_tasks",
    "stale_completion_tasks",
    "expired_task_leases",
]

OVERRIDABLE_GATE_KEYS = set(HARD_GATE_KEYS + TASK_BLOCKING_GATE_KEYS)


def load_tasks(path: Path = TASKS_FILE) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["tasks"]


def runtime_tasks() -> dict[str, Any]:
    base_tasks = load_tasks()
    store = EventStore()
    derived = store.derive_tasks(base_tasks)
    leases = LeaseManager().summarize()
    for task in derived["tasks"]:
        if task["id"] in leases["expired_task_ids"] and task.get("status") in {"claimed", "in-progress"}:
            task["status"] = "lease-expired"
        if task["id"] in leases["active_task_ids"] and task.get("status") == "ready-for-ledger-review":
            task["status"] = "claimed"
    return {"tasks": derived["tasks"], "derived": derived, "leases": leases}


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))


def matching_terminal_event(
    store: EventStore,
    *,
    event_type: str,
    task_id: str,
    actor: str,
    session_id: str,
    payload_subset: dict[str, Any],
) -> dict[str, Any] | None:
    if not hasattr(store, "read_events"):
        return None
    for event in reversed(store.read_events()):
        if event.get("event_type") != event_type:
            continue
        if event.get("task_id") != task_id:
            continue
        if event.get("actor") != actor or event.get("session_id") != session_id:
            continue
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        if all(payload.get(key) == value for key, value in payload_subset.items()):
            return event
    return None


def release_after_terminal_event(
    lease_manager: LeaseManager,
    *,
    task_id: str,
    actor: str,
    session_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        return lease_manager.release(task_id, actor=actor, session_id=session_id), None
    except LeaseError as exc:
        return None, {"error": str(exc), "task_id": task_id}


def build_preflight_summary(audit_returncode: int, audit_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = runtime_tasks()
    store = EventStore()
    validation = store.validate_events()
    deps = dependency_violations(runtime["tasks"])
    summary: dict[str, Any] = {
        "audit_exit_code": audit_returncode,
        "event_valid": validation["valid"],
        "task_event_errors": len(validation["errors"]),
        "dependency_violations": len(deps),
        "active_leases": len(runtime["leases"]["active_leases"]),
        "expired_task_leases": len(runtime["leases"]["expired_leases"]),
        "invalid_task_leases": len(runtime["leases"]["invalid_leases"]),
        "status_counts": status_counts(runtime["tasks"]),
    }
    if audit_summary:
        summary["audit_gate_summary"] = audit_summary.get("gate_summary", {})
        for key in HARD_GATE_KEYS:
            if key in audit_summary:
                summary[key] = audit_summary[key]
    return summary


def load_preflight_audit_summary(audit_stdout: str) -> dict[str, Any] | None:
    try:
        return json.loads(audit_stdout)
    except json.JSONDecodeError:
        pass

    for path in [
        ROOT / "ledger" / "snapshots" / "public-state-summary.json",
        ROOT / "ledger" / "snapshots" / "audit-summary.json",
    ]:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data.get("summary"), dict):
            return data["summary"]
        counts = data.get("counts")
        if isinstance(counts, dict):
            return {
                "gate_summary": {
                    "hard_blocking_gates": counts.get("hard_blocking_gates", {}),
                    "task_blocking_states": counts.get("task_blocking_states", {}),
                    "informational_counts": {
                        "plan_documents": counts.get("plan_documents", 0),
                        "tasks": counts.get("tasks", 0),
                    },
                },
                "public_snapshot_counts_only": True,
            }
    return None


def preflight_allows_claim(summary: dict[str, Any]) -> bool:
    gate_summary = summary.get("audit_gate_summary", {})
    hard_gates = gate_summary.get("hard_blocking_gates", {}) if isinstance(gate_summary, dict) else {}
    task_blocking = gate_summary.get("task_blocking_states", {}) if isinstance(gate_summary, dict) else {}
    hard_count = sum(int(value) for value in hard_gates.values()) if isinstance(hard_gates, dict) else 0
    task_blocking_count = sum(int(value) for value in task_blocking.values()) if isinstance(task_blocking, dict) else 0
    return (
        int(summary.get("audit_exit_code", 1)) == 0
        and bool(summary.get("event_valid")) is True
        and int(summary.get("dependency_violations", 0)) == 0
        and hard_count == 0
        and task_blocking_count == 0
    )


def run_preflight_gate() -> dict[str, Any]:
    audit = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "audit_xq_zip_analysis.py")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    audit_summary = load_preflight_audit_summary(audit.stdout)
    summary = build_preflight_summary(audit.returncode, audit_summary)
    return {
        "ok": preflight_allows_claim(summary),
        "summary": summary,
        "stdout": audit.stdout,
        "stderr": audit.stderr,
    }


def command_preflight(args: argparse.Namespace) -> int:
    result = run_preflight_gate()
    summary = result["summary"]
    print_json(summary)
    if not result["ok"]:
        if result.get("stdout"):
            print(result["stdout"], file=sys.stderr)
        if result.get("stderr"):
            print(result["stderr"], file=sys.stderr)
        return 1
    return 0


def command_validate_events(args: argparse.Namespace) -> int:
    store = EventStore()
    validation = store.validate_events()
    print_json(
        {
            "valid": validation["valid"],
            "event_count": validation["event_count"],
            "errors": validation["errors"],
            "event_type_counts": event_type_counts(validation["events"]),
            "failure_count_by_type": failure_count_by_type(validation["events"]),
        }
    )
    return 0 if validation["valid"] else 1


def command_explain_next(args: argparse.Namespace) -> int:
    runtime = runtime_tasks()
    explanation = explain_selection(runtime["tasks"])
    if args.task_id:
        explanation["task"] = next((task for task in runtime["tasks"] if task["id"] == args.task_id), None)
    print_json(explanation)
    return 0


def command_claim_next(args: argparse.Namespace) -> int:
    preflight = run_preflight_gate()
    if not preflight["ok"]:
        print_json(
            {
                "error": "preflight failed; claim-next stopped before task selection",
                "preflight": preflight["summary"],
            }
        )
        return 1
    runtime = runtime_tasks()
    explanation = explain_selection(runtime["tasks"])
    selected = explanation.get("selected")
    if selected is None:
        print_json(explanation)
        return 1
    if args.dry_run:
        print_json({"dry_run": True, "selected": selected, "explanation": explanation})
        return 0
    lease_manager = LeaseManager(lease_seconds=args.lease_seconds)
    store = EventStore()
    claimed = None
    lease = None
    try:
        lease = lease_manager.claim(selected["id"], actor=args.actor, session_id=args.session_id)
        claimed = store.append_event(
            EVENT_TASK_CLAIMED,
            task_id=selected["id"],
            actor=args.actor,
            session_id=args.session_id,
            payload={"lease": lease},
        )
        started = store.append_event(
            EVENT_TASK_STARTED,
            task_id=selected["id"],
            actor=args.actor,
            session_id=args.session_id,
            payload={"lease": lease},
        )
    except (LeaseError, Exception) as exc:
        if claimed is not None:
            try:
                store.append_event(
                    EVENT_TASK_RELEASED,
                    task_id=selected["id"],
                    actor=args.actor,
                    session_id=args.session_id,
                    payload={"lease": lease, "reason": "claim-next rollback after append failure"},
                )
            except Exception as rollback_exc:
                print_json(
                    {
                        "error": str(exc),
                        "rollback_error": str(rollback_exc),
                        "selected": selected,
                        "lease_left_active": True,
                    }
                )
                return 1
        if lease is not None:
            try:
                lease_manager.release(selected["id"], actor=args.actor, session_id=args.session_id)
            except LeaseError as release_exc:
                print_json({"error": str(exc), "release_error": str(release_exc), "selected": selected})
                return 1
        print_json({"error": str(exc), "selected": selected})
        return 1
    print_json({"selected": selected, "lease": lease, "events": [claimed, started]})
    return 0


def command_heartbeat(args: argparse.Namespace) -> int:
    try:
        lease = LeaseManager().heartbeat(args.task_id, actor=args.actor, session_id=args.session_id)
        event = EventStore().append_event(
            EVENT_TASK_HEARTBEAT,
            task_id=args.task_id,
            actor=args.actor or lease.get("actor") or "codex",
            session_id=args.session_id or lease.get("session_id") or "unknown",
            payload={"lease": lease},
        )
    except LeaseError as exc:
        print_json({"error": str(exc)})
        return 1
    print_json({"lease": lease, "event": event})
    return 0


def command_release_claim(args: argparse.Namespace) -> int:
    try:
        lease_manager = LeaseManager()
        lease = lease_manager.read(args.task_id)
        if lease is None:
            raise LeaseError(f"task {args.task_id} has no active lease")
        if lease.get("actor") != args.actor:
            raise LeaseError(f"task {args.task_id} lease actor mismatch")
        if lease.get("session_id") != args.session_id:
            raise LeaseError(f"task {args.task_id} lease session mismatch")
        event = EventStore().append_event(
            EVENT_TASK_RELEASED,
            task_id=args.task_id,
            actor=args.actor,
            session_id=args.session_id,
            payload={"lease": lease, "reason": args.reason},
        )
        lease_manager.release(args.task_id, actor=args.actor, session_id=args.session_id)
    except (LeaseError, Exception) as exc:
        print_json({"error": str(exc), "task_id": args.task_id})
        return 1
    print_json({"released_lease": lease, "event": event})
    return 0


def require_owned_lease(task_id: str, *, actor: str, session_id: str, action: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    lease_manager = LeaseManager()
    lease = lease_manager.read(task_id)
    if lease is None:
        return None, {"error": f"{action} requires an active lease", "task_id": task_id}
    if lease_manager.is_expired(lease):
        return None, {"error": f"{action} requires a non-expired lease", "task_id": task_id, "lease": lease}
    if lease.get("actor") != actor:
        return None, {
            "error": f"{action} lease actor mismatch",
            "task_id": task_id,
            "lease_actor": lease.get("actor"),
            "actor": actor,
        }
    if lease.get("session_id") != session_id:
        return None, {
            "error": f"{action} lease session mismatch",
            "task_id": task_id,
            "lease_session_id": lease.get("session_id"),
            "session_id": session_id,
        }
    return lease, None


def command_record_complete(args: argparse.Namespace) -> int:
    runtime = runtime_tasks()
    task = next((item for item in runtime["tasks"] if item["id"] == args.task_id), None)
    if task is None:
        print_json({"error": f"unknown task_id {args.task_id}"})
        return 1
    record_path = Path(args.evidence)
    if not record_path.is_absolute():
        record_path = TREE_ROOT / record_path
    try:
        record = validate_completion_record(
            record_path,
            task=task,
            require_runner_commands=True,
            require_completion_gate_coverage=True,
        )
    except CompletionRecordError as exc:
        print_json({"error": str(exc), "task_id": args.task_id, "evidence": str(record_path)})
        return 1
    if not args.command_summary:
        print_json({"error": "record-complete requires --command-summary", "task_id": args.task_id})
        return 1
    command_summary_path = Path(args.command_summary)
    if not command_summary_path.is_absolute():
        command_summary_path = TREE_ROOT / command_summary_path
    command_summary, summary_error = validate_command_summary_file(
        command_summary_path,
        require_success=True,
        require_runner_commands=True,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
    )
    if summary_error is not None:
        print_json(
            {
                "error": summary_error,
                "task_id": args.task_id,
                "command_summary": str(command_summary_path),
            }
        )
        return 1
    match_error = validate_command_summary_matches_evidence(
        command_summary or {},
        record,
        require_runner_commands=True,
    )
    if match_error is not None:
        print_json(
            {
                "error": match_error,
                "task_id": args.task_id,
                "evidence": str(record_path),
                "command_summary": str(command_summary_path),
            }
        )
        return 1
    _, lease_error = require_owned_lease(
        args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        action="record-complete",
    )
    if lease_error is not None:
        print_json(lease_error)
        return 1
    lease_manager = LeaseManager()
    store = EventStore()
    payload = {
        "record_path": str(record_path),
        "record_sha256": file_sha256(record_path),
        "source_md_sha256": record["source_md_sha256"],
        "command_summary": str(command_summary_path),
        "command_summary_sha256": file_sha256(command_summary_path),
        "command_capture": "runner-artifact-v1",
        "completion_coverage": "acceptance-and-test-plan-all-items-v1",
    }
    existing_event = matching_terminal_event(
        store,
        event_type=EVENT_TASK_COMPLETED,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        payload_subset=payload,
    )
    if existing_event is not None:
        released, release_error = release_after_terminal_event(
            lease_manager,
            task_id=args.task_id,
            actor=args.actor,
            session_id=args.session_id,
        )
        if release_error is not None:
            release_error["event"] = existing_event
            print_json(release_error)
            return 1
        print_json({"event": existing_event, "evidence": record, "released_lease": released, "idempotent": True})
        return 0
    try:
        event = store.append_event(
            EVENT_TASK_COMPLETED,
            task_id=args.task_id,
            actor=args.actor,
            session_id=args.session_id,
            payload=payload,
        )
    except Exception as exc:
        print_json({"error": str(exc), "task_id": args.task_id})
        return 1
    released, release_error = release_after_terminal_event(
        lease_manager,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
    )
    if release_error is not None:
        release_error["event"] = event
        print_json(release_error)
        return 1
    print_json({"event": event, "evidence": record, "released_lease": released})
    return 0


def command_run_command(args: argparse.Namespace) -> int:
    lease, lease_error = require_owned_lease(
        args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        action="run-command",
    )
    if lease_error is not None:
        print_json(lease_error)
        return 1
    command_argv = list(args.command_argv or [])
    if command_argv and command_argv[0] == "--":
        command_argv = command_argv[1:]
    if not command_argv:
        print_json({"error": "run-command requires a command after --", "task_id": args.task_id})
        return 1
    artifact_path = Path(args.artifact) if args.artifact else None
    if artifact_path is not None and not artifact_path.is_absolute():
        artifact_path = TREE_ROOT / artifact_path
    command_summary_path = Path(args.command_summary) if args.command_summary else None
    if command_summary_path is not None and not command_summary_path.is_absolute():
        command_summary_path = TREE_ROOT / command_summary_path
    cwd = Path(args.cwd).resolve()
    try:
        result = run_harness_command(
            task_id=args.task_id,
            actor=args.actor,
            session_id=args.session_id,
            argv=command_argv,
            cwd=cwd,
            artifact_path=artifact_path,
            command_summary_path=command_summary_path,
        )
    except Exception as exc:
        print_json({"error": str(exc), "task_id": args.task_id, "lease": lease})
        return 1
    print_json(
        {
            "task_id": args.task_id,
            "artifact": str(result.artifact_path),
            "command_summary": str(result.command_summary_path) if result.command_summary_path else None,
            "evidence_command": result.command,
            "exit_code": result.command["exit_code"],
        }
    )
    return int(result.command["exit_code"])


def command_record_fail(args: argparse.Namespace) -> int:
    if args.failure_type not in FAILURE_TYPES:
        print_json({"error": f"failure_type must be one of {sorted(FAILURE_TYPES)}"})
        return 1
    _, lease_error = require_owned_lease(
        args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        action="record-fail",
    )
    if lease_error is not None:
        print_json(lease_error)
        return 1
    lease_manager = LeaseManager()
    store = EventStore()
    payload = {"failure_type": args.failure_type, "reason": args.reason}
    existing_event = matching_terminal_event(
        store,
        event_type=EVENT_TASK_FAILED,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        payload_subset=payload,
    )
    if existing_event is not None:
        released, release_error = release_after_terminal_event(
            lease_manager,
            task_id=args.task_id,
            actor=args.actor,
            session_id=args.session_id,
        )
        if release_error is not None:
            release_error["event"] = existing_event
            print_json(release_error)
            return 1
        print_json({"event": existing_event, "released_lease": released, "idempotent": True})
        return 0
    try:
        event = store.append_event(
            EVENT_TASK_FAILED,
            task_id=args.task_id,
            actor=args.actor,
            session_id=args.session_id,
            payload=payload,
        )
    except Exception as exc:
        print_json({"error": str(exc), "task_id": args.task_id})
        return 1
    released, release_error = release_after_terminal_event(
        lease_manager,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
    )
    if release_error is not None:
        release_error["event"] = event
        print_json(release_error)
        return 1
    print_json({"event": event, "released_lease": released})
    return 0


def command_record_block(args: argparse.Namespace) -> int:
    if args.failure_type not in FAILURE_TYPES:
        print_json({"error": f"failure_type must be one of {sorted(FAILURE_TYPES)}"})
        return 1
    _, lease_error = require_owned_lease(
        args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        action="record-block",
    )
    if lease_error is not None:
        print_json(lease_error)
        return 1
    lease_manager = LeaseManager()
    store = EventStore()
    payload = {"failure_type": args.failure_type, "reason": args.reason}
    existing_event = matching_terminal_event(
        store,
        event_type=EVENT_TASK_BLOCKED,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        payload_subset=payload,
    )
    if existing_event is not None:
        released, release_error = release_after_terminal_event(
            lease_manager,
            task_id=args.task_id,
            actor=args.actor,
            session_id=args.session_id,
        )
        if release_error is not None:
            release_error["event"] = existing_event
            print_json(release_error)
            return 1
        print_json({"event": existing_event, "released_lease": released, "idempotent": True})
        return 0
    try:
        event = store.append_event(
            EVENT_TASK_BLOCKED,
            task_id=args.task_id,
            actor=args.actor,
            session_id=args.session_id,
            payload=payload,
        )
    except Exception as exc:
        print_json({"error": str(exc), "task_id": args.task_id})
        return 1
    released, release_error = release_after_terminal_event(
        lease_manager,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
    )
    if release_error is not None:
        release_error["event"] = event
        print_json(release_error)
        return 1
    print_json({"event": event, "released_lease": released})
    return 0


def command_record_override(args: argparse.Namespace) -> int:
    runtime = runtime_tasks()
    if not any(task.get("id") == args.task_id for task in runtime["tasks"]):
        print_json({"error": f"unknown task_id {args.task_id}", "task_id": args.task_id})
        return 1
    if args.gate not in OVERRIDABLE_GATE_KEYS:
        print_json({"error": f"gate must be one of {sorted(OVERRIDABLE_GATE_KEYS)}", "gate": args.gate})
        return 1
    store = EventStore()
    validation = store.validate_events()
    if not validation["valid"]:
        print_json({"error": "record-override requires a valid event log", "errors": validation["errors"]})
        return 1
    event = store.append_event(
        EVENT_TASK_OVERRIDE,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        payload={"gate": args.gate, "reason": args.reason},
    )
    print_json({"event": event})
    return 0


def command_record_reopen(args: argparse.Namespace) -> int:
    preflight = run_preflight_gate()
    summary = preflight["summary"]
    gate_summary = summary.get("audit_gate_summary", {})
    hard_gates = gate_summary.get("hard_blocking_gates", {}) if isinstance(gate_summary, dict) else {}
    hard_count = sum(int(value) for value in hard_gates.values()) if isinstance(hard_gates, dict) else 0
    if int(summary.get("audit_exit_code", 1)) != 0 or not bool(summary.get("event_valid")) or hard_count != 0:
        print_json(
            {
                "error": "record-reopen requires zero hard gates and a valid event log",
                "preflight": summary,
            }
        )
        return 1
    store = EventStore()
    validation = store.validate_events()
    if not validation["valid"]:
        print_json({"error": "record-reopen requires a valid event log", "errors": validation["errors"]})
        return 1
    runtime = runtime_tasks()
    task = next((item for item in runtime["tasks"] if item.get("id") == args.task_id), None)
    if task is None:
        print_json({"error": f"unknown task_id {args.task_id}", "task_id": args.task_id})
        return 1
    current_status = str(task.get("status"))
    if current_status not in {STATUS_BLOCKED, STATUS_STALE_COMPLETION}:
        print_json(
            {
                "error": "record-reopen only accepts blocked or stale-completion tasks",
                "task_id": args.task_id,
                "status": current_status,
            }
        )
        return 1
    event = store.append_event(
        EVENT_TASK_REOPENED,
        task_id=args.task_id,
        actor=args.actor,
        session_id=args.session_id,
        payload={
            "from_status": current_status,
            "reason": args.reason,
        },
    )
    print_json({"event": event})
    return 0


def command_graph(args: argparse.Namespace) -> int:
    runtime = runtime_tasks()
    print_json(build_task_graph(runtime["tasks"]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XQ ledger task harness")
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight")
    preflight.set_defaults(func=command_preflight)

    validate = sub.add_parser("validate-events")
    validate.set_defaults(func=command_validate_events)

    explain = sub.add_parser("explain-next")
    explain.add_argument("--task-id")
    explain.set_defaults(func=command_explain_next)

    claim = sub.add_parser("claim-next")
    claim.add_argument("--actor", required=True)
    claim.add_argument("--session-id", required=True)
    claim.add_argument("--dry-run", action="store_true")
    claim.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)
    claim.set_defaults(func=command_claim_next)

    heartbeat = sub.add_parser("heartbeat")
    heartbeat.add_argument("--task-id", required=True)
    heartbeat.add_argument("--actor", required=True)
    heartbeat.add_argument("--session-id", required=True)
    heartbeat.set_defaults(func=command_heartbeat)

    release = sub.add_parser("release-claim")
    release.add_argument("--task-id", required=True)
    release.add_argument("--actor", required=True)
    release.add_argument("--session-id", required=True)
    release.add_argument("--reason", default="released without completion")
    release.set_defaults(func=command_release_claim)

    complete = sub.add_parser("record-complete")
    complete.add_argument("--task-id", required=True)
    complete.add_argument("--evidence", required=True)
    complete.add_argument("--actor", default="codex")
    complete.add_argument("--session-id", required=True)
    complete.add_argument("--command-summary", required=True)
    complete.set_defaults(func=command_record_complete)

    run = sub.add_parser("run-command")
    run.add_argument("--task-id", required=True)
    run.add_argument("--actor", required=True)
    run.add_argument("--session-id", required=True)
    run.add_argument("--cwd", default=str(ROOT))
    run.add_argument("--artifact")
    run.add_argument("--command-summary")
    run.add_argument("command_argv", nargs=argparse.REMAINDER)
    run.set_defaults(func=command_run_command)

    fail = sub.add_parser("record-fail")
    fail.add_argument("--task-id", required=True)
    fail.add_argument("--reason", required=True)
    fail.add_argument("--failure-type", default="test-failed")
    fail.add_argument("--actor", default="codex")
    fail.add_argument("--session-id", required=True)
    fail.set_defaults(func=command_record_fail)

    block = sub.add_parser("record-block")
    block.add_argument("--task-id", required=True)
    block.add_argument("--reason", required=True)
    block.add_argument("--failure-type", default="plan-ambiguous")
    block.add_argument("--actor", default="codex")
    block.add_argument("--session-id", required=True)
    block.set_defaults(func=command_record_block)

    override = sub.add_parser("record-override")
    override.add_argument("--task-id", required=True)
    override.add_argument("--gate", required=True)
    override.add_argument("--reason", required=True)
    override.add_argument("--actor", required=True)
    override.add_argument("--session-id", required=True)
    override.set_defaults(func=command_record_override)

    reopen = sub.add_parser("record-reopen")
    reopen.add_argument("--task-id", required=True)
    reopen.add_argument("--reason", required=True)
    reopen.add_argument("--actor", required=True)
    reopen.add_argument("--session-id", required=True)
    reopen.set_defaults(func=command_record_reopen)

    graph = sub.add_parser("task-graph")
    graph.set_defaults(func=command_graph)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
