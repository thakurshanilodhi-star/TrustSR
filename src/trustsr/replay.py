"""Replay / rollback protection for versioned checkpoints.

A validly signed *old* checkpoint is still validly signed. Without a monotonic version
and a high-water mark kept outside the attacker's reach, it can be replayed to roll state
back to a vulnerable past. This module provides that mark, in memory or in SQLite
(transactional, survives restart).

Limits: the mark is only as trustworthy as its storage. An attacker who can rewrite the
SQLite file can lower the mark. Anchor it in storage the attacker cannot write.
"""
import sqlite3
import threading
from .checkpoint import valid_version


class ReplayError(ValueError):
    """Raised when a checkpoint version is stale, replayed, missing or invalid."""


class HighWaterMark:
    """In-memory monotonic mark of the newest checkpoint version ever registered."""

    def __init__(self, initial: int = 0) -> None:
        if not (isinstance(initial, int) and not isinstance(initial, bool) and initial >= 0):
            raise ValueError("initial must be a non-negative int")
        self._mark = initial
        self._lock = threading.Lock()

    @property
    def mark(self) -> int:
        return self._mark

    def register(self, version: int) -> bool:
        """Accept a *new* checkpoint: only strictly newer versions advance the mark."""
        if not valid_version(version):
            return False
        with self._lock:  # check-and-set must be atomic across threads
            if version <= self._mark:
                return False
            self._mark = version
            return True

    def is_current_or_newer(self, version: int | None) -> bool:
        """Recovery check: a checkpoint older than the mark is a rollback."""
        return valid_version(version) and version >= self._mark


class SqliteHighWaterMark(HighWaterMark):
    """Same interface, persisted with ``BEGIN IMMEDIATE`` transactions."""

    def __init__(self, path: str = ":memory:") -> None:
        self._lock = threading.Lock()  # serialises use of the single shared connection
        self._conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=10.0)
        self._conn.execute("CREATE TABLE IF NOT EXISTS checkpoint_state("
                           "singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),"
                           "high_water_mark INTEGER NOT NULL CHECK (high_water_mark >= 0))")
        self._conn.execute("INSERT OR IGNORE INTO checkpoint_state VALUES (1, 0)")

    @property
    def mark(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT high_water_mark FROM checkpoint_state WHERE singleton_id=1").fetchone()[0])

    def register(self, version: int) -> bool:
        if not valid_version(version):
            return False
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")  # cross-connection/process write lock
            try:
                current = int(self._conn.execute(
                    "SELECT high_water_mark FROM checkpoint_state WHERE singleton_id=1").fetchone()[0])
                if version <= current:
                    self._conn.execute("ROLLBACK")
                    return False
                self._conn.execute("UPDATE checkpoint_state SET high_water_mark=? WHERE singleton_id=1", (version,))
                self._conn.execute("COMMIT")
                return True
            except BaseException:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise

    def is_current_or_newer(self, version: int | None) -> bool:
        return valid_version(version) and version >= self.mark

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()
