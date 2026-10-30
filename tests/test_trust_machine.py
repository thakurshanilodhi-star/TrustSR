import itertools
from trustsr.trust_machine import TrustLabel as L, TrustTracker, transition, ALLOWED_TRANSITIONS
from helpers import make_case, bindings
from trustsr.verification import verify_recovery

FLAGS = ("verified", "trusted_snapshot", "compromise_confirmed", "evidence_available")


def t(a, b, **k): return transition(a, b, **k)[0]


def test_lab09_critical_rules():
    assert not t(L.RECOVERED, L.TRUSTED, verified=False, trusted_snapshot=True)
    assert t(L.RECOVERED, L.TRUSTED, verified=True, trusted_snapshot=True)
    assert not t(L.CONTAMINATED, L.TRUSTED, verified=True, trusted_snapshot=True)
    assert not t(L.CONTAMINATED, L.RECOVERED) and t(L.CONTAMINATED, L.RECOVERED, trusted_snapshot=True)
    assert not t(L.SUSPECT, L.CONTAMINATED) and t(L.SUSPECT, L.CONTAMINATED, compromise_confirmed=True)
    assert not t(L.UNKNOWN, L.TRUSTED, verified=True, trusted_snapshot=True)
    assert t(L.UNKNOWN, L.TRUSTED, verified=True, trusted_snapshot=True, evidence_available=True)
    assert not t(L.TRUSTED, L.CONTAMINATED)


def test_invariant_trusted_only_via_verified_snapshot_exhaustively():
    # For every (from, to, flag-combination), any accepted move into Trusted needs verified AND snapshot,
    # and may only come from Recovered or Unknown.
    for a, b in itertools.product(L, L):
        for combo in itertools.product([False, True], repeat=4):
            ok, _ = transition(a, b, **dict(zip(FLAGS, combo)))
            if ok and b is L.TRUSTED:
                flags = dict(zip(FLAGS, combo))
                assert a in (L.RECOVERED, L.UNKNOWN) and flags["verified"] and flags["trusted_snapshot"]
            if ok:
                assert b in ALLOWED_TRANSITIONS[a]


def test_truthy_non_bool_flags_do_not_count():
    assert not t(L.RECOVERED, L.TRUSTED, verified=1, trusted_snapshot="yes")
    assert transition("Bogus", L.TRUSTED) == (False, "invalid_state")


def test_tracker_fails_closed_and_keeps_history():
    tr = TrustTracker()
    assert tr.apply(L.TRUSTED)[0] is False and tr.label is L.UNKNOWN
    assert tr.apply(L.RECOVERED, trusted_snapshot=True)[0] and tr.label is L.RECOVERED
    assert len(tr.history) == 2 and tr.history[0]["accepted"] is False


def test_promotion_requires_verify_recovery_pass():
    tr = TrustTracker(L.RECOVERED)
    good = verify_recovery(**make_case(anchored=True))
    assert tr.promote_after_verification(good, **bindings(good))[0] and tr.label is L.TRUSTED
    case = make_case(); case["observed_record_ids"] = ["e1"]
    bad = verify_recovery(**case)
    tr2 = TrustTracker(L.RECOVERED)
    assert not tr2.promote_after_verification(bad, **bindings(bad))[0] and tr2.label is L.RECOVERED
