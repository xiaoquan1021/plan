#!/usr/bin/env python3
"""Validate task definition graph integrity."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_jsonish(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_tasks() -> dict[str, dict[str, Any]]:
    index = load_jsonish(ROOT / "ledger/task-definitions/index.yaml")
    tasks: dict[str, dict[str, Any]] = {}
    for entry in index["task_definitions"]:
        task = load_jsonish(ROOT / entry["path"])
        task_id = task["task_id"]
        if task_id in tasks:
            raise ValueError(f"duplicate task id: {task_id}")
        tasks[task_id] = task
    return tasks


def find_cycle(tasks: dict[str, dict[str, Any]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(task_id: str) -> list[str] | None:
        if task_id in visiting:
            start = stack.index(task_id)
            return stack[start:] + [task_id]
        if task_id in visited:
            return None
        visiting.add(task_id)
        stack.append(task_id)
        for dep in tasks[task_id].get("dependencies", []):
            if dep in tasks:
                cycle = visit(dep)
                if cycle:
                    return cycle
        visiting.remove(task_id)
        visited.add(task_id)
        stack.pop()
        return None

    for task_id in tasks:
        cycle = visit(task_id)
        if cycle:
            return cycle
    return None


def main() -> int:
    errors: list[str] = []
    try:
        tasks = load_tasks()
    except Exception as exc:  # noqa: BLE001
        print(f"failed to load tasks: {exc}", file=sys.stderr)
        return 1

    for task_id, task in tasks.items():
        for dep in task.get("dependencies", []):
            if dep not in tasks:
                errors.append(f"{task_id}: missing dependency {dep}")
        for source in task.get("source_contracts", []):
            if not (ROOT / source).exists():
                errors.append(f"{task_id}: missing source contract {source}")

    cycle = find_cycle(tasks)
    if cycle:
        errors.append("dependency cycle: " + " -> ".join(cycle))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"task graph validation passed ({len(tasks)} tasks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
