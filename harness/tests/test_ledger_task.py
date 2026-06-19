#!/usr/bin/env python3
"""Tests for the XQ ledger task harness."""

from __future__ import annotations

import inspect
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from evidence_validator import CompletionRecordError, validate_completion_record  # noqa: E402
import lease_manager as lease_module  # noqa: E402
from lease_manager import LeaseError, LeaseManager  # noqa: E402
from ledger_models import EVENT_TASK_COMPLETED, EVENT_TASK_FAILED, EVENT_TASK_REOPENED, file_sha256, sha256_text, utc_now  # noqa: E402
import ledger_task  # noqa: E402
from command_runner import build_command_entry, run_harness_command  # noqa: E402
import task_event_store as event_module  # noqa: E402
from audit_xq_zip_analysis import authoritative_state, test_plan_exit_semantics_violations as plan_exit_semantics_violations  # noqa: E402
from task_event_store import EventStore, status_counts  # noqa: E402
from task_selector import build_task_graph, dependency_violations, explain_selection  # noqa: E402


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_lease(task_id: str, *, actor: str = "codex", session_id: str = "s") -> dict:
    timestamp = utc_now()
    return {
        "schema_version": 1,
        "task_id": task_id,
        "actor": actor,
        "session_id": session_id,
        "claimed_at": timestamp,
        "heartbeat_at": timestamp,
        "lease_seconds": 3600,
    }


def make_task(tmp_path: Path, task_id: str = "00-governance-00-source-boundary-and-rules") -> tuple[dict, Path]:
    source = tmp_path / "plans/xq-integrated-rebuild/00-governance/00-source-boundary-and-rules.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "\n".join(
            [
                "# Source Boundary",
                "",
                "## Purpose",
                "Keep source boundaries clear.",
                "",
                "## Test Plan",
                "- Run ledger preflight.",
                "",
                "## Acceptance",
                "- Boundary rules remain enforced.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    task = {
        "id": task_id,
        "source_md": "plans/xq-integrated-rebuild/00-governance/00-source-boundary-and-rules.md",
        "role": "governance",
        "status": "ready-for-ledger-review",
        "missing_required_sections": [],
        "unchecked_step_count": 1,
        "checked_step_count": 0,
        "verification_source": "Test Plan",
        "evidence_status": "unverified",
    }
    return task, source


def make_record(
    path: Path,
    task: dict,
    source: Path,
    *,
    overall_status: str = "passed",
    acceptance_item: str = "Boundary rules remain enforced.",
    source_section: str | None = "Acceptance",
    acceptance_status: str | None = None,
    command_entry: dict | None = None,
    acceptance_items: list[dict] | None = None,
    actor: str = "codex",
    session_id: str = "test-session",
) -> None:
    status = acceptance_status or overall_status
    acceptance = {
        "item": acceptance_item,
        "status": status,
        "evidence": "preflight command output",
    }
    if source_section is not None:
        acceptance["source_section"] = source_section
        acceptance["source_item_sha256"] = sha256_text(acceptance_item)
    commands = [
        command_entry
        if command_entry is not None
        else {
            "argv": ["python3", "-m", "py_compile", "ledger_task.py"],
            "cwd": str(path.parent),
            "started_at": utc_now(),
            "ended_at": utc_now(),
            "exit_code": 0 if overall_status == "passed" else 1,
            "stdout_excerpt": "",
            "stderr_excerpt": "",
        }
    ]
    write_json(
        path,
        {
            "schema_version": 1,
            "task_id": task["id"],
            "source_md": task["source_md"],
            "source_md_sha256": file_sha256(source),
            "created_at": utc_now(),
            "actor": actor,
            "session_id": session_id,
            "commands": commands,
            "acceptance": acceptance_items or [acceptance],
            "overall_status": overall_status,
        },
    )


def make_runner_command_entry(
    tmp_path: Path,
    task: dict,
    *,
    argv: list[str] | None = None,
    command_id: str | None = None,
    exit_code: int = 0,
    actor: str = "codex",
    session_id: str = "test-session",
) -> dict:
    safe_command_id = command_id or f"cmd-{task['id']}"
    artifact = tmp_path / "private-evidence-dir/command-runs" / session_id / f"{safe_command_id}.json"
    started_at = utc_now()
    ended_at = utc_now()
    stdout_text = "ok\n" if exit_code == 0 else ""
    stderr_text = "" if exit_code == 0 else "failed\n"
    write_json(
        artifact,
        {
            "schema_version": 1,
            "artifact_type": "xq-ledger-command-run",
            "command_id": safe_command_id,
            "task_id": task["id"],
            "actor": actor,
            "session_id": session_id,
            "argv": argv or ["python3", "-m", "py_compile", "ledger_task.py"],
            "cwd": str(tmp_path),
            "started_at": started_at,
            "ended_at": ended_at,
            "exit_code": exit_code,
            "stdout_excerpt": stdout_text,
            "stderr_excerpt": stderr_text,
            "stdout_sha256": sha256_text(stdout_text),
            "stderr_sha256": sha256_text(stderr_text),
        },
    )
    return build_command_entry(artifact, root=tmp_path, tree_root=tmp_path)


def make_full_gate_items() -> list[dict]:
    return [
        {
            "item": "Run ledger preflight.",
            "source_section": "Test Plan",
            "source_item_sha256": sha256_text("Run ledger preflight."),
            "status": "passed",
            "evidence": "runner command captured the test-plan command",
        },
        {
            "item": "Boundary rules remain enforced.",
            "source_section": "Acceptance",
            "source_item_sha256": sha256_text("Boundary rules remain enforced."),
            "status": "passed",
            "evidence": "runner command and source review support the acceptance item",
        },
    ]


def make_command_summary(path: Path, *, exit_code: int = 0, command_entry: dict | None = None) -> None:
    command = command_entry or {
        "argv": ["python3", "-m", "py_compile", "ledger_task.py"],
        "cwd": str(path.parent),
        "started_at": utc_now(),
        "ended_at": utc_now(),
        "exit_code": exit_code,
    }
    write_json(
        path,
        {
            "schema_version": 1,
            "artifact_type": "xq-ledger-command-summary",
            "generated_by": "xq-ledger-command-runner",
            "task_id": command.get("task_id", "test-task"),
            "actor": command.get("actor", "codex"),
            "session_id": command.get("session_id", "test-session"),
            "commands": [command],
            "overall_status": "passed" if exit_code == 0 else "failed",
        },
    )


def fake_passing_record(cwd: Path | str) -> dict:
    return {
        "source_md_sha256": "a" * 64,
        "commands": [
            {
                "argv": ["python3", "-m", "py_compile", "ledger_task.py"],
                "cwd": str(cwd),
                "exit_code": 0,
            }
        ],
    }


def completion_payload(evidence: Path, command_summary: Path) -> dict:
    data = json.loads(evidence.read_text(encoding="utf-8"))
    return {
        "record_path": str(evidence),
        "record_sha256": file_sha256(evidence),
        "source_md_sha256": data["source_md_sha256"],
        "command_summary": str(command_summary),
        "command_summary_sha256": file_sha256(command_summary),
    }


def test_empty_event_log_preserves_baseline_counts() -> None:
    tasks = [
        {"id": "index", "source_md": "plans/xq-integrated-rebuild/README.md", "status": "not-executable-index"},
        {"id": "a", "source_md": "plans/xq-integrated-rebuild/00-governance/a.md", "status": "ready-for-ledger-review"},
        {"id": "b", "source_md": "plans/xq-integrated-rebuild/01-foundation/b.md", "status": "ready-for-ledger-review"},
    ]
    events = Path("/tmp/nonexistent-xq-ledger-test-events.jsonl")
    store = EventStore(events, tree_root=Path("/tmp/nonexistent-tree-root"), root=Path("/tmp/nonexistent-root"))
    derived = store.derive_tasks(tasks)
    counts = status_counts(derived["tasks"])

    assert counts["not-executable-index"] == 1
    assert counts["ready-for-ledger-review"] == 2


