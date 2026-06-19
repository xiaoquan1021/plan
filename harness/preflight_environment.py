#!/usr/bin/env python3
"""Resolve local toolchain bindings without committing machine paths."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_version(command: str) -> dict[str, Any]:
    executable = command
    if command == "python":
        executable = sys.executable
    elif not Path(command).exists():
        resolved = shutil.which(command)
        executable = resolved or command
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=15)
        return {
            "command": command,
            "resolved": executable,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip().splitlines()[:2],
            "stderr": result.stderr.strip().splitlines()[:2],
        }
    except Exception as exc:  # noqa: BLE001
        return {"command": command, "resolved": executable, "exit_code": 127, "error": str(exc)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bindings", default="config/toolchain-bindings.example.json")
    args = parser.parse_args(argv)
    bindings = load(ROOT / args.bindings)
    results = {}
    ok = True
    for name, spec in bindings.get("tools", {}).items():
        if not isinstance(spec, dict):
            results[name] = {"status": "recorded", "value_kind": type(spec).__name__, "required": False}
            continue
        command = spec.get("command")
        if not command:
            results[name] = {
                "required": spec.get("required", False),
                "status": "not-bound" if not spec.get("root") else "root-bound",
                "root": spec.get("root"),
            }
            if spec.get("required"):
                ok = False
            continue
        result = run_version(str(command))
        result["required"] = bool(spec.get("required"))
        if result["required"] and result.get("exit_code") != 0:
            ok = False
        results[name] = result
    print(json.dumps({"schema_version": 1, "tools": results}, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
