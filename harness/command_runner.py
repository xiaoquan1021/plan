#!/usr/bin/env python3
"""Run task commands through the XQ ledger harness and write command artifacts."""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ledger_models import EVIDENCE_DIR, ROOT, TREE_ROOT, file_sha256, resolve_tree_path, safe_task_id, sha256_text, utc_now


COMMAND_RUN_SCHEMA_VERSION = 1
COMMAND_RUN_ARTIFACT_TYPE = "xq-ledger-command-run"
COMMAND_SUMMARY_ARTIFACT_TYPE = "xq-ledger-command-summary"
COMMAND_SUMMARY_GENERATOR = "xq-ledger-command-runner"
EXCERPT_LIMIT = 4000


@dataclass
class CommandRunResult:
    artifact_path: Path
    command_summary_path: Path | None
    artifact: dict[str, Any]
    command: dict[str, Any]


def output_excerpt(text: str, limit: int = EXCERPT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit]


def default_command_artifact_path(task_id: str, session_id: str) -> Path:
    return (
        EVIDENCE_DIR
        / "command-runs"
        / safe_task_id(session_id)
        / f"{safe_task_id(task_id)}-{uuid.uuid4().hex}.json"
    )


def default_command_summary_path(task_id: str, session_id: str) -> Path:
    return EVIDENCE_DIR / "command-summaries" / safe_task_id(session_id) / f"{safe_task_id(task_id)}.json"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def build_command_entry(
    artifact_path: Path,
    *,
    root: Path = ROOT,
    tree_root: Path = TREE_ROOT,
) -> dict[str, Any]:
    path = resolve_tree_path(str(artifact_path), tree_root=tree_root, root=root)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    return {
        "command_id": artifact["command_id"],
        "task_id": artifact["task_id"],
        "actor": artifact["actor"],
        "session_id": artifact["session_id"],
        "argv": artifact["argv"],
        "cwd": artifact["cwd"],
        "started_at": artifact["started_at"],
        "ended_at": artifact["ended_at"],
        "exit_code": artifact["exit_code"],
        "stdout_excerpt": artifact["stdout_excerpt"],
        "stderr_excerpt": artifact["stderr_excerpt"],
        "stdout_sha256": artifact["stdout_sha256"],
        "stderr_sha256": artifact["stderr_sha256"],
        "runner_artifact": str(path),
        "runner_artifact_sha256": file_sha256(path),
    }


def append_command_summary(
    summary_path: Path,
    *,
    task_id: str,
    actor: str,
    session_id: str,
    command: dict[str, Any],
) -> dict[str, Any]:
    if summary_path.exists():
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("command summary root must be an object")
        commands = data.setdefault("commands", [])
        if not isinstance(commands, list):
            raise ValueError("command summary commands must be a list")
    else:
        data = {
            "schema_version": 1,
            "task_id": task_id,
            "actor": actor,
            "session_id": session_id,
            "commands": [],
            "overall_status": "passed",
        }
        commands = data["commands"]

    data["schema_version"] = COMMAND_RUN_SCHEMA_VERSION
    data["artifact_type"] = COMMAND_SUMMARY_ARTIFACT_TYPE
    data["generated_by"] = COMMAND_SUMMARY_GENERATOR
    for key, value in {"task_id": task_id, "actor": actor, "session_id": session_id}.items():
        if data.get(key) not in (None, value):
            raise ValueError(f"command summary {key} mismatch")
        data[key] = value

    commands.append(command)
    data["overall_status"] = "passed" if all(item.get("exit_code") == 0 for item in commands) else "failed"
    write_json(summary_path, data)
    return data


def validate_command_entry_against_artifact(
    command: dict[str, Any],
    *,
    root: Path = ROOT,
    tree_root: Path = TREE_ROOT,
    task_id: str | None = None,
    actor: str | None = None,
    session_id: str | None = None,
) -> str | None:
    artifact_value = command.get("runner_artifact")
    artifact_sha256 = command.get("runner_artifact_sha256")
    if not isinstance(artifact_value, str) or not artifact_value:
        return "runner command missing runner_artifact"
    if not isinstance(artifact_sha256, str) or len(artifact_sha256) != 64:
        return "runner command missing runner_artifact_sha256"
    artifact_path = resolve_tree_path(artifact_value, tree_root=tree_root, root=root)
    if not artifact_path.exists():
        return f"runner artifact does not exist: {artifact_path}"
    if file_sha256(artifact_path) != artifact_sha256:
        return "runner_artifact_sha256 mismatch"
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return f"runner artifact must be valid JSON: {exc}"
    if not isinstance(artifact, dict):
        return "runner artifact root must be an object"
    if artifact.get("schema_version") != COMMAND_RUN_SCHEMA_VERSION:
        return f"runner artifact schema_version must be {COMMAND_RUN_SCHEMA_VERSION}"
    if artifact.get("artifact_type") != COMMAND_RUN_ARTIFACT_TYPE:
        return f"runner artifact_type must be {COMMAND_RUN_ARTIFACT_TYPE}"

    expected_context = {"task_id": task_id, "actor": actor, "session_id": session_id}
    for key, expected in expected_context.items():
        if expected is not None and artifact.get(key) != expected:
            return f"runner artifact {key} mismatch"

    for key in [
        "command_id",
        "task_id",
        "actor",
        "session_id",
        "argv",
        "cwd",
        "started_at",
        "ended_at",
        "exit_code",
        "stdout_excerpt",
        "stderr_excerpt",
        "stdout_sha256",
        "stderr_sha256",
    ]:
        if key not in command:
            return f"runner command missing {key}"
        if command.get(key) != artifact.get(key):
            return f"runner command {key} does not match artifact"
    return None


def run_harness_command(
    *,
    task_id: str,
    actor: str,
    session_id: str,
    argv: list[str],
    cwd: Path,
    artifact_path: Path | None = None,
    command_summary_path: Path | None = None,
    root: Path = ROOT,
    tree_root: Path = TREE_ROOT,
) -> CommandRunResult:
    if not argv:
        raise ValueError("argv must not be empty")
    cwd = cwd.resolve()
    artifact_path = artifact_path or default_command_artifact_path(task_id, session_id)
    command_summary_path = command_summary_path or default_command_summary_path(task_id, session_id)

    started_at = utc_now()
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    ended_at = utc_now()
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    artifact = {
        "schema_version": COMMAND_RUN_SCHEMA_VERSION,
        "artifact_type": COMMAND_RUN_ARTIFACT_TYPE,
        "command_id": f"{started_at}-{uuid.uuid4().hex}",
        "task_id": task_id,
        "actor": actor,
        "session_id": session_id,
        "argv": list(argv),
        "cwd": str(cwd),
        "started_at": started_at,
        "ended_at": ended_at,
        "exit_code": int(completed.returncode),
        "stdout_excerpt": output_excerpt(stdout),
        "stderr_excerpt": output_excerpt(stderr),
        "stdout_sha256": sha256_text(stdout),
        "stderr_sha256": sha256_text(stderr),
    }
    write_json(artifact_path, artifact)
    command = build_command_entry(artifact_path, root=root, tree_root=tree_root)
    append_command_summary(
        command_summary_path,
        task_id=task_id,
        actor=actor,
        session_id=session_id,
        command=command,
    )
    return CommandRunResult(
        artifact_path=artifact_path,
        command_summary_path=command_summary_path,
        artifact=artifact,
        command=command,
    )
