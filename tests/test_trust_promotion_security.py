"""Regression tests for the trust-promotion flaw: a fabricated report must never promote trust."""
import copy, pickle
import pytest
from helpers import bindings, make_case
from trustsr.trust_machine import TrustLabel as L, TrustTracker
from trustsr.verification import VerificationReport, verify_recovery

FAKE = {"decision": "PASS", "trust_state": "trusted",
        "gates": {"checkpoint_valid": True, "audit_valid": True, "recovery_complete": True,
                  "contamination_removed": True, "scope_complete": True}}


def good():
    return verify_recovery(**make_case(anchored=True))


B0 = dict(expected_checkpoint_sha256="a" * 64, expected_recovery_id="r", committed_state_sha256="b" * 64)


def test_fabricated_minimal_dict_cannot_promote():
    tr = TrustTracker(L.RECOVERED)
    fake = {"decision": "PASS", "trust_state": "trusted", "gates": {"checkpoint_valid": True}}
    assert tr.promote_after_verification(fake, **B0) == (False, "report_not_issued_by_verify_recovery")
    assert tr.label is L.RECOVERED


def test_fabricated_complete_dict_cannot_promote():
    tr = TrustTracker(L.RECOVERED)
    assert not tr.promote_after_verification(FAKE, **B0)[0] and tr.label is L.RECOVERED


def test_real_report_converted_to_dict_cannot_promote():
    tr = TrustTracker(L.RECOVERED)
    assert not tr.promote_after_verification(dict(good()), **B0)[0]
    assert not tr.promote_after_verification(good().to_dict(), **B0)[0]


def test_report_cannot_be_constructed_or_subclassed():
    with pytest.raises(TypeError):
        VerificationReport(dict(FAKE))
    with pytest.raises(TypeError):
        VerificationReport(dict(FAKE), _token=object())
    with pytest.raises(TypeError):
        type("Sub", (VerificationReport,), {})


def test_report_is_immutable_and_reads_are_copies():
    report = good()
    with pytest.raises(AttributeError):
        report._content = dict(FAKE)
    with pytest.raises(AttributeError):
        report.report_id = "x"
    with pytest.raises(TypeError):
        report["decision"] = "PASS"
    report["gates"]["scope_complete"] = False      # mutating a returned copy...
    assert report["gates"]["scope_complete"] is True  # ...does not touch the report
    assert report.is_authentic()


def test_report_cannot_be_copied_or_pickled_into_a_second_identity():
    report = good()
    assert copy.deepcopy(report) is report and copy.copy(report) is report
    with pytest.raises(TypeError):
        pickle.dumps(report)


def test_tampering_with_internals_after_issue_is_detected():
    case = make_case(); case["observed_record_ids"] = ["e1"]            # a failing verification
    bad = verify_recovery(**case)
    assert bad["decision"] == "FAIL"
    bad._content["gates"]["scope_complete"] = True                     # attacker edits internals in place
    bad._content["decision"] = "PASS"
    assert not bad.is_authentic()
    tr = TrustTracker(L.RECOVERED)
    assert tr.promote_after_verification(bad, **bindings(bad)) == (False, "report_not_issued_by_verify_recovery")


def test_promotion_ignores_decision_string_and_rederives_from_gates():
    case = make_case(); case["observed_record_ids"] = ["e1"]
    bad = verify_recovery(**case)
    # Even if the (sealed) text said PASS, the gates are what count: a failed gate blocks promotion.
    tr = TrustTracker(L.RECOVERED)
    assert tr.promote_after_verification(bad, **bindings(bad)) == (False, "verification_not_passed")


def test_apply_cannot_enter_trusted_directly():
    tr = TrustTracker(L.RECOVERED)
    for target in (L.TRUSTED, "Trusted"):
        assert tr.apply(target, verified=True, trusted_snapshot=True, evidence_available=True) == \
            (False, "trusted_requires_verification_report")
    assert tr.label is L.RECOVERED


def test_label_and_history_cannot_be_edited_from_outside():
    tr = TrustTracker(L.RECOVERED)
    with pytest.raises(AttributeError):
        tr.label = L.TRUSTED
    tr.history[0:0]  # history is a tuple snapshot
    assert isinstance(tr.history, tuple)
    tr.promote_after_verification(FAKE, **B0)
    tr.history[0]["accepted"] = True               # edit a returned copy
    assert tr.history[0]["accepted"] is False


def test_report_is_single_use_per_tracker():
    report = good()
    tr = TrustTracker(L.RECOVERED)
    assert tr.promote_after_verification(report, **bindings(report))[0] and tr.label is L.TRUSTED
    assert tr.apply(L.SUSPECT, evidence_available=True)[0]
    assert tr.apply(L.RECOVERED, trusted_snapshot=True)[0]
    assert tr.promote_after_verification(report, **bindings(report)) == (False, "report_already_used")   # replayed report
    assert tr.label is L.RECOVERED


