#!/usr/bin/env python3
"""Plan repository preflight gates for public CI and local private checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, argv: list[str]) -> dict[str, Any]:
    result = subprocess.run(argv, cwd=str(ROOT), text=True, capture_output=True)
    return {
        "name": name,
        "argv": argv,
        "exit_code": result.returncode,
        "stdout": result.stdout.strip().splitlines()[-10:],
        "stderr": result.stderr.strip().splitlines()[-10:],
    }


def public_steps() -> list[tuple[str, list[str]]]:
    py = sys.executable
    return [
        ("schema validation", [py, "harness/validate_schema.py"]),
        ("task graph validation", [py, "harness/validate_task_graph.py"]),
        ("snapshot check", [py, "harness/generate_snapshots.py", "--definitions-only", "--check"]),
        ("public contract scan", [py, "harness/validate_public_contracts.py"]),
        ("migration fixture check", [py, "harness/migrate_legacy_ledger.py", "--check"]),
    ]


def private_steps(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    steps = public_steps()
    if args.runtime_events and args.completion_records and args.workspace_report:
        steps.append(
            (
                "full private projection",
                [
                    sys.executable,
                    "harness/generate_snapshots.py",
                    "--runtime-events",
                    args.runtime_events,
                    "--completion-records",
                    args.completion_records,
                    "--workspace-report",
                    args.workspace_report,
                    "--public-output",
                    args.public_output,
                    "--check",
                ],
            )
        )
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--runtime-events")
    parser.add_argument("--completion-records")
    parser.add_argument("--workspace-report")
    parser.add_argument("--public-output", default="ledger/snapshots")
    args = parser.parse_args(argv)

    steps = public_steps() if args.public or not args.full else private_steps(args)
    results = [run_step(name, command) for name, command in steps]
    ok = all(item["exit_code"] == 0 for item in results)
    report = {
        "schema_version": 1,
        "mode": "public" if args.public or not args.full else "full",
        "ok": ok,
        "private_runtime_projection": "not run" if args.public or not args.full or not (args.runtime_events and args.completion_records and args.workspace_report) else "run",
        "steps": results,
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
