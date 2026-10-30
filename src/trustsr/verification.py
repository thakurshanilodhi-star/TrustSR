"""Independent recovery verification gates and fail-closed decision.

``verify_recovery`` returns a :class:`VerificationReport`: an immutable, sealed mapping. Only this
module can mint one, and ``TrustTracker.promote_after_verification`` accepts nothing else, so a
hand-written ``{"decision": "PASS", ...}`` dict cannot promote trust.

Limit: this is an in-process integrity seal, not a security boundary. Code running in the same
Python process with introspection access can still bypass it (see ``docs/limitations.md``).
"""
import hashlib
import hmac
import os
import time
import uuid
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Iterator
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .audit import AuditLog, manifest_digest
from .checkpoint import SignedCheckpoint, canonical_bytes, state_digest, verify_checkpoint
from .contamination import detect_contamination, normalize_keys
from .replay import HighWaterMark
from .trust_state import TrustState, reinstate_trust

_SEAL_KEY = os.urandom(32)      # per-process secret; never stored, never exported
_MINT = object()                # private capability required to construct a report


def _seal(report_id: str, issued_at: float, content: dict[str, Any]) -> str:
    body = canonical_bytes({"id": report_id, "issued_at": issued_at, "content": content})
    return hmac.new(_SEAL_KEY, body, hashlib.sha256).hexdigest()


class VerificationReport(Mapping):
    """Immutable result of :func:`verify_recovery`.

    Behaves like a read-only dict (``report["decision"]``, ``.get``, ``dict(report)``); every read
    returns a deep copy, so callers cannot edit it in place. ``is_authentic()`` re-computes the
    seal, so tampering with the internals after issue is detected. Cannot be subclassed or built
    directly. Use :meth:`to_dict` for JSON-style serialisation.
    """
    __slots__ = ("_content", "_report_id", "_issued_at", "_seal_hex")

    def __init_subclass__(cls, **kwargs):
        raise TypeError("VerificationReport cannot be subclassed")

    def __init__(self, content: dict[str, Any], *, _token: object = None) -> None:
        if _token is not _MINT:
            raise TypeError("VerificationReport can only be issued by verify_recovery()")
        object.__setattr__(self, "_content", deepcopy(content))
        object.__setattr__(self, "_report_id", uuid.uuid4().hex)
        object.__setattr__(self, "_issued_at", time.time())
        object.__setattr__(self, "_seal_hex", _seal(self._report_id, self._issued_at, self._content))

    def __setattr__(self, name, value):
        raise AttributeError("VerificationReport is immutable")

    def __delattr__(self, name):
        raise AttributeError("VerificationReport is immutable")

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self  # immutable: sharing is safe, and a "copy" must not mint a second authentic object

    def __reduce__(self):
        raise TypeError("VerificationReport cannot be pickled; use to_dict() for a plain snapshot")

    def __getitem__(self, key: str) -> Any:
        return deepcopy(self._content[key])

    def __iter__(self) -> Iterator[str]:
        return iter(self._content)

    def __len__(self) -> int:
        return len(self._content)

    def __repr__(self) -> str:
        return f"VerificationReport(decision={self._content.get('decision')!r}, id={self._report_id[:8]})"

    @property
    def report_id(self) -> str:
        return self._report_id

    @property
    def issued_at(self) -> float:
        return self._issued_at

    def is_authentic(self) -> bool:
        """True only if this object was issued by this process's ``verify_recovery`` and is unmodified."""
        try:
            return hmac.compare_digest(self._seal_hex, _seal(self._report_id, self._issued_at, self._content))
        except Exception:
            return False

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self._content)


REQUIRED_GATES = ("checkpoint_valid", "audit_valid", "recovery_complete", "contamination_removed", "scope_complete")


