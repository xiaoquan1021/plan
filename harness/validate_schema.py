#!/usr/bin/env python3
"""Lightweight schema checks for public XQ plan contracts.

This validator intentionally avoids third-party dependencies so public CI can run
before the implementation toolchain is settled.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


TASK_REQUIRED = [
    "schema_version",
    "task_id",
    "title",
    "task_kind",
    "plan_rewrite_milestone",
    "product_milestone",
    "epic_id",
    "dependencies",
    "source_contracts",
    "source_contract_hashes",
    "allowed_logical_scopes",
    "forbidden_actions",
    "claimability_rules",
    "machine_acceptance",
    "required_evidence",
    "owner",
    "next_action",
    "supersedes",
]

LEGAL_STATUS = {
    "not-executable-index",
    "ready-for-ledger-review",
    "claimed",
    "in-progress",
    "completed",
    "failed-retry-ready",
    "blocked",
    "stale-completion",
    "lease-expired",
}

LEGAL_DECISION = {"none", "open", "proposed", "approved", "rejected", "superseded"}
LEGAL_ISSUANCE = {"draft", "issued", "revoked", "stale"}
EPIC_REQUIRED = ["schema_version", "contract_version", "epic_id", "title", "decision_state"]
TASK_PACK_REQUIRED = [
    "schema_version",
    "contract_version",
    "task_id",
    "epic_id",
    "issuance_status",
    "execution_ready",
    "baseline_requirement",
]


def load_jsonish(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_json(path: Path, errors: list[str]) -> None:
    try:
        load_jsonish(path)
    except Exception as exc:  # noqa: BLE001 - report all parse errors.
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON/YAML-compatible content: {exc}")


def validate_epic_contract(path: Path, errors: list[str]) -> None:
    try:
        data = load_jsonish(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.relative_to(ROOT)}: invalid epic contract: {exc}")
        return
    for key in EPIC_REQUIRED:
        require(key in data, f"{path.relative_to(ROOT)}: missing required field {key}", errors)
    require(data.get("schema_version") == 1, f"{path.relative_to(ROOT)}: schema_version must be 1", errors)
    require(isinstance(data.get("contract_version"), int), f"{path.relative_to(ROOT)}: contract_version must be integer", errors)
    require(data.get("decision_state") in LEGAL_DECISION, f"{path.relative_to(ROOT)}: illegal decision_state {data.get('decision_state')}", errors)


def validate_atomic_task_pack(path: Path, errors: list[str]) -> None:
    try:
        data = load_jsonish(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.relative_to(ROOT)}: invalid atomic task pack: {exc}")
        return
    for key in TASK_PACK_REQUIRED:
        require(key in data, f"{path.relative_to(ROOT)}: missing required field {key}", errors)
    require(data.get("schema_version") == 1, f"{path.relative_to(ROOT)}: schema_version must be 1", errors)
    require(isinstance(data.get("contract_version"), int), f"{path.relative_to(ROOT)}: contract_version must be integer", errors)
    require(data.get("issuance_status") in LEGAL_ISSUANCE, f"{path.relative_to(ROOT)}: illegal issuance_status {data.get('issuance_status')}", errors)
    require(isinstance(data.get("execution_ready"), bool), f"{path.relative_to(ROOT)}: execution_ready must be boolean", errors)
    if data.get("issuance_status") == "draft":
        require(data.get("base_commit") in (None, ""), f"{path.relative_to(ROOT)}: draft task pack must not bind a fake base_commit", errors)
        require(data.get("execution_ready") is False, f"{path.relative_to(ROOT)}: draft task pack must not be execution_ready", errors)


def validate_task_definitions(errors: list[str]) -> None:
    index_path = ROOT / "ledger/task-definitions/index.yaml"
    index = load_jsonish(index_path)
    require(index.get("schema_version") == 1, "task definition index schema_version must be 1", errors)
    entries = index.get("task_definitions")
    require(isinstance(entries, list), "task definition index requires task_definitions list", errors)
    if not isinstance(entries, list):
        return

    seen: set[str] = set()
    for entry in entries:
        task_id = entry.get("task_id") if isinstance(entry, dict) else None
        path_value = entry.get("path") if isinstance(entry, dict) else None
        require(isinstance(task_id, str) and bool(task_id), f"invalid task index entry: {entry}", errors)
        require(task_id not in seen, f"duplicate task id in index: {task_id}", errors)
        if isinstance(task_id, str):
            seen.add(task_id)
        require(isinstance(path_value, str) and bool(path_value), f"task {task_id}: missing path", errors)
        if not isinstance(path_value, str):
            continue
        task_path = ROOT / path_value
        require(task_path.exists(), f"task {task_id}: missing file {path_value}", errors)
        if not task_path.exists():
            continue
        task = load_jsonish(task_path)
        for key in TASK_REQUIRED:
            require(key in task, f"{path_value}: missing required field {key}", errors)
        require(task.get("schema_version") == 1, f"{path_value}: schema_version must be 1", errors)
        require(task.get("task_id") == task_id, f"{path_value}: task_id does not match index", errors)
        status = task.get("status")
        if status is not None:
            require(status in LEGAL_STATUS, f"{path_value}: illegal status {status}", errors)
        decision_state = task.get("decision_state")
        if decision_state is not None:
            require(decision_state in LEGAL_DECISION, f"{path_value}: illegal decision_state {decision_state}", errors)
        for list_key in ["dependencies", "source_contracts", "allowed_logical_scopes", "forbidden_actions", "claimability_rules", "machine_acceptance", "required_evidence", "supersedes"]:
            require(isinstance(task.get(list_key), list), f"{path_value}: {list_key} must be a list", errors)


def validate_known_json_files(errors: list[str]) -> None:
    for pattern in [
        "config/*.json",
        "ledger/schema/*.json",
        "ledger/fixtures/*.json",
    ]:
        for path in sorted(ROOT.glob(pattern)):
            if path.name.endswith(".local.json"):
                continue
            validate_json(path, errors)
    for path in sorted(ROOT.glob("docs/contracts/epics/*.yaml")):
        validate_epic_contract(path, errors)
    for path in sorted(ROOT.glob("docs/contracts/task-packs/*.yaml")):
        validate_atomic_task_pack(path, errors)

    for path in sorted((ROOT / "docs/contracts/templates").glob("*.yaml")):
        # Templates are illustrative YAML and may use null/list syntax. They are
        # not parsed here; task and fixture YAML files are JSON-compatible.
        if not path.read_text(encoding="utf-8").strip():
            errors.append(f"{path.relative_to(ROOT)}: template is empty")

    validate_task_definitions(errors)


def main() -> int:
    errors: list[str] = []
    validate_known_json_files(errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("schema validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
