#!/usr/bin/env python3
"""Small cross-platform flock facade for ledger harness files."""

from __future__ import annotations

import os

try:  # POSIX public CI path.
    import fcntl as _fcntl

    LOCK_SH = _fcntl.LOCK_SH
    LOCK_EX = _fcntl.LOCK_EX
    LOCK_UN = _fcntl.LOCK_UN

    def flock(fd: int, operation: int) -> None:
        _fcntl.flock(fd, operation)

except ModuleNotFoundError:  # Windows local preflight path.
    import msvcrt

    LOCK_SH = 1
    LOCK_EX = 2
    LOCK_UN = 8

    def flock(fd: int, operation: int) -> None:
        position = os.lseek(fd, 0, os.SEEK_CUR)
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            if operation & LOCK_UN:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                # Windows has no shared byte-range lock equivalent via msvcrt;
                # use an exclusive one-byte lock for both shared and exclusive callers.
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        finally:
            os.lseek(fd, position, os.SEEK_SET)
