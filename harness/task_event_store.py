#!/usr/bin/env python3
"""Append-only event store and replay for the XQ ledger harness."""

from __future__ import annotations

import json
import uuid
import fcntl
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from command_summary_validator import validate_command_summary_file, validate_command_summary_matches_evidence
from evidence_validator import CompletionRecordError, validate_completion_record
from ledger_models import (
    EVENT_SCHEMA_VERSION,
    EVENT_TASK_BLOCKED,
    EVENT_TASK_CLAIMED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_FAILED,
    EVENT_TASK_HEARTBEAT,
    EVENT_TASK_OVERRIDE,
    EVENT_TASK_REOPENED,
    EVENT_TASK_RELEASED,
    EVENT_TASK_STARTED,
    EVENT_TYPES,
    EVENTS_FILE,
    FAILURE_TYPES,
    IMMEDIATE_BLOCK_FAILURE_TYPES,
    RETRYABLE_FAILURE_TYPES,
    ROOT,
    STATUS_BLOCKED,
    STATUS_CLAIMED,
    STATUS_COMPLETED,
    STATUS_FAILED_RETRY_READY,
    STATUS_IN_PROGRESS,
    STATUS_READY,
    STATUS_STALE_COMPLETION,
    TREE_ROOT,
    clone_task,
    file_sha256,
    resolve_tree_path,
    sha256_json,
    utc_now,
)


class EventStoreError(Exception):
    """Raised when event store operations fail."""


def _payload_errors(event: dict[str, Any]) -> list[str]:
    event_type = event.get("event_type")
    payload = event.get("payload")
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be an object"]
    if event_type in {EVENT_TASK_CLAIMED, EVENT_TASK_STARTED, EVENT_TASK_HEARTBEAT}:
        lease = payload.get("lease")
        if not isinstance(lease, dict):
            errors.append("payload.lease must be an object")
        else:
            for key in ["task_id", "actor", "session_id", "claimed_at", "heartbeat_at", "lease_seconds"]:
                if lease.get(key) in (None, ""):
                    errors.append(f"payload.lease.{key} is required")
    elif event_type == EVENT_TASK_RELEASED:
        if "reason" not in payload:
            errors.append("payload.reason is required")
        lease = payload.get("lease")
        if lease is not None and not isinstance(lease, dict):
            errors.append("payload.lease must be an object or null")
    elif event_type == EVENT_TASK_COMPLETED:
        if not isinstance(payload.get("record_path"), str) or not payload.get("record_path"):
            errors.append("payload.record_path is required")
        if not isinstance(payload.get("command_summary"), str) or not payload.get("command_summary"):
            errors.append("payload.command_summary is required")
        for key in ["record_sha256", "source_md_sha256", "command_summary_sha256"]:
            value = payload.get(key)
            if not isinstance(value, str) or len(value) != 64:
                errors.append(f"payload.{key} must be a 64-character string")
    elif event_type in {EVENT_TASK_FAILED, EVENT_TASK_BLOCKED}:
        failure_type = payload.get("failure_type")
        if failure_type not in FAILURE_TYPES:
            errors.append(f"payload.failure_type must be one of {sorted(FAILURE_TYPES)}")
        if not isinstance(payload.get("reason"), str) or not payload.get("reason"):
            errors.append("payload.reason is required")
    elif event_type == EVENT_TASK_REOPENED:
        if payload.get("from_status") not in {STATUS_BLOCKED, STATUS_STALE_COMPLETION}:
            errors.append("payload.from_status must be blocked or stale-completion")
        if not isinstance(payload.get("reason"), str) or not payload.get("reason"):
            errors.append("payload.reason is required")
    elif event_type == EVENT_TASK_OVERRIDE:
        if not isinstance(payload.get("gate"), str) or not payload.get("gate"):
            errors.append("payload.gate is required")
        if not isinstance(payload.get("reason"), str) or not payload.get("reason"):
            errors.append("payload.reason is required")
    return errors


