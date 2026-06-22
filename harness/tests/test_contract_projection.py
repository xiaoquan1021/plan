#!/usr/bin/env python3
"""Tests for contract projection, schema validation, and public preflight."""

from __future__ import annotations

import filecmp
import json
import sys
from pathlib import Path

import pytest


TOOLS_DIR = Path(__file__).resolve().parents[1]
ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import generate_snapshots  # noqa: E402
import migrate_legacy_ledger  # noqa: E402
import projection  # noqa: E402
import validate_public_contracts  # noqa: E402
import validate_schema  # noqa: E402
import validate_task_graph  # noqa: E402
import preflight_plan  # noqa: E402


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def runtime_projection(task_id: str = "PR-M0-001", *, status: str = "in-progress") -> dict:
    return {
        "schema_version": 1,
        "events": [
            {
                "event_id": "e1",
                "task_id": task_id,
                "event_type": "task_started",
                "event_time": "2026-06-20T00:00:00+00:00",
                "status": status,
                "payload": {"private_path": "C:/Users/OCEAN/private/raw.log"},
            }
        ],
    }


def workspace_projection() -> dict:
    return {
        "schema_version": 1,
        "workspace_state": "baseline-frozen",
        "base_commit": "abcdef1234567890",
        "rollback_point": "rollback123",
        "implementation_dependency_lock_sha256": "d" * 64,
        "dependency_lock_sha256": "d" * 64,
        "toolchain_manifest_sha256": "e" * 64,
        "local_git_state": None,
    }


def completion_projection(*, include_gate: bool = True, include_review: bool = False) -> dict:
    task_result = {
        "schema_version": 1,
        "task_id": "XQ-M1-CORE-001",
        "task_pack_sha256": "a" * 64,
        "epic_contract_sha256": "e" * 64,
        "base_commit": "abcdef1234567890",
        "result_commit": "fedcba9876543210",
        "changed_files": ["IMPLEMENTATION_WORKSPACE/src/core/XQDataNode.h"],
        "commands_run": ["COMMAND-REQ-XQ-M1-L0-CORE"],
        "test_results": ["passed"],
        "artifacts": ["artifact-a"],
        "unresolved_issues": [],
        "decision_request": "gate-required",
        "decision": "completed",
        "dependency_lock_sha256": "d" * 64,
        "toolchain_manifest_sha256": "e" * 64,
    }
    gate = {
        "schema_version": 1,
        "task_id": "XQ-M1-CORE-001",
        "task_pack_sha256": "a" * 64,
        "epic_contract_sha256": "e" * 64,
        "base_commit": "abcdef1234567890",
        "result_commit": "fedcba9876543210",
        "changed_files": ["IMPLEMENTATION_WORKSPACE/src/core/XQDataNode.h"],
        "allowed_path_check": {"passed": True, "violations": []},
        "workspace_clean_before": True,
        "workspace_clean_after": True,
        "commands_reexecuted": ["COMMAND-REQ-XQ-M1-L0-CORE"],
        "exit_codes": [0],
        "tests_observed": ["L0 core identity"],
        "test_integrity_check": {"passed": True, "notes": []},
        "forbidden_scan": {"passed": True, "findings": []},
        "result_artifact_hashes": ["a" * 64],
        "decision": "accepted",
        "rework_reason": None,
        "escalation_reason": None,
        "dependency_lock_sha256": "d" * 64,
        "toolchain_manifest_sha256": "e" * 64,
    }
    review = {
        "schema_version": 1,
        "epic_id": "XQ-M1-CORE-DATA",
        "epic_contract_sha256": "e" * 64,
        "review_base_commit": "abcdef1234567890",
        "review_head_commit": "fedcba9876543210",
        "required_outcomes": ["core identity"],
        "architecture_constraints": ["no external public graph"],
        "acceptance_evidence": ["L0 core accepted"],
        "cross_task_integration_findings": [],
        "unresolved_risks": [],
        "contract_defects": [],
        "decision": "accepted",
        "required_repairs": [],
        "dependency_lock_sha256": "d" * 64,
        "toolchain_manifest_sha256": "e" * 64,
    }
    return {
        "schema_version": 1,
        "task_results": [task_result],
        "gate_results": [gate] if include_gate else [],
        "epic_reviews": [review] if include_review else [],
    }


