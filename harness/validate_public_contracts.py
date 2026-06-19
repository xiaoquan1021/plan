#!/usr/bin/env python3
"""Public contract scans that must not depend on private local bindings."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
STATUS_MANIFEST = ROOT / "docs/contracts/public-plan-document-status.json"
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
    ROOT / "plans/xq-integrated-rebuild",
    ROOT / "plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md",
]
SNAPSHOT_ROOT = ROOT / "ledger/snapshots"
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".txt"}
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^>\n]*>")
ABSOLUTE_PRIVATE_RE = re.compile(r"(?:[A-Za-z]:[/\\]Users[/\\]|/Users/OCEAN\b|PRIVATE_RUNTIME_LEDGER.*[A-Za-z]:[/\\])")


def load_status_manifest() -> dict:
    return json.loads(STATUS_MANIFEST.read_text(encoding="utf-8"))


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


def repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_historical(path: Path, manifest: dict) -> bool:
    relative = repo_path(path)
    if relative in set(manifest.get("active_documents", [])):
        return False
    for root in manifest.get("historical_roots", []):
        if relative == root or relative.startswith(root.rstrip("/") + "/"):
            return True
    return False


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
            errors.append(f"{repo_path(path)}: link escapes repository: {raw_target}")
            continue
        if not resolved.exists():
            errors.append(f"{repo_path(path)}: missing link target: {raw_target}")


def validate_public_text(path: Path, text: str, errors: list[str], *, historical: bool) -> None:
    if ABSOLUTE_PRIVATE_RE.search(text):
        errors.append(f"{repo_path(path)}: contains forbidden private absolute path")
    if PLACEHOLDER_RE.search(text) and not historical:
        errors.append(f"{repo_path(path)}: active document contains unresolved angle-bracket placeholder")
    if not historical and "audit_xq_zip_analysis.py" in text:
        errors.append(f"{repo_path(path)}: active document references legacy audit as execution gate")
    forbidden_completion_claims = [
        "legacy completed is current implementation completion",
        "old completed is current implementation completion",
        "completed statuses are implementation completion",
    ]
    lowered = text.lower()
    if not historical and any(claim in lowered for claim in forbidden_completion_claims):
        errors.append(f"{repo_path(path)}: active document claims legacy completed is current implementation completion")


def validate_historical_manifest(path: Path, text: str, errors: list[str], *, historical: bool) -> None:
    if not historical or path.suffix != ".md":
        return
    # Historical docs do not need invasive front matter rewrites; the public
    # status manifest is the authoritative metadata. This check verifies they
    # are covered by that manifest and cannot silently become active inputs.
    if not STATUS_MANIFEST.exists():
        errors.append(f"{repo_path(path)}: historical document status manifest missing")


def validate_snapshot_privacy(errors: list[str]) -> None:
    if not SNAPSHOT_ROOT.exists():
        errors.append("ledger/snapshots: missing snapshot directory")
        return
    allowed = {"tasks.json", "task-graph.json", "public-state-summary.json", "task-runtime-summary.json"}
    for path in sorted(SNAPSHOT_ROOT.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        if ABSOLUTE_PRIVATE_RE.search(text):
            errors.append(f"{repo_path(path)}: snapshot contains private absolute path")
        if path.name not in allowed:
            errors.append(f"{repo_path(path)}: old snapshot is not an active projection")


def main() -> int:
    errors: list[str] = []
    manifest = load_status_manifest()
    for path in iter_public_files():
        text = path.read_text(encoding="utf-8")
        historical = is_historical(path, manifest)
        validate_public_text(path, text, errors, historical=historical)
        validate_historical_manifest(path, text, errors, historical=historical)
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
