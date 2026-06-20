#!/usr/bin/env python3
"""Regression coverage for the final execution-closure P0 fixes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


TOOLS_DIR = Path(__file__).resolve().parents[1]
ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import preflight_plan  # noqa: E402
import projection  # noqa: E402
from task_selector import explain_selection  # noqa: E402


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64
HEX_E = "e" * 64
HEX_F = "f" * 64


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def task_definition() -> dict:
    return {
        "task_id": "XQ-M1-CORE-001",
        "task_kind": "implementation",
        "task_pack_sha256": HEX_A,
        "computed_task_pack_sha256": HEX_A,
        "declared_task_pack_sha256": HEX_A,
        "issuance_status": "issued",
        "execution_ready": True,
        "base_commit": "base123",
        "epic_contract_sha256": HEX_B,
        "dependency_contract_sha256": HEX_C,
        "implementation_dependency_lock_sha256": HEX_D,
        "dependency_lock_sha256": HEX_D,
        "toolchain_manifest_sha256": HEX_E,
    }


def workspace_projection() -> dict:
    return {
        "schema_version": 1,
        "workspace_state": "baseline-frozen",
        "base_commit": "base123",
        "dependency_contract_sha256": HEX_C,
        "implementation_dependency_lock_sha256": HEX_D,
        "dependency_lock_sha256": HEX_D,
        "toolchain_manifest_sha256": HEX_E,
        "reconciled_at": "2026-06-20T00:30:00+00:00",
    }


def valid_task_result() -> dict:
    return {
        "schema_version": 1,
        "task_id": "XQ-M1-CORE-001",
        "task_pack_sha256": HEX_A,
        "epic_contract_sha256": HEX_B,
        "base_commit": "base123",
        "result_commit": "result456",
        "changed_files": ["IMPLEMENTATION_WORKSPACE/src/core/XQDataNode.h"],
        "commands_run": ["COMMAND-REQ-XQ-M1-L0-CORE"],
        "test_results": ["L0 core identity passed"],
        "artifacts": ["artifact-a"],
        "unresolved_issues": [],
        "decision_request": "gate-required",
        "decision": "completed",
        "overall_status": "completed",
        "dependency_lock_sha256": HEX_D,
        "toolchain_manifest_sha256": HEX_E,
    }


def valid_gate() -> dict:
    return {
        "schema_version": 1,
        "task_id": "XQ-M1-CORE-001",
        "task_pack_sha256": HEX_A,
        "epic_contract_sha256": HEX_B,
        "base_commit": "base123",
        "result_commit": "result456",
        "changed_files": ["IMPLEMENTATION_WORKSPACE/src/core/XQDataNode.h"],
        "allowed_path_check": {"passed": True, "violations": []},
        "workspace_clean_before": True,
        "workspace_clean_after": True,
        "commands_reexecuted": ["COMMAND-REQ-XQ-M1-L0-CORE"],
        "exit_codes": [0],
        "tests_observed": ["L0 core identity"],
        "test_integrity_check": {"passed": True, "notes": []},
        "forbidden_scan": {"passed": True, "findings": []},
        "result_artifact_hashes": [HEX_F],
        "decision": "accepted",
        "rework_reason": None,
        "escalation_reason": None,
        "dependency_contract_sha256": HEX_C,
        "implementation_dependency_lock_sha256": HEX_D,
        "dependency_lock_sha256": HEX_D,
        "toolchain_manifest_sha256": HEX_E,
    }


def runtime_projection(events: list[dict] | None = None) -> dict:
    return {"schema_version": 1, "events": events or []}


def completion_projection(
    *,
    task_results: list[dict] | None = None,
    gate_results: list[dict] | None = None,
    epic_reviews: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "task_results": task_results or [],
        "gate_results": gate_results or [],
        "epic_reviews": epic_reviews or [],
    }


def write_full_inputs(tmp_path: Path, runtime: dict, completion: dict, workspace: dict) -> tuple[Path, Path, Path]:
    runtime_path = tmp_path / "runtime.json"
    completion_path = tmp_path / "completion.json"
    workspace_path = tmp_path / "workspace.json"
    write_json(runtime_path, runtime)
    write_json(completion_path, completion)
    write_json(workspace_path, workspace)
    return runtime_path, completion_path, workspace_path


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda gate: gate["allowed_path_check"].update({"passed": False}), "gate-allowed-path-check-failed"),
        (lambda gate: gate.update({"workspace_clean_before": False}), "gate-workspace-not-clean-before"),
        (lambda gate: gate.update({"workspace_clean_after": False}), "gate-workspace-not-clean-after"),
        (lambda gate: gate.update({"exit_codes": [1]}), "gate-command-exit-nonzero"),
        (lambda gate: gate["test_integrity_check"].update({"passed": False}), "gate-test-integrity-failed"),
        (lambda gate: gate["forbidden_scan"].update({"passed": False}), "gate-forbidden-scan-failed"),
        (lambda gate: gate.update({"tests_observed": []}), "gate-tests-observed-missing"),
        (lambda gate: gate.update({"result_artifact_hashes": []}), "gate-artifact-hash-missing"),
    ],
)
def test_accepted_gate_semantic_failures_are_rejected(mutator, reason) -> None:
    gate = valid_gate()
    mutator(gate)

    ok, reasons = projection.valid_gate(task_definition(), workspace_projection(), gate, valid_task_result())

    assert ok is False
    assert reason in reasons


def test_only_fully_valid_accepted_gate_is_valid() -> None:
    ok, reasons = projection.valid_gate(task_definition(), workspace_projection(), valid_gate(), valid_task_result())

    assert ok is True
    assert reasons == []


def test_missing_expected_hash_is_not_accepted() -> None:
    result = valid_task_result()
    result.pop("dependency_lock_sha256")

    ok, reasons = projection.valid_task_result(task_definition(), workspace_projection(), result)

    assert ok is False
    assert "missing-dependency_lock_sha256" in reasons


def test_full_projection_rejects_unknown_runtime_field(tmp_path: Path) -> None:
    runtime, completion, workspace = write_full_inputs(
        tmp_path,
        {
            "schema_version": 1,
            "events": [
                {
                    "event_id": "e1",
                    "task_id": "PR-M0-001",
                    "event_type": "task_started",
                    "event_time": "2026-06-20T00:00:00+00:00",
                    "extra": "not allowed",
                }
            ],
        },
        completion_projection(),
        workspace_projection(),
    )

    with pytest.raises(projection.ProjectionError, match="runtime"):
        projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)


def test_full_projection_rejects_duplicate_event_id(tmp_path: Path) -> None:
    event = {
        "event_id": "dup",
        "task_id": "PR-M0-001",
        "event_type": "task_claimed",
        "event_time": "2026-06-20T00:00:00+00:00",
    }
    runtime, completion, workspace = write_full_inputs(
        tmp_path,
        runtime_projection([event, {**event, "task_id": "PR-M1-001"}]),
        completion_projection(),
        workspace_projection(),
    )

    with pytest.raises(projection.ProjectionError, match="duplicate event_id dup"):
        projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)


def test_projection_loads_task_pack_issuance_status() -> None:
    snapshots = projection.build_snapshots(definitions_only=True)
    task = next(item for item in snapshots["tasks.json"]["tasks"] if item["task_id"] == "XQ-M1-CORE-001")

    assert task["task_pack_path"] == "docs/contracts/task-packs/XQ-M1-CORE-001.draft.yaml"
    assert task["issuance_status"] == "draft"
    assert task["execution_ready"] is False
    assert task["base_commit"] is None


def test_selector_uses_projected_issuance_status_not_task_pack_issued() -> None:
    tasks = [
        {
            "id": "ready-impl",
            "task_kind": "implementation",
            "status": "ready-for-ledger-review",
            "decision_state": "approved",
            "claimability_rules": ["Task Pack must be issued"],
            "issuance_status": "issued",
            "execution_ready": True,
            "task_pack_path": "docs/contracts/task-packs/T.draft.yaml",
            "base_commit": "base123",
            "rollback_point": "rollback123",
            "worktree_binding": "TASK_WORKTREE",
            "task_pack_hash_valid": True,
            "epic_contract_status": "approved",
        }
    ]

    explanation = explain_selection(tasks)

    assert explanation["selected"]["id"] == "ready-impl"


def test_draft_task_pack_is_not_claimable() -> None:
    tasks = [
        {
            "id": "draft-impl",
            "task_kind": "implementation",
            "status": "ready-for-ledger-review",
            "decision_state": "approved",
            "claimability_rules": ["Task Pack must be issued"],
            "issuance_status": "draft",
            "execution_ready": False,
        }
    ]

    explanation = explain_selection(tasks)

    assert explanation["selected"] is None
    assert "task pack is draft" in explanation["skipped_tasks"][0]["blockers"]


def test_issued_task_pack_wrong_hash_is_not_claimable() -> None:
    tasks = [
        {
            "id": "bad-hash-impl",
            "task_kind": "implementation",
            "status": "ready-for-ledger-review",
            "decision_state": "approved",
            "task_pack_path": "docs/contracts/task-packs/T.issued.yaml",
            "task_pack_schema_valid": True,
            "issuance_status": "issued",
            "execution_ready": True,
            "base_commit": "base123",
            "rollback_point": "rollback123",
            "worktree_binding": "TASK_WORKTREE",
            "task_pack_hash_valid": False,
            "epic_contract_status": "approved",
        }
    ]

    explanation = explain_selection(tasks)

    assert explanation["selected"] is None
    assert "task pack hash mismatch" in explanation["skipped_tasks"][0]["blockers"]


def test_full_preflight_without_private_inputs_fails() -> None:
    assert preflight_plan.main(["--full"]) != 0


def test_definitions_only_generated_at_ignores_git_head_time(monkeypatch) -> None:
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    monkeypatch.setattr(projection, "source_commit_time", lambda: "2999-01-01T00:00:00+00:00")

    snapshots = projection.build_snapshots(definitions_only=True)

    assert snapshots["tasks.json"]["metadata"]["generated_at"] == "1970-01-01T00:00:00+00:00"


def test_full_projection_uses_latest_valid_input_time_with_timezones(tmp_path: Path) -> None:
    runtime, completion, workspace = write_full_inputs(
        tmp_path,
        runtime_projection(
            [
                {
                    "event_id": "e1",
                    "task_id": "PR-M0-001",
                    "event_type": "task_started",
                    "event_time": "2026-06-20T08:00:00+08:00",
                }
            ]
        ),
        completion_projection(),
        {**workspace_projection(), "reconciled_at": "2026-06-20T01:00:00+00:00"},
    )

    snapshots = projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)

    assert snapshots["tasks.json"]["metadata"]["generated_at"] == "2026-06-20T01:00:00+00:00"


def test_invalid_full_projection_time_is_rejected(tmp_path: Path) -> None:
    runtime, completion, workspace = write_full_inputs(
        tmp_path,
        runtime_projection(
            [
                {
                    "event_id": "e1",
                    "task_id": "PR-M0-001",
                    "event_type": "task_started",
                    "event_time": "not-a-time",
                }
            ]
        ),
        completion_projection(),
        workspace_projection(),
    )

    with pytest.raises(projection.ProjectionError, match="invalid timestamp"):
        projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)


def test_completed_plan_task_does_not_approve_contract() -> None:
    milestones = projection.aggregate_milestones(
        [
            {
                "id": "PR-M0-001",
                "task_id": "PR-M0-001",
                "task_kind": "plan-contract",
                "plan_rewrite_milestone": "PR-M0",
                "status": "completed",
            }
        ]
    )

    assert milestones["PR-M0"]["contract_status"] != "approved"
    assert milestones["PR-M0"]["contract_readiness_status"] in {"ready-for-approval", "in-progress"}
    assert milestones["PR-M0"]["plan_acceptance_status"] == "not-run"


def test_one_completed_task_does_not_complete_multi_task_milestone() -> None:
    milestones = projection.aggregate_milestones(
        [
            {
                "id": "a",
                "task_id": "a",
                "task_kind": "implementation",
                "product_milestone": "XQ-M1",
                "epic_id": "E",
                "required_for_epic": True,
                "status": "completed",
            },
            {
                "id": "b",
                "task_id": "b",
                "task_kind": "implementation",
                "product_milestone": "XQ-M1",
                "epic_id": "E",
                "required_for_epic": True,
                "status": "ready-for-ledger-review",
            },
        ]
    )

    assert milestones["XQ-M1"]["implementation_status"] == "in-progress"


def test_epic_review_before_required_tasks_complete_is_rejected_in_projection(tmp_path: Path, monkeypatch) -> None:
    task_a = {
        "task_id": "TASK-A",
        "task_kind": "implementation",
        "required_for_epic": True,
        "epic_id": "EPIC",
        "epic_contract_status": "approved",
        "epic_contract_sha256": HEX_B,
        "base_commit": "base123",
        "task_pack_path": "docs/contracts/task-packs/TASK-A.issued.yaml",
        "task_pack_schema_valid": True,
        "computed_task_pack_sha256": HEX_A,
        "declared_task_pack_sha256": HEX_A,
        "task_pack_hash_valid": True,
        "issuance_status": "issued",
        "execution_ready": True,
        "rollback_point": "rollback",
        "worktree_binding": "TASK_WORKTREE",
        "task_pack_sha256": HEX_A,
        "dependency_contract_sha256": HEX_C,
        "implementation_dependency_lock_sha256": HEX_D,
        "dependency_lock_sha256": HEX_D,
        "toolchain_manifest_sha256": HEX_E,
    }
    task_b = {**task_a, "task_id": "TASK-B"}
    projected = [
        {
            **task_a,
            "id": "TASK-A",
            "status": "completed",
            "stale_reasons": [],
            "acceptance_evidence": "none",
            "runtime_projection": "projected",
        },
        {
            **task_b,
            "id": "TASK-B",
            "status": "ready-for-ledger-review",
            "stale_reasons": [],
            "acceptance_evidence": "none",
            "runtime_projection": "projected",
        },
    ]
    completion = completion_projection(
        epic_reviews=[
            {
                "schema_version": 1,
                "epic_id": "EPIC",
                "epic_contract_sha256": HEX_B,
                "review_base_commit": "base123",
                "review_head_commit": "head456",
                "required_outcomes": ["outcome"],
                "architecture_constraints": ["constraint"],
                "acceptance_evidence": ["evidence"],
                "cross_task_integration_findings": [],
                "unresolved_risks": [],
                "contract_defects": [],
                "decision": "accepted",
                "required_repairs": [],
                "dependency_lock_sha256": HEX_D,
                "toolchain_manifest_sha256": HEX_E,
            }
        ]
    )

    projection.apply_full_projection(
        projected,
        [task_a, task_b],
        runtime_projection(),
        completion,
        workspace_projection(),
    )

    task = next(item for item in projected if item["task_id"] == "TASK-A")
    assert task["acceptance_evidence"] == "not-passed"
    assert "epic-review-before-required-tasks-complete" in task["stale_reasons"]


def test_canonical_hash_preserves_array_order_and_sorts_object_keys() -> None:
    assert projection.hash_data({"b": 2, "a": 1}) == projection.hash_data({"a": 1, "b": 2})
    assert projection.hash_data({"commands": ["configure", "build", "test"]}) != projection.hash_data(
        {"commands": ["test", "build", "configure"]}
    )
    assert projection.hash_data({"workflow_steps": ["one", "two"]}) != projection.hash_data({"workflow_steps": ["two", "one"]})


def test_task_pack_command_order_changes_hash() -> None:
    pack = {
        "schema_version": 1,
        "task_id": "T",
        "epic_id": "E",
        "task_pack_sha256": None,
        "commands": [{"command": "configure"}, {"command": "build"}, {"command": "test"}],
    }
    reordered = {**pack, "commands": list(reversed(pack["commands"]))}

    assert projection.canonical_task_pack_hash(pack) != projection.canonical_task_pack_hash(reordered)


def test_epic_contract_content_hash_ignores_runtime_fields_and_path() -> None:
    contract = {"schema_version": 1, "epic_id": "E", "required_outcomes": ["a", "b"]}
    with_runtime = {**contract, "_path": "docs/contracts/epics/E.yaml", "_computed_sha256": HEX_A}
    changed = {**contract, "required_outcomes": ["b", "a"]}

    assert projection.canonical_contract_hash(contract) == projection.canonical_contract_hash(with_runtime)
    assert projection.canonical_contract_hash(contract) != projection.canonical_contract_hash(changed)


def test_approval_record_self_hash_and_tamper_detection() -> None:
    approval = {
        "schema_version": 1,
        "epic_id": "E",
        "epic_contract_sha256": HEX_B,
        "reviewer_role": "Codex A",
        "reviewed_at": "2026-06-20T00:00:00+00:00",
        "decision": "approved",
        "architecture_findings": ["ok"],
        "unresolved_decisions": [],
        "required_repairs": [],
        "approval_record_sha256": None,
    }
    computed = projection.canonical_approval_record_hash(approval)
    approval["approval_record_sha256"] = computed
    tampered = {**approval, "architecture_findings": ["changed"]}

    assert projection.canonical_approval_record_hash(approval) == computed
    assert projection.canonical_approval_record_hash(tampered) != approval["approval_record_sha256"]


def test_valid_approval_record_uses_contract_content_hash(tmp_path: Path, monkeypatch) -> None:
    contract = {"epic_id": "E", "decision_state": "approved"}
    contract_hash = projection.canonical_contract_hash(contract)
    approval = {
        "schema_version": 1,
        "epic_id": "E",
        "epic_contract_sha256": contract_hash,
        "reviewer_role": "Codex A",
        "reviewed_at": "2026-06-20T00:00:00+00:00",
        "decision": "approved",
        "architecture_findings": ["architecture reviewed"],
        "unresolved_decisions": [],
        "required_repairs": [],
        "approval_record_sha256": None,
    }
    approval["approval_record_sha256"] = projection.canonical_approval_record_hash(approval)
    approval_path = tmp_path / "approval.yaml"
    write_json(approval_path, approval)
    monkeypatch.setattr(projection, "ROOT", tmp_path)
    contract.update(
        {
            "_computed_sha256": contract_hash,
            "approval_record": {
                "record_type": "codex-a-epic-contract-approval",
                "record_sha256": approval["approval_record_sha256"],
                "record_path": "approval.yaml",
            },
        }
    )

    assert projection.approval_record_valid(contract)


def accepted_review(**overrides) -> dict:
    review = {
        "schema_version": 1,
        "epic_id": "EPIC",
        "epic_contract_sha256": HEX_B,
        "review_base_commit": "base123",
        "review_head_commit": "head456",
        "required_outcomes": ["outcome"],
        "architecture_constraints": ["constraint"],
        "acceptance_evidence": ["evidence"],
        "cross_task_integration_findings": [],
        "unresolved_risks": [],
        "contract_defects": [],
        "decision": "accepted",
        "required_repairs": [],
        "dependency_lock_sha256": HEX_D,
        "toolchain_manifest_sha256": HEX_E,
    }
    review.update(overrides)
    return review


def test_accepted_review_with_blocking_risk_is_rejected() -> None:
    review = accepted_review(
        unresolved_risks=[
            {
                "severity": "blocking",
                "description": "cannot accept",
                "evidence": "missing required path",
                "owner": "Codex A",
            }
        ]
    )

    ok, reasons = projection.valid_epic_review(
        {**task_definition(), "epic_id": "EPIC"},
        workspace_projection(),
        review,
    )

    assert ok is False
    assert "epic-review-blocking-risk" in reasons


def test_accepted_review_with_non_blocking_risk_is_allowed() -> None:
    review = accepted_review(
        unresolved_risks=[
            {
                "severity": "non-blocking",
                "description": "follow later",
                "follow_up": "track in next milestone",
                "owner": "Codex A",
                "non_blocking_rationale": "does not affect current acceptance contract",
            }
        ]
    )

    ok, reasons = projection.valid_epic_review(
        {**task_definition(), "epic_id": "EPIC"},
        workspace_projection(),
        review,
    )

    assert ok is True
    assert reasons == []


def test_epic_review_head_and_task_commit_must_match_workspace() -> None:
    required = [{"task_id": "T1", "status": "completed"}]
    gates = {"T1": {"result_commit": "taskcommit"}}
    workspace = {
        "epic_id": "EPIC",
        "epic_base_commit": "base123",
        "epic_head_commit": "head456",
        "integrated_task_commits": {"T1": "taskcommit"},
    }

    assert projection.epic_review_integration_reasons(accepted_review(), workspace, required, gates) == []
    assert "epic-review-head-mismatch" in projection.epic_review_integration_reasons(
        accepted_review(review_head_commit="otherhead"), workspace, required, gates
    )
    assert "epic-review-base-mismatch" in projection.epic_review_integration_reasons(
        accepted_review(review_base_commit="otherbase"), workspace, required, gates
    )
    assert "required-task-commit-missing" in projection.epic_review_integration_reasons(
        accepted_review(), {**workspace, "integrated_task_commits": {}}, required, gates
    )
    assert "required-task-commit-mismatch" in projection.epic_review_integration_reasons(
        accepted_review(), {**workspace, "integrated_task_commits": {"T1": "other"}}, required, gates
    )


@pytest.mark.parametrize("implementation_status", ["not-started", "in-progress", "blocked"])
def test_product_acceptance_requires_completed_implementation(implementation_status: str) -> None:
    status_to_task_status = {
        "not-started": "ready-for-ledger-review",
        "in-progress": "in-progress",
        "blocked": "blocked",
    }
    milestones = projection.aggregate_milestones(
        [
            {
                "id": "impl",
                "task_id": "impl",
                "task_kind": "implementation",
                "product_milestone": "XQ-M1",
                "epic_id": "EPIC",
                "required_for_epic": True,
                "status": status_to_task_status[implementation_status],
                "epic_contract_status": "approved",
                "acceptance_evidence": "codex-a-epic-review-accepted",
                "stale_reasons": [],
            }
        ]
    )

    assert milestones["XQ-M1"]["implementation_status"] == implementation_status
    assert milestones["XQ-M1"]["acceptance_status"] != "passed"


def test_product_acceptance_passes_only_after_all_required_tasks_complete() -> None:
    milestones = projection.aggregate_milestones(
        [
            {
                "id": "impl",
                "task_id": "impl",
                "task_kind": "implementation",
                "product_milestone": "XQ-M1",
                "epic_id": "EPIC",
                "required_for_epic": True,
                "status": "completed",
                "epic_contract_status": "approved",
                "acceptance_evidence": "codex-a-epic-review-accepted",
                "stale_reasons": [],
            }
        ]
    )

    assert milestones["XQ-M1"]["implementation_status"] == "completed"
    assert milestones["XQ-M1"]["acceptance_status"] == "passed"
