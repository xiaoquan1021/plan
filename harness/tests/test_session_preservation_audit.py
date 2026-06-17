#!/usr/bin/env python3
"""Tests for session comparison and preservation summary helpers."""

from __future__ import annotations

import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from session_preservation_audit import extract_patch_paths, classify_current_preservation  # noqa: E402


def test_extract_patch_paths_counts_created_plan_files() -> None:
    patch = """*** Begin Patch
*** Add File: plans/example.md
+# Example
*** Update File: plans/xq-integrated-rebuild/README.md
@@
-old
+new
*** End Patch
"""

    changes = extract_patch_paths(patch)

    assert changes == [
        {
            "operation": "add",
            "path": "plans/example.md",
        },
        {
            "operation": "update",
            "path": "plans/xq-integrated-rebuild/README.md",
        },
    ]


def test_classify_current_preservation_requires_task_and_archives() -> None:
    status = classify_current_preservation(
        tasks_count=60,
        archived_blocks=65,
        deferred_archive_rows=149,
        registered_deferred_boundaries=156,
        active_plan_kernel_violations=0,
    )

    assert status["task_layer_preserved"] is True
    assert status["execution_records_preserved"] is True
    assert status["deferred_details_preserved"] is True
    assert status["active_plan_kernel_clean"] is True


if __name__ == "__main__":
    test_extract_patch_paths_counts_created_plan_files()
    test_classify_current_preservation_requires_task_and_archives()