def test_checkpoint_recovery_state_and_age_bindings():
    report = good(); b = bindings(report)
    tr = TrustTracker(L.RECOVERED)
    assert tr.promote_after_verification(report, **{**b, "expected_checkpoint_sha256": "0" * 64}) == \
        (False, "report_for_different_checkpoint")
    assert tr.promote_after_verification(report, **{**b, "expected_recovery_id": "other"}) == \
        (False, "report_for_different_recovery_attempt")
    assert tr.promote_after_verification(report, **{**b, "committed_state_sha256": "0" * 64}) == \
        (False, "committed_state_mismatch")
    assert tr.promote_after_verification(report, **b, max_age_seconds=-1) == (False, "report_expired")
    assert tr.label is L.RECOVERED
    assert tr.promote_after_verification(report, **b, max_age_seconds=60)[0]


def test_bindings_are_mandatory_and_checked_even_when_blank():
    report = good(); b = bindings(report)
    tr = TrustTracker(L.RECOVERED)
    for name in b:                                                    # omitted -> Python refuses the call
        with pytest.raises(TypeError):
            tr.promote_after_verification(report, **{k: v for k, v in b.items() if k != name})
    for name in b:                                                    # None / "" / non-str -> refused + recorded
        for bad in (None, "", 0):
            assert tr.promote_after_verification(report, **{**b, name: bad}) == (False, f"binding_required:{name}")
    assert tr.label is L.RECOVERED and tr.history[-1]["accepted"] is False


def test_unanchored_report_cannot_promote_by_default():
    report = verify_recovery(**make_case())                          # no anchored head
    assert report["audit_head_anchored"] is False and report["decision"] == "PASS"
    tr = TrustTracker(L.RECOVERED)
    assert tr.promote_after_verification(report, **bindings(report)) == (False, "audit_head_not_anchored")
    assert tr.promote_after_verification(report, **bindings(report), require_anchored_head=False)[0]


def test_report_carries_recovery_id_and_state_digest_from_the_log_and_the_state():
    out = []
    case = make_case(anchored=True, attempt_out=out)
    report = verify_recovery(**case)
    assert report["recovery_id"] == out[0].recovery_id and report["verified_state_sha256"] == out[0].state_sha256


def test_report_for_a_different_recovery_attempt_is_not_accepted():
    a, b = [], []
    case = make_case(anchored=True, attempt_out=a)
    report = verify_recovery(**case)
    other = make_case(anchored=True, attempt_out=b)                  # a second, unrelated recovery
    tr = TrustTracker(L.RECOVERED)
    bnd = dict(bindings(report), expected_recovery_id=b[0].recovery_id)
    assert tr.promote_after_verification(report, **bnd) == (False, "report_for_different_recovery_attempt")
    pinned = verify_recovery(**case, recovery_id="not-an-attempt")   # verifier can also pin one attempt
    assert pinned["gates"]["recovery_complete"] is False and pinned["recovery_id"] is None


def test_state_changed_after_verification_cannot_promote():
    report = good()
    tampered_digest = "f" * 64                                       # digest of the live store, re-read later
    tr = TrustTracker(L.RECOVERED)
    assert tr.promote_after_verification(report, **dict(bindings(report), committed_state_sha256=tampered_digest)) == \
        (False, "committed_state_mismatch")


def test_non_canonical_state_fails_closed_and_cannot_be_bound():
    case = make_case(anchored=True)
    case["recovered_state"] = dict(case["recovered_state"], counter=float("nan"))
    report = verify_recovery(**case)
    assert report["decision"] == "FAIL" and report["verified_state_sha256"] is None


def test_unknown_state_still_needs_evidence_even_with_real_report():
    tr = TrustTracker(L.UNKNOWN)
    g = good()
    assert tr.promote_after_verification(g, **bindings(g)) == (False, "unknown_requires_evidence_and_verification")
    g2 = good()
    assert tr.promote_after_verification(g2, **bindings(g2), evidence_available=True)[0]


def test_contaminated_state_cannot_jump_to_trusted_even_with_real_report():
    tr = TrustTracker(L.CONTAMINATED)
    g = good()
    assert not tr.promote_after_verification(g, **bindings(g))[0] and tr.label is L.CONTAMINATED


def test_constructor_cannot_start_trusted():
    with pytest.raises(ValueError, match="cannot start Trusted"):
        TrustTracker(L.TRUSTED)
    with pytest.raises(ValueError, match="cannot start Trusted"):
        TrustTracker("Trusted")
