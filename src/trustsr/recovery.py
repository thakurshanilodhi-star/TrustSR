"""Fail-closed recovery from a verified checkpoint payload."""
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .audit import AuditLog
from .contamination import normalize_keys
from .checkpoint import SignedCheckpoint, state_digest, verify_checkpoint
from .replay import HighWaterMark, ReplayError


@dataclass(frozen=True)
class RecoveryAttempt:
    """What one recovery produced, with the identifiers a later promotion must be bound to.

    ``state`` is the dictionary the caller must **commit** to its persistent store (see
    ``trustsr.state_store``); ``state_sha256`` is its digest at recovery time. Nothing here proves the
    state was committed: re-read the store and use that digest for promotion.
    """
    recovery_id: str
    state: dict[str, Any]
    state_sha256: str
    checkpoint_sha256: str
    version: int | None
    mode: str
    keys: list[str] | None


def recover_state_attempt(checkpoint: SignedCheckpoint, trusted_public_key: Ed25519PublicKey,
                          current_state: dict[str, Any], keys: list[str] | None = None,
                          audit_log: AuditLog | None = None, replay_guard: HighWaterMark | None = None,
                          allow_rollback: bool = False) -> RecoveryAttempt:
    """Recover state only after signature/hash verification and return a :class:`RecoveryAttempt`.

    * ``keys is None`` -> **full recovery**: the result *is* the checkpoint payload.
      Keys injected into ``current_state`` that are not in the checkpoint are dropped.
    * ``keys`` given   -> **selective recovery**: only those keys are restored; all
      other keys of ``current_state`` are left untouched (and therefore unverified).

    Missing requested keys raise ``KeyError``. If ``audit_log`` is supplied, the
    operation is recorded (``recovery_started`` / ``recovery_completed`` or
    ``recovery_refused``) so that ``verify_recovery`` can derive completion from the
    log instead of trusting a caller-supplied flag.

    If ``replay_guard`` is given, the checkpoint must carry a signed ``version`` that is not
    older than the guard's high-water mark; otherwise recovery is refused with ``ReplayError``
    (a ``ValueError``). Pass ``allow_rollback=True`` to deliberately recover from an older
    checkpoint (e.g. the newest one is contaminated); this is recorded in the audit log.
    The caller remains responsible for checkpoint provenance, for committing ``attempt.state``
    atomically, and for reconciling irreversible external side effects.
    """
    recovery_id = uuid.uuid4().hex
    selected = normalize_keys(keys)  # TypeError for a bare string such as keys="mode"
    mode = "full" if selected is None else "selective"

    def refuse(reason: str, exc: Exception):
        if audit_log is not None:
            audit_log.append("recovery_refused", {"recovery_id": recovery_id, "reason": reason})
        raise exc

    if not verify_checkpoint(checkpoint, trusted_public_key):
        refuse("checkpoint_verification_failed", ValueError("Checkpoint verification failed; recovery refused"))
    source = deepcopy(checkpoint.payload)  # work on a private copy of the *verified* payload
    rollback = False
    if replay_guard is not None:
        if checkpoint.version is None:
            refuse("unversioned_checkpoint", ReplayError("Replay guard requires a versioned checkpoint"))
        if not replay_guard.is_current_or_newer(checkpoint.version):
            if not allow_rollback:
                refuse("stale_or_replayed_checkpoint", ReplayError(
                    f"Checkpoint version {checkpoint.version} is older than high-water mark {replay_guard.mark}"))
            rollback = True
    if selected is not None:
        missing = [k for k in selected if k not in source]
        if missing:
            refuse("keys_absent_from_checkpoint", KeyError(f"Requested keys absent from checkpoint: {missing}"))
    if audit_log is not None:
        audit_log.append("recovery_started", {"recovery_id": recovery_id, "mode": mode, "keys": selected,
                                              "checkpoint_sha256": checkpoint.payload_sha256,
                                              "version": checkpoint.version, "rollback": rollback})
    if selected is None:
        restored = source
    else:
        restored = deepcopy(current_state)
        for key in selected:
            restored[key] = source[key]
    if audit_log is not None:
        audit_log.append("recovery_completed", {"recovery_id": recovery_id, "mode": mode, "keys": selected,
                                                "checkpoint_sha256": checkpoint.payload_sha256,
                                                "version": checkpoint.version, "rollback": rollback})
    return RecoveryAttempt(recovery_id=recovery_id, state=restored, state_sha256=state_digest(restored),
                           checkpoint_sha256=checkpoint.payload_sha256, version=checkpoint.version,
                           mode=mode, keys=selected)


def recover_state(checkpoint: SignedCheckpoint, trusted_public_key: Ed25519PublicKey,
                  current_state: dict[str, Any], keys: list[str] | None = None,
                  audit_log: AuditLog | None = None, replay_guard: HighWaterMark | None = None,
                  allow_rollback: bool = False) -> dict[str, Any]:
    """Backward-compatible wrapper: same checks as :func:`recover_state_attempt`, returns only the state.

    Prefer ``recover_state_attempt``: promotion to ``Trusted`` now needs the ``recovery_id``.
    """
    return recover_state_attempt(checkpoint, trusted_public_key, current_state, keys=keys,
                                 audit_log=audit_log, replay_guard=replay_guard,
                                 allow_rollback=allow_rollback).state
