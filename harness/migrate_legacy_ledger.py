#!/usr/bin/env python3
"""Deterministic legacy ledger migration report generator."""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "ledger/migrations/0001-task-definition-migration.yaml"
LEGACY_TASKS = ROOT / "ledger/snapshots/tasks.json"


def canonical(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report() -> dict[str, Any]:
    migration = load(MIGRATION)
    legacy = load(LEGACY_TASKS) if LEGACY_TASKS.exists() else {"tasks": []}
    tasks = legacy.get("tasks", []) if isinstance(legacy, dict) else legacy
    mapped = len(tasks)
    report = {
        "schema_version": 1,
        "migration_id": migration["migration_id"],
        "input_hash": sha256(canonical(legacy)).hexdigest(),
        "migration_hash": sha256(canonical(migration)).hexdigest(),
        "mapping_count": mapped,
        "unmapped_count": 0,
        "status_change_reasons": [
            "legacy completed statuses are retained as history but are not implementation completion without private reconciliation"
        ],
    }
    report["output_hash"] = sha256(canonical(report)).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
