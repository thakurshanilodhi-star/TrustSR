"""Five-label trust state machine (Lab 09) and its link to ``verify_recovery``.

Labels are policy states, not proof of real-world trustworthiness. Any transition not
explicitly allowed is rejected (fail closed).

``transition()`` is a pure *policy predicate*: the caller asserts the flags. The enforcement
point is ``TrustTracker``, which (a) keeps its label private, (b) refuses to enter ``Trusted``
through ``apply()``, and (c) promotes only from an authentic, unused, passing
``VerificationReport`` issued by ``verify_recovery``; plain dicts are rejected.
"""
import time
from enum import Enum
from typing import Any

from .trust_state import TrustState, reinstate_trust
from .verification import REQUIRED_GATES, VerificationReport


class TrustLabel(str, Enum):
    TRUSTED = "Trusted"
    RECOVERED = "Recovered"
    UNKNOWN = "Unknown"
    SUSPECT = "Suspect"
    CONTAMINATED = "Contaminated"


ALLOWED_TRANSITIONS: dict[TrustLabel, frozenset[TrustLabel]] = {
    TrustLabel.TRUSTED: frozenset({TrustLabel.SUSPECT, TrustLabel.CONTAMINATED, TrustLabel.UNKNOWN}),
    TrustLabel.RECOVERED: frozenset({TrustLabel.TRUSTED, TrustLabel.SUSPECT, TrustLabel.CONTAMINATED, TrustLabel.UNKNOWN}),
    TrustLabel.UNKNOWN: frozenset({TrustLabel.TRUSTED, TrustLabel.RECOVERED, TrustLabel.SUSPECT, TrustLabel.CONTAMINATED}),
    TrustLabel.SUSPECT: frozenset({TrustLabel.RECOVERED, TrustLabel.CONTAMINATED, TrustLabel.UNKNOWN}),
    TrustLabel.CONTAMINATED: frozenset({TrustLabel.RECOVERED, TrustLabel.UNKNOWN}),
}


def transition(current: TrustLabel, target: TrustLabel, *, verified: bool = False, trusted_snapshot: bool = False,
               compromise_confirmed: bool = False, evidence_available: bool = False) -> tuple[bool, str]:
    """Return ``(accepted, reason)``. Flags must be exactly ``True`` to count."""
    try:
        current, target = TrustLabel(current), TrustLabel(target)
    except ValueError:
        return False, "invalid_state"
    verified, trusted_snapshot = verified is True, trusted_snapshot is True
    compromise_confirmed, evidence_available = compromise_confirmed is True, evidence_available is True
    if target not in ALLOWED_TRANSITIONS[current]:
        return False, "transition_not_allowed"
    if target is TrustLabel.TRUSTED:
        if current is TrustLabel.RECOVERED and not verified:
            return False, "recovery_requires_independent_verification"
        if current is TrustLabel.UNKNOWN and not (verified and evidence_available):
            return False, "unknown_requires_evidence_and_verification"
        if not trusted_snapshot:
            return False, "trusted_snapshot_required"
    if target is TrustLabel.CONTAMINATED and not compromise_confirmed:
        return False, "confirmed_compromise_evidence_required"
    if target is TrustLabel.RECOVERED and not trusted_snapshot:
        return False, "trusted_snapshot_required"
    if target is TrustLabel.SUSPECT and not evidence_available:
        return False, "suspicion_evidence_required"
    return True, "accepted_by_policy"


