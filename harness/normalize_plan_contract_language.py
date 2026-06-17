#!/usr/bin/env python3
"""Normalize source-pass wording in active plan Markdown.

This migration rewrites active plan documents away from time-based execution
language such as "current source pass" or "latest source pass" and toward
stable contract language. It does not touch generated ledger files or archived
execution records.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TREE_ROOT = ROOT / "plans" / "xq-integrated-rebuild"


LINE_REWRITES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^Current decoded VTI source pass owns:\s*$"), "Decoded VTI contract owns:"),
    (re.compile(r"^Existing TIFF source pass owns:\s*$"), "Existing TIFF contract owns:"),
    (re.compile(r"^Current unified image dispatch source pass owns:\s*$"), "Unified image dispatch contract owns:"),
    (re.compile(r"^Current Qt adapter source pass owns:\s*$"), "Qt adapter contract owns:"),
    (re.compile(r"^Current QTreeView widget source pass owns:\s*$"), "QTreeView widget contract owns:"),
    (re.compile(r"^Current source pass owns:\s*$"), "Implementation Contract owns:"),
    (re.compile(r"^Current source pass covers:\s*$"), "Implementation Contract covers:"),
    (re.compile(r"^Current source pass:\s*$"), "Implementation Contract:"),
    (re.compile(r"^The latest hardening passes reject\b"), "This document rejects"),
    (re.compile(r"^The latest source pass\b"), "This document"),
    (re.compile(r"^The current source pass\b"), "This document"),
    (re.compile(r"^The previous source passes\b"), "Earlier implementation work"),
    (re.compile(r"^The first source pass\b"), "The initial implementation"),
    (re.compile(r"^The first ([^:]+?) source pass\b"), r"The initial \1 implementation"),
    (re.compile(r"^The latest ([^:]+?) source pass\b"), r"The \1 contract"),
    (re.compile(r"^The current ([^:]+?) source pass\b"), r"The \1 contract"),
    (re.compile(r"^The repeated ([^:]+?) source pass\b"), r"The repeated \1 contract"),
    (re.compile(r"^After the first 0007 acceptance source pass\b"), "After the 0007 acceptance implementation"),
    (re.compile(r"^The first 0007 acceptance source pass\b"), "The 0007 acceptance implementation"),
]

PHRASE_REWRITES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bcurrent source pass\b", re.IGNORECASE), "current contract"),
    (re.compile(r"\bcurrent source passes\b", re.IGNORECASE), "current contracts"),
    (re.compile(r"\blatest source pass\b", re.IGNORECASE), "current contract"),
    (re.compile(r"\blatest source passes\b", re.IGNORECASE), "current contracts"),
    (re.compile(r"\bthe first source passes created\b", re.IGNORECASE), "The implementation contract includes"),
    (re.compile(r"\bfirst source passes\b", re.IGNORECASE), "initial implementation contracts"),
    (re.compile(r"\bprevious source passes\b", re.IGNORECASE), "earlier implementation work"),
    (re.compile(r"\bfirst source pass\b", re.IGNORECASE), "initial implementation"),
    (re.compile(r"\bsource passes\b", re.IGNORECASE), "implementation contracts"),
    (re.compile(r"\bin this source pass\b", re.IGNORECASE), "in this document"),
    (re.compile(r"\bduring this source pass\b", re.IGNORECASE), "during this implementation stage"),
    (re.compile(r"\bfor this source pass\b", re.IGNORECASE), "for this implementation stage"),
    (re.compile(r"\bsource pass proves\b", re.IGNORECASE), "acceptance requires"),
    (re.compile(r"\bsource pass applies\b", re.IGNORECASE), "contract applies"),
    (re.compile(r"\bsource pass creates\b", re.IGNORECASE), "document defines"),
    (re.compile(r"\bsource pass adds\b", re.IGNORECASE), "document adds"),
    (re.compile(r"\bsource pass moves\b", re.IGNORECASE), "document moves"),
    (re.compile(r"\bsource pass centralizes\b", re.IGNORECASE), "document centralizes"),
    (re.compile(r"\bsource pass treats\b", re.IGNORECASE), "document treats"),
    (re.compile(r"\bsource pass converts\b", re.IGNORECASE), "document converts"),
    (re.compile(r"\bsource pass centralizes\b", re.IGNORECASE), "document centralizes"),
    (re.compile(r"\bsource pass uses\b", re.IGNORECASE), "document uses"),
    (re.compile(r"\bsource pass reads\b", re.IGNORECASE), "document reads"),
    (re.compile(r"\bsource pass emits\b", re.IGNORECASE), "document emits"),
    (re.compile(r"\bsource pass must create\b", re.IGNORECASE), "document must define"),
    (re.compile(r"\bsource pass does not\b", re.IGNORECASE), "document does not"),
    (re.compile(r"\bsource pass can\b", re.IGNORECASE), "document can"),
    (re.compile(r"\bsource pass owns\b", re.IGNORECASE), "contract owns"),
    (re.compile(r"\bsource pass covers\b", re.IGNORECASE), "contract covers"),
    (re.compile(r"\bsource pass\b", re.IGNORECASE), "contract"),
]


def active_plan_docs() -> list[Path]:
    docs: list[Path] = []
    for path in sorted(TREE_ROOT.rglob("*.md")):
        rel = path.relative_to(TREE_ROOT)
        if any(part.startswith("_") for part in rel.parts):
            continue
        docs.append(path)
    return docs


def rewrite_line(line: str) -> str:
    updated = line
    for pattern, replacement in LINE_REWRITES:
        updated = pattern.sub(replacement, updated)
    for pattern, replacement in PHRASE_REWRITES:
        updated = pattern.sub(replacement, updated)
    return updated


def normalize_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    lines = original.splitlines()
    rewritten = [rewrite_line(line) for line in lines]
    text = "\n".join(rewritten)
    if text != original.rstrip("\n"):
        path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
        return True
    return False


def main() -> int:
    changed: list[str] = []
    for path in active_plan_docs():
        if normalize_file(path):
            changed.append(str(path.relative_to(ROOT)))
    for item in changed:
        print(item)
    print(f"changed={len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