def test_harness_runner_creates_command_artifact_and_summary(tmp_path: Path) -> None:
    artifact = tmp_path / "private-evidence-dir/command-runs/s/task-a.json"
    summary = tmp_path / "private-evidence-dir/command-summaries/s/task-a.json"

    result = run_harness_command(
        task_id="task-a",
        actor="codex",
        session_id="s",
        argv=["python3", "-c", "print('runner-ok')"],
        cwd=tmp_path,
        artifact_path=artifact,
        command_summary_path=summary,
        root=tmp_path,
        tree_root=tmp_path,
    )

    artifact_data = json.loads(artifact.read_text(encoding="utf-8"))
    summary_data = json.loads(summary.read_text(encoding="utf-8"))
    assert result.command["command_id"] == artifact_data["command_id"]
    assert result.command["stdout_sha256"] == sha256_text("runner-ok\n")
    assert result.command["runner_artifact_sha256"] == file_sha256(artifact)
    assert summary_data["commands"][0] == result.command
    assert summary_data["overall_status"] == "passed"


def test_completion_requires_runner_backed_command_when_requested(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source)

    try:
        validate_completion_record(
            record,
            task=task,
            tree_root=tmp_path / "plans/xq-integrated-rebuild",
            root=tmp_path,
            require_runner_commands=True,
        )
    except CompletionRecordError as exc:
        assert "runner_artifact" in str(exc) or "command_id" in str(exc)
    else:
        raise AssertionError("completion record must bind runner artifacts when requested")


