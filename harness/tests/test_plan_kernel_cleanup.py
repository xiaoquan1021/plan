#!/usr/bin/env python3
"""Tests for plan-kernel cleanup helpers."""

from __future__ import annotations

import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from plan_kernel_cleanup import clean_markdown_text  # noqa: E402
from audit_xq_zip_analysis import classify_deferred_item  # noqa: E402


def test_removes_execution_record_and_archives_deferred_block() -> None:
    source = "\n".join(
        [
            "# Example",
            "",
            "## Purpose",
            "",
            "Plan text.",
            "",
            "## Execution Record",
            "",
            "Historical source-pass commands, results, and current-behavior notes were moved out.",
            "Index: `<private-execution-records>/by-document/example.md`",
            "Full archive: `<private-execution-records>/by-document/archived-flow-blocks/example.md`",
            "",
            "Do not use the archived text as fresh record. Link new command output under `<private-evidence-dir>/` before changing `ledger/snapshots/tasks.json`.",
            "Deferred:",
            "",
            "```text",
            "expanded interaction beyond the current pass",
            "future payload support",
            "```",
            "",
            "## Acceptance",
            "",
            "- The implementation must pass.",
            "",
            "## Failure Repair",
            "",
            "Repair the owning contract.",
        ]
    )

    result = clean_markdown_text(
        source_path="plans/xq-integrated-rebuild/example.md",
        text=source,
    )

    assert "## Execution Record" not in result.text
    assert "Historical source-pass" not in result.text
    assert "Deferred:" not in result.text
    assert "expanded interaction" not in result.text
    assert "## Acceptance" in result.text
    assert "## Failure Repair" in result.text
    assert len(result.archived_blocks) == 2
    assert result.deferred_archive_items[0]["items"] == [
        "expanded interaction beyond the current pass",
        "future payload support",
    ]


def test_rewrites_entry_register_to_pointer() -> None:
    source = "\n".join(
        [
            "# Entry",
            "",
            "## Purpose",
            "",
            "This file tracks where the plan currently stands, what is complete, what has not started.",
            "",
            "## Deferred Issue Register",
            "",
            "| Issue | Area | Severity | Action timing |",
            "| --- | --- | --- | --- |",
            "| Thing is deferred | Area | Medium | Later |",
            "",
            "## How to Resume Work",
            "",
            "1. Open this file.",
            "2. Update this file only when the entry-document policy or deferred issue register changes.",
        ]
    )

    result = clean_markdown_text(
        source_path="plans/xq-integrated-rebuild/00-execution-entry.md",
        text=source,
    )

    assert "what is complete" not in result.text
    assert "## Deferred Issue Register" not in result.text
    assert "deferred issue register" not in result.text
    assert "Thing is deferred" not in result.text
    assert "Deferred scope is tracked in `ledger/deferred-register.md`" in result.text
    assert len(result.deferred_archive_items) == 1
    assert result.deferred_archive_items[0]["items"] == ["Thing is deferred | Area | Medium | Later"]


def test_rewrites_readme_folder_map_away_from_deferred_register() -> None:
    source = "\n".join(
        [
            "# README",
            "",
            "## Folder Map",
            "",
            "| Folder | Responsibility |",
            "| --- | --- |",
            "| `00-execution-entry.md` | Execution entry, ledger-position pointer, policy notes, and deferred issue register. |",
        ]
    )

    result = clean_markdown_text(
        source_path="plans/xq-integrated-rebuild/README.md",
        text=source,
    )

    assert "deferred issue register" not in result.text
    assert "Execution entry and ledger pointer." in result.text


def test_deferred_pointer_is_not_owner_confirmation() -> None:
    triage = classify_deferred_item(
        "plans/xq-integrated-rebuild/example.md",
        "Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.",
    )

    assert triage["ledger_status"] == "not-a-deferred-boundary"
    assert triage["deferred_bucket"] == "ledger-pointer"


if __name__ == "__main__":
    test_removes_execution_record_and_archives_deferred_block()
    test_rewrites_entry_register_to_pointer()
    test_rewrites_readme_folder_map_away_from_deferred_register()
    test_deferred_pointer_is_not_owner_confirmation()
