#!/usr/bin/env python3
"""Completion record validation for XQ ledger task completion."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any

from command_runner import validate_command_entry_against_artifact
from ledger_models import (
    EVIDENCE_SCHEMA_VERSION,
    ROOT,
    TREE_ROOT,
    file_sha256,
    resolve_tree_path,
    sha256_text,
)


VALID_ACCEPTANCE_STATUSES = {"passed", "failed", "not-applicable"}
VALID_SOURCE_SECTIONS = {"Acceptance", "Test Plan"}
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?P<item>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\[[ xX]\]\s+")
HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
SHELL_PROMPT_RE = re.compile(r"^(?:\$|>)\s+")


class CompletionRecordError(Exception):
    """Raised when record cannot support a ledger completion."""


def _require(data: dict[str, Any], key: str, errors: list[str]) -> Any:
    value = data.get(key)
    if value in (None, ""):
        errors.append(f"missing required field: {key}")
    return value


def _is_list(value: Any, key: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
        return []
    return value


def normalize_source_item(value: str) -> str:
    """Normalize a Markdown checklist/list item for record matching."""

    text = value.strip()
    match = LIST_ITEM_RE.match(text)
    if match:
        text = match.group("item").strip()
    text = CHECKBOX_RE.sub("", text).strip()
    return re.sub(r"\s+", " ", text)


def normalize_fenced_test_command(value: str) -> str:
    """Normalize one command line from a fenced Test Plan block."""

    text = value.strip()
    if not text or text.startswith("#"):
        return ""
    text = SHELL_PROMPT_RE.sub("", text).strip()
    return re.sub(r"\s+", " ", text)


def command_line_words(value: str) -> list[str]:
    """Return normalized shell words for a fenced Test Plan command."""

    normalized = normalize_fenced_test_command(value)
    if not normalized:
        return []
    try:
        return shlex.split(normalized)
    except ValueError:
        return normalized.split()


def runner_argv_variants(command: dict[str, Any]) -> list[list[str]]:
    """Return argv word variants that can prove a fenced Test Plan command."""

    argv = command.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        return []
    variants = [list(argv)]
    if len(argv) >= 3 and argv[0] in {"bash", "sh"} and argv[1] in {"-c", "-lc"}:
        inner = command_line_words(argv[2])
        if inner:
            variants.append(inner)
    return variants


def section_items(source_text: str, section_name: str) -> list[dict[str, Any]]:
    """Return normalized completion gate items from a named Markdown section."""

    items: list[dict[str, Any]] = []
    in_section = False
    in_fence = False
    section_level = 0
    for line_number, line in enumerate(source_text.splitlines(), start=1):
        if in_section:
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                if section_name == "Test Plan":
                    normalized_command = normalize_fenced_test_command(line)
                    if normalized_command:
                        items.append(
                            {
                                "item": normalized_command,
                                "sha256": sha256_text(normalized_command),
                                "line": line_number,
                                "kind": "fenced-command",
                            }
                        )
                continue
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group("level"))
            title = heading.group("title").strip()
            if in_section and level <= section_level:
                in_section = False
                in_fence = False
            if title == section_name:
                in_section = True
                in_fence = False
                section_level = level
            continue
        if not in_section:
            continue
        match = LIST_ITEM_RE.match(line)
        if not match:
            continue
        normalized = normalize_source_item(match.group("item"))
        if normalized:
            items.append(
                {
                    "item": normalized,
                    "sha256": sha256_text(normalized),
                    "line": line_number,
                    "kind": "list-item",
                }
            )
    return items


def source_acceptance_index(source_path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    source_text = source_path.read_text(encoding="utf-8")
    return {
        section: {item["item"]: item for item in section_items(source_text, section)}
        for section in sorted(VALID_SOURCE_SECTIONS)
    }


def validate_record_file(
    record_path: Path,
    *,
    task: dict[str, Any] | None = None,
    require_passed: bool = False,
    require_current_source_hash: bool = True,
    require_runner_commands: bool = False,
    require_completion_gate_coverage: bool = False,
    tree_root: Path = TREE_ROOT,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate one record JSON file and return its parsed data."""

    errors: list[str] = []
    if not record_path.exists():
        raise CompletionRecordError(f"evidence file does not exist: {record_path}")

    try:
        data = json.loads(record_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CompletionRecordError(f"invalid record JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise CompletionRecordError("evidence root must be an object")

    schema_version = _require(data, "schema_version", errors)
    if schema_version != EVIDENCE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {EVIDENCE_SCHEMA_VERSION}")

    task_id = _require(data, "task_id", errors)
    source_md = _require(data, "source_md", errors)
    source_md_sha256 = _require(data, "source_md_sha256", errors)
    _require(data, "created_at", errors)
    _require(data, "actor", errors)
    _require(data, "session_id", errors)
    overall_status = _require(data, "overall_status", errors)

    if task is not None:
        if task_id != task.get("id"):
            errors.append(f"task_id {task_id!r} does not match task {task.get('id')!r}")
        if source_md != task.get("source_md"):
            errors.append(f"source_md {source_md!r} does not match task source {task.get('source_md')!r}")

    if require_passed and overall_status != "passed":
        errors.append("record-complete requires overall_status = passed")
    if overall_status not in {"passed", "failed"}:
        errors.append("overall_status must be passed or failed")

    commands = _is_list(data.get("commands"), "commands", errors)
    runner_command_variants: list[list[str]] = []
    if not commands:
        errors.append("commands must not be empty")
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            errors.append(f"commands[{index}] must be an object")
            continue
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            errors.append(f"commands[{index}].argv must be a non-empty string list")
        for key in ["cwd", "started_at", "ended_at", "stdout_excerpt", "stderr_excerpt"]:
            if key not in command:
                errors.append(f"commands[{index}] missing {key}")
        if command.get("exit_code") != 0 and require_passed:
            errors.append(f"commands[{index}].exit_code must be 0 for completion evidence")
        if require_runner_commands:
            runner_error = validate_command_entry_against_artifact(
                command,
                root=root,
                tree_root=tree_root,
                task_id=str(task_id) if task_id else None,
                actor=str(data.get("actor")) if data.get("actor") else None,
                session_id=str(data.get("session_id")) if data.get("session_id") else None,
            )
            if runner_error is not None:
                errors.append(f"commands[{index}] {runner_error}")
            else:
                runner_command_variants.extend(runner_argv_variants(command))

    source_path: Path | None = None
    source_index: dict[str, dict[str, dict[str, Any]]] = {}
    if source_md:
        source_path = resolve_tree_path(str(source_md), tree_root=tree_root, root=root)
        if not source_path.exists():
            errors.append(f"source_md file does not exist: {source_path}")
        elif require_current_source_hash and source_md_sha256 != file_sha256(source_path):
            errors.append("source_md_sha256 does not match current source document")
        elif source_path.exists():
            source_index = source_acceptance_index(source_path)

    acceptance = _is_list(data.get("acceptance"), "acceptance", errors)
    if not acceptance:
        errors.append("acceptance must not be empty")
    passed_acceptance_count = 0
    covered_gate_hashes: set[tuple[str, str]] = set()
    for index, item in enumerate(acceptance):
        if not isinstance(item, dict):
            errors.append(f"acceptance[{index}] must be an object")
            continue
        raw_item = item.get("item")
        if not raw_item:
            errors.append(f"acceptance[{index}] missing item")
            normalized_item = ""
        else:
            normalized_item = normalize_source_item(str(raw_item))
        if item.get("status") not in VALID_ACCEPTANCE_STATUSES:
            errors.append(f"acceptance[{index}].status must be one of {sorted(VALID_ACCEPTANCE_STATUSES)}")
        if item.get("status") == "passed":
            passed_acceptance_count += 1
        if require_passed and item.get("status") == "failed":
            errors.append(f"acceptance[{index}] failed")
        if not item.get("evidence"):
            errors.append(f"acceptance[{index}] missing evidence")
        source_section = item.get("source_section")
        if not source_section:
            errors.append(f"acceptance[{index}] missing source_section")
            continue
        if source_section not in VALID_SOURCE_SECTIONS:
            errors.append(f"acceptance[{index}].source_section must be Acceptance or Test Plan")
            continue
        source_items = source_index.get(str(source_section), {})
        source_match = source_items.get(normalized_item)
        if source_path is not None and source_path.exists() and source_match is None:
            errors.append(
                f"acceptance[{index}].item not found in current source {source_section}: {normalized_item!r}"
            )
            continue
        source_item_sha256 = item.get("source_item_sha256")
        if not source_item_sha256:
            errors.append(f"acceptance[{index}] missing source_item_sha256")
        elif source_match is not None and source_item_sha256 != source_match["sha256"]:
            errors.append(f"acceptance[{index}].source_item_sha256 does not match source item")
        elif source_item_sha256:
            covered_gate_hashes.add((str(source_section), str(source_item_sha256)))
        if (
            require_runner_commands
            and source_match is not None
            and source_section == "Test Plan"
            and source_match.get("kind") == "fenced-command"
        ):
            expected_words = command_line_words(str(source_match["item"]))
            if expected_words and expected_words not in runner_command_variants:
                errors.append(
                    f"acceptance[{index}].item does not match any runner command argv: {source_match['item']!r}"
                )
    if require_passed and passed_acceptance_count == 0:
        errors.append("record-complete requires at least one acceptance item must be passed")

    if require_completion_gate_coverage and source_index:
        required_gate_hashes: set[tuple[str, str]] = set()
        for section in sorted(VALID_SOURCE_SECTIONS):
            for source_item in source_index.get(section, {}).values():
                required_gate_hashes.add((section, str(source_item["sha256"])))
        missing_gate_hashes = sorted(required_gate_hashes - covered_gate_hashes)
        if missing_gate_hashes:
            errors.append(
                "missing completion gate coverage for current Acceptance/Test Plan items: "
                + ", ".join(f"{section}:{item_hash}" for section, item_hash in missing_gate_hashes)
            )

    if errors:
        raise CompletionRecordError("; ".join(errors))

    return data


def validate_completion_record(
    record_path: Path,
    *,
    task: dict[str, Any],
    require_current_source_hash: bool = True,
    require_runner_commands: bool = False,
    require_completion_gate_coverage: bool = False,
    tree_root: Path = TREE_ROOT,
    root: Path = ROOT,
) -> dict[str, Any]:
    return validate_record_file(
        record_path,
        task=task,
        require_passed=True,
        require_current_source_hash=require_current_source_hash,
        require_runner_commands=require_runner_commands,
        require_completion_gate_coverage=require_completion_gate_coverage,
        tree_root=tree_root,
        root=root,
    )
