#!/usr/bin/env python3
"""Generate deterministic public ledger snapshots."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from projection import SNAPSHOT_NAMES, ProjectionError, build_snapshots, canonical_bytes, repo_relative, write_snapshots


ROOT = Path(__file__).resolve().parents[1]


def read_snapshot(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def compare_snapshot_data(generated_dir: Path, committed_dir: Path) -> list[str]:
    diffs: list[str] = []
    for name in SNAPSHOT_NAMES:
        generated_path = generated_dir / name
        committed_path = committed_dir / name
        if not committed_path.exists():
            diffs.append(f"{name}: missing committed snapshot")
            continue
        generated_bytes = generated_path.read_bytes()
        committed_bytes = committed_path.read_bytes()
        if generated_bytes == committed_bytes:
            continue
        try:
            generated = read_snapshot(generated_path)
            committed = read_snapshot(committed_path)
        except json.JSONDecodeError:
            diffs.append(f"{name}: differs and at least one side is invalid JSON")
            continue
        if generated != committed:
            generated_keys = set(generated.keys()) if isinstance(generated, dict) else set()
            committed_keys = set(committed.keys()) if isinstance(committed, dict) else set()
            key_diff = sorted(generated_keys ^ committed_keys)
            if key_diff:
                diffs.append(f"{name}: top-level keys differ: {key_diff}")
            else:
                diffs.append(f"{name}: content differs under shared keys")
        else:
            diffs.append(f"{name}: byte formatting differs")
    return diffs


def generate_to(
    output: Path,
    *,
    definitions_only: bool,
    runtime_events: str | None = None,
    completion_records: str | None = None,
    workspace_report: str | None = None,
) -> dict[str, Path]:
    snapshots = build_snapshots(
        definitions_only=definitions_only,
        runtime_events=Path(runtime_events) if runtime_events else None,
        completion_records=Path(completion_records) if completion_records else None,
        workspace_report=Path(workspace_report) if workspace_report else None,
    )
    return write_snapshots(snapshots, output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--definitions-only", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--runtime-events")
    parser.add_argument("--completion-records")
    parser.add_argument("--workspace-report")
    parser.add_argument("--public-output", default="ledger/snapshots")
    args = parser.parse_args(argv)

    output = ROOT / args.public_output
    definitions_only = bool(args.definitions_only or not any([args.runtime_events, args.completion_records, args.workspace_report]))
    try:
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                temp_output = Path(tmp)
                generate_to(
                    temp_output,
                    definitions_only=definitions_only,
                    runtime_events=args.runtime_events,
                    completion_records=args.completion_records,
                    workspace_report=args.workspace_report,
                )
                diffs = compare_snapshot_data(temp_output, output)
                if diffs:
                    for diff in diffs:
                        print(diff, file=sys.stderr)
                    return 1
                print("snapshot check passed")
                return 0
        generate_to(
            output,
            definitions_only=definitions_only,
            runtime_events=args.runtime_events,
            completion_records=args.completion_records,
            workspace_report=args.workspace_report,
        )
    except (ProjectionError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"snapshot generation failed: {exc}", file=sys.stderr)
        return 1
    print(f"generated snapshots in {repo_relative(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
