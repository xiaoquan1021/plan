#!/usr/bin/env python3
"""Validate public XQ plan contracts with JSON Schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonschema import Draft202012Validator
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by CI install step.
    print(f"missing CI dependency: {exc}", file=sys.stderr)
    raise


ROOT = Path(__file__).resolve().parents[1]


class SchemaValidationError(ValueError):
    pass


def load_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def load_schema(name: str) -> dict[str, Any]:
    return load_data(ROOT / "ledger/schema" / name)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def validate_instance(path: Path, schema: dict[str, Any], errors: list[str]) -> None:
    try:
        data = load_data(path)
    except Exception as exc:  # noqa: BLE001 - report malformed YAML/JSON.
        errors.append(f"{display_path(path)}: parse failed: {exc}")
        return
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = "/".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{display_path(path)}:{location}: {error.message}")


def validate_task_definition_index(errors: list[str]) -> None:
    index_path = ROOT / "ledger/task-definitions/index.yaml"
    index_schema = load_schema("task-definition-index.schema.json")
    task_schema = load_schema("task-definition.schema.json")
    validate_instance(index_path, index_schema, errors)
    try:
        index = load_data(index_path)
    except Exception:
        return
    seen: set[str] = set()
    legal_milestones = {
        "PR-M0",
        "PR-M1",
        "PR-M2",
        "PR-M3",
        "XQ-M0",
        "XQ-M1",
        "XQ-M2A",
        "XQ-M2B",
        "XQ-M3",
        "XQ-M4",
        "XQ-M5",
        "XQ-M6",
        "XQ-M7",
        "XQ-M8",
        "XQ-M9",
    }
    for entry in index.get("task_definitions", []):
        task_id = entry.get("task_id")
        path_value = entry.get("path")
        if task_id in seen:
            errors.append(f"ledger/task-definitions/index.yaml: duplicate task_id {task_id}")
        seen.add(task_id)
        task_path = ROOT / path_value
        if not task_path.exists():
            errors.append(f"{path_value}: task definition file does not exist")
            continue
        validate_instance(task_path, task_schema, errors)
        try:
            task = load_data(task_path)
        except Exception:
            continue
        if task.get("task_id") != task_id:
            errors.append(f"{path_value}: task_id does not match index entry {task_id}")
        if entry.get("schema_version") != task.get("schema_version"):
            errors.append(f"{path_value}: schema_version does not match index")
        for key in ["plan_rewrite_milestone", "product_milestone"]:
            milestone = task.get(key)
            if milestone is not None and milestone not in legal_milestones:
                errors.append(f"{path_value}: illegal {key} {milestone}")


def validate_required_groups(errors: list[str]) -> None:
    groups: list[tuple[str, str]] = [
        ("config/path-bindings.example.json", "path-bindings.schema.json"),
        ("config/toolchain-bindings.example.json", "toolchain-bindings.schema.json"),
        ("config/dependency-baseline.proposed.json", "dependency-baseline.schema.json"),
        ("ledger/fixtures/fixture-manifest.json", "fixture-manifest.schema.json"),
        ("ledger/migrations/0001-task-definition-migration.yaml", "ledger-migration.schema.json"),
    ]
    for relative, schema_name in groups:
        validate_instance(ROOT / relative, load_schema(schema_name), errors)

    for path in sorted((ROOT / "docs/contracts/epics").glob("*.yaml")):
        validate_instance(path, load_schema("epic-contract.schema.json"), errors)
    for path in sorted((ROOT / "docs/contracts/task-packs").glob("*.yaml")):
        validate_instance(path, load_schema("atomic-task-pack.schema.json"), errors)

    for name in ["task-result", "task-gate-result", "epic-review"]:
        template = ROOT / "docs/contracts/templates" / f"{name}.template.yaml"
        validate_instance(template, load_schema(f"{name}.schema.json"), errors)

    # Public snapshots are generated artifacts, but their shape is still
    # validated so stale or manually edited files are caught in CI.
    snapshot_schema = load_schema("public-snapshot.schema.json")
    for path in sorted((ROOT / "ledger/snapshots").glob("*.json")):
        if path.name in {"tasks.json", "task-graph.json", "public-state-summary.json", "task-runtime-summary.json"}:
            validate_instance(path, snapshot_schema, errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    errors: list[str] = []
    validate_task_definition_index(errors)
    validate_required_groups(errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("schema validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
