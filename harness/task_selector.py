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


BLOCKING_STATES = {STATUS_BLOCKED, STATUS_LEASE_EXPIRED, STATUS_STALE_COMPLETION}
CLAIMABLE_STATES = {STATUS_FAILED_RETRY_READY, STATUS_READY}


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
    completed = completed_task_ids(tasks)
    return all(dependency_id in completed for dependency_id in task_dependencies(task))


def dependencies_done(task: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
    return previous_phases_done(task, tasks) and task_dependencies_done(task, tasks)


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
    blocking = [task for task in tasks if task.get("status") in BLOCKING_STATES]
    if blocking:
        return {
            "selected": None,
            "reason": "task-blocking-state-present",
            "blocking_tasks": [
                {"id": task.get("id"), "status": task.get("status")}
                for task in blocking
            ],
            "status_counts": dict(sorted(counts.items())),
        }

    claimable = [
        task
        for task in tasks
        if task.get("status") in CLAIMABLE_STATES
        and dependencies_done(task, tasks)
    ]
    if not claimable:
        return {
            "selected": None,
            "reason": "no-claimable-task-after-dependencies",
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
