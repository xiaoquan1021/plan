#!/usr/bin/env python3
"""Shared JSON/YAML loading and JSON Schema validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "ledger" / "schema"


class SchemaValidationError(ValueError):
    """Raised when an instance fails schema validation."""


def load_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def load_schema(name: str) -> dict[str, Any]:
    return load_data(SCHEMA_DIR / name)


def _schema_with_id(path: Path) -> dict[str, Any]:
    schema = dict(load_data(path))
    schema.setdefault("$id", path.as_uri())
    return schema


def _schema_registry() -> Registry:
    registry = Registry()
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = _schema_with_id(path)
        registry = registry.with_resource(path.as_uri(), Resource.from_contents(schema))
    return registry


def validator_for(schema_name: str) -> Draft202012Validator:
    schema_path = SCHEMA_DIR / schema_name
    return Draft202012Validator(_schema_with_id(schema_path), registry=_schema_registry())


def validation_errors(data: Any, schema_name: str, *, label: str) -> list[str]:
    validator = validator_for(schema_name)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = "/".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{label}:{location}: {error.message}")
    return errors


def validate_data(data: Any, schema_name: str, *, label: str) -> None:
    errors = validation_errors(data, schema_name, label=label)
    if errors:
        raise SchemaValidationError("\n".join(errors))


def validate_file(path: Path, schema_name: str, *, label: str | None = None) -> None:
    try:
        data = load_data(path)
    except Exception as exc:  # noqa: BLE001 - callers need a concise validation error.
        raise SchemaValidationError(f"{label or path}: parse failed: {exc}") from exc
    validate_data(data, schema_name, label=label or str(path))
