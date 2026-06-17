#!/usr/bin/env python3
"""Replace archived execution-flow narrative in plan Markdown with ledger links.

The script is intentionally conservative: it only removes sections or labels
that are already archived by audit_xq_zip_analysis.py into
private execution records. It does not edit generated ledger files.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TREE_ROOT = ROOT / "plans" / "xq-integrated-rebuild"
LEDGER_DIR = ROOT / "ledger"
RECORDS_JSON = LEDGER_DIR / "private-execution-records" / "by-document" / "records.json"
ARCHIVED_BLOCKS_DIR = LEDGER_DIR / "private-execution-records" / "by-document" / "archived-flow-blocks"

CANONICAL_STOP_HEADINGS = {
    "## Purpose",
    "## Owns",
    "## Code Ownership",
    "## Rules",
    "## Implementation Contract",
    "## Step Plan",
    "## Test Plan",
    "## Acceptance",
    "## Failure Repair",
}

REMOVABLE_HEADING_RE = re.compile(
    r"^##\s+(Current Source Pass|Current Source Pass Summary|First-Pass Verification Commands)\s*$"
)
REMOVABLE_LABEL_RE = re.compile(
    r"^(Current behavior|Verified command|Verified commands|Verified result|Result after first source pass):\s*$",
    re.IGNORECASE,
)
REMOVABLE_SOURCE_PASS_LABEL_RE = re.compile(
    r"^[A-Za-z][A-Za-z0-9 /_-]*source pass:\s*$",
    re.IGNORECASE,
)
EXECUTION_RECORD_HEADING = "## Execution Record"
EXECUTION_RECORD_END_MARKER = "Do not use the archived text as fresh record. Link new command output under `<private-evidence-dir>/` before changing `ledger/snapshots/tasks.json`."
PRESERVE_DEFERRED_RE = re.compile(
    r"^(Deferred|Still deferred|Deferred coverage|Deferred source files|Deferred solver fidelity|Deferred domain-specific commands):\s*$",
    re.IGNORECASE,
)


def load_record_map() -> dict[str, str]:
    data = json.loads(RECORDS_JSON.read_text(encoding="utf-8"))
    return {row["path"]: row["record"] for row in data["records"]}


def execution_record_slug(path: str) -> str:
    slug = Path(path).with_suffix("")
    return re.sub(r"[^A-Za-z0-9]+", "-", str(slug)).strip("-").lower()


def replacement_block(source_path: str, record_path: str) -> list[str]:
    archive_record = f"ledger/private-execution-records/by-document/archived-flow-blocks/{execution_record_slug(source_path)}.md"
    return [
        "## Execution Record",
        "",
        "Historical source-pass commands, results, and current-behavior notes were moved out of this plan kernel.",
        f"Index: `{record_path}`",
        f"Full archive: `{archive_record}`",
        "",
        "Do not use the archived text as fresh record. Link new command output under `<private-evidence-dir>/` before changing `ledger/snapshots/tasks.json`.",
    ]


def find_next_stop(lines: list[str], start: int) -> int:
    idx = start
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("## ") and (line in CANONICAL_STOP_HEADINGS or not REMOVABLE_HEADING_RE.match(line)):
            return idx
        idx += 1
    return idx


def find_deferred_preserve_start(lines: list[str], start: int, end: int) -> int | None:
    in_fence = False
    for idx in range(start, end):
        stripped = lines[idx].strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and PRESERVE_DEFERRED_RE.match(stripped):
            return idx
    return None


def find_block_after_label(lines: list[str], start: int) -> int:
    idx = start + 1
    in_fence = False
    saw_fence = False
    while idx < len(lines):
        stripped = lines[idx].strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            saw_fence = True
            idx += 1
            if saw_fence and not in_fence:
                break
            continue
        if not in_fence and lines[idx].startswith("## "):
            break
        idx += 1

    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    return idx


def find_existing_execution_record_end(lines: list[str], start: int) -> int:
    idx = start + 1
    while idx < len(lines):
        if lines[idx] == EXECUTION_RECORD_END_MARKER:
            idx += 1
            while idx < len(lines) and lines[idx].strip() == "":
                idx += 1
            return idx
        if idx != start and lines[idx].startswith("## "):
            return idx
        idx += 1
    return idx


def slim_lines(
    source_rel: str, lines: list[str], record_path: str
) -> tuple[list[str], int, list[dict[str, object]]]:
    output: list[str] = []
    idx = 0
    replacements = 0
    inserted_record_link = EXECUTION_RECORD_HEADING in lines
    removed_blocks: list[dict[str, object]] = []

    while idx < len(lines):
        line = lines[idx]
        if line == EXECUTION_RECORD_HEADING:
            end = find_existing_execution_record_end(lines, idx)
            if not any(existing == EXECUTION_RECORD_HEADING for existing in output):
                output.extend(lines[idx:end])
            else:
                replacements += 1
            idx = end
            continue

        if REMOVABLE_HEADING_RE.match(line):
            end = find_next_stop(lines, idx + 1)
            preserve_start = find_deferred_preserve_start(lines, idx + 1, end)
            removal_end = preserve_start if preserve_start is not None else end
            if not inserted_record_link:
                output.extend(replacement_block(source_rel, record_path))
                inserted_record_link = True
            removed_blocks.append(
                {
                    "start_line": idx + 1,
                    "end_line": removal_end,
                    "kind": "removable-heading-section",
                    "text": "\n".join(lines[idx:removal_end]),
                }
            )
            replacements += 1
            idx = removal_end
            continue

        if REMOVABLE_LABEL_RE.match(line) or REMOVABLE_SOURCE_PASS_LABEL_RE.match(line):
            end = find_block_after_label(lines, idx)
            if not inserted_record_link:
                output.extend(replacement_block(source_rel, record_path))
                inserted_record_link = True
            removed_blocks.append(
                {
                    "start_line": idx + 1,
                    "end_line": end,
                    "kind": "removable-label-block",
                    "text": "\n".join(lines[idx:end]),
                }
            )
            replacements += 1
            idx = end
            continue

        output.append(line)
        idx += 1

    while output and output[-1] == "":
        output.pop()
    return output + [""], replacements, removed_blocks


def write_archived_blocks(source_rel: str, record_path: str, blocks: list[dict[str, object]]) -> str:
    ARCHIVED_BLOCKS_DIR.mkdir(parents=True, exist_ok=True)
    archive = ARCHIVED_BLOCKS_DIR / f"{execution_record_slug(source_rel)}.md"
    lines = [
        f"# Archived Execution-Flow Blocks: {source_rel}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "These blocks were moved out of the source plan Markdown by `slim_execution_flow_markdown.py`.",
        "They are historical execution narrative, not fresh verification record.",
        "",
        f"- Source document: `{source_rel}`",
        f"- Execution-flow index: `{record_path}`",
        f"- Removed blocks: {len(blocks)}",
        "",
    ]
    for index, block in enumerate(blocks, start=1):
        lines.extend(
            [
                f"## Removed Block {index}",
                "",
                f"- Source lines: {block['start_line']}-{block['end_line']}",
                f"- Kind: `{block['kind']}`",
                "",
                "````markdown",
                str(block["text"]),
                "````",
                "",
            ]
        )
    archive.write_text("\n".join(lines), encoding="utf-8")
    return str(archive.relative_to(TREE_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="modify Markdown files")
    args = parser.parse_args()

    record_map = load_record_map()
    changes = []
    archived_records = []
    for source_rel, record_path in sorted(record_map.items()):
        source = ROOT / source_rel
        if not source.exists():
            changes.append({"path": source_rel, "status": "missing-source", "replacements": 0})
            continue
        original = source.read_text(encoding="utf-8", errors="replace")
        lines = original.splitlines()
        new_lines, replacements, removed_blocks = slim_lines(source_rel, lines, record_path)
        new_text = "\n".join(new_lines)
        changed = replacements > 0 and new_text != original
        if changed and args.write:
            source.write_text(new_text, encoding="utf-8")
            archived_records.append(write_archived_blocks(source_rel, record_path, removed_blocks))
        changes.append(
            {
                "path": source_rel,
                "status": "changed" if changed else "unchanged",
                "replacements": replacements,
                "removed_blocks": len(removed_blocks),
                "removed_lines": sum(str(block["text"]).count("\n") + 1 for block in removed_blocks),
                "record": record_path,
            }
        )

    if args.write:
        (ARCHIVED_BLOCKS_DIR / "index.json").write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "archives": archived_records,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    summary = {
        "write": args.write,
        "documents_considered": len(changes),
        "documents_changed": sum(1 for row in changes if row["status"] == "changed"),
        "replacements": sum(row["replacements"] for row in changes),
        "removed_blocks": sum(row.get("removed_blocks", 0) for row in changes),
        "removed_lines": sum(row.get("removed_lines", 0) for row in changes),
        "changes": changes,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