class EventStore:
    def __init__(self, events_file: Path = EVENTS_FILE, *, tree_root: Path = TREE_ROOT, root: Path = ROOT) -> None:
        self.events_file = events_file
        self.tree_root = tree_root
        self.root = root

    def read_events(self) -> list[dict[str, Any]]:
        if not self.events_file.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.events_file.open("r", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
            try:
                for line in handle:
                    if not line.strip():
                        continue
                    events.append(json.loads(line))
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return events

    def last_hash(self) -> str | None:
        events = self.read_events()
        if not events:
            return None
        return str(events[-1].get("event_sha256"))

    @staticmethod
    def _last_hash_from_open_file(handle: Any) -> str | None:
        handle.seek(0)
        last_event: dict[str, Any] | None = None
        for raw in handle:
            if not raw.strip():
                continue
            last_event = json.loads(raw)
        handle.seek(0, 2)
        if last_event is None:
            return None
        return str(last_event.get("event_sha256"))

    def append_event(
        self,
        event_type: str,
        *,
        task_id: str,
        actor: str,
        session_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise EventStoreError(f"unsupported event_type: {event_type}")
        self.events_file.parent.mkdir(parents=True, exist_ok=True)
        with self.events_file.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            event = {
                "schema_version": EVENT_SCHEMA_VERSION,
                "event_id": f"{utc_now()}-{uuid.uuid4().hex}",
                "created_at": utc_now(),
                "event_type": event_type,
                "task_id": task_id,
                "actor": actor,
                "session_id": session_id,
                "payload": payload or {},
                "previous_event_sha256": self._last_hash_from_open_file(handle),
            }
            payload_errors = _payload_errors(event)
            if payload_errors:
                raise EventStoreError("; ".join(payload_errors))
            event["event_sha256"] = self.compute_hash(event)
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            try:
                import os

                os.fsync(handle.fileno())
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return event

    @staticmethod
    def compute_hash(event: dict[str, Any]) -> str:
        normalized = dict(event)
        normalized.pop("event_sha256", None)
        return sha256_json(normalized)

    def validate_events(self) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        previous_hash: str | None = None
        if not self.events_file.exists():
            return {"valid": True, "errors": [], "events": [], "event_count": 0}

        with self.events_file.open("r", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
            try:
                for line_no, raw in enumerate(handle, start=1):
                    if not raw.strip():
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        errors.append({"line": line_no, "error": f"invalid JSON: {exc}"})
                        continue
                    if not isinstance(event, dict):
                        errors.append({"line": line_no, "error": "event root must be an object"})
                        continue
                    events.append(event)
                    for key in [
                        "schema_version",
                        "event_id",
                        "created_at",
                        "event_type",
                        "task_id",
                        "actor",
                        "session_id",
                        "payload",
                        "previous_event_sha256",
                        "event_sha256",
                    ]:
                        if key not in event:
                            errors.append({"line": line_no, "event_id": event.get("event_id"), "error": f"missing {key}"})
                    if event.get("schema_version") != EVENT_SCHEMA_VERSION:
                        errors.append({"line": line_no, "event_id": event.get("event_id"), "error": "bad schema_version"})
                    for key in ["event_id", "created_at", "task_id", "actor", "session_id"]:
                        if not isinstance(event.get(key), str) or not event.get(key):
                            errors.append({"line": line_no, "event_id": event.get("event_id"), "error": f"{key} must be a non-empty string"})
                    if event.get("event_type") not in EVENT_TYPES:
                        errors.append({"line": line_no, "event_id": event.get("event_id"), "error": "unsupported event_type"})
                    for payload_error in _payload_errors(event):
                        errors.append({"line": line_no, "event_id": event.get("event_id"), "error": payload_error})
                    if event.get("previous_event_sha256") != previous_hash:
                        errors.append({"line": line_no, "event_id": event.get("event_id"), "error": "hash chain previous pointer mismatch"})
                    expected_hash = self.compute_hash(event)
                    if event.get("event_sha256") != expected_hash:
                        errors.append({"line": line_no, "event_id": event.get("event_id"), "error": "event_sha256 mismatch"})
                    previous_hash = event.get("event_sha256")
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        return {"valid": not errors, "errors": errors, "events": events, "event_count": len(events)}

    def derive_tasks(self, base_tasks: list[dict[str, Any]]) -> dict[str, Any]:
        validation = self.validate_events()
        tasks_by_id = {task["id"]: clone_task(task) for task in base_tasks}
        failure_counts: Counter[str] = Counter()
        overrides = 0
        missing_private_evidence: list[dict[str, Any]] = []
        invalid_private_evidence: list[dict[str, Any]] = []
        stale_completed: list[dict[str, Any]] = []
        event_errors = list(validation["errors"])

        if event_errors:
            return {
                "tasks": list(tasks_by_id.values()),
                "events": validation["events"],
                "event_errors": event_errors,
                "missing_private_evidence": missing_private_evidence,
                "invalid_private_evidence": invalid_private_evidence,
                "stale_completed": stale_completed,
                "failure_counts": dict(failure_counts),
                "override_count": overrides,
            }

        for event in validation["events"]:
            task_id = str(event.get("task_id"))
            task = tasks_by_id.get(task_id)
            if task is None:
                event_errors.append({"event_id": event.get("event_id"), "error": f"unknown task_id {task_id}"})
                continue
            payload = event.get("payload") or {}
            event_type = event.get("event_type")

            if event_type == EVENT_TASK_CLAIMED:
                task["status"] = STATUS_CLAIMED
                task["claimed_by"] = event.get("actor")
                task["session_id"] = event.get("session_id")
            elif event_type == EVENT_TASK_STARTED:
                task["status"] = STATUS_IN_PROGRESS
                task["claimed_by"] = event.get("actor")
                task["session_id"] = event.get("session_id")
            elif event_type == EVENT_TASK_HEARTBEAT:
                task["last_heartbeat_at"] = event.get("created_at")
            elif event_type == EVENT_TASK_RELEASED:
                if task.get("status") in {STATUS_CLAIMED, STATUS_IN_PROGRESS}:
                    task["status"] = STATUS_READY
                task.pop("claimed_by", None)
                task.pop("session_id", None)
            elif event_type == EVENT_TASK_COMPLETED:
                record_path_value = payload.get("record_path")
                if not record_path_value:
                    missing_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": "missing record_path"})
                    continue
                record_path = resolve_tree_path(str(record_path_value), tree_root=self.tree_root, root=self.root)
                if not record_path.exists():
                    missing_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": f"evidence file does not exist: {record_path}"})
                    continue
                if file_sha256(record_path) != payload.get("record_sha256"):
                    invalid_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": "record_sha256 mismatch"})
                    continue
                require_runner_commands = payload.get("command_capture") == "runner-artifact-v1"
                require_completion_gate_coverage = (
                    payload.get("completion_coverage") == "acceptance-and-test-plan-all-items-v1"
                )
                try:
                    record = validate_completion_record(
                        record_path,
                        task=task,
                        require_current_source_hash=False,
                        require_runner_commands=require_runner_commands,
                        require_completion_gate_coverage=require_completion_gate_coverage,
                        tree_root=self.tree_root,
                        root=self.root,
                    )
                except CompletionRecordError as exc:
                    invalid_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": str(exc)})
                    continue
                if record.get("source_md_sha256") != payload.get("source_md_sha256"):
                    invalid_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": "source_md_sha256 mismatch between event and evidence"})
                    continue
                command_summary_value = payload.get("command_summary")
                command_summary_path = resolve_tree_path(str(command_summary_value), tree_root=self.tree_root, root=self.root)
                if not command_summary_path.exists():
                    invalid_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": f"command summary file does not exist: {command_summary_path}"})
                    continue
                if file_sha256(command_summary_path) != payload.get("command_summary_sha256"):
                    invalid_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": "command_summary_sha256 mismatch"})
                    continue
                command_summary, summary_error = validate_command_summary_file(
                    command_summary_path,
                    require_success=True,
                    require_runner_commands=require_runner_commands,
                    tree_root=self.tree_root,
                    root=self.root,
                    task_id=task_id if require_runner_commands else None,
                    actor=str(event.get("actor")) if require_runner_commands else None,
                    session_id=str(event.get("session_id")) if require_runner_commands else None,
                )
                if summary_error is not None:
                    invalid_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": summary_error})
                    continue
                match_error = validate_command_summary_matches_evidence(
                    command_summary or {},
                    record,
                    require_runner_commands=require_runner_commands,
                )
                if match_error is not None:
                    invalid_private_evidence.append({"event_id": event.get("event_id"), "task_id": task_id, "reason": match_error})
                    continue
                completion_standard = (
                    "verified-runner-backed"
                    if require_runner_commands and require_completion_gate_coverage
                    else "legacy-verified"
                )
                task["status"] = STATUS_COMPLETED
                task["evidence_status"] = completion_standard
                task["completion_standard"] = completion_standard
                task["command_capture"] = payload.get("command_capture", "legacy-command-summary")
                task["completion_coverage"] = payload.get("completion_coverage", "legacy-acceptance-coverage")
                task["record_path"] = str(record_path)
                task["record_sha256"] = payload.get("record_sha256")
                task["command_summary"] = str(command_summary_path)
                task["command_summary_sha256"] = payload.get("command_summary_sha256")
                task["completed_at"] = event.get("created_at")
                task["source_md_sha256"] = payload.get("source_md_sha256")
            elif event_type == EVENT_TASK_FAILED:
                failure_type = str(payload.get("failure_type", "test-failed"))
                if failure_type not in FAILURE_TYPES:
                    event_errors.append({"event_id": event.get("event_id"), "task_id": task_id, "error": f"unsupported failure_type {failure_type}"})
                    continue
                failure_counts[task_id] += 1
                task["last_failure_type"] = failure_type
                task["last_failure_reason"] = payload.get("reason")
                task["failure_count"] = failure_counts[task_id]
                if failure_type in IMMEDIATE_BLOCK_FAILURE_TYPES or failure_counts[task_id] >= 2:
                    task["status"] = STATUS_BLOCKED
                elif failure_type in RETRYABLE_FAILURE_TYPES:
                    task["status"] = STATUS_FAILED_RETRY_READY
            elif event_type == EVENT_TASK_BLOCKED:
                task["status"] = STATUS_BLOCKED
                task["blocked_reason"] = payload.get("reason")
                task["last_failure_type"] = payload.get("failure_type")
            elif event_type == EVENT_TASK_REOPENED:
                task["status"] = STATUS_READY
                task["reopened_from"] = payload.get("from_status")
                task["reopen_reason"] = payload.get("reason")
                task["reopened_at"] = event.get("created_at")
                task["reopened_by"] = event.get("actor")
                for key in [
                    "blocked_reason",
                    "claimed_by",
                    "session_id",
                    "last_heartbeat_at",
                    "completion_standard",
                    "command_capture",
                    "completion_coverage",
                    "record_path",
                    "record_sha256",
                    "command_summary",
                    "command_summary_sha256",
                    "completed_at",
                    "source_md_sha256",
                ]:
                    task.pop(key, None)
                task["evidence_status"] = "unverified"
            elif event_type == EVENT_TASK_OVERRIDE:
                overrides += 1
                task.setdefault("overrides", []).append(
                    {
                        "event_id": event.get("event_id"),
                        "gate": payload.get("gate"),
                        "reason": payload.get("reason"),
                        "actor": event.get("actor"),
                        "created_at": event.get("created_at"),
                    }
                )

        for task in tasks_by_id.values():
            if task.get("status") != STATUS_COMPLETED:
                continue
            source_md = task.get("source_md")
            source_md_sha256 = task.get("source_md_sha256")
            if not source_md or not source_md_sha256:
                stale_completed.append({"task_id": task["id"], "reason": "completed task missing source_md_sha256"})
                task["status"] = STATUS_STALE_COMPLETION
                continue
            source_path = resolve_tree_path(str(source_md), tree_root=self.tree_root, root=self.root)
            if not source_path.exists() or file_sha256(source_path) != source_md_sha256:
                stale_completed.append({"task_id": task["id"], "reason": "source document changed after completion"})
                task["status"] = STATUS_STALE_COMPLETION

        return {
            "tasks": list(tasks_by_id.values()),
            "events": validation["events"],
            "event_errors": event_errors,
            "missing_private_evidence": missing_private_evidence,
            "invalid_private_evidence": invalid_private_evidence,
            "stale_completed": stale_completed,
            "failure_counts": dict(failure_counts),
            "override_count": overrides,
        }


def event_type_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(event.get("event_type")) for event in events).items()))


def status_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(task.get("status")) for task in tasks).items()))


def failure_count_by_type(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for event in events:
        if event.get("event_type") != EVENT_TASK_FAILED:
            continue
        payload = event.get("payload") or {}
        counts[str(payload.get("failure_type", "test-failed"))] += 1
    return dict(sorted(counts.items()))