def _scope_complete(manifest: dict[str, Any], observed: list[str]) -> tuple[bool, bool]:
    """Return (well_formed, complete)."""
    if not isinstance(manifest, dict) or not isinstance(observed, (list, tuple)):
        return False, False
    ids, count = manifest.get("expected_record_ids"), manifest.get("expected_count")
    ok = (isinstance(ids, list) and all(isinstance(i, str) for i in ids)
          and isinstance(count, int) and not isinstance(count, bool))
    if not ok:
        return False, False
    complete = (len(ids) == count == len(set(ids))
                and all(isinstance(i, str) for i in observed)
                and len(observed) == len(set(observed))
                and set(observed) == set(ids))
    return True, complete


def _recovery_completed_in_log(events: tuple, checkpoint: SignedCheckpoint, keys: list[str] | None,
                               recovery_id: str | None = None) -> str | None:
    """Return the ``recovery_id`` of a completed recovery, or ``None``. Derived from the audit log only.

    Requires a ``recovery_completed`` event with a matching ``recovery_started`` (same details,
    earlier in the chain) for *this* checkpoint and the same key scope, and no ``recovery_refused``
    for that id. If ``recovery_id`` is given, only that attempt can satisfy the gate.
    """
    want_keys = None if keys is None else sorted(set(keys))
    want_mode = "full" if keys is None else "selective"
    for i in range(len(events) - 1, -1, -1):
        done = events[i]
        d = done.details
        if done.event_type != "recovery_completed":
            continue
        if (d.get("checkpoint_sha256") != checkpoint.payload_sha256 or d.get("mode") != want_mode
                or d.get("keys") != want_keys or d.get("version") != checkpoint.version):
            continue
        rid = d.get("recovery_id")
        if recovery_id is not None and rid != recovery_id:
            continue
        started = any(e.event_type == "recovery_started" and e.details == {**d} for e in events[:i])
        refused = any(e.event_type == "recovery_refused" and e.details.get("recovery_id") == rid for e in events)
        if started and not refused:
            return rid if isinstance(rid, str) else None
        if recovery_id is not None:
            return None
    return None


def _scope_bound_in_log(events: tuple, manifest: dict[str, Any]) -> bool:
    try:
        digest = manifest_digest(manifest)
    except (TypeError, ValueError):
        return False
    declared = [e for e in events if e.event_type == "scope_declared"]
    return bool(declared) and declared[-1].details.get("manifest_sha256") == digest


