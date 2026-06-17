#!/usr/bin/env python3
"""Shared constants and helpers for the XQ ledger harness."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TREE_ROOT = ROOT / "plans" / "xq-integrated-rebuild"
LEDGER_DIR = ROOT / "ledger"
TOOLS_DIR = ROOT / "harness"
SNAPSHOTS_DIR = LEDGER_DIR / "snapshots"
TASKS_FILE = SNAPSHOTS_DIR / "tasks.json"
EVENTS_FILE = LEDGER_DIR / "private-task-events.jsonl"
LOCKS_DIR = LEDGER_DIR / "task-locks"
TASK_GRAPH_FILE = SNAPSHOTS_DIR / "task-graph.json"
EVIDENCE_DIR = LEDGER_DIR / "private-evidence"

EVENT_SCHEMA_VERSION = 1
EVIDENCE_SCHEMA_VERSION = 1
DEFAULT_LEASE_SECONDS = 3600

STATUS_NOT_EXECUTABLE = "not-executable-index"
STATUS_READY = "ready-for-ledger-review"
STATUS_CLAIMED = "claimed"
STATUS_IN_PROGRESS = "in-progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED_RETRY_READY = "failed-retry-ready"
STATUS_BLOCKED = "blocked"
STATUS_STALE_COMPLETION = "stale-completion"
STATUS_LEASE_EXPIRED = "lease-expired"

RETRYABLE_FAILURE_TYPES = {"test-failed", "build-failed"}
IMMEDIATE_BLOCK_FAILURE_TYPES = {
    "missing-dependency",
    "plan-ambiguous",
    "source-boundary-risk",
    "harness-error",
}
FAILURE_TYPES = RETRYABLE_FAILURE_TYPES | IMMEDIATE_BLOCK_FAILURE_TYPES

EVENT_TASK_CLAIMED = "task_claimed"
EVENT_TASK_STARTED = "task_started"
EVENT_TASK_HEARTBEAT = "task_heartbeat"
EVENT_TASK_RELEASED = "task_released"
EVENT_TASK_COMPLETED = "task_completed"
EVENT_TASK_FAILED = "task_failed"
EVENT_TASK_BLOCKED = "task_blocked"
EVENT_TASK_REOPENED = "task_reopened"
EVENT_TASK_OVERRIDE = "task_override"

EVENT_TYPES = {
    EVENT_TASK_CLAIMED,
    EVENT_TASK_STARTED,
    EVENT_TASK_HEARTBEAT,
    EVENT_TASK_RELEASED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_FAILED,
    EVENT_TASK_BLOCKED,
    EVENT_TASK_REOPENED,
    EVENT_TASK_OVERRIDE,
}

DEPENDENCY_PHASES = [
    "00-governance",
    "01-foundation",
    "02-core-data",
    "03-native-project-io",
    "04-medical-image-io",
    "05-workbench-visualization",
    "06-workflow",
    "07-domain-features",
    "08-xq-zip-selection",
    "09-acceptance-repair",
]


@dataclass
class GateSummary:
    hard_blocking_gates: dict[str, int] = field(default_factory=dict)
    task_blocking_states: dict[str, int] = field(default_factory=dict)
    informational_counts: dict[str, int] = field(default_factory=dict)

    def hard_block_count(self) -> int:
        return sum(int(value) for value in self.hard_blocking_gates.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "hard_blocking_gates": dict(sorted(self.hard_blocking_gates.items())),
            "task_blocking_states": dict(sorted(self.task_blocking_states.items())),
            "informational_counts": dict(sorted(self.informational_counts.items())),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8", errors="replace")).hexdigest()


def sha256_json(data: Any) -> str:
    return sha256_text(canonical_json(data))


def safe_task_id(task_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", task_id).strip("-")


def resolve_tree_path(path_value: str, *, tree_root: Path = TREE_ROOT, root: Path = ROOT) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    if path_value.startswith("plans/xq-integrated-rebuild/"):
        return root / path_value
    if path_value.startswith("plans/"):
        return root / path_value
    return tree_root / path_value


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def task_phase(task: dict[str, Any]) -> str:
    source_md = str(task.get("source_md", ""))
    for phase in DEPENDENCY_PHASES:
        if f"/{phase}/" in source_md or source_md.endswith(f"/{phase}.md"):
            return phase
        if source_md.startswith(f"plans/xq-integrated-rebuild/{phase}/"):
            return phase
    return "zz-unknown"


def clone_task(task: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(task, ensure_ascii=False))
