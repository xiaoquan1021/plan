#!/usr/bin/env python3
"""Public-safe session preservation helpers.

The private planning session logs used by the original audit are intentionally
not included in this public snapshot. This module keeps the reusable helper
logic and emits a small public summary instead of reading private JSONL logs.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TREE_ROOT = ROOT / "plans" / "xq-integrated-rebuild"
LEDGER_DIR = ROOT / "ledger"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def extract_patch_paths(patch_text: str) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    patterns = [
        ("add", re.compile(r"^\*\*\* Add File: (.+)$")),
        ("update", re.compile(r"^\*\*\* Update File: (.+)$")),
        ("delete", re.compile(r"^\*\*\* Delete File: (.+)$")),
    ]
    for line in patch_text.splitlines():
        for operation, pattern in patterns:
            match = pattern.match(line)
            if match:
                changes.append({"operation": operation, "path": match.group(1).strip()})
                break
    return changes


def classify_current_preservation(
    *,
    tasks_count: int,
    archived_blocks: int,
    deferred_archive_rows: int,
    registered_deferred_boundaries: int,
    active_plan_kernel_violations: int,
) -> dict[str, bool]:
    return {
        "task_layer_preserved": tasks_count > 0,
        "execution_records_preserved": archived_blocks > 0,
        "deferred_details_preserved": deferred_archive_rows > 0 and registered_deferred_boundaries > 0,
        "active_plan_kernel_clean": active_plan_kernel_violations == 0,
    }


def public_preservation_summary() -> dict[str, Any]:
    public_state = read_json(LEDGER_DIR / "snapshots" / "public-state-summary.json")
    tasks = read_json(LEDGER_DIR / "snapshots" / "tasks.json")
    task_status_counts = Counter(task.get("status", "unknown") for task in tasks.get("tasks", []))
    hard_gates = public_state.get("counts", {}).get("hard_blocking_gates", {})
    return {
        "metadata": {
            "generated_at": now_iso(),
            "scope_root": str(ROOT),
            "tree_root": str(TREE_ROOT),
            "private_sessions_included": False,
        },
        "public_snapshot": {
            "tasks_count": len(tasks.get("tasks", [])),
            "task_status_counts": dict(sorted(task_status_counts.items())),
            "raw_private_evidence_included": public_state.get("raw_private_evidence_included", False),
            "raw_execution_records_included": public_state.get("raw_execution_records_included", False),
            "hard_blocking_gates": hard_gates,
        },
        "preservation": classify_current_preservation(
            tasks_count=len(tasks.get("tasks", [])),
            archived_blocks=0,
            deferred_archive_rows=0,
            registered_deferred_boundaries=int(hard_gates.get("deferred_needs_owner_confirmation", 0) == 0),
            active_plan_kernel_violations=int(hard_gates.get("active_plan_kernel_violations", 0)),
        ),
        "note": "Private session logs and raw execution records are intentionally omitted from this public snapshot.",
    }


def main() -> int:
    print(json.dumps(public_preservation_summary(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
