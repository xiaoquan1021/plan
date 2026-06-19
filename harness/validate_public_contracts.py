#!/usr/bin/env python3
"""Public contract scans that must not depend on private local bindings."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SCAN_ROOTS = [
    ROOT / "README.md",
    ROOT / "docs/adr",
    ROOT / "docs/contracts",
    ROOT / "ledger/README.md",
    ROOT / "ledger/task-definitions",
    ROOT / "ledger/schema",
    ROOT / "ledger/fixtures",
    ROOT / "ledger/migrations",
    ROOT / "config",
    ROOT / ".github/workflows",
    ROOT / "plans/xq-integrated-rebuild/README.md",
    ROOT / "plans/xq-integrated-rebuild/00-execution-entry.md",
]
SNAPSHOT_ROOT = ROOT / "ledger/snapshots"
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".txt"}
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^>\n]*>")
ABSOLUTE_PRIVATE_RE = re.compile(r"(?:[A-Za-z]:[/\\]Users[/\\]|/Users/OCEAN\b|PRIVATE_RUNTIME_LEDGER.*[A-Za-z]:[/\\])")


def iter_public_files() -> list[Path]:
    files: list[Path] = []
    for root in PUBLIC_SCAN_ROOTS:
        if root.is_file():
            files.append(root)
        elif root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(
        path
        for path in files
        if path.suffix in TEXT_SUFFIXES and not path.name.endswith(".local.json") and "__pycache__" not in path.parts
    )


def strip_anchor(target: str) -> str:
    return target.split("#", 1)[0]


def validate_markdown_links(path: Path, text: str, errors: list[str]) -> None:
    if path.suffix != ".md":
        return
    for match in LINK_RE.finditer(text):
        raw_target = match.group(1).strip()
        if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        target = strip_anchor(raw_target)
        if not target:
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = unquote(target)
        if "://" in target:
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {raw_target}")
            continue
        if not resolved.exists():
            errors.append(f"{path.relative_to(ROOT)}: missing link target: {raw_target}")


def validate_public_text(path: Path, text: str, errors: list[str]) -> None:
    if ABSOLUTE_PRIVATE_RE.search(text):
        errors.append(f"{path.relative_to(ROOT)}: contains forbidden private absolute path")
    if PLACEHOLDER_RE.search(text):
        errors.append(f"{path.relative_to(ROOT)}: contains unresolved angle-bracket placeholder")


def validate_snapshot_privacy(errors: list[str]) -> None:
    if not SNAPSHOT_ROOT.exists():
        errors.append("ledger/snapshots: missing snapshot directory")
        return
    for path in sorted(SNAPSHOT_ROOT.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        if ABSOLUTE_PRIVATE_RE.search(text):
            errors.append(f"{path.relative_to(ROOT)}: snapshot contains private absolute path")


def main() -> int:
    errors: list[str] = []
    for path in iter_public_files():
        text = path.read_text(encoding="utf-8")
        validate_public_text(path, text, errors)
        validate_markdown_links(path, text, errors)
    validate_snapshot_privacy(errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("public contract scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
