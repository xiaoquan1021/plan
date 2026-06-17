#!/usr/bin/env python3
"""Lock/lease management for the XQ ledger harness."""

from __future__ import annotations

import json
import os
import uuid
import fcntl
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ledger_models import DEFAULT_LEASE_SECONDS, LOCKS_DIR, parse_iso, safe_task_id, utc_now


class LeaseError(Exception):
    """Raised when a lease operation is not allowed."""


class LeaseManager:
    def __init__(self, locks_dir: Path = LOCKS_DIR, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> None:
        self.locks_dir = locks_dir
        self.lease_seconds = lease_seconds

    def _path(self, task_id: str) -> Path:
        return self.locks_dir / f"{safe_task_id(task_id)}.json"

    def _lock_path(self) -> Path:
        return self.locks_dir / ".leases.lock"

    @contextmanager
    def _locked(self, lock_type: int):
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self._lock_path()
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), lock_type)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_unlocked(self, task_id: str) -> dict[str, Any] | None:
        path = self._path(task_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read(self, task_id: str) -> dict[str, Any] | None:
        with self._locked(fcntl.LOCK_SH):
            return self._read_unlocked(task_id)

    def _write_unlocked(self, lease: dict[str, Any]) -> None:
        path = self._path(lease["task_id"])
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(lease, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, path)

    def write(self, lease: dict[str, Any]) -> None:
        with self._locked(fcntl.LOCK_EX):
            self._write_unlocked(lease)

    def is_expired(self, lease: dict[str, Any], *, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        heartbeat_at = parse_iso(str(lease.get("heartbeat_at") or lease.get("claimed_at")))
        lease_seconds = int(lease.get("lease_seconds") or self.lease_seconds)
        return (now - heartbeat_at).total_seconds() > lease_seconds

    def claim(self, task_id: str, *, actor: str, session_id: str) -> dict[str, Any]:
        with self._locked(fcntl.LOCK_EX):
            timestamp = utc_now()
            lease = {
                "schema_version": 1,
                "task_id": task_id,
                "actor": actor,
                "session_id": session_id,
                "claimed_at": timestamp,
                "heartbeat_at": timestamp,
                "lease_seconds": self.lease_seconds,
            }
            path = self._path(task_id)
            tmp_path = self.locks_dir / f".{safe_task_id(task_id)}.{uuid.uuid4().hex}.tmp"
            try:
                tmp_path.write_text(json.dumps(lease, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                with tmp_path.open("r+", encoding="utf-8") as handle:
                    handle.flush()
                    os.fsync(handle.fileno())
                os.link(tmp_path, path)
            except FileExistsError as exc:
                existing = self._read_unlocked(task_id)
                state = "expired" if existing is not None and self.is_expired(existing) else "active"
                raise LeaseError(f"task {task_id} already has {state} lease; release or block it first") from exc
            finally:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except FileNotFoundError:
                        pass
            return lease

    def heartbeat(self, task_id: str, *, actor: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        if not actor or not session_id:
            raise LeaseError("heartbeat requires actor and session_id")
        with self._locked(fcntl.LOCK_EX):
            lease = self._read_unlocked(task_id)
            if lease is None:
                raise LeaseError(f"task {task_id} has no active lease")
            if self.is_expired(lease):
                raise LeaseError(f"task {task_id} lease is expired")
            if lease.get("actor") != actor:
                raise LeaseError(f"task {task_id} lease actor mismatch")
            if lease.get("session_id") != session_id:
                raise LeaseError(f"task {task_id} lease session mismatch")
            lease["heartbeat_at"] = utc_now()
            self._write_unlocked(lease)
            return lease

    def release(self, task_id: str, *, actor: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        if not actor or not session_id:
            raise LeaseError("release requires actor and session_id")
        with self._locked(fcntl.LOCK_EX):
            path = self._path(task_id)
            if not path.exists():
                raise LeaseError(f"task {task_id} has no active lease")
            lease = json.loads(path.read_text(encoding="utf-8"))
            if lease.get("actor") != actor:
                raise LeaseError(f"task {task_id} lease actor mismatch")
            if lease.get("session_id") != session_id:
                raise LeaseError(f"task {task_id} lease session mismatch")
            path.unlink()
            return lease

    def all_leases(self) -> list[dict[str, Any]]:
        with self._locked(fcntl.LOCK_SH):
            if not self.locks_dir.exists():
                return []
            leases: list[dict[str, Any]] = []
            for path in sorted(self.locks_dir.glob("*.json")):
                try:
                    leases.append(json.loads(path.read_text(encoding="utf-8")))
                except json.JSONDecodeError:
                    leases.append({"task_id": path.stem, "invalid": True, "path": str(path)})
            return leases

    def summarize(self) -> dict[str, Any]:
        active: list[dict[str, Any]] = []
        expired: list[dict[str, Any]] = []
        invalid: list[dict[str, Any]] = []
        for lease in self.all_leases():
            if lease.get("invalid"):
                invalid.append(lease)
            elif self.is_expired(lease):
                expired.append(lease)
            else:
                active.append(lease)
        return {
            "active_leases": active,
            "expired_leases": expired,
            "invalid_leases": invalid,
            "active_task_ids": [lease["task_id"] for lease in active if lease.get("task_id")],
            "expired_task_ids": [lease["task_id"] for lease in expired if lease.get("task_id")],
        }
