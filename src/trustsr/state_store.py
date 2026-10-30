"""Transactional persistent agent-state store: commit a recovery, re-read it, hash what was read.

``recover_state`` only *builds* a dictionary. A verification report about that dictionary is a
different claim from "the agent's persistent state is correct". This module closes that gap for a
reference store (SQLite): the recovered state, its ``recovery_id`` and its digest are written in ONE
transaction; the store is then re-read through a fresh connection, the digest is recomputed from the
bytes actually stored, and promotion is bound to *that* digest.

    attempt = recover_state_attempt(...)             # builds the state, logs started/completed
    committed = store.commit_recovery(attempt)       # atomic write + independent re-read
    report = verify_recovery(..., recovered_state=committed.state, recovery_id=attempt.recovery_id)
    fresh = store.read_committed()                   # read AGAIN right before promotion
    tracker.promote_after_verification(report, expected_checkpoint_sha256=attempt.checkpoint_sha256,
                                       expected_recovery_id=fresh.recovery_id,
                                       committed_state_sha256=fresh.state_sha256)

Windows/Linux: every operation opens and *closes* its own connection (no handle outlives a call), so
temporary directories can be deleted on Windows. Limits: this is a reference store, not a distributed
database; whoever can rewrite the SQLite file can rewrite the state, its digest and the recovery id
together. The audit log and the store are still two systems: a crash after the store commit but before the
audit event is visible as ``recovery_id`` in the store with no matching log event, and fails verification
(fail closed) rather than being repaired automatically.
"""
import contextlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from .checkpoint import canonical_bytes, state_digest
from .recovery import RecoveryAttempt


class StateCommitError(RuntimeError):
    """The store could not commit, or what was read back is not what was written."""


@dataclass(frozen=True)
class CommittedState:
    state: dict[str, Any]
    state_sha256: str            # recomputed from the stored bytes at read time
    recovery_id: str | None      # None after an ordinary write: no recovery vouches for this state
    revision: int


class SqliteStateStore:
    def __init__(self, path) -> None:
        self.path = str(path)
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS agent_state(singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),"
                         "state_json TEXT NOT NULL, state_sha256 TEXT NOT NULL, recovery_id TEXT,"
                         "revision INTEGER NOT NULL)")

    @contextlib.contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=10.0)
        try:
            yield conn
        finally:
            conn.close()  # always: an open handle blocks file deletion on Windows

    def _write(self, state: dict[str, Any], recovery_id: str | None) -> None:
        text = canonical_bytes(state).decode("utf-8")      # raises for NaN / non-JSON values
        digest = state_digest(state)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT revision FROM agent_state WHERE singleton_id=1").fetchone()
                conn.execute("INSERT OR REPLACE INTO agent_state VALUES (1, ?, ?, ?, ?)",
                             (text, digest, recovery_id, (row[0] + 1) if row else 1))
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def write_state(self, state: dict[str, Any]) -> None:
        """Ordinary agent write. Clears ``recovery_id``: no recovery vouches for state written this way."""
        self._write(state, None)

    def read_committed(self) -> CommittedState | None:
        """Fresh read; the digest is recomputed from the stored JSON and must match the stored digest."""
        with self._connect() as conn:
            row = conn.execute("SELECT state_json, state_sha256, recovery_id, revision FROM agent_state "
                               "WHERE singleton_id=1").fetchone()
        if row is None:
            return None
        text, stored_digest, rid, revision = row
        try:
            state = json.loads(text)
            actual = state_digest(state)
        except (ValueError, TypeError) as exc:
            raise StateCommitError(f"stored state is not valid canonical JSON: {exc}") from exc
        if actual != stored_digest or canonical_bytes(state).decode("utf-8") != text:
            raise StateCommitError("stored state does not match its stored digest (corrupted or edited)")
        return CommittedState(state=state, state_sha256=actual, recovery_id=rid, revision=revision)

    def commit_recovery(self, attempt: RecoveryAttempt) -> CommittedState:
        """Atomically store ``attempt.state`` with its ``recovery_id``, then re-read and compare."""
        if not isinstance(attempt, RecoveryAttempt):
            raise TypeError("commit_recovery needs a RecoveryAttempt from recover_state_attempt()")
        self._write(attempt.state, attempt.recovery_id)
        committed = self.read_committed()
        if (committed is None or committed.state_sha256 != attempt.state_sha256
                or committed.recovery_id != attempt.recovery_id):
            raise StateCommitError("re-read of the committed state does not match the recovery attempt")
        return committed
