"""Explicit trust-state model. Unknown is never treated as trusted."""
from enum import Enum

class TrustState(str, Enum):
    UNKNOWN = "unknown"
    TRUSTED = "trusted"
    QUARANTINED = "quarantined"


def reinstate_trust(gates: dict[str, bool]) -> TrustState:
    """Trust is reinstated only when every required verification gate passes."""
    required = {"checkpoint_valid", "audit_valid", "recovery_complete", "contamination_removed", "scope_complete"}
    if not required.issubset(gates):
        return TrustState.UNKNOWN
    if any(not isinstance(gates[k], bool) for k in required):
        return TrustState.UNKNOWN
    if all(gates[k] is True for k in required):
        return TrustState.TRUSTED
    return TrustState.QUARANTINED
