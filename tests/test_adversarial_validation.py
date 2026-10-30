"""Adversarial validation v1: fail-closed behavior under hostile/malformed evidence.

These are deterministic unit tests, not a claim of exhaustive or production security.
"""
import pytest

from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair
from trustsr.verification import verify_recovery
from helpers import make_case


def test_missing_anchored_head_fails_when_anchor_is_required():
    case = make_case()
    report = verify_recovery(**case, require_anchored_head=True)
    assert report["decision"] == "FAIL"
    assert report["gates"]["audit_valid"] is False


def test_wrong_external_audit_head_fails_closed():
    case = make_case()
    report = verify_recovery(**case, trusted_audit_head="f" * 64, require_anchored_head=True)
    assert report["decision"] == "FAIL"
    assert report["gates"]["audit_valid"] is False


def test_wrong_recovery_attempt_id_does_not_borrow_another_attempt():
    case = make_case()
    report = verify_recovery(**case, recovery_id="not-the-recorded-attempt")
    assert report["decision"] == "FAIL"
    assert report["gates"]["recovery_complete"] is False


def test_duplicate_observed_ids_fail_closed():
    case = make_case()
    case["observed_record_ids"] = ["e1", "e1"]
    report = verify_recovery(**case)
    assert report["decision"] == "FAIL"
    assert report["gates"]["scope_complete"] is False


def test_non_json_recovered_state_cannot_be_verified():
    case = make_case()
    case["recovered_state"] = {"counter": float("nan"), "mode": "safe"}
    report = verify_recovery(**case)
    assert report["decision"] == "FAIL"
    assert report["gates"]["contamination_removed"] is False
    assert report["verified_state_sha256"] is None


def test_wrong_checkpoint_signing_key_fails_closed():
    case = make_case()
    _, unrelated_public_key = generate_keypair()
    case["public_key"] = unrelated_public_key
    report = verify_recovery(**case)
    assert report["decision"] == "FAIL"
    assert report["gates"]["checkpoint_valid"] is False
    assert report["gates"]["contamination_removed"] is False


def test_empty_audit_with_expected_external_head_fails():
    case = make_case()
    case["audit_log"] = AuditLog()
    report = verify_recovery(**case, trusted_audit_head="GENESIS")
    assert report["decision"] == "FAIL"
    assert report["gates"]["audit_valid"] is False


def test_verification_report_is_sealed_against_internal_mutation():
    report = verify_recovery(**make_case())
    assert report.is_authentic() is True
    # Deliberately bypass Python's ordinary attribute guard to test seal detection.
    object.__setattr__(report, "_content", {"decision": "PASS", "gates": {}})
    assert report.is_authentic() is False
