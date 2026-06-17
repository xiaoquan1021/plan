#!/usr/bin/env python3
"""Clean plan Markdown down to plan kernel and archive removed blocks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
TREE_ROOT = ROOT / "plans" / "xq-integrated-rebuild"
LEDGER_DIR = ROOT / "ledger"
EXEC_DIR = LEDGER_DIR / "private-execution-records" / "by-document"
ARCHIVE_PATH = EXEC_DIR / "plan-kernel-cleanup-archive.md"
DEFERRED_ARCHIVE_PATH = LEDGER_DIR / "deferred-archive.jsonl"
POLICY_PATH = LEDGER_DIR / "plan-kernel-policy.md"

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

EXECUTION_RECORD_HEADING = "## Execution Record"
EXECUTION_RECORD_END_MARKER = (
    "Do not use the archived text as fresh record. Link new command output under `<private-evidence-dir>/` before changing `ledger/snapshots/tasks.json`."
)
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
DEFERRED_LABEL_RE = re.compile(
    r"^(Deferred|Still deferred|Deferred coverage|Deferred source files|Deferred solver fidelity|Deferred domain-specific commands):\s*$",
    re.IGNORECASE,
)
DEFERRED_POINTER = "Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record."


@dataclass
class CleanupResult:
    text: str
    archived_blocks: list[dict[str, object]] = field(default_factory=list)
    deferred_archive_items: list[dict[str, object]] = field(default_factory=list)


def active_markdown_files() -> list[Path]:
    return [
        path
        for path in sorted(TREE_ROOT.rglob("*.md"))
        if not any(part.startswith("_") for part in path.relative_to(TREE_ROOT).parts)
    ]


def rel_to_root(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _find_next_heading(lines: list[str], start: int) -> int:
    idx = start
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("## ") and line not in CANONICAL_STOP_HEADINGS and not REMOVABLE_HEADING_RE.match(line):
            return idx
        idx += 1
    return idx


def _find_block_after_label(lines: list[str], start: int) -> int:
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


def _find_existing_execution_record_end(lines: list[str], start: int) -> int:
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


def _collect_deferred_items(block_lines: list[str]) -> list[str]:
    items: list[str] = []
    in_fence = False
    for line in block_lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            if stripped:
                items.append(stripped)
            continue
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
        elif stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and cells[0] and cells[0] not in {"---", "Issue", "Deferred issue"}:
                items.append(" | ".join(cells))
        elif stripped and not stripped.startswith("##"):
            items.append(stripped)
    return items


def clean_markdown_text(source_path: str, text: str) -> CleanupResult:
    lines = text.splitlines()
    output: list[str] = []
    archived_blocks: list[dict[str, object]] = []
    deferred_archive_items: list[dict[str, object]] = []
    idx = 0
    entry_doc = source_path.endswith("00-execution-entry.md")

    while idx < len(lines):
        line = lines[idx]

        if entry_doc and line == "## Purpose":
            output.append(line)
            output.extend(
                [
                    "",
                    "This is the fixed entry point for executing the XQ integrated rebuild plan.",
                    "",
                    "Use this document first, then follow the owning child document for the current layer or feature. This file is an entry pointer, not a status ledger.",
                    "",
                ]
            )
            idx += 1
            while idx < len(lines) and not lines[idx].startswith("## "):
                idx += 1
            continue

        if entry_doc and line == "## Completion Meaning":
            idx = _find_next_heading(lines, idx + 1)
            continue

        if entry_doc and line == "## Deferred Issue Register":
            end = _find_next_heading(lines, idx + 1)
            block_lines = lines[idx + 1 : end]
            deferred_archive_items.append(
                {
                    "source_path": source_path,
                    "section": "Deferred Issue Register",
                    "items": _collect_deferred_items(block_lines),
                }
            )
            output.extend(
                [
                    "## Ledger Position",
                    "",
                    "Plan-position text is no longer stored in this entry document. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in:",
                    "",
                    "- [audit ledger README](../ledger/README.md)",
                    "- [tasks.json](../ledger/snapshots/tasks.json)",
                    "- [source inventory](../ledger/source-inventory.md)",
                    "- [by-document execution index](../README.md#what-is-not-included)",
                    "",
                    "Do not resume implementation from historical batch summaries or test-count text. Pick repair or implementation work only from `ledger/snapshots/tasks.json` after ledger reconciliation.",
                    "",
                    DEFERRED_POINTER,
                    "",
                ]
            )
            idx = end
            continue

        if line == EXECUTION_RECORD_HEADING:
            end = _find_existing_execution_record_end(lines, idx)
            archived_blocks.append(
                {
                    "source_path": source_path,
                    "kind": "execution-record",
                    "text": "\n".join(lines[idx:end]),
                }
            )
            idx = end
            continue

        if REMOVABLE_HEADING_RE.match(line) or REMOVABLE_LABEL_RE.match(line) or REMOVABLE_SOURCE_PASS_LABEL_RE.match(line) or DEFERRED_LABEL_RE.match(line):
            end = _find_block_after_label(lines, idx) if ":" in line or REMOVABLE_LABEL_RE.match(line) or REMOVABLE_SOURCE_PASS_LABEL_RE.match(line) or DEFERRED_LABEL_RE.match(line) else _find_next_heading(lines, idx + 1)
            if DEFERRED_LABEL_RE.match(line):
                deferred_archive_items.append(
                    {
                        "source_path": source_path,
                        "section": line.strip().rstrip(":"),
                        "items": _collect_deferred_items(lines[idx + 1 : end]),
                    }
                )
                if DEFERRED_POINTER not in output:
                    output.extend(
                        [
                            DEFERRED_POINTER,
                            "",
                        ]
                    )
            archived_blocks.append(
                {
                    "source_path": source_path,
                    "kind": "removable-block",
                    "text": "\n".join(lines[idx:end]),
                }
            )
            idx = end
            continue

        output.append(line)
        idx += 1

    cleaned = "\n".join(output).rstrip() + "\n"
    cleaned = normalize_status_language(cleaned)
    if entry_doc:
        cleaned = cleaned.replace(
            "This file tracks where the plan currently stands, what is complete, what has not started, and which possible issues should be recorded without immediate repair.",
            "Use this document first, then follow the owning child document for the current layer or feature. This file is an entry pointer, not a status ledger.",
        )
        cleaned = remove_section(cleaned, "Status Matrix")
        cleaned = collapse_duplicate_section(cleaned, "Ledger Position")
        cleaned = cleaned.replace(
            "Update this file only when the entry-document policy or deferred issue register changes.",
            "Update this file only when the entry-document policy changes.",
        )
    if source_path.endswith("README.md"):
        cleaned = cleaned.replace(
            "| `00-execution-entry.md` | Execution entry, ledger-position pointer, policy notes, and deferred issue register. |",
            "| `00-execution-entry.md` | Execution entry and ledger pointer. |",
        )
    return CleanupResult(
        text=cleaned,
        archived_blocks=archived_blocks,
        deferred_archive_items=deferred_archive_items,
    )


def normalize_status_language(text: str) -> str:
    replacements = [
        ("initial implementation", "initial contract"),
        ("Initial implementation", "Initial contract"),
        ("Implemented initial contract:", "Contract scope:"),
        ("## initial contract Scope", "## Initial Contract Scope"),
        ("currently implemented payloads", "supported payloads"),
        ("currently visible category", "visible category"),
        ("currently hidden category", "hidden category"),
        ("currently has no", "does not yet define"),
        ("currently stores", "stores"),
        ("first-pass supports", "initial contract supports"),
        ("source pass", "source stage"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def remove_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    idx = 0
    marker = f"## {heading}"
    while idx < len(lines):
        if lines[idx] == marker:
            idx += 1
            while idx < len(lines) and not lines[idx].startswith("## "):
                idx += 1
            continue
        output.append(lines[idx])
        idx += 1
    return "\n".join(output).rstrip() + "\n"


def collapse_duplicate_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    idx = 0
    seen = False
    marker = f"## {heading}"
    while idx < len(lines):
        if lines[idx] == marker:
            if seen:
                idx += 1
                while idx < len(lines) and not lines[idx].startswith("## "):
                    idx += 1
                continue
            seen = True
        output.append(lines[idx])
        idx += 1
    return "\n".join(output).rstrip() + "\n"


def _archive_id(source_path: str, section: str, index: int) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", f"{source_path}-{section}-{index}").strip("-").lower()
    return f"deferred-archive-{slug}"


def render_policy() -> str:
    return "\n".join(
        [
            "# Plan Kernel Policy",
            "",
            "Active Markdown under `plans/xq-integrated-rebuild/` is a plan kernel, not an execution record.",
            "",
            "## Allowed",
            "",
            "- Purpose, Owns, Rules, Implementation Contract, Step Plan, Test Plan, Acceptance, and Failure Repair.",
            "- Stable future-facing contract language such as `must`, `reject`, `preserve`, and `route`.",
            "- Short links to `ledger/snapshots/tasks.json`, `ledger/deferred-register.md`, and generated execution indexes.",
            "",
            "## Disallowed",
            "",
            "- `## Execution Record` sections or historical execution-record pointers.",
            "- Historical source-pass, verified command, verified result, current-behavior, or test-count text.",
            "- Deferred detail blocks; deferred boundaries are tracked in `ledger/deferred-register.md`.",
            "- Entry-document status summaries such as current cursor, completed batches, or implementation status.",
            "",
        ]
    )


def render_archive(blocks: list[dict[str, object]], deferred_items: list[dict[str, object]]) -> str:
    lines = [
        "# Plan Kernel Cleanup Archive",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "This file records text moved out of active plan Markdown during plan-kernel cleanup.",
        "It is historical context, not fresh record and not task completion state.",
        "",
        "## Summary",
        "",
        f"- Archived blocks: {len(blocks)}",
        f"- Deferred archive groups: {len(deferred_items)}",
        "",
    ]
    for index, block in enumerate(blocks, start=1):
        lines.extend(
            [
                f"## Archived Block {index}",
                "",
                f"- Source: `{block['source_path']}`",
                f"- Kind: `{block['kind']}`",
                "",
                "````markdown",
                str(block["text"]),
                "````",
                "",
            ]
        )
    lines.extend(["## Deferred Archive Groups", ""])
    for index, item in enumerate(deferred_items, start=1):
        lines.extend(
            [
                f"### Deferred Group {index}",
                "",
                f"- Source: `{item['source_path']}`",
                f"- Section: `{item['section']}`",
                "",
            ]
        )
        for value in item.get("items", []):
            lines.append(f"- {value}")
        lines.append("")
    return "\n".join(lines)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def normalize_deferred_archive(groups: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group_index, group in enumerate(groups, start=1):
        source_path = str(group["source_path"])
        section = str(group["section"])
        for item_index, item in enumerate(group.get("items", []), start=1):
            text = str(item).strip()
            if not text:
                continue
            rows.append(
                {
                    "archive_id": _archive_id(source_path, section, item_index),
                    "source_path": source_path,
                    "section": section,
                    "item_index": item_index,
                    "text_excerpt": text,
                    "text_sha256": sha256(text.encode("utf-8", errors="replace")).hexdigest(),
                    "archive_source": str(ARCHIVE_PATH.relative_to(TREE_ROOT)),
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="modify active Markdown files and write archives")
    args = parser.parse_args()

    changes = []
    archived_blocks: list[dict[str, object]] = []
    deferred_groups: list[dict[str, object]] = []
    for path in active_markdown_files():
        source_rel = rel_to_root(path)
        original = path.read_text(encoding="utf-8", errors="replace")
        result = clean_markdown_text(source_rel, original)
        changed = result.text != original
        if changed and args.write:
            path.write_text(result.text, encoding="utf-8")
        archived_blocks.extend(result.archived_blocks)
        deferred_groups.extend(result.deferred_archive_items)
        changes.append(
            {
                "path": source_rel,
                "changed": changed,
                "archived_blocks": len(result.archived_blocks),
                "deferred_groups": len(result.deferred_archive_items),
            }
        )

    deferred_rows = normalize_deferred_archive(deferred_groups)
    if args.write:
        EXEC_DIR.mkdir(parents=True, exist_ok=True)
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        if archived_blocks or not ARCHIVE_PATH.exists():
            ARCHIVE_PATH.write_text(render_archive(archived_blocks, deferred_groups), encoding="utf-8")
        POLICY_PATH.write_text(render_policy(), encoding="utf-8")
        if deferred_rows or not DEFERRED_ARCHIVE_PATH.exists():
            write_jsonl(DEFERRED_ARCHIVE_PATH, deferred_rows)

    print(
        json.dumps(
            {
                "write": args.write,
                "documents_considered": len(changes),
                "documents_changed": sum(1 for row in changes if row["changed"]),
                "archived_blocks": len(archived_blocks),
                "deferred_groups": len(deferred_groups),
                "deferred_archive_rows": len(deferred_rows),
                "changes": changes,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