def test_completion_requires_all_acceptance_and_test_plan_items_when_requested(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    source.write_text(
        "\n".join(
            [
                "# Multi Gate",
                "",
                "## Test Plan",
                "- Run unit tests.",
                "- Run audit.",
                "",
                "## Acceptance",
                "- First acceptance.",
                "- Second acceptance.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    task["source_md_sha256"] = file_sha256(source)
    command_entry = make_runner_command_entry(tmp_path, task)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(
        record,
        task,
        source,
        acceptance_item="First acceptance.",
        command_entry=command_entry,
    )

    try:
        validate_completion_record(
            record,
            task=task,
            tree_root=tmp_path / "plans/xq-integrated-rebuild",
            root=tmp_path,
            require_runner_commands=True,
            require_completion_gate_coverage=True,
        )
    except CompletionRecordError as exc:
        assert "missing completion gate coverage" in str(exc)
    else:
        raise AssertionError("partial Acceptance/Test Plan coverage must not complete a task")


def test_completion_coverage_includes_fenced_test_plan_commands(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    source.write_text(
        "\n".join(
            [
                "# Fenced Test Plan",
                "",
                "## Test Plan",
                "```bash",
                "python3 harness/ledger_task.py preflight",
                "python3 harness/ledger_task.py validate-events",
                "```",
                "",
                "## Acceptance",
                "- Fenced test commands are covered.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    preflight_command = make_runner_command_entry(
        tmp_path,
        task,
        argv=["python3", "harness/ledger_task.py", "preflight"],
        command_id="cmd-preflight",
    )
    validate_events_command = make_runner_command_entry(
        tmp_path,
        task,
        argv=["python3", "harness/ledger_task.py", "validate-events"],
        command_id="cmd-validate-events",
    )
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(
        record,
        task,
        source,
        command_entry=preflight_command,
        acceptance_items=[
            {
                "item": "python3 harness/ledger_task.py preflight",
                "source_section": "Test Plan",
                "source_item_sha256": sha256_text(
                    "python3 harness/ledger_task.py preflight"
                ),
                "status": "passed",
                "evidence": "runner command captured the fenced test command",
            },
            {
                "item": "python3 harness/ledger_task.py validate-events",
                "source_section": "Test Plan",
                "source_item_sha256": sha256_text(
                    "python3 harness/ledger_task.py validate-events"
                ),
                "status": "passed",
                "evidence": "runner command captured the fenced test command",
            },
            {
                "item": "Fenced test commands are covered.",
                "source_section": "Acceptance",
                "source_item_sha256": sha256_text("Fenced test commands are covered."),
                "status": "passed",
                "evidence": "source acceptance is covered",
            },
        ],
    )
    evidence_data = json.loads(record.read_text(encoding="utf-8"))
    evidence_data["commands"].append(validate_events_command)
    write_json(record, evidence_data)

    validate_completion_record(
        record,
        task=task,
        tree_root=tmp_path / "plans/xq-integrated-rebuild",
        root=tmp_path,
        require_runner_commands=True,
        require_completion_gate_coverage=True,
    )


def test_completion_coverage_rejects_missing_fenced_test_plan_commands(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    source.write_text(
        "\n".join(
            [
                "# Fenced Test Plan",
                "",
                "## Test Plan",
                "```bash",
                "python3 harness/ledger_task.py preflight",
                "```",
                "",
                "## Acceptance",
                "- Fenced test commands are covered.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    command_entry = make_runner_command_entry(tmp_path, task)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(
        record,
        task,
        source,
        command_entry=command_entry,
        acceptance_items=[
            {
                "item": "Fenced test commands are covered.",
                "source_section": "Acceptance",
                "source_item_sha256": sha256_text("Fenced test commands are covered."),
                "status": "passed",
                "evidence": "source acceptance is covered",
            },
        ],
    )

    try:
        validate_completion_record(
            record,
            task=task,
            tree_root=tmp_path / "plans/xq-integrated-rebuild",
            root=tmp_path,
            require_runner_commands=True,
            require_completion_gate_coverage=True,
        )
    except CompletionRecordError as exc:
        assert "missing completion gate coverage" in str(exc)
    else:
        raise AssertionError("fenced Test Plan commands must be completion gates")


def test_fenced_test_plan_command_must_match_runner_argv(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    source.write_text(
        "\n".join(
            [
                "# Fenced Test Plan",
                "",
                "## Test Plan",
                "```bash",
                "python3 harness/ledger_task.py preflight",
                "```",
                "",
                "## Acceptance",
                "- Fenced test commands are covered.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    command_entry = make_runner_command_entry(
        tmp_path,
        task,
        argv=["python3", "-m", "py_compile", "ledger_task.py"],
    )
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(
        record,
        task,
        source,
        command_entry=command_entry,
        acceptance_items=[
            {
                "item": "python3 harness/ledger_task.py preflight",
                "source_section": "Test Plan",
                "source_item_sha256": sha256_text(
                    "python3 harness/ledger_task.py preflight"
                ),
                "status": "passed",
                "evidence": "runner command captured the fenced test command",
            },
            {
                "item": "Fenced test commands are covered.",
                "source_section": "Acceptance",
                "source_item_sha256": sha256_text("Fenced test commands are covered."),
                "status": "passed",
                "evidence": "source acceptance is covered",
            },
        ],
    )

    try:
        validate_completion_record(
            record,
            task=task,
            tree_root=tmp_path / "plans/xq-integrated-rebuild",
            root=tmp_path,
            require_runner_commands=True,
            require_completion_gate_coverage=True,
        )
    except CompletionRecordError as exc:
        assert "does not match any runner command argv" in str(exc)
    else:
        raise AssertionError("fenced Test Plan coverage must be bound to runner argv")


def test_fenced_test_plan_command_accepts_equivalent_runner_argv(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    source.write_text(
        "\n".join(
            [
                "# Fenced Test Plan",
                "",
                "## Test Plan",
                "```bash",
                "$ python3   harness/ledger_task.py   preflight",
                "```",
                "",
                "## Acceptance",
                "- Fenced test commands are covered.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    command_entry = make_runner_command_entry(
        tmp_path,
        task,
        argv=["python3", "harness/ledger_task.py", "preflight"],
    )
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    normalized_command = "python3 harness/ledger_task.py preflight"
    make_record(
        record,
        task,
        source,
        command_entry=command_entry,
        acceptance_items=[
            {
                "item": normalized_command,
                "source_section": "Test Plan",
                "source_item_sha256": sha256_text(normalized_command),
                "status": "passed",
                "evidence": "runner artifact argv matches the fenced test command",
            },
            {
                "item": "Fenced test commands are covered.",
                "source_section": "Acceptance",
                "source_item_sha256": sha256_text("Fenced test commands are covered."),
                "status": "passed",
                "evidence": "source acceptance is covered",
            },
        ],
    )

    validate_completion_record(
        record,
        task=task,
        tree_root=tmp_path / "plans/xq-integrated-rebuild",
        root=tmp_path,
        require_runner_commands=True,
        require_completion_gate_coverage=True,
    )


def test_event_hash_chain_detects_tampering(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_claimed",
        task_id=task["id"],
        actor="codex",
        session_id="s",
        payload={"lease": make_lease(task["id"])},
    )
    rows = events.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(rows[0])
    tampered["actor"] = "other"
    events.write_text(json.dumps(tampered, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    validation = store.validate_events()

    assert validation["valid"] is False
    assert any("event_sha256 mismatch" in item["error"] for item in validation["errors"])


def test_completion_requires_passing_evidence(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source, overall_status="failed")

    try:
        validate_completion_record(
            record,
            task=task,
            tree_root=tmp_path / "plans/xq-integrated-rebuild",
            root=tmp_path,
        )
    except CompletionRecordError as exc:
        assert "overall_status = passed" in str(exc) or "exit_code" in str(exc)
    else:
        raise AssertionError("failed record must not validate as completion evidence")


def test_completion_requires_acceptance_item_from_current_source(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source, acceptance_item="Imaginary acceptance item.")

    try:
        validate_completion_record(
            record,
            task=task,
            tree_root=tmp_path / "plans/xq-integrated-rebuild",
            root=tmp_path,
        )
    except CompletionRecordError as exc:
        assert "not found in current source" in str(exc)
    else:
        raise AssertionError("forged acceptance items must not validate")


def test_completion_requires_acceptance_source_section(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source, source_section=None)

    try:
        validate_completion_record(
            record,
            task=task,
            tree_root=tmp_path / "plans/xq-integrated-rebuild",
            root=tmp_path,
        )
    except CompletionRecordError as exc:
        assert "missing source_section" in str(exc)
    else:
        raise AssertionError("acceptance source_section must be required")


def test_completion_rejects_all_not_applicable_acceptance(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source, overall_status="passed", acceptance_status="not-applicable")

    try:
        validate_completion_record(
            record,
            task=task,
            tree_root=tmp_path / "plans/xq-integrated-rebuild",
            root=tmp_path,
        )
    except CompletionRecordError as exc:
        assert "at least one acceptance item must be passed" in str(exc)
    else:
        raise AssertionError("all not-applicable acceptance must not complete a task")


def test_claim_next_stops_before_selection_when_preflight_fails() -> None:
    calls = {"runtime": 0}
    original_preflight = ledger_task.run_preflight_gate
    original_runtime = ledger_task.runtime_tasks

    def failing_preflight() -> dict:
        return {
            "ok": False,
            "summary": {"audit_exit_code": 1, "event_valid": True},
            "stdout": "",
            "stderr": "audit failed",
        }

    def runtime_should_not_run() -> dict:
        calls["runtime"] += 1
        return {"tasks": []}

    ledger_task.run_preflight_gate = failing_preflight
    ledger_task.runtime_tasks = runtime_should_not_run
    try:
        result = ledger_task.command_claim_next(
            SimpleNamespace(actor="codex", session_id="s", dry_run=True, lease_seconds=30)
        )
    finally:
        ledger_task.run_preflight_gate = original_preflight
        ledger_task.runtime_tasks = original_runtime

    assert result == 1
    assert calls["runtime"] == 0


def test_preflight_disallows_claim_when_task_blocking_state_exists() -> None:
    allowed = ledger_task.preflight_allows_claim(
        {
            "audit_exit_code": 0,
            "event_valid": True,
            "dependency_violations": 0,
            "audit_gate_summary": {
                "hard_blocking_gates": {},
                "task_blocking_states": {"blocked_tasks": 1},
            },
        }
    )

    assert allowed is False


def test_claim_next_keeps_lease_when_rollback_release_event_fails() -> None:
    selected_task = {
        "id": "task-a",
        "source_md": "plans/xq-integrated-rebuild/00-governance/task-a.md",
        "status": "ready-for-ledger-review",
    }
    released: list[tuple[str, str | None, str | None]] = []
    original_preflight = ledger_task.run_preflight_gate
    original_runtime = ledger_task.runtime_tasks
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class FailingRollbackStore:
        def __init__(self):
            self.calls = 0

        def append_event(self, event_type, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {"event_type": event_type, "payload": kwargs["payload"]}
            raise RuntimeError(f"{event_type} append failed")

    class LeaseManagerWithReleaseTracking:
        def __init__(self, lease_seconds: int = 3600):
            self.lease_seconds = lease_seconds

        def claim(self, task_id: str, *, actor: str, session_id: str):
            return make_lease(task_id, actor=actor, session_id=session_id)

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            released.append((task_id, actor, session_id))
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "s")

    ledger_task.run_preflight_gate = lambda: {"ok": True, "summary": {}, "stdout": "", "stderr": ""}
    ledger_task.runtime_tasks = lambda: {"tasks": [selected_task]}
    ledger_task.EventStore = FailingRollbackStore
    ledger_task.LeaseManager = LeaseManagerWithReleaseTracking
    try:
        result = ledger_task.command_claim_next(
            SimpleNamespace(actor="codex", session_id="s", dry_run=False, lease_seconds=3600)
        )
    finally:
        ledger_task.run_preflight_gate = original_preflight
        ledger_task.runtime_tasks = original_runtime
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 1
    assert released == []


def test_record_complete_requires_active_lease_for_actor_and_session(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    appended: list[dict] = []
    original_runtime = ledger_task.runtime_tasks
    original_validator = ledger_task.validate_completion_record
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class FakeStore:
        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "should-not-append"}

    class FakeLeaseManager:
        def read(self, task_id: str):
            return {
                "task_id": task_id,
                "actor": "codex",
                "session_id": "different-session",
                "heartbeat_at": utc_now(),
                "lease_seconds": 3600,
            }

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str):
            return None

    ledger_task.runtime_tasks = lambda: {"tasks": [task]}
    ledger_task.validate_completion_record = lambda record_path, task, **kwargs: fake_passing_record(tmp_path)
    ledger_task.EventStore = FakeStore
    ledger_task.LeaseManager = FakeLeaseManager
    try:
        result = ledger_task.command_record_complete(
            SimpleNamespace(
                task_id=task["id"],
                evidence=str(tmp_path / "evidence.json"),
                actor="codex",
                session_id="test-session",
                command_summary=None,
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.validate_completion_record = original_validator
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 1
    assert appended == []


def test_record_complete_requires_command_summary_file(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    appended: list[dict] = []
    original_runtime = ledger_task.runtime_tasks
    original_validator = ledger_task.validate_completion_record
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class FakeStore:
        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "should-not-append"}

    class FakeLeaseManager:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="test-session")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str):
            return None

    ledger_task.runtime_tasks = lambda: {"tasks": [task]}
    ledger_task.validate_completion_record = lambda record_path, task, **kwargs: fake_passing_record(tmp_path)
    ledger_task.EventStore = FakeStore
    ledger_task.LeaseManager = FakeLeaseManager
    try:
        result = ledger_task.command_record_complete(
            SimpleNamespace(
                task_id=task["id"],
                evidence=str(tmp_path / "evidence.json"),
                actor="codex",
                session_id="test-session",
                command_summary=str(tmp_path / "missing-summary.json"),
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.validate_completion_record = original_validator
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 1
    assert appended == []


def test_record_complete_keeps_lease_when_event_fails(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    command_entry = make_runner_command_entry(tmp_path, task)
    make_record(
        record,
        task,
        source,
        command_entry=command_entry,
        acceptance_items=make_full_gate_items(),
        session_id="smoke",
    )
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary, command_entry=command_entry)
    events = []
    original_runtime = ledger_task.runtime_tasks
    original_validator = ledger_task.validate_completion_record
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class FailingStore:
        def append_event(self, *args, **kwargs):
            raise RuntimeError("event append failed")

    class LeaseManagerWithReleaseTracking:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="test-session")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            events.append((task_id, actor, session_id))
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "test-session")

    ledger_task.runtime_tasks = lambda: {"tasks": [task]}
    ledger_task.validate_completion_record = lambda record_path, task, **kwargs: {
        "source_md_sha256": "a" * 64,
        "commands": [command_entry],
    }
    ledger_task.EventStore = FailingStore
    ledger_task.LeaseManager = LeaseManagerWithReleaseTracking
    try:
        result = ledger_task.command_record_complete(
            SimpleNamespace(
                task_id=task["id"],
                evidence=str(record),
                actor="codex",
                session_id="test-session",
                command_summary=str(command_summary),
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.validate_completion_record = original_validator
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 1
    assert events == []


def test_record_complete_payload_binds_evidence_and_command_summary_hashes(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    command_entry = make_runner_command_entry(tmp_path, task)
    make_record(record, task, source, command_entry=command_entry, acceptance_items=make_full_gate_items())
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary, command_entry=command_entry)
    appended_payloads: list[dict] = []
    original_runtime = ledger_task.runtime_tasks
    original_validator = ledger_task.validate_completion_record
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class CapturingStore:
        def read_events(self):
            return []

        def append_event(self, *args, **kwargs):
            appended_payloads.append(kwargs["payload"])
            return {"event_id": "completed-event", "payload": kwargs["payload"]}

    class FakeLeaseManager:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="test-session")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "test-session")

    ledger_task.runtime_tasks = lambda: {"tasks": [task]}
    def validated_evidence(record_path, task, **kwargs):
        data = {"commands": [command_entry]}
        data["source_md_sha256"] = file_sha256(source)
        return data

    ledger_task.validate_completion_record = validated_evidence
    ledger_task.EventStore = CapturingStore
    ledger_task.LeaseManager = FakeLeaseManager
    try:
        result = ledger_task.command_record_complete(
            SimpleNamespace(
                task_id=task["id"],
                evidence=str(record),
                actor="codex",
                session_id="test-session",
                command_summary=str(command_summary),
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.validate_completion_record = original_validator
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 0
    assert appended_payloads[0]["record_sha256"] == file_sha256(record)
    assert appended_payloads[0]["command_summary_sha256"] == file_sha256(command_summary)


def test_record_fail_releases_lease_after_event_success(tmp_path: Path) -> None:
    released: list[tuple[str, str | None, str | None]] = []
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class SuccessfulStore:
        def append_event(self, *args, **kwargs):
            return {"event_id": "failed-event"}

    class LeaseManagerWithReleaseTracking:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="s")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            released.append((task_id, actor, session_id))
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "s")

    ledger_task.EventStore = SuccessfulStore
    ledger_task.LeaseManager = LeaseManagerWithReleaseTracking
    try:
        result = ledger_task.command_record_fail(
            SimpleNamespace(
                task_id="task-a",
                failure_type="test-failed",
                reason="test failed",
                actor="codex",
                session_id="s",
            )
        )
    finally:
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 0
    assert released == [("task-a", "codex", "s")]


def test_record_block_releases_lease_after_event_success(tmp_path: Path) -> None:
    released: list[tuple[str, str | None, str | None]] = []
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class SuccessfulStore:
        def append_event(self, *args, **kwargs):
            return {"event_id": "blocked-event"}

    class LeaseManagerWithReleaseTracking:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="s")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            released.append((task_id, actor, session_id))
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "s")

    ledger_task.EventStore = SuccessfulStore
    ledger_task.LeaseManager = LeaseManagerWithReleaseTracking
    try:
        result = ledger_task.command_record_block(
            SimpleNamespace(
                task_id="task-a",
                failure_type="plan-ambiguous",
                reason="ambiguous",
                actor="codex",
                session_id="s",
            )
        )
    finally:
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 0
    assert released == [("task-a", "codex", "s")]


def test_record_fail_and_block_require_owned_lease(tmp_path: Path) -> None:
    appended: list[dict] = []
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class FakeStore:
        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "should-not-append"}

    class NoLeaseManager:
        def read(self, task_id: str):
            return None

        def is_expired(self, lease: dict) -> bool:
            return False

    ledger_task.EventStore = FakeStore
    ledger_task.LeaseManager = NoLeaseManager
    try:
        fail_result = ledger_task.command_record_fail(
            SimpleNamespace(
                task_id="task-a",
                failure_type="test-failed",
                reason="test failed",
                actor="codex",
                session_id="s",
            )
        )
        block_result = ledger_task.command_record_block(
            SimpleNamespace(
                task_id="task-a",
                failure_type="plan-ambiguous",
                reason="ambiguous",
                actor="codex",
                session_id="s",
            )
        )
    finally:
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert fail_result == 1
    assert block_result == 1
    assert appended == []


def test_event_payload_schema_detects_missing_required_fields(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    valid_complete = {
        "schema_version": 1,
        "event_id": "bad-complete",
        "created_at": utc_now(),
        "event_type": EVENT_TASK_COMPLETED,
        "task_id": task["id"],
        "actor": "codex",
        "session_id": "s",
        "payload": {},
        "previous_event_sha256": None,
    }
    valid_complete["event_sha256"] = store.compute_hash(valid_complete)
    valid_fail = {
        "schema_version": 1,
        "event_id": "bad-fail",
        "created_at": utc_now(),
        "event_type": EVENT_TASK_FAILED,
        "task_id": task["id"],
        "actor": "codex",
        "session_id": "s",
        "payload": {"failure_type": "test-failed"},
        "previous_event_sha256": valid_complete["event_sha256"],
    }
    valid_fail["event_sha256"] = store.compute_hash(valid_fail)
    events.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False, sort_keys=True) for event in [valid_complete, valid_fail])
        + "\n",
        encoding="utf-8",
    )

    validation = store.validate_events()

    assert validation["valid"] is False
    error_text = "\n".join(str(item["error"]) for item in validation["errors"])
    assert "payload.record_path" in error_text
    assert "payload.record_sha256" in error_text
    assert "payload.command_summary_sha256" in error_text
    assert "payload.reason" in error_text


def test_completion_event_derives_completed_and_stale(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source)
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_completed",
        task_id=task["id"],
        actor="codex",
        session_id="s",
        payload=completion_payload(record, command_summary),
    )

    derived = store.derive_tasks([task])
    assert derived["tasks"][0]["status"] == "completed"

    source.write_text(source.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    stale = store.derive_tasks([task])
    assert stale["tasks"][0]["status"] == "stale-completion"
    assert stale["stale_completed"]


def test_legacy_completion_replay_is_marked_legacy_verified(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source)
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_completed",
        task_id=task["id"],
        actor="codex",
        session_id="legacy-smoke",
        payload=completion_payload(record, command_summary),
    )

    derived = store.derive_tasks([task])
    derived_task = derived["tasks"][0]

    assert derived_task["status"] == "completed"
    assert derived_task["evidence_status"] == "legacy-verified"
    assert derived_task["completion_standard"] == "legacy-verified"


def test_runner_backed_completion_replay_is_marked_verified_runner_backed(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    command_entry = make_runner_command_entry(tmp_path, task)
    make_record(record, task, source, command_entry=command_entry, acceptance_items=make_full_gate_items())
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary, command_entry=command_entry)
    payload = completion_payload(record, command_summary)
    payload["command_capture"] = "runner-artifact-v1"
    payload["completion_coverage"] = "acceptance-and-test-plan-all-items-v1"
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_completed",
        task_id=task["id"],
        actor="codex",
        session_id="test-session",
        payload=payload,
    )

    derived = store.derive_tasks([task])
    derived_task = derived["tasks"][0]

    assert derived_task["status"] == "completed"
    assert derived_task["evidence_status"] == "verified-runner-backed"
    assert derived_task["completion_standard"] == "verified-runner-backed"


def test_replay_rejects_tampered_completion_evidence_hash(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source)
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_completed",
        task_id=task["id"],
        actor="codex",
        session_id="s",
        payload=completion_payload(record, command_summary),
    )
    tampered = json.loads(record.read_text(encoding="utf-8"))
    tampered["acceptance"][0]["evidence"] = "tampered after event"
    write_json(record, tampered)

    derived = store.derive_tasks([task])

    assert derived["tasks"][0]["status"] == "ready-for-ledger-review"
    assert any("record_sha256 mismatch" in item["reason"] for item in derived["invalid_private_evidence"])


def test_replay_rejects_completion_source_hash_payload_mismatch(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source)
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary)
    payload = completion_payload(record, command_summary)
    payload["source_md_sha256"] = "b" * 64
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_completed",
        task_id=task["id"],
        actor="codex",
        session_id="s",
        payload=payload,
    )

    derived = store.derive_tasks([task])

    assert derived["tasks"][0]["status"] == "ready-for-ledger-review"
    assert any("source_md_sha256 mismatch" in item["reason"] for item in derived["invalid_private_evidence"])


def test_replay_revalidates_command_summary_against_evidence(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source)
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    write_json(
        command_summary,
        {
            "schema_version": 1,
            "commands": [
                {
                    "argv": ["python3", "-m", "compileall", "other.py"],
                    "cwd": str(command_summary.parent),
                    "started_at": utc_now(),
                    "ended_at": utc_now(),
                    "exit_code": 0,
                }
            ],
            "overall_status": "passed",
        },
    )
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_completed",
        task_id=task["id"],
        actor="codex",
        session_id="s",
        payload=completion_payload(record, command_summary),
    )

    derived = store.derive_tasks([task])

    assert derived["tasks"][0]["status"] == "ready-for-ledger-review"
    assert any("command summary missing record command" in item["reason"] for item in derived["invalid_private_evidence"])


def test_two_retryable_failures_block_task(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    for _ in range(2):
        store.append_event(
            "task_failed",
            task_id=task["id"],
            actor="codex",
            session_id="s",
            payload={"failure_type": "test-failed", "reason": "test failed"},
        )

    derived = store.derive_tasks([task])

    assert derived["tasks"][0]["status"] == "blocked"
    assert derived["tasks"][0]["failure_count"] == 2


def test_source_boundary_risk_blocks_immediately(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_failed",
        task_id=task["id"],
        actor="codex",
        session_id="s",
        payload={"failure_type": "source-boundary-risk", "reason": "would touch <xq-implementation-workspace>"},
    )

    derived = store.derive_tasks([task])

    assert derived["tasks"][0]["status"] == "blocked"


def test_reopen_blocked_task_returns_to_ready_without_erasing_block_event(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    blocked = store.append_event(
        "task_blocked",
        task_id=task["id"],
        actor="codex",
        session_id="s",
        payload={"failure_type": "harness-error", "reason": "plan text needed cleanup"},
    )
    reopened = store.append_event(
        EVENT_TASK_REOPENED,
        task_id=task["id"],
        actor="codex",
        session_id="s2",
        payload={
            "from_status": "blocked",
            "reason": "plan text was cleaned; task must be rerun through normal claim/evidence flow",
        },
    )

    derived = store.derive_tasks([task])

    assert derived["tasks"][0]["status"] == "ready-for-ledger-review"
    assert derived["tasks"][0]["reopened_from"] == "blocked"
    assert derived["tasks"][0]["reopen_reason"].startswith("plan text was cleaned")
    assert [event["event_type"] for event in derived["events"]] == ["task_blocked", EVENT_TASK_REOPENED]
    assert blocked["event_id"] != reopened["event_id"]


def test_reopen_stale_completion_requires_new_claim_instead_of_counting_completed(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source)
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_completed",
        task_id=task["id"],
        actor="codex",
        session_id="legacy",
        payload=completion_payload(record, command_summary),
    )
    source.write_text(source.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    store.append_event(
        EVENT_TASK_REOPENED,
        task_id=task["id"],
        actor="codex",
        session_id="repair",
        payload={
            "from_status": "stale-completion",
            "reason": "source plan changed; previous completion must be rerun",
        },
    )

    derived = store.derive_tasks([task])

    assert derived["tasks"][0]["status"] == "ready-for-ledger-review"
    assert derived["tasks"][0]["reopened_from"] == "stale-completion"
    assert "completion_standard" not in derived["tasks"][0]
    assert not derived["stale_completed"]


def test_active_lease_blocks_duplicate_claim(tmp_path: Path) -> None:
    manager = LeaseManager(tmp_path / "task-locks", lease_seconds=3600)
    manager.claim("task-a", actor="codex", session_id="s")

    try:
        manager.claim("task-a", actor="codex", session_id="s2")
    except LeaseError as exc:
        assert "already has active lease" in str(exc)
    else:
        raise AssertionError("duplicate lease claim must fail")


def test_heartbeat_requires_actor_and_session(tmp_path: Path) -> None:
    manager = LeaseManager(tmp_path / "task-locks", lease_seconds=3600)
    manager.claim("task-a", actor="codex", session_id="s")

    for kwargs in [{}, {"actor": "codex"}, {"session_id": "s"}]:
        try:
            manager.heartbeat("task-a", **kwargs)
        except LeaseError as exc:
            assert "actor and session_id" in str(exc)
        else:
            raise AssertionError("heartbeat must require both actor and session_id")


def test_release_requires_lease_owner(tmp_path: Path) -> None:
    manager = LeaseManager(tmp_path / "task-locks", lease_seconds=3600)
    manager.claim("task-a", actor="codex", session_id="s")

    try:
        manager.release("task-a", actor="other", session_id="s")
    except LeaseError as exc:
        assert "lease actor mismatch" in str(exc)
    else:
        raise AssertionError("release by non-owner must fail")

    assert manager.read("task-a") is not None


def test_lease_claim_uses_atomic_create() -> None:
    source = inspect.getsource(LeaseManager.claim)

    assert "os.link" in source
    assert "tmp_path" in source


def test_concurrent_claim_allows_only_one_owner(tmp_path: Path) -> None:
    manager = LeaseManager(tmp_path / "task-locks", lease_seconds=3600)

    def try_claim(index: int) -> bool:
        try:
            manager.claim("task-a", actor=f"actor-{index}", session_id=f"s-{index}")
            return True
        except LeaseError:
            return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(try_claim, range(16)))

    assert results.count(True) == 1
    assert manager.read("task-a") is not None


def test_lease_heartbeat_and_release_take_exclusive_lock(tmp_path: Path) -> None:
    calls: list[int] = []
    original_flock = lease_module.fcntl.flock

    def recording_flock(fd: int, operation: int) -> None:
        calls.append(operation)
        original_flock(fd, operation)

    lease_module.fcntl.flock = recording_flock
    try:
        manager = LeaseManager(tmp_path / "task-locks", lease_seconds=3600)
        manager.claim("task-a", actor="codex", session_id="s")
        manager.heartbeat("task-a", actor="codex", session_id="s")
        manager.release("task-a", actor="codex", session_id="s")
    finally:
        lease_module.fcntl.flock = original_flock

    exclusive_locks = [
        operation
        for operation in calls
        if operation & lease_module.fcntl.LOCK_EX
    ]
    assert len(exclusive_locks) >= 3


def test_event_append_serializes_hash_chain_with_file_lock() -> None:
    source = inspect.getsource(EventStore.append_event)

    assert "fcntl.flock" in source
    assert "LOCK_EX" in source
    assert "_last_hash_from_open_file" in source


def test_event_reads_take_shared_lock(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)
    store.append_event(
        "task_failed",
        task_id=task["id"],
        actor="codex",
        session_id="s",
        payload={"failure_type": "test-failed", "reason": "test failed"},
    )
    calls: list[int] = []
    original_flock = event_module.fcntl.flock

    def recording_flock(fd: int, operation: int) -> None:
        calls.append(operation)
        original_flock(fd, operation)

    event_module.fcntl.flock = recording_flock
    try:
        store.read_events()
        store.validate_events()
    finally:
        event_module.fcntl.flock = original_flock

    shared_locks = [
        operation
        for operation in calls
        if operation & event_module.fcntl.LOCK_SH
    ]
    assert len(shared_locks) >= 2


def test_concurrent_event_appends_keep_valid_hash_chain(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    events = tmp_path / "task-events.jsonl"
    store = EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path)

    def append_failure(index: int) -> None:
        EventStore(events, tree_root=tmp_path / "plans/xq-integrated-rebuild", root=tmp_path).append_event(
            "task_failed",
            task_id=task["id"],
            actor=f"actor-{index}",
            session_id=f"s-{index}",
            payload={"failure_type": "test-failed", "reason": f"failure {index}"},
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(append_failure, range(24)))

    validation = store.validate_events()

    assert validation["valid"] is True
    assert validation["event_count"] == 24


def test_command_summary_must_have_content(tmp_path: Path) -> None:
    task, _ = make_task(tmp_path)
    appended: list[dict] = []
    original_runtime = ledger_task.runtime_tasks
    original_validator = ledger_task.validate_completion_record
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class FakeStore:
        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "should-not-append"}

    class FakeLeaseManager:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="test-session")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "test-session")

    ledger_task.runtime_tasks = lambda: {"tasks": [task]}
    ledger_task.validate_completion_record = lambda record_path, task, **kwargs: fake_passing_record(tmp_path)
    ledger_task.EventStore = FakeStore
    ledger_task.LeaseManager = FakeLeaseManager
    try:
        empty_summary = tmp_path / "empty-summary.json"
        empty_summary.write_text("", encoding="utf-8")
        result = ledger_task.command_record_complete(
            SimpleNamespace(
                task_id=task["id"],
                evidence=str(tmp_path / "evidence.json"),
                actor="codex",
                session_id="test-session",
                command_summary=str(empty_summary),
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.validate_completion_record = original_validator
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 1
    assert appended == []


def test_command_summary_must_match_evidence_commands(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    make_record(record, task, source)
    mismatched_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    write_json(
        mismatched_summary,
        {
            "schema_version": 1,
            "commands": [
                {
                    "argv": ["python3", "-m", "compileall", "other.py"],
                    "cwd": str(mismatched_summary.parent),
                    "started_at": utc_now(),
                    "ended_at": utc_now(),
                    "exit_code": 0,
                }
            ],
            "overall_status": "passed",
        },
    )
    appended: list[dict] = []
    original_runtime = ledger_task.runtime_tasks
    original_validator = ledger_task.validate_completion_record
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class FakeStore:
        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "should-not-append"}

    class FakeLeaseManager:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="test-session")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "test-session")

    ledger_task.runtime_tasks = lambda: {"tasks": [task]}
    ledger_task.validate_completion_record = lambda record_path, task, **kwargs: {
        "source_md_sha256": "a" * 64,
        "commands": [
            {
                "argv": ["python3", "-m", "py_compile", "ledger_task.py"],
                "cwd": str(record.parent),
                "exit_code": 0,
            }
        ],
    }
    ledger_task.EventStore = FakeStore
    ledger_task.LeaseManager = FakeLeaseManager
    try:
        result = ledger_task.command_record_complete(
            SimpleNamespace(
                task_id=task["id"],
                evidence=str(record),
                actor="codex",
                session_id="test-session",
                command_summary=str(mismatched_summary),
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.validate_completion_record = original_validator
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 1
    assert appended == []


def test_record_complete_retries_release_without_duplicate_terminal_event(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    command_entry = make_runner_command_entry(tmp_path, task)
    make_record(record, task, source, command_entry=command_entry, acceptance_items=make_full_gate_items())
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary, command_entry=command_entry)
    appended: list[dict] = []
    released: list[tuple[str, str | None, str | None]] = []
    existing_event = {
        "event_type": EVENT_TASK_COMPLETED,
        "task_id": task["id"],
        "actor": "codex",
        "session_id": "test-session",
        "payload": {
            "record_path": str(record),
            "record_sha256": file_sha256(record),
            "source_md_sha256": "a" * 64,
            "command_summary": str(command_summary),
            "command_summary_sha256": file_sha256(command_summary),
            "command_capture": "runner-artifact-v1",
            "completion_coverage": "acceptance-and-test-plan-all-items-v1",
        },
    }
    original_runtime = ledger_task.runtime_tasks
    original_validator = ledger_task.validate_completion_record
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class ExistingTerminalStore:
        def read_events(self):
            return [existing_event]

        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "should-not-append"}

    class LeaseManagerWithReleaseTracking:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="test-session")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            released.append((task_id, actor, session_id))
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "test-session")

    ledger_task.runtime_tasks = lambda: {"tasks": [task]}
    ledger_task.validate_completion_record = lambda record_path, task, **kwargs: {
        "source_md_sha256": "a" * 64,
        "commands": [command_entry],
    }
    ledger_task.EventStore = ExistingTerminalStore
    ledger_task.LeaseManager = LeaseManagerWithReleaseTracking
    try:
        result = ledger_task.command_record_complete(
            SimpleNamespace(
                task_id=task["id"],
                evidence=str(record),
                actor="codex",
                session_id="test-session",
                command_summary=str(command_summary),
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.validate_completion_record = original_validator
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 0
    assert appended == []
    assert released == [(task["id"], "codex", "test-session")]


def test_record_fail_retries_release_without_duplicate_terminal_event() -> None:
    appended: list[dict] = []
    released: list[tuple[str, str | None, str | None]] = []
    existing_event = {
        "event_type": EVENT_TASK_FAILED,
        "task_id": "task-a",
        "actor": "codex",
        "session_id": "s",
        "payload": {"failure_type": "test-failed", "reason": "test failed"},
    }
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager

    class ExistingTerminalStore:
        def read_events(self):
            return [existing_event]

        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "should-not-append"}

    class LeaseManagerWithReleaseTracking:
        def read(self, task_id: str):
            return make_lease(task_id, actor="codex", session_id="s")

        def is_expired(self, lease: dict) -> bool:
            return False

        def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None):
            released.append((task_id, actor, session_id))
            return make_lease(task_id, actor=actor or "codex", session_id=session_id or "s")

    ledger_task.EventStore = ExistingTerminalStore
    ledger_task.LeaseManager = LeaseManagerWithReleaseTracking
    try:
        result = ledger_task.command_record_fail(
            SimpleNamespace(
                task_id="task-a",
                failure_type="test-failed",
                reason="test failed",
                actor="codex",
                session_id="s",
            )
        )
    finally:
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager

    assert result == 0
    assert appended == []
    assert released == [("task-a", "codex", "s")]


def test_temp_end_to_end_claim_complete_replay_smoke(tmp_path: Path) -> None:
    task, source = make_task(tmp_path)
    task["source_md"] = str(source)
    record = tmp_path / "private-evidence-dir/test-runs/task/evidence.json"
    command_entry = make_runner_command_entry(tmp_path, task, session_id="smoke")
    make_record(
        record,
        task,
        source,
        command_entry=command_entry,
        acceptance_items=make_full_gate_items(),
        session_id="smoke",
    )
    command_summary = tmp_path / "private-evidence-dir/test-runs/task/command-summary.json"
    make_command_summary(command_summary, command_entry=command_entry)
    events = tmp_path / "task-events.jsonl"
    locks = tmp_path / "task-locks"
    tree_root = tmp_path / "plans/xq-integrated-rebuild"
    store = EventStore(events, tree_root=tree_root, root=tmp_path)
    manager = LeaseManager(locks, lease_seconds=3600)
    lease = manager.claim(task["id"], actor="codex", session_id="smoke")
    store.append_event("task_claimed", task_id=task["id"], actor="codex", session_id="smoke", payload={"lease": lease})
    store.append_event("task_started", task_id=task["id"], actor="codex", session_id="smoke", payload={"lease": lease})
    original_store = ledger_task.EventStore
    original_lease_manager = ledger_task.LeaseManager
    original_runtime = ledger_task.runtime_tasks

    class TempEventStore(EventStore):
        def __init__(self):
            super().__init__(events, tree_root=tree_root, root=tmp_path)

    class TempLeaseManager(LeaseManager):
        def __init__(self, lease_seconds: int = 3600):
            super().__init__(locks, lease_seconds=lease_seconds)

    def temp_runtime() -> dict:
        derived = store.derive_tasks([task])
        leases = manager.summarize()
        for runtime_task in derived["tasks"]:
            if runtime_task["id"] in leases["expired_task_ids"] and runtime_task.get("status") in {"claimed", "in-progress"}:
                runtime_task["status"] = "lease-expired"
            if runtime_task["id"] in leases["active_task_ids"] and runtime_task.get("status") == "ready-for-ledger-review":
                runtime_task["status"] = "claimed"
        return {"tasks": derived["tasks"], "derived": derived, "leases": leases}

    ledger_task.EventStore = TempEventStore
    ledger_task.LeaseManager = TempLeaseManager
    ledger_task.runtime_tasks = temp_runtime
    try:
        result = ledger_task.command_record_complete(
            SimpleNamespace(
                task_id=task["id"],
                evidence=str(record),
                actor="codex",
                session_id="smoke",
                command_summary=str(command_summary),
            )
        )
    finally:
        ledger_task.EventStore = original_store
        ledger_task.LeaseManager = original_lease_manager
        ledger_task.runtime_tasks = original_runtime

    derived = store.derive_tasks([task])
    validation = store.validate_events()

    assert result == 0
    assert validation["valid"] is True
    assert validation["event_count"] == 3
    assert derived["tasks"][0]["status"] == "completed"
    assert manager.summarize()["active_leases"] == []


def test_selection_stops_on_blocking_state() -> None:
    tasks = [
        {"id": "a", "source_md": "plans/xq-integrated-rebuild/00-governance/a.md", "status": "blocked"},
        {"id": "b", "source_md": "plans/xq-integrated-rebuild/01-foundation/b.md", "status": "ready-for-ledger-review"},
    ]

    explanation = explain_selection(tasks)

    assert explanation["selected"] is None
    assert explanation["reason"] == "task-blocking-state-present"


def test_selection_prefers_failed_retry_before_ready() -> None:
    tasks = [
        {"id": "a", "source_md": "plans/xq-integrated-rebuild/00-governance/a.md", "status": "completed"},
        {"id": "b", "source_md": "plans/xq-integrated-rebuild/01-foundation/b.md", "status": "ready-for-ledger-review"},
        {"id": "c", "source_md": "plans/xq-integrated-rebuild/01-foundation/c.md", "status": "failed-retry-ready"},
    ]

    explanation = explain_selection(tasks)

    assert explanation["selected"]["id"] == "c"


def test_task_level_dependencies_block_selection_within_phase() -> None:
    tasks = [
        {
            "id": "a-dependent",
            "source_md": "plans/xq-integrated-rebuild/00-governance/a-dependent.md",
            "status": "ready-for-ledger-review",
            "depends_on": ["z-prerequisite"],
        },
        {
            "id": "z-prerequisite",
            "source_md": "plans/xq-integrated-rebuild/00-governance/z-prerequisite.md",
            "status": "ready-for-ledger-review",
        },
    ]

    explanation = explain_selection(tasks)

    assert explanation["selected"]["id"] == "z-prerequisite"


def test_task_graph_contains_task_dependencies() -> None:
    tasks = [
        {
            "id": "a",
            "source_md": "plans/xq-integrated-rebuild/00-governance/a.md",
            "status": "completed",
        },
        {
            "id": "b",
            "source_md": "plans/xq-integrated-rebuild/00-governance/b.md",
            "status": "ready-for-ledger-review",
            "task_dependencies": ["a"],
        },
    ]

    graph = build_task_graph(tasks)
    node_b = next(node for node in graph["nodes"] if node["id"] == "b")

    assert node_b["task_dependencies"] == ["a"]
    assert graph["edges"] == [{"from": "a", "to": "b", "kind": "task"}]


def test_dependency_violations_include_task_level_edges() -> None:
    tasks = [
        {
            "id": "a",
            "source_md": "plans/xq-integrated-rebuild/00-governance/a.md",
            "status": "ready-for-ledger-review",
        },
        {
            "id": "b",
            "source_md": "plans/xq-integrated-rebuild/00-governance/b.md",
            "status": "completed",
            "depends_on": ["a"],
        },
    ]

    violations = dependency_violations(tasks)

    assert violations == [
        {
            "task_id": "b",
            "dependency_task_id": "a",
            "reason": "completed task has incomplete task dependency",
        }
    ]


def test_authoritative_state_disallows_resume_when_task_blocking_states_exist() -> None:
    state = authoritative_state(
        {"generated_at": utc_now()},
        {
            "status_source_lines": 0,
            "claim_actionable": 0,
            "execution_flow_items": 0,
            "deferred_needs_owner_confirmation": 0,
            "needs_hardening_documents": 0,
            "scope_violations": 0,
            "active_plan_kernel_violations": 0,
            "task_event_errors": 0,
            "missing_private_evidence_links": 0,
            "invalid_private_evidence_files": 0,
            "dependency_violations": 0,
            "blocked_tasks": 1,
            "lease_expired_tasks": 0,
            "expired_task_leases": 0,
            "stale_completion_tasks": 0,
            "stale_completed_tasks": 0,
        },
    )

    assert state["task_selection"]["implementation_resume_allowed"] is False
    assert state["task_selection"]["claim_next_allowed"] is False
    assert "blocked-tasks" in state["task_selection"]["task_blocking_reasons"]


def test_negative_rg_test_plan_command_must_return_zero_on_expected_success() -> None:
    lines = [
        "# Document Repair Policy",
        "",
        "## Test Plan",
        "",
        "Document consistency checks:",
        "",
        "```text",
        "rg -n \"Current cursor|Next implementation document\" plans/xq-integrated-rebuild/README.md",
        "```",
        "",
        "Expected result:",
        "",
        "state-source lines remain 0 except diagnostic command references",
    ]

    violations = plan_exit_semantics_violations(
        "plans/xq-integrated-rebuild/00-governance/02-document-repair-policy.md",
        lines,
    )

    assert len(violations) == 1
    assert violations[0]["kind"] == "test_plan_negative_rg_without_exit_zero_wrapper"
    assert "bash -lc '! rg" in violations[0]["repair"]


def test_positive_rg_test_plan_command_is_allowed_without_negation() -> None:
    lines = [
        "# Selection Rules",
        "",
        "## Test Plan",
        "",
        "Document consistency checks:",
        "",
        "```text",
        "rg -n \"XQ-main.zip Evidence|Behavior kept\" plans/xq-integrated-rebuild",
        "```",
        "",
        "Expected result:",
        "",
        "feature documents that use old XQ behavior contain an record record before source work resumes",
    ]

    violations = plan_exit_semantics_violations(
        "plans/xq-integrated-rebuild/08-xq-zip-selection/01-code-selection-rules.md",
        lines,
    )

    assert violations == []


def test_negated_rg_test_plan_command_is_allowed_for_expected_no_match() -> None:
    lines = [
        "# Document Repair Policy",
        "",
        "## Test Plan",
        "",
        "Document consistency checks:",
        "",
        "```text",
        "bash -lc '! rg -n \"Current cursor|Next implementation document\" plans/xq-integrated-rebuild/README.md'",
        "```",
        "",
        "Expected result:",
        "",
        "state-source lines remain 0 except diagnostic command references",
    ]

    violations = plan_exit_semantics_violations(
        "plans/xq-integrated-rebuild/00-governance/02-document-repair-policy.md",
        lines,
    )

    assert violations == []


def test_negative_rg_detection_is_scoped_to_each_fenced_command() -> None:
    lines = [
        "# Dependency Role Map",
        "",
        "## Test Plan",
        "",
        "Forbidden dependency check:",
        "",
        "```text",
        "rg -n \"find_package\\\\((MITK|BlueBerry|CTK)|\\\\bSWIG\\\\b\" src",
        "```",
        "",
        "Expected result:",
        "",
        "no matches",
        "",
        "Allowed wrapper check:",
        "",
        "```text",
        "rg -n \"vtk|itk|DCMTK|GDCM\" src/core",
        "```",
        "",
        "Expected result:",
        "",
        "only allowed wrapper-handle declarations appear in core payload internals",
    ]

    violations = plan_exit_semantics_violations(
        "plans/xq-integrated-rebuild/01-foundation/04-dependency-role-map.md",
        lines,
    )

    assert len(violations) == 1
    assert "find_package" in violations[0]["excerpt"]


def test_record_override_requires_known_task_and_gate() -> None:
    appended: list[dict] = []
    original_runtime = ledger_task.runtime_tasks
    original_store = ledger_task.EventStore

    class FakeStore:
        def validate_events(self):
            return {"valid": True, "errors": []}

        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "override-event"}

    ledger_task.runtime_tasks = lambda: {"tasks": [{"id": "task-a", "status": "blocked"}]}
    ledger_task.EventStore = FakeStore
    try:
        unknown_task_result = ledger_task.command_record_override(
            SimpleNamespace(
                task_id="missing-task",
                gate="blocked_tasks",
                reason="manual decision",
                actor="human",
                session_id="s",
            )
        )
        unknown_gate_result = ledger_task.command_record_override(
            SimpleNamespace(
                task_id="task-a",
                gate="not-a-real-gate",
                reason="manual decision",
                actor="human",
                session_id="s",
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.EventStore = original_store

    assert unknown_task_result == 1
    assert unknown_gate_result == 1
    assert appended == []


def test_record_reopen_requires_known_blocking_task_and_appends_reopen_event() -> None:
    appended: list[dict] = []
    original_runtime = ledger_task.runtime_tasks
    original_store = ledger_task.EventStore
    original_preflight = ledger_task.run_preflight_gate

    class FakeStore:
        def validate_events(self):
            return {"valid": True, "errors": []}

        def append_event(self, *args, **kwargs):
            appended.append({"args": args, "kwargs": kwargs})
            return {"event_id": "reopen-event", "event_type": args[0], "payload": kwargs["payload"]}

    ledger_task.runtime_tasks = lambda: {
        "tasks": [
            {"id": "task-a", "status": "blocked"},
            {"id": "task-b", "status": "ready-for-ledger-review"},
        ]
    }
    ledger_task.run_preflight_gate = lambda: {
        "summary": {
            "audit_exit_code": 0,
            "event_valid": True,
            "audit_gate_summary": {"hard_blocking_gates": {"task_event_errors": 0}},
        }
    }
    ledger_task.EventStore = FakeStore
    try:
        unknown_task_result = ledger_task.command_record_reopen(
            SimpleNamespace(
                task_id="missing-task",
                reason="fixed by plan cleanup",
                actor="codex",
                session_id="s",
            )
        )
        non_blocking_result = ledger_task.command_record_reopen(
            SimpleNamespace(
                task_id="task-b",
                reason="fixed by plan cleanup",
                actor="codex",
                session_id="s",
            )
        )
        blocking_result = ledger_task.command_record_reopen(
            SimpleNamespace(
                task_id="task-a",
                reason="fixed by plan cleanup",
                actor="codex",
                session_id="s",
            )
        )
    finally:
        ledger_task.runtime_tasks = original_runtime
        ledger_task.EventStore = original_store
        ledger_task.run_preflight_gate = original_preflight

    assert unknown_task_result == 1
    assert non_blocking_result == 1
    assert blocking_result == 0
    assert len(appended) == 1
    assert appended[0]["args"][0] == EVENT_TASK_REOPENED
    assert appended[0]["kwargs"]["task_id"] == "task-a"
    assert appended[0]["kwargs"]["payload"]["from_status"] == "blocked"


if __name__ == "__main__":
    import tempfile

    test_empty_event_log_preserves_baseline_counts()
    test_selection_stops_on_blocking_state()
    test_selection_prefers_failed_retry_before_ready()
    test_task_level_dependencies_block_selection_within_phase()
    test_task_graph_contains_task_dependencies()
    test_dependency_violations_include_task_level_edges()
    with tempfile.TemporaryDirectory() as tmp:
        test_event_hash_chain_detects_tampering(Path(tmp) / "hash")
    with tempfile.TemporaryDirectory() as tmp:
        test_completion_requires_passing_evidence(Path(tmp) / "failed-evidence")
    with tempfile.TemporaryDirectory() as tmp:
        test_completion_requires_acceptance_item_from_current_source(Path(tmp) / "forged-acceptance")
    with tempfile.TemporaryDirectory() as tmp:
        test_completion_requires_acceptance_source_section(Path(tmp) / "source-section")
    with tempfile.TemporaryDirectory() as tmp:
        test_completion_rejects_all_not_applicable_acceptance(Path(tmp) / "all-na")
    with tempfile.TemporaryDirectory() as tmp:
        test_completion_coverage_includes_fenced_test_plan_commands(Path(tmp) / "fenced-coverage")
    with tempfile.TemporaryDirectory() as tmp:
        test_completion_coverage_rejects_missing_fenced_test_plan_commands(Path(tmp) / "missing-fenced-coverage")
    with tempfile.TemporaryDirectory() as tmp:
        test_fenced_test_plan_command_must_match_runner_argv(Path(tmp) / "fenced-runner-mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        test_fenced_test_plan_command_accepts_equivalent_runner_argv(Path(tmp) / "fenced-runner-match")
    test_claim_next_stops_before_selection_when_preflight_fails()
    test_preflight_disallows_claim_when_task_blocking_state_exists()
    test_claim_next_keeps_lease_when_rollback_release_event_fails()
    with tempfile.TemporaryDirectory() as tmp:
        test_record_complete_requires_active_lease_for_actor_and_session(Path(tmp) / "complete-lease")
    with tempfile.TemporaryDirectory() as tmp:
        test_record_complete_requires_command_summary_file(Path(tmp) / "command-summary")
    with tempfile.TemporaryDirectory() as tmp:
        test_record_complete_keeps_lease_when_event_fails(Path(tmp) / "complete-release")
    with tempfile.TemporaryDirectory() as tmp:
        test_record_complete_payload_binds_evidence_and_command_summary_hashes(Path(tmp) / "payload-hash")
    with tempfile.TemporaryDirectory() as tmp:
        test_record_fail_releases_lease_after_event_success(Path(tmp) / "fail-release")
    with tempfile.TemporaryDirectory() as tmp:
        test_record_block_releases_lease_after_event_success(Path(tmp) / "block-release")
    with tempfile.TemporaryDirectory() as tmp:
        test_record_fail_and_block_require_owned_lease(Path(tmp) / "fail-block-lease")
    with tempfile.TemporaryDirectory() as tmp:
        test_command_summary_must_have_content(Path(tmp) / "summary-content")
    with tempfile.TemporaryDirectory() as tmp:
        test_command_summary_must_match_evidence_commands(Path(tmp) / "summary-match")
    with tempfile.TemporaryDirectory() as tmp:
        test_record_complete_retries_release_without_duplicate_terminal_event(Path(tmp) / "complete-idempotent")
    test_record_fail_retries_release_without_duplicate_terminal_event()
    with tempfile.TemporaryDirectory() as tmp:
        test_event_payload_schema_detects_missing_required_fields(Path(tmp) / "payload-schema")
    with tempfile.TemporaryDirectory() as tmp:
        test_completion_event_derives_completed_and_stale(Path(tmp) / "complete")
    with tempfile.TemporaryDirectory() as tmp:
        test_legacy_completion_replay_is_marked_legacy_verified(Path(tmp) / "legacy-complete")
    with tempfile.TemporaryDirectory() as tmp:
        test_runner_backed_completion_replay_is_marked_verified_runner_backed(Path(tmp) / "runner-complete")
    with tempfile.TemporaryDirectory() as tmp:
        test_replay_rejects_tampered_completion_evidence_hash(Path(tmp) / "tampered-evidence")
    with tempfile.TemporaryDirectory() as tmp:
        test_replay_rejects_completion_source_hash_payload_mismatch(Path(tmp) / "source-mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        test_replay_revalidates_command_summary_against_evidence(Path(tmp) / "command-summary-replay")
    with tempfile.TemporaryDirectory() as tmp:
        test_two_retryable_failures_block_task(Path(tmp) / "failures")
    with tempfile.TemporaryDirectory() as tmp:
        test_source_boundary_risk_blocks_immediately(Path(tmp) / "boundary")
    with tempfile.TemporaryDirectory() as tmp:
        test_reopen_blocked_task_returns_to_ready_without_erasing_block_event(Path(tmp) / "reopen-blocked")
    with tempfile.TemporaryDirectory() as tmp:
        test_reopen_stale_completion_requires_new_claim_instead_of_counting_completed(Path(tmp) / "reopen-stale")
    with tempfile.TemporaryDirectory() as tmp:
        test_active_lease_blocks_duplicate_claim(Path(tmp) / "lease")
    with tempfile.TemporaryDirectory() as tmp:
        test_heartbeat_requires_actor_and_session(Path(tmp) / "heartbeat")
    with tempfile.TemporaryDirectory() as tmp:
        test_release_requires_lease_owner(Path(tmp) / "release")
    test_lease_claim_uses_atomic_create()
    with tempfile.TemporaryDirectory() as tmp:
        test_concurrent_claim_allows_only_one_owner(Path(tmp) / "concurrent-claim")
    with tempfile.TemporaryDirectory() as tmp:
        test_lease_heartbeat_and_release_take_exclusive_lock(Path(tmp) / "lease-lock")
    test_event_append_serializes_hash_chain_with_file_lock()
    with tempfile.TemporaryDirectory() as tmp:
        test_event_reads_take_shared_lock(Path(tmp) / "read-lock")
    with tempfile.TemporaryDirectory() as tmp:
        test_concurrent_event_appends_keep_valid_hash_chain(Path(tmp) / "concurrent-events")
    test_authoritative_state_disallows_resume_when_task_blocking_states_exist()
    test_negative_rg_test_plan_command_must_return_zero_on_expected_success()
    test_positive_rg_test_plan_command_is_allowed_without_negation()
    test_negated_rg_test_plan_command_is_allowed_for_expected_no_match()
    test_negative_rg_detection_is_scoped_to_each_fenced_command()
    test_record_override_requires_known_task_and_gate()
    test_record_reopen_requires_known_blocking_task_and_appends_reopen_event()
    with tempfile.TemporaryDirectory() as tmp:
        test_temp_end_to_end_claim_complete_replay_smoke(Path(tmp) / "smoke")

