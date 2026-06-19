#!/usr/bin/env python3
"""Tests for the contract-kernel projection harness."""

from __future__ import annotations

import filecmp
import json
import os
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import generate_snapshots  # noqa: E402
import migrate_legacy_ledger  # noqa: E402
import validate_public_contracts  # noqa: E402
import validate_schema  # noqa: E402
import validate_task_graph  # noqa: E402


def test_schema_and_task_graph_valid() -> None:
    assert validate_schema.main() == 0
    assert validate_task_graph.main() == 0


def test_snapshot_generation_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_snapshots.generate(first)
    generate_snapshots.generate(second)
    for name in generate_snapshots.SNAPSHOT_NAMES:
        assert filecmp.cmp(first / name, second / name, shallow=False), name


def test_source_date_epoch_controls_generated_at(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "123")
    generate_snapshots.generate(tmp_path)
    data = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert data["metadata"]["generated_at"] == "1970-01-01T00:02:03+00:00"


def test_public_snapshots_do_not_contain_private_absolute_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    generate_snapshots.generate(tmp_path)
    combined = "\n".join((tmp_path / name).read_text(encoding="utf-8") for name in generate_snapshots.SNAPSHOT_NAMES)
    assert "C:/Users/OCEAN" not in combined
    assert "C:\\Users\\OCEAN" not in combined


def test_snapshot_check_passes_for_current_committed_projection(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert generate_snapshots.main(["--definitions-only", "--check"]) == 0


def test_migration_report_is_deterministic() -> None:
    first = migrate_legacy_ledger.build_report()
    second = migrate_legacy_ledger.build_report()
    assert first == second
    assert first["migration_id"] == "0001-task-definition-migration"
    assert first["mapping_count"] >= 1


def test_public_contract_scan_valid() -> None:
    assert validate_public_contracts.main() == 0