def generated_task(snapshots: dict, task_id: str) -> dict:
    return next(task for task in snapshots["tasks.json"]["tasks"] if task["task_id"] == task_id)


def test_schema_and_task_graph_valid() -> None:
    assert validate_schema.main([]) == 0
    assert validate_task_graph.main() == 0


def test_definitions_only_never_completes_implementation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    snapshots = projection.build_snapshots(definitions_only=True)
    assert snapshots["task-runtime-summary.json"]["runtime_projection"] == "none"
    for task in snapshots["tasks.json"]["tasks"]:
        if task["task_kind"] == "implementation":
            assert task["implementation_evidence"] == "none"
            assert task["status"] != "completed"


def test_runtime_merge_projects_claimed_and_in_progress(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    write_json(runtime, runtime_projection("PR-M0-001", status="in-progress"))
    write_json(completion, {"schema_version": 1, "task_results": [], "gate_results": [], "epic_reviews": []})
    write_json(workspace, workspace_projection())
    snapshots = projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)
    task = generated_task(snapshots, "PR-M0-001")
    assert task["status"] == "in-progress"
    assert task["runtime_projection"] == "projected"


def test_missing_b_gate_result_cannot_complete_implementation(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    write_json(runtime, {"schema_version": 1, "events": []})
    write_json(completion, completion_projection(include_gate=False))
    write_json(workspace, workspace_projection())
    snapshots = projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)
    task = generated_task(snapshots, "XQ-M1-CORE-001")
    assert task["status"] != "completed"
    assert "missing-b-gate-result" in task["stale_reasons"]


def test_valid_b_gate_controls_implementation_completion(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    write_json(runtime, {"schema_version": 1, "events": []})
    write_json(completion, completion_projection(include_gate=True))
    write_json(workspace, workspace_projection())
    snapshots = projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)
    task = generated_task(snapshots, "XQ-M1-CORE-001")
    assert task["status"] != "completed"
    assert task["implementation_evidence"] == "incomplete"
    assert "task-pack-draft" in task["stale_reasons"]
    assert "epic-contract-not-approved" in task["stale_reasons"]


def test_missing_a_epic_review_cannot_pass_acceptance(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    write_json(runtime, {"schema_version": 1, "events": []})
    write_json(completion, completion_projection(include_gate=True, include_review=False))
    write_json(workspace, workspace_projection())
    snapshots = projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)
    task = generated_task(snapshots, "XQ-M1-CORE-001")
    assert task["acceptance_evidence"] == "not-passed"


def test_valid_a_epic_review_controls_acceptance(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    write_json(runtime, {"schema_version": 1, "events": []})
    write_json(completion, completion_projection(include_gate=True, include_review=True))
    write_json(workspace, workspace_projection())
    snapshots = projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)
    task = generated_task(snapshots, "XQ-M1-CORE-001")
    assert task["acceptance_evidence"] == "not-passed"
    assert "epic-contract-not-approved" in task["stale_reasons"]
    assert "epic_contract_sha256-changed" in task["stale_reasons"]


def test_hash_change_marks_result_stale(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    data = completion_projection(include_gate=True)
    data["gate_results"][0]["dependency_lock_sha256"] = "f" * 64
    write_json(runtime, {"schema_version": 1, "events": []})
    write_json(completion, data)
    write_json(workspace, workspace_projection())
    snapshots = projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)
    task = generated_task(snapshots, "XQ-M1-CORE-001")
    assert task["status"] == "stale-completion"
    assert "dependency_lock_sha256-changed" in task["stale_reasons"]


def test_unknown_task_id_is_rejected(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    write_json(runtime, runtime_projection("UNKNOWN-TASK", status="claimed"))
    write_json(completion, {"schema_version": 1, "task_results": [], "gate_results": [], "epic_reviews": []})
    write_json(workspace, workspace_projection())
    with pytest.raises(projection.ProjectionError):
        projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace)


def test_private_path_redaction_and_deterministic_bytes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    runtime = tmp_path / "runtime.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    write_json(runtime, runtime_projection("PR-M0-001", status="claimed"))
    write_json(completion, {"schema_version": 1, "task_results": [], "gate_results": [], "epic_reviews": []})
    write_json(workspace, workspace_projection())
    first = tmp_path / "first"
    second = tmp_path / "second"
    projection.write_snapshots(projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace), first)
    projection.write_snapshots(projection.build_snapshots(runtime_events=runtime, completion_records=completion, workspace_report=workspace), second)
    for name in projection.SNAPSHOT_NAMES:
        assert filecmp.cmp(first / name, second / name, shallow=False), name
    combined = "\n".join((first / name).read_text(encoding="utf-8") for name in projection.SNAPSHOT_NAMES)
    assert "C:/Users/OCEAN" not in combined
    assert "PRIVATE_PATH_REDACTED" in combined


