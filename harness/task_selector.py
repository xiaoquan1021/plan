#!/usr/bin/env python3
"""Task dependency and selection logic for the XQ ledger harness."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ledger_models import (
    DEPENDENCY_PHASES,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_FAILED_RETRY_READY,
    STATUS_LEASE_EXPIRED,
    STATUS_NOT_EXECUTABLE,
    STATUS_READY,
    STATUS_STALE_COMPLETION,
    task_phase,
)


CLAIMABLE_STATES = {STATUS_FAILED_RETRY_READY, STATUS_READY}
TERMINAL_OK_STATES = {STATUS_COMPLETED}
TASK_LOCAL_BLOCKING_STATES = {STATUS_BLOCKED, STATUS_LEASE_EXPIRED, STATUS_STALE_COMPLETION}


def phase_index(phase: str) -> int:
    try:
        return DEPENDENCY_PHASES.index(phase)
    except ValueError:
        return len(DEPENDENCY_PHASES)


def task_sort_key(task: dict[str, Any]) -> tuple[int, int, str]:
    status_priority = 0 if task.get("status") == STATUS_FAILED_RETRY_READY else 1
    return (status_priority, phase_index(task_phase(task)), str(task.get("id")))


def completed_phases(tasks: list[dict[str, Any]]) -> set[str]:
    phases = set()
    for phase in DEPENDENCY_PHASES:
        phase_tasks = [
            task
            for task in tasks
            if task_phase(task) == phase and task.get("status") != STATUS_NOT_EXECUTABLE
        ]
        if phase_tasks and all(task.get("status") == STATUS_COMPLETED for task in phase_tasks):
            phases.add(phase)
    return phases


def task_dependencies(task: dict[str, Any]) -> list[str]:
    dependencies: list[str] = []
    for key in ("task_dependencies", "depends_on"):
        raw = task.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            raw_items = [raw]
        elif isinstance(raw, list):
            raw_items = raw
        else:
            continue
        for item in raw_items:
            if isinstance(item, str) and item and item not in dependencies:
                dependencies.append(item)
    return dependencies


def completed_task_ids(tasks: list[dict[str, Any]]) -> set[str]:
    return {
        str(task.get("id"))
        for task in tasks
        if task.get("id") and task.get("status") == STATUS_COMPLETED
    }


def accepted_task_ids(tasks: list[dict[str, Any]]) -> set[str]:
    return {
        str(task.get("id"))
        for task in tasks
        if task.get("id") and task.get("status") in TERMINAL_OK_STATES
    }


def previous_phases_done(task: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
    phase = task_phase(task)
    index = phase_index(phase)
    if index == 0:
        return True
    completed = completed_phases(tasks)
    for previous in DEPENDENCY_PHASES[:index]:
        previous_tasks = [
            item
            for item in tasks
            if task_phase(item) == previous and item.get("status") != STATUS_NOT_EXECUTABLE
        ]
        if previous_tasks and previous not in completed:
            return False
    return True


def task_dependencies_done(task: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
    completed = accepted_task_ids(tasks)
    return all(dependency_id in completed for dependency_id in task_dependencies(task))


def dependencies_done(task: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
    # The new contract model uses explicit task dependencies. Legacy phase
    # ordering is kept in graph metadata but must not globally block unrelated
    # plan-rewrite tasks.
    return task_dependencies_done(task, tasks)


def task_local_blockers(task: dict[str, Any], tasks: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    by_id = {str(item.get("id")): item for item in tasks if item.get("id")}
    for dependency_id in task_dependencies(task):
        dependency = by_id.get(dependency_id)
        if dependency is None:
            blockers.append(f"missing dependency {dependency_id}")
        elif dependency.get("status") in TASK_LOCAL_BLOCKING_STATES:
            blockers.append(f"dependency {dependency_id} is {dependency.get('status')}")
        elif dependency.get("status") not in TERMINAL_OK_STATES:
            blockers.append(f"dependency {dependency_id} is not completed")
    if task.get("decision_state") in {"open", "proposed"} and task.get("task_kind") not in {"plan-contract", "harness"}:
        blockers.append(f"decision_state is {task.get('decision_state')}")
    if task.get("task_kind") in {"implementation", "acceptance"}:
        if not task.get("task_pack_path"):
            blockers.append("task pack is missing")
        if task.get("task_pack_schema_valid") is False:
            blockers.append("task pack schema invalid")
        if task.get("issuance_status") != "issued":
            blockers.append(f"task pack is {task.get('issuance_status') or 'missing'}")
        if task.get("execution_ready") is False:
            blockers.append("execution_ready is false")
        for key in ["base_commit", "rollback_point", "worktree_binding"]:
            if not task.get(key):
                blockers.append(f"{key} is missing")
        if task.get("task_pack_hash_valid") is False:
            blockers.append("task pack hash mismatch")
        if task.get("epic_contract_status") not in {None, "approved"}:
            blockers.append("epic contract is not approved")
    return blockers


def dependency_violations(tasks: list[dict[str, Any]]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    completed = completed_task_ids(tasks)
    for task in tasks:
        if task.get("status") != STATUS_COMPLETED:
            continue
        if not previous_phases_done(task, tasks):
            violations.append(
                {
                    "task_id": str(task.get("id")),
                    "phase": task_phase(task),
                    "reason": "completed task has incomplete dependency phase",
                }
            )
        for dependency_id in task_dependencies(task):
            if dependency_id not in completed:
                violations.append(
                    {
                        "task_id": str(task.get("id")),
                        "dependency_task_id": dependency_id,
                        "reason": "completed task has incomplete task dependency",
                    }
                )
    return violations


def explain_selection(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(task.get("status")) for task in tasks)
    skipped: list[dict[str, Any]] = []
    claimable = [
        task
        for task in tasks
        if task.get("status") in CLAIMABLE_STATES
        and dependencies_done(task, tasks)
        and not task_local_blockers(task, tasks)
    ]
    for task in tasks:
        if task.get("status") in CLAIMABLE_STATES and task not in claimable:
            blockers = task_local_blockers(task, tasks)
            if blockers or not dependencies_done(task, tasks):
                skipped.append({"id": task.get("id"), "blockers": blockers or ["dependencies incomplete"]})
    if not claimable:
        return {
            "selected": None,
            "reason": "no-claimable-task-after-dependencies",
            "skipped_tasks": skipped,
            "status_counts": dict(sorted(counts.items())),
        }
    selected = sorted(claimable, key=task_sort_key)[0]
    return {
        "selected": selected,
        "reason": "selected-by-failed-retry-then-dependency-order",
        "status_counts": dict(sorted(counts.items())),
    }


def select_next_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    return explain_selection(tasks).get("selected")


def build_task_graph(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = []
    edges = []
    for task in tasks:
        phase = task_phase(task)
        phase_position = phase_index(phase)
        dependencies = []
        if task.get("status") != STATUS_NOT_EXECUTABLE:
            for previous_phase in DEPENDENCY_PHASES[:phase_position]:
                if any(task_phase(item) == previous_phase and item.get("status") != STATUS_NOT_EXECUTABLE for item in tasks):
                    dependencies.append(previous_phase)
        explicit_task_dependencies = task_dependencies(task)
        for dependency_id in explicit_task_dependencies:
            edges.append(
                {
                    "from": dependency_id,
                    "to": task.get("id"),
                    "kind": "task",
                }
            )
        nodes.append(
            {
                "id": task.get("id"),
                "source_md": task.get("source_md"),
                "status": task.get("status"),
                "phase": phase,
                "phase_index": phase_position,
                "phase_dependencies": dependencies,
                "task_dependencies": explicit_task_dependencies,
            }
        )
    return {"schema_version": 1, "dependency_phases": DEPENDENCY_PHASES, "nodes": nodes, "edges": edges}