def verify_recovery(*, checkpoint: SignedCheckpoint, public_key: Ed25519PublicKey, audit_log: AuditLog,
                    recovered_state: dict[str, Any], scope_manifest: dict[str, Any],
                    observed_record_ids: list[str], keys: list[str] | None = None,
                    trusted_audit_head: str | None = None, replay_guard: HighWaterMark | None = None,
                    allow_rollback: bool = False, require_anchored_head: bool = False,
                    recovery_id: str | None = None) -> VerificationReport:
    """Verify the five gates and fail closed.

    * checkpoint_valid: signature + digest verify under the trusted key and, when a
      ``replay_guard`` is supplied, the signed version is present and not older than the
      high-water mark (unless ``allow_rollback`` is set explicitly).
    * audit_valid: non-empty, internally consistent chain (and equals ``trusted_audit_head``
      when supplied). ``trusted_audit_head`` must be a value stored *before and outside* the log
      being checked (see ``trustsr.anchor.HeadAnchor``); passing ``audit_log.head`` is circular.
      With ``require_anchored_head=True`` a missing head fails this gate; otherwise the report
      carries ``audit_head_anchored=False`` and a warning.
    * recovery_complete: the audit log records a matching started/completed pair for this
      checkpoint and key scope.
    * contamination_removed: ``recovered_state`` equals the **signed checkpoint payload**
      (restricted to ``keys`` for selective recovery). The reference is no longer a
      caller-supplied value, so it cannot be set to the contaminated state.
    * scope_complete: observed IDs match the manifest exactly, and the manifest's digest
      was recorded in the audit log via ``AuditLog.declare_scope``.

    Binding fields in the report (used by ``TrustTracker.promote_after_verification``):

    * ``recovery_id``: the id of the recovery attempt found *in the audit log* that satisfied
      ``recovery_complete`` (``None`` if none did). Pass ``recovery_id=`` to require one specific attempt.
    * ``verified_state_sha256``: digest of the exact ``recovered_state`` that was compared. Pass the state
      **re-read from the committed store**, so the report speaks about persistent state and not about an
      in-memory dictionary. Passing the report is a different claim from the store being correct; the
      promotion call re-checks the digest against a fresh read.

    Limits: the manifest's *content* is still an assumption about the real world, and
    selective recovery says nothing about keys outside ``keys``.
    """
    try:
        selected = normalize_keys(keys)
        keys_well_formed = True
    except TypeError:
        selected, keys_well_formed = None, False
    events = audit_log.events  # one defensive copy for all gate checks
    signature_valid = verify_checkpoint(checkpoint, public_key)
    if replay_guard is None:
        fresh = True
    else:
        fresh = checkpoint.version is not None and (allow_rollback or replay_guard.is_current_or_newer(checkpoint.version))
    checkpoint_valid = signature_valid and fresh

    if signature_valid and keys_well_formed:
        if selected is None:
            reference, observed = checkpoint.payload, recovered_state
            keys_valid = True
        else:
            wanted = selected
            keys_valid = all(k in checkpoint.payload for k in wanted)
            reference = {k: checkpoint.payload[k] for k in wanted if k in checkpoint.payload}
            observed = {k: recovered_state[k] for k in wanted if k in recovered_state}
        contamination = detect_contamination(reference, observed)
    else:  # no trusted reference exists
        keys_valid = False
        contamination = {"contaminated": True, "changed_keys": [], "missing_keys": [], "extra_keys": [],
                         "note": "checkpoint invalid; no trusted reference"}

    try:
        verified_digest = state_digest(recovered_state)
    except (TypeError, ValueError):
        verified_digest = None  # not canonical JSON (NaN, objects, ...): cannot be bound -> fail closed
    found_recovery_id = (_recovery_completed_in_log(events, checkpoint, selected, recovery_id)
                         if signature_valid and keys_well_formed else None)

    well_formed, id_match = _scope_complete(scope_manifest, observed_record_ids)
    scope_bound = well_formed and _scope_bound_in_log(events, scope_manifest)

    gates = {
        "checkpoint_valid": checkpoint_valid,
        "audit_valid": audit_log.verify(trusted_head=trusted_audit_head)
                       and not (require_anchored_head and trusted_audit_head is None),
        "recovery_complete": found_recovery_id is not None,
        "contamination_removed": keys_valid and contamination["contaminated"] is False and verified_digest is not None,
        "scope_complete": id_match and scope_bound,
    }
    state = reinstate_trust(gates)
    warnings = [] if trusted_audit_head is not None else ["audit_head_not_anchored"]
    report = {"decision": "PASS" if state is TrustState.TRUSTED else "FAIL",
              "trust_state": state.value, "gates": gates, "contamination_report": contamination,
              "checkpoint_sha256": checkpoint.payload_sha256, "checkpoint_version": checkpoint.version,
              "recovery_id": found_recovery_id, "verified_state_sha256": verified_digest,
              "audit_head_anchored": trusted_audit_head is not None, "warnings": warnings,
              "replay_report": {"guard_used": replay_guard is not None, "signature_valid": signature_valid,
                                "version": checkpoint.version, "fresh": fresh,
                                "high_water_mark": None if replay_guard is None else replay_guard.mark},
              "scope_report": {"manifest_well_formed": well_formed, "ids_match": id_match,
                               "manifest_bound_in_audit": scope_bound,
                               "expected_count": scope_manifest.get("expected_count") if isinstance(scope_manifest, dict) else None,
                               "observed_count": len(observed_record_ids) if isinstance(observed_record_ids, (list, tuple)) else None}}
    return VerificationReport(report, _token=_MINT)
