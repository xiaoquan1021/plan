#!/usr/bin/env python3
"""Negative schema tests for public contract validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


TOOLS_DIR = Path(__file__).resolve().parents[1]
ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import validate_schema  # noqa: E402


def schema(name: str) -> dict:
    return validate_schema.load_schema(name)


def errors_for(instance: dict, schema_name: str) -> list:
    return list(Draft202012Validator(schema(schema_name)).iter_errors(instance))


def test_malformed_yaml_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("schema_version: 1\nbad: [\n", encoding="utf-8")
    errors: list[str] = []
    validate_schema.validate_instance(path, schema("task-definition.schema.json"), errors)
    assert errors


def test_additional_property_rejected() -> None:
    task = {
        "schema_version": 1,
        "task_id": "T",
        "title": "Title",
        "task_kind": "plan-contract",
        "plan_rewrite_milestone": "PR-M0",
        "product_milestone": None,
        "epic_id": "E",
        "dependencies": [],
        "source_contracts": [],
        "source_contract_hashes": {},
        "allowed_logical_scopes": [],
        "forbidden_actions": [],
        "claimability_rules": [],
        "machine_acceptance": [],
        "required_evidence": [],
        "blocked_reason": None,
        "unblock_condition": None,
        "owner": "Codex B",
        "next_action": "validate",
        "supersedes": [],
        "unexpected": True,
    }
    assert errors_for(task, "task-definition.schema.json")


def valid_task_pack() -> dict:
    return {
        "schema_version": 1,
        "contract_version": 1,
        "task_id": "XQ-M1-CORE-001",
        "epic_id": "XQ-M1-CORE-DATA",
        "issuance_status": "draft",
        "execution_ready": False,
        "baseline_requirement": "requires XQ-M0",
        "base_commit": None,
        "rollback_point": None,
        "worktree_binding": None,
        "epic_contract_sha256": None,
        "task_pack_sha256": None,
        "dependency_contract_sha256": None,
        "implementation_dependency_lock_path": "IMPLEMENTATION_WORKSPACE/dependencies.lock.json",
        "implementation_dependency_lock_sha256": None,
        "toolchain_manifest_sha256": None,
        "supersedes": [],
        "allowed_logical_scopes": [],
        "allowed_paths": [],
        "forbidden_actions": [],
        "commands": [],
        "machine_acceptance": [],
        "required_evidence": [],
        "stop_conditions": [],
    }


def test_invalid_issued_task_rejected() -> None:
    pack = valid_task_pack()
    pack["issuance_status"] = "issued"
    pack["execution_ready"] = False
    assert errors_for(pack, "atomic-task-pack.schema.json")


def test_issued_task_with_null_base_rejected() -> None:
    pack = valid_task_pack()
    pack.update(
        {
            "issuance_status": "issued",
            "execution_ready": True,
            "rollback_point": "rollback",
            "worktree_binding": "TASK_WORKTREE",
            "epic_contract_sha256": "e" * 64,
            "task_pack_sha256": "p" * 64,
            "dependency_contract_sha256": "d" * 64,
            "implementation_dependency_lock_sha256": "l" * 64,
            "toolchain_manifest_sha256": "t" * 64,
            "allowed_paths": ["IMPLEMENTATION_WORKSPACE/src/core"],
            "commands": [{"command": "ctest", "required": True}],
            "machine_acceptance": ["passes"],
            "required_evidence": ["gate"],
            "stop_conditions": ["stop"],
        }
    )
    assert errors_for(pack, "atomic-task-pack.schema.json")


def test_accepted_gate_missing_evidence_rejected() -> None:
    gate = {
        "schema_version": 1,
        "task_id": "T",
        "task_pack_sha256": None,
        "epic_contract_sha256": None,
        "base_commit": None,
        "result_commit": None,
        "changed_files": [],
        "allowed_path_check": {"passed": True, "violations": []},
        "workspace_clean_before": True,
        "workspace_clean_after": True,
        "commands_reexecuted": [],
        "exit_codes": [],
        "tests_observed": [],
        "test_integrity_check": {"passed": True, "notes": []},
        "forbidden_scan": {"passed": True, "findings": []},
        "result_artifact_hashes": [],
        "decision": "accepted",
        "rework_reason": None,
        "escalation_reason": None,
    }
    assert errors_for(gate, "task-gate-result.schema.json")


def test_accepted_review_missing_hashes_rejected() -> None:
    review = {
        "schema_version": 1,
        "epic_id": "E",
        "epic_contract_sha256": None,
        "review_base_commit": None,
        "review_head_commit": None,
        "required_outcomes": [],
        "architecture_constraints": [],
        "acceptance_evidence": [],
        "cross_task_integration_findings": [],
        "unresolved_risks": [],
        "contract_defects": [],
        "decision": "accepted",
        "required_repairs": [],
    }
    assert errors_for(review, "epic-review.schema.json")
