#!/usr/bin/env python3
"""Deterministic legacy public ledger migration report generator."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from fnmatch import fnmatch
from hashlib import sha256
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIGRATION = ROOT / "ledger/migrations/0001-task-definition-migration.yaml"
DEFAULT_LEGACY_TASKS = ROOT / "ledger/archive/legacy-public-snapshot-202606/tasks.json"
DEFAULT_REPORT = ROOT / "ledger/archive/legacy-public-snapshot-202606/migration-report.json"


def canonical(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def hash_data(data: Any) -> str:
    return sha256(canonical(data)).hexdigest()


def load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required for migration definitions")
        return yaml.safe_load(text)
    return json.loads(text)


def resolve(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def repo_relative(path: Path) -> str:
    if path.is_relative_to(ROOT):
        return path.relative_to(ROOT).as_posix()
    return path.as_posix()


def legacy_tasks(legacy: Any) -> list[dict[str, Any]]:
    if isinstance(legacy, dict):
        tasks = legacy.get("tasks", [])
    else:
        tasks = legacy
    if not isinstance(tasks, list):
        raise ValueError("legacy input must contain a tasks list")
    return tasks


def match_mapping(task: dict[str, Any], mappings: list[dict[str, Any]]) -> dict[str, Any] | None:
    task_id = str(task.get("id") or task.get("task_id") or "")
    source = str(task.get("source_md") or "")
    for mapping in mappings:
        pattern = str(mapping["old_task_id"])
        source_pattern = str(mapping["old_source"])
        if fnmatch(task_id, pattern) or (source and (source == source_pattern or source.startswith(source_pattern.rstrip("/") + "/"))):
            return mapping
    return None


def classify_status(task: dict[str, Any], mapping: dict[str, Any] | None) -> tuple[str, str]:
    if mapping is None:
        return "unmapped", "No migration mapping matched this legacy task."
    rule = str(mapping["status_rule"])
    if task.get("status") == "completed" and rule not in {"historical-only", "superseded"}:
        return rule, "Legacy completed is historical and requires runner-backed private reconciliation before implementation credit."
    return rule, str(mapping["reason"])


def build_report(legacy_input: Path = DEFAULT_LEGACY_TASKS, migration_definition: Path = DEFAULT_MIGRATION) -> dict[str, Any]:
    migration = load(migration_definition)
    legacy = load(legacy_input)
    tasks = legacy_tasks(legacy)
    mappings = migration.get("mappings", [])
    migrated: list[dict[str, Any]] = []
    counts = {
        "mapped": 0,
        "unmapped": 0,
        "superseded": 0,
        "historical_only": 0,
        "requires_private_reconciliation": 0,
        "stale_completion": 0,
    }
    unmapped: list[str] = []
    status_change_reasons: list[dict[str, str]] = []
    for task in sorted(tasks, key=lambda item: str(item.get("id") or item.get("task_id") or "")):
        old_task_id = str(task.get("id") or task.get("task_id") or "")
        mapping = match_mapping(task, mappings)
        status_rule, reason = classify_status(task, mapping)
        if mapping is None:
            unmapped.append(old_task_id)
            counts["unmapped"] += 1
            migrated_entry = {
                "old_task_id": old_task_id,
                "old_status": task.get("status"),
                "classification": "unmapped",
                "new_task_ids": [],
                "new_milestone": None,
                "new_epic": None,
                "superseded_by": None,
                "reason": reason,
            }
        else:
            if status_rule == "superseded":
                counts["superseded"] += 1
            elif status_rule == "historical-only":
                counts["historical_only"] += 1
            elif status_rule == "requires-private-reconciliation":
                counts["requires_private_reconciliation"] += 1
            elif status_rule == "stale-completion":
                counts["stale_completion"] += 1
            else:
                counts["mapped"] += 1
            migrated_entry = {
                "old_task_id": old_task_id,
                "old_source": task.get("source_md"),
                "old_status": task.get("status"),
                "classification": status_rule,
                "new_task_ids": mapping["new_task_ids"],
                "new_milestone": mapping["new_milestone"],
                "new_epic": mapping["new_epic"],
                "superseded_by": mapping["superseded_by"],
                "reason": reason,
            }
        if task.get("status") == "completed":
            status_change_reasons.append(
                {
                    "old_task_id": old_task_id,
                    "old_status": "completed",
                    "current_interpretation": migrated_entry["classification"],
                    "reason": "legacy completed does not inherit implementation completed",
                }
            )
        migrated.append(migrated_entry)

    report_without_hash = {
        "schema_version": 1,
        "migration_id": migration["migration_id"],
        "legacy_input": repo_relative(legacy_input),
        "migration_definition": repo_relative(migration_definition),
        "input_hash": hash_data(legacy),
        "migration_definition_hash": hash_data(migration),
        "mapped_count": counts["mapped"],
        "unmapped_count": counts["unmapped"],
        "superseded_count": counts["superseded"],
        "historical_only_count": counts["historical_only"],
        "requires_private_reconciliation_count": counts["requires_private_reconciliation"],
        "stale_completion_count": counts["stale_completion"],
        "status_change_reasons": status_change_reasons,
        "unmapped_tasks": unmapped,
        "migrated_tasks": migrated,
        "legacy_completed_inherited_as_implementation_completed": False,
    }
    report = dict(report_without_hash)
    report["output_hash"] = hash_data(report_without_hash)
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(report))


def compare_reports(expected: dict[str, Any], path: Path) -> list[str]:
    if not path.exists():
        return [f"{path}: missing migration report"]
    actual = load(path)
    if actual == expected:
        return []
    return [f"{path}: migration report differs from deterministic output"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-input", default=str(DEFAULT_LEGACY_TASKS))
    parser.add_argument("--migration-definition", default=str(DEFAULT_MIGRATION))
    parser.add_argument("--output-report", default=str(DEFAULT_REPORT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    legacy_input = resolve(args.legacy_input)
    migration_definition = resolve(args.migration_definition)
    output_report = resolve(args.output_report)
    try:
        report = build_report(legacy_input, migration_definition)
        if args.check:
            if output_report.exists():
                diffs = compare_reports(report, output_report)
                if diffs:
                    for diff in diffs:
                        print(diff, file=sys.stderr)
                    return 1
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    temp_report = Path(tmp) / "migration-report.json"
                    write_report(report, temp_report)
                print(f"{output_report}: missing migration report", file=sys.stderr)
                return 1
            print("migration check passed")
            return 0
        write_report(report, output_report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"migration failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
