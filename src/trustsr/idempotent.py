"""Idempotent event receiver (Labs 03.04-03.07): one physical record per event_id."""
import hashlib
import threading
from typing import Any
from .checkpoint import canonical_bytes


class ConflictError(ValueError):
    """Same event_id re-submitted with a different payload."""


class IdempotentReceiver:
    """Deduplicates by ``event_id``; re-sending the same payload is a harmless no-op.

    A retry after a lost acknowledgement therefore cannot create a duplicate. The same id
    with a *different* payload is rejected loudly rather than silently overwritten.
    In-memory only; thread-safe within one process.
    """

    def __init__(self) -> None:
        self._records: dict[str, str] = {}
        self._lock = threading.Lock()

    def store(self, event_id: str, payload: dict[str, Any]) -> str:
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("event_id must be a non-empty string")
        digest = hashlib.sha256(canonical_bytes(payload)).hexdigest()
        with self._lock:  # check-then-insert must be atomic so concurrent retries stay single-record
            existing = self._records.get(event_id)
            if existing is None:
                self._records[event_id] = digest
                return "stored"
            if existing != digest:
                raise ConflictError(f"event_id {event_id!r} re-used with a different payload")
            return "duplicate"

    @property
    def event_ids(self) -> frozenset[str]:
        return frozenset(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def reconcile(self, intended_ids: list[str]) -> dict[str, Any]:
        """Compare intended IDs with what was stored (missing / unexpected / duplicate intents)."""
        intended = set(intended_ids)
        return {"missing": sorted(intended - set(self._records)),
                "unexpected": sorted(set(self._records) - intended),
                "intended_has_duplicates": len(intended_ids) != len(intended)}