def test_input_ordering_does_not_change_output(tmp_path: Path) -> None:
    runtime_a = tmp_path / "runtime-a.json"
    runtime_b = tmp_path / "runtime-b.json"
    completion = tmp_path / "completion.json"
    workspace = tmp_path / "workspace.json"
    events = [
        {"event_id": "b", "task_id": "PR-M0-001", "event_type": "task_claimed", "event_time": "2026-06-20T00:00:00+00:00", "status": "claimed"},
        {"event_id": "a", "task_id": "PR-M0-001", "event_type": "task_started", "event_time": "2026-06-20T00:01:00+00:00", "status": "in-progress"},
    ]
    write_json(runtime_a, {"schema_version": 1, "events": events})
    write_json(runtime_b, {"schema_version": 1, "events": list(reversed(events))})
    write_json(completion, {"schema_version": 1, "task_results": [], "gate_results": [], "epic_reviews": []})
    write_json(workspace, workspace_projection())
    first = projection.build_snapshots(runtime_events=runtime_a, completion_records=completion, workspace_report=workspace)
    second = projection.build_snapshots(runtime_events=runtime_b, completion_records=completion, workspace_report=workspace)
    assert first == second


def test_snapshot_check_passes_for_current_projection(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert generate_snapshots.main(["--definitions-only", "--check"]) == 0


def test_migration_uses_synthetic_legacy_input_and_is_deterministic(tmp_path: Path) -> None:
    legacy = ROOT / "harness/tests/fixtures/synthetic-legacy-tasks.json"
    definition = ROOT / "harness/tests/fixtures/synthetic-migration.yaml"
    first = migrate_legacy_ledger.build_report(legacy, definition)
    second = migrate_legacy_ledger.build_report(legacy, definition)
    assert first == second
    assert first["legacy_input"] == "harness/tests/fixtures/synthetic-legacy-tasks.json"
    assert first["migration_definition"] == "harness/tests/fixtures/synthetic-migration.yaml"
    assert first["unmapped_count"] == 1
    assert first["stale_completion_count"] == 1
    assert first["requires_private_reconciliation_count"] == 1
    assert first["legacy_completed_inherited_as_implementation_completed"] is False


def test_migration_report_paths_are_stable_for_relative_and_absolute_inputs() -> None:
    relative_legacy = Path("harness/tests/fixtures/synthetic-legacy-tasks.json")
    relative_definition = Path("harness/tests/fixtures/synthetic-migration.yaml")
    absolute_legacy = ROOT / relative_legacy
    absolute_definition = ROOT / relative_definition

    relative_report = migrate_legacy_ledger.build_report(relative_legacy, relative_definition)
    absolute_report = migrate_legacy_ledger.build_report(absolute_legacy, absolute_definition)

    assert relative_report == absolute_report
    assert relative_report["legacy_input"] == "harness/tests/fixtures/synthetic-legacy-tasks.json"
    assert relative_report["migration_definition"] == "harness/tests/fixtures/synthetic-migration.yaml"


def test_migration_check_detects_drift(tmp_path: Path) -> None:
    legacy = ROOT / "harness/tests/fixtures/synthetic-legacy-tasks.json"
    definition = ROOT / "harness/tests/fixtures/synthetic-migration.yaml"
    report = tmp_path / "migration-report.json"
    write_json(report, {"wrong": True})
    result = migrate_legacy_ledger.main([
        "--legacy-input", str(legacy),
        "--migration-definition", str(definition),
        "--output-report", str(report),
        "--check",
    ])
    assert result == 1


def test_public_contract_scan_valid() -> None:
    assert validate_public_contracts.main() == 0


def test_public_preflight_runs_without_private_data() -> None:
    assert preflight_plan.main(["--public"]) == 0


def test_full_preflight_requires_all_private_inputs() -> None:
    assert preflight_plan.main(["--full", "--runtime-events", "x.json"]) != 0