class TrustTracker:
    """Holds one current label and an append-only history of attempted transitions.

    ``label`` is read-only and ``history`` returns copies, so neither can be edited from outside.
    Entering ``Trusted`` is possible only through :meth:`promote_after_verification`.
    """

    def __init__(self, label: TrustLabel = TrustLabel.UNKNOWN) -> None:
        initial = TrustLabel(label)
        if initial is TrustLabel.TRUSTED:
            raise ValueError("TrustTracker cannot start Trusted; use a verified promotion flow")
        self._label = initial
        self._history: list[dict[str, Any]] = []
        self._used_reports: set[str] = set()

    @property
    def label(self) -> TrustLabel:
        return self._label

    @property
    def history(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(h) for h in self._history)

    def _record(self, target: Any, accepted: bool, reason: str) -> tuple[bool, str]:
        self._history.append({"from": self._label.value, "to": str(getattr(target, "value", target)),
                              "accepted": accepted, "reason": reason})
        return accepted, reason

    def apply(self, target: TrustLabel, **flags: bool) -> tuple[bool, str]:
        """Attempt a non-promoting transition. ``Trusted`` is refused here, whatever the flags say."""
        if target == TrustLabel.TRUSTED or target == TrustLabel.TRUSTED.value:
            return self._record(target, False, "trusted_requires_verification_report")
        accepted, reason = transition(self._label, target, **flags)
        self._record(target, accepted, reason)
        if accepted:
            self._label = TrustLabel(target)
        return accepted, reason

    def promote_after_verification(self, report: VerificationReport, *, expected_checkpoint_sha256: str,
                                   expected_recovery_id: str, committed_state_sha256: str,
                                   evidence_available: bool = False, max_age_seconds: float | None = None,
                                   require_anchored_head: bool = True) -> tuple[bool, str]:
        """Promote to ``Trusted`` only on an authentic, unused, fully passing report **bound to this recovery**.

        The three ``expected_*`` / ``committed_*`` arguments are mandatory (keyword-only, non-empty
        strings); a missing or empty value is refused and recorded, never ignored:

        * ``expected_checkpoint_sha256``: the checkpoint whose trust the caller wants restored.
        * ``expected_recovery_id``: the recovery attempt that produced the state (from the committed store
          or ``RecoveryAttempt.recovery_id``), which must equal the id the verifier found in the audit log.
        * ``committed_state_sha256``: digest of the state **freshly re-read from the persistent store**
          now; it must equal ``report["verified_state_sha256"]``. A report that passed for some other
          state, or for state that changed afterwards, cannot promote.

        The five gates are re-evaluated with ``reinstate_trust`` instead of trusting the ``decision``
        string. By default the report must also say the audit head was anchored
        (``require_anchored_head=True``). ``max_age_seconds`` rejects stale reports. A report can
        promote at most once per tracker.
        """
        T = TrustLabel.TRUSTED
        for name, value in (("expected_checkpoint_sha256", expected_checkpoint_sha256),
                            ("expected_recovery_id", expected_recovery_id),
                            ("committed_state_sha256", committed_state_sha256)):
            if not isinstance(value, str) or not value:
                return self._record(T, False, f"binding_required:{name}")
        if not isinstance(report, VerificationReport) or not report.is_authentic():
            return self._record(T, False, "report_not_issued_by_verify_recovery")
        if report.report_id in self._used_reports:
            return self._record(T, False, "report_already_used")
        gates = report["gates"]
        if not (set(REQUIRED_GATES) <= set(gates)) or reinstate_trust(gates) is not TrustState.TRUSTED:
            return self._record(T, False, "verification_not_passed")
        if require_anchored_head and report["audit_head_anchored"] is not True:
            return self._record(T, False, "audit_head_not_anchored")
        if report["checkpoint_sha256"] != expected_checkpoint_sha256:
            return self._record(T, False, "report_for_different_checkpoint")
        if report["recovery_id"] != expected_recovery_id:
            return self._record(T, False, "report_for_different_recovery_attempt")
        verified = report["verified_state_sha256"]
        if not isinstance(verified, str) or verified != committed_state_sha256:
            return self._record(T, False, "committed_state_mismatch")
        if max_age_seconds is not None and time.time() - report.issued_at > max_age_seconds:
            return self._record(T, False, "report_expired")
        accepted, reason = transition(self._label, T, verified=True, trusted_snapshot=gates["checkpoint_valid"] is True,
                                      evidence_available=evidence_available is True)
        self._record(T, accepted, reason)
        if accepted:
            self._label = T
            self._used_reports.add(report.report_id)
        return accepted, reason
