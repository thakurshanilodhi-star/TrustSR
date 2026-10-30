"""Small append-only hash-chain audit log for local experiments.

This detects accidental/tamper edits to the represented chain. It does not provide
remote append-only storage, trusted timestamps, or protection against an attacker who
can rewrite the entire log *and* its trusted head. Pass a ``trusted_head`` obtained
out-of-band to ``verify`` to detect truncation or wholesale replacement.
"""
import hashlib
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from .checkpoint import canonical_bytes

GENESIS = "GENESIS"


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    event_type: str
    details: dict[str, Any]
    previous_hash: str
    event_hash: str


def manifest_digest(manifest: dict[str, Any]) -> str:
    """SHA-256 of the canonical encoding of a scope manifest."""
    return hashlib.sha256(canonical_bytes(manifest)).hexdigest()


class AuditLog:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    @classmethod
    def from_events(cls, events) -> "AuditLog":
        """Rebuild a log from event dicts/``AuditEvent`` objects **without trusting them**.

        The result may be inconsistent; call :meth:`verify` (and :meth:`extends`) before relying on
        it. Used by the anchor service to check a log it received from a client.
        """
        log = cls()
        for e in events:
            if isinstance(e, dict):
                e = AuditEvent(sequence=e["sequence"], event_type=e["event_type"], details=deepcopy(e["details"]),
                               previous_hash=e["previous_hash"], event_hash=e["event_hash"])
            log._events.append(deepcopy(e))
        return log

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        """Return defensive copies so callers cannot mutate the stored chain.

        ``frozen=True`` prevents field reassignment but does not recursively freeze
        nested dictionaries. Deep-copying both the collection and event details
        keeps the public accessor read-only with respect to internal state.
        """
        return tuple(deepcopy(self._events))

    @property
    def head(self) -> str:
        """Hash of the latest event (``GENESIS`` when empty). Store it out-of-band."""
        return self._events[-1].event_hash if self._events else GENESIS

    def append(self, event_type: str, details: dict[str, Any]) -> AuditEvent:
        details = deepcopy(details)  # later mutation of caller's dict cannot alter the log
        body = {"sequence": len(self._events), "event_type": event_type,
                "details": details, "previous_hash": self.head}
        digest = hashlib.sha256(canonical_bytes(body)).hexdigest()  # raises on non-JSON data
        event = AuditEvent(**body, event_hash=digest)
        self._events.append(event)
        # Do not expose the internal event object: its nested details are mutable.
        return deepcopy(event)

    def declare_scope(self, manifest: dict[str, Any]) -> AuditEvent:
        """Bind a scope manifest to the log by recording its digest."""
        return self.append("scope_declared", {"manifest_sha256": manifest_digest(manifest)})

    def extends(self, earlier_head: str) -> bool:
        """True if ``earlier_head`` is ``GENESIS`` or the hash of an event in this (valid) chain.

        Used by ``HeadAnchor.advance``: a newly anchored head must grow from the previously
        anchored one, so truncation or wholesale replacement of the log is noticed.
        """
        if not self.verify(require_nonempty=False):
            return False
        return earlier_head == GENESIS or any(e.event_hash == earlier_head for e in self._events)

    def verify(self, trusted_head: str | None = None, require_nonempty: bool = True) -> bool:
        """Check chain consistency. An empty log is invalid unless ``require_nonempty=False``.

        If ``trusted_head`` is given, the chain must end at exactly that hash.
        """
        if require_nonempty and not self._events:
            return False
        previous = GENESIS
        for index, event in enumerate(self._events):
            body = {"sequence": event.sequence, "event_type": event.event_type,
                    "details": event.details, "previous_hash": event.previous_hash}
            if event.sequence != index or event.previous_hash != previous:
                return False
            try:
                digest = hashlib.sha256(canonical_bytes(body)).hexdigest()
            except (TypeError, ValueError):
                return False
            if digest != event.event_hash:
                return False
            previous = event.event_hash
        return trusted_head is None or previous == trusted_head
