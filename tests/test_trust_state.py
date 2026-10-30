from trustsr.trust_state import TrustState, reinstate_trust

ALL = {"checkpoint_valid": True, "audit_valid": True, "recovery_complete": True,
       "contamination_removed": True, "scope_complete": True}


def test_all_true_is_trusted():
    assert reinstate_trust(ALL) is TrustState.TRUSTED


def test_missing_gate_is_unknown():
    assert reinstate_trust({k: v for k, v in ALL.items() if k != "audit_valid"}) is TrustState.UNKNOWN


def test_failed_gate_is_quarantined():
    assert reinstate_trust({**ALL, "scope_complete": False}) is TrustState.QUARANTINED


def test_non_bool_gate_is_never_trusted():
    assert reinstate_trust({**ALL, "audit_valid": 1}) is TrustState.UNKNOWN
