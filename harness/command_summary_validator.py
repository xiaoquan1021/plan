#!/usr/bin/env python3
"""Command summary validation shared by completion recording and replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from command_runner import (
    COMMAND_SUMMARY_ARTIFACT_TYPE,
    COMMAND_SUMMARY_GENERATOR,
    validate_command_entry_against_artifact,
)
from ledger_models import ROOT, TREE_ROOT


def validate_command_summary_file(
    path: Path,
    *,
    require_success: bool = False,
    require_runner_commands: bool = False,
    root: Path = ROOT,
    tree_root: Path = TREE_ROOT,
    task_id: str | None = None,
    actor: str | None = None,
    session_id: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists() or not path.is_file():
        return None, "record-complete requires an existing command summary file"
    if path.stat().st_size <= 0:
        return None, "record-complete requires a non-empty command summary file"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"command summary must be valid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "command summary root must be an object"
    overall_status = data.get("overall_status")
    if require_success and overall_status != "passed":
        return None, "record-complete requires command summary overall_status = passed"
    if task_id is not None and data.get("task_id") not in (None, task_id):
        return None, "command summary task_id mismatch"
    if actor is not None and data.get("actor") not in (None, actor):
        return None, "command summary actor mismatch"
    if session_id is not None and data.get("session_id") not in (None, session_id):
        return None, "command summary session_id mismatch"
    commands = data.get("commands")
    if not isinstance(commands, list) or not commands:
        return None, "command summary commands must be a non-empty list"
    if require_runner_commands:
        if data.get("artifact_type") != COMMAND_SUMMARY_ARTIFACT_TYPE:
            return None, f"command summary artifact_type must be {COMMAND_SUMMARY_ARTIFACT_TYPE}"
        if data.get("generated_by") != COMMAND_SUMMARY_GENERATOR:
            return None, f"command summary generated_by must be {COMMAND_SUMMARY_GENERATOR}"
    successful_command = False
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            return None, f"command summary commands[{index}] must be an object"
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            return None, f"command summary commands[{index}].argv must be a non-empty string list"
        for key in ["cwd", "started_at", "ended_at", "exit_code"]:
            if key not in command:
                return None, f"command summary commands[{index}] missing {key}"
        if require_runner_commands:
            runner_error = validate_command_entry_against_artifact(
                command,
                root=root,
                tree_root=tree_root,
                task_id=task_id,
                actor=actor,
                session_id=session_id,
            )
            if runner_error is not None:
                return None, f"command summary commands[{index}] {runner_error}"
        if command.get("exit_code") == 0:
            successful_command = True
    if require_success and not successful_command:
        return None, "record-complete requires at least one successful command summary entry"
    return data, None


def command_identity(command: dict[str, Any]) -> tuple[tuple[str, ...], str, int] | None:
    argv = command.get("argv")
    cwd = command.get("cwd")
    exit_code = command.get("exit_code")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        return None
    if not isinstance(cwd, str):
        return None
    if not isinstance(exit_code, int):
        return None
    return (tuple(argv), cwd, exit_code)


def runner_command_identity(command: dict[str, Any]) -> tuple[str, str] | None:
    command_id = command.get("command_id")
    artifact_sha256 = command.get("runner_artifact_sha256")
    if isinstance(command_id, str) and command_id and isinstance(artifact_sha256, str) and artifact_sha256:
        return (command_id, artifact_sha256)
    return None


def validate_command_summary_matches_evidence(
    command_summary: dict[str, Any],
    record: dict[str, Any],
    *,
    require_runner_commands: bool = False,
) -> str | None:
    summary_commands = command_summary.get("commands")
    evidence_commands = record.get("commands")
    if not isinstance(summary_commands, list) or not isinstance(evidence_commands, list):
        return "command summary and record commands must both be lists"
    if require_runner_commands:
        summary_identities = {
            identity
            for command in summary_commands
            if isinstance(command, dict)
            for identity in [runner_command_identity(command)]
            if identity is not None
        }
        for index, command in enumerate(evidence_commands):
            if not isinstance(command, dict):
                return f"evidence commands[{index}] must be an object"
            identity = runner_command_identity(command)
            if identity is None:
                return f"evidence commands[{index}] missing command_id/runner_artifact_sha256"
            if identity not in summary_identities:
                return f"command summary missing runner-backed record command {index}"
        return None
    summary_identities = {
        identity
        for command in summary_commands
        if isinstance(command, dict)
        for identity in [command_identity(command)]
        if identity is not None
    }
    for index, command in enumerate(evidence_commands):
        if not isinstance(command, dict):
            return f"evidence commands[{index}] must be an object"
        identity = command_identity(command)
        if identity is None:
            return f"evidence commands[{index}] missing argv/cwd/exit_code for command-summary match"
        if identity not in summary_identities:
            return f"command summary missing record command {index}"
    return None
