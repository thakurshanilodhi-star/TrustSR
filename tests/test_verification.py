import pytest
from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint
from trustsr.verification import verify_recovery
from helpers import make_case, CLEAN


def test_all_gates_pass_for_clean_case():
    result = verify_recovery(**make_case())
    assert result["decision"] == "PASS"
    assert all(result["gates"].values())


def test_incomplete_scope_fails_closed():
    case = make_case(); case["observed_record_ids"] = ["e1"]
    result = verify_recovery(**case)
    assert result["decision"] == "FAIL" and result["gates"]["scope_complete"] is False


def test_duplicate_or_unexpected_ids_fail():
    for ids in (["e1", "e1"], ["e1", "e2", "e3"]):
        case = make_case(); case["observed_record_ids"] = ids
        assert verify_recovery(**case)["gates"]["scope_complete"] is False


def test_recovery_not_logged_means_not_complete():
    case = make_case()
    case["audit_log"] = AuditLog()  # fresh log: no recovery events
    case["audit_log"].declare_scope(case["scope_manifest"])
    result = verify_recovery(**case)
    assert result["decision"] == "FAIL" and result["gates"]["recovery_complete"] is False


# --- regression: problem 1 (verifier compared against caller-supplied reference) ---
def test_recovered_state_must_match_signed_checkpoint_not_caller_value():
    case = make_case()
    case["recovered_state"] = {"counter": 999, "mode": "unsafe"}  # contaminated
    result = verify_recovery(**case)
    assert result["decision"] == "FAIL" and result["gates"]["contamination_removed"] is False
    assert result["contamination_report"]["changed_keys"] == ["counter", "mode"]


def test_extra_injected_key_in_recovered_state_fails():
    case = make_case(); case["recovered_state"] = {**CLEAN, "backdoor": True}
    result = verify_recovery(**case)
    assert result["gates"]["contamination_removed"] is False
    assert result["contamination_report"]["extra_keys"] == ["backdoor"]


# --- regression: problem 3 (empty / unrelated audit log) ---
def test_empty_audit_log_fails():
    case = make_case(); case["audit_log"] = AuditLog()
    result = verify_recovery(**case)
    assert result["decision"] == "FAIL" and result["gates"]["audit_valid"] is False


def test_trusted_head_mismatch_fails():
    case = make_case()
    assert verify_recovery(**case, trusted_audit_head=case["audit_log"].head)["decision"] == "PASS"
    assert verify_recovery(**case, trusted_audit_head="0" * 64)["gates"]["audit_valid"] is False


def test_audit_for_different_checkpoint_fails():
    case = make_case()
    other_private, _ = generate_keypair()
    # a different (validly signed under same-key? no) checkpoint digest must not match the log
    case["checkpoint"] = sign_checkpoint(dict(CLEAN, extra=1), other_private)
    result = verify_recovery(**case)
    assert result["decision"] == "FAIL"


# --- regression: problem 4 (self-attested completion, unbound manifest) ---
def test_manifest_not_declared_in_audit_fails():
    case = make_case()
    case["scope_manifest"] = {"expected_record_ids": ["e1"], "expected_count": 1}
    case["observed_record_ids"] = ["e1"]
    result = verify_recovery(**case)
    assert result["gates"]["scope_complete"] is False
    assert result["scope_report"]["manifest_bound_in_audit"] is False


def test_malformed_manifest_fails_closed():
    for bad in ({}, {"expected_record_ids": ["e1"], "expected_count": True},
                {"expected_record_ids": [1], "expected_count": 1}):
        case = make_case(); case["scope_manifest"] = bad
        assert verify_recovery(**case)["decision"] == "FAIL"


def test_invalid_checkpoint_fails_everything_dependent():
    case = make_case()
    _, other_public = generate_keypair()
    case["public_key"] = other_public
    result = verify_recovery(**case)
    assert result["decision"] == "FAIL"
    assert result["gates"]["checkpoint_valid"] is False
    assert result["gates"]["contamination_removed"] is False


def test_selective_recovery_verifies_only_selected_keys():
    case = make_case(current={"counter": 999, "mode": "unsafe", "other": 1}, keys=["counter"])
    result = verify_recovery(**case)
    assert result["decision"] == "PASS"
    # wrong key scope claimed at verification time must not match the logged recovery
    case["keys"] = ["mode"]
    assert verify_recovery(**case)["gates"]["recovery_complete"] is False
    case["keys"] = None
    assert verify_recovery(**case)["gates"]["recovery_complete"] is False


def test_selective_recovery_unrestored_key_is_not_asserted_clean():
    case = make_case(current={"counter": 999, "mode": "unsafe"}, keys=["counter"])
    case["keys"] = ["counter"]
    assert verify_recovery(**case)["decision"] == "PASS"  # 'mode' is out of declared scope


def test_keys_must_be_a_collection_not_a_bare_string():
    from trustsr.recovery import recover_state
    case = make_case()
    with pytest.raises(TypeError):
        recover_state(case["checkpoint"], case["public_key"], {"mode": "x"}, keys="mode")
    bad = verify_recovery(**{**case, "keys": "mode"})
    assert bad["decision"] == "FAIL"


def test_malformed_manifest_and_observed_ids_fail_closed_instead_of_raising():
    case = make_case()
    for manifest in (None, [], "x", 5):
        assert verify_recovery(**{**case, "scope_manifest": manifest})["decision"] == "FAIL"
    for observed in (None, "e1e2", 5):
        assert verify_recovery(**{**case, "observed_record_ids": observed})["decision"] == "FAIL"


def test_report_exposes_checkpoint_binding_fields():
    case = make_case()
    report = verify_recovery(**case)
    assert report["checkpoint_sha256"] == case["checkpoint"].payload_sha256
    assert report["checkpoint_version"] is None
    assert report.to_dict()["decision"] == "PASS"
