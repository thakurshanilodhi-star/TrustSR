import pytest
from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint, verify_checkpoint
from trustsr.recovery import recover_state
from trustsr.replay import HighWaterMark, SqliteHighWaterMark, ReplayError
from trustsr.verification import verify_recovery


def two_checkpoints():
    priv, pub = generate_keypair()
    return (sign_checkpoint({"mode": "old-vulnerable"}, priv, version=1),
            sign_checkpoint({"mode": "patched"}, priv, version=9), pub)


def test_old_valid_checkpoint_is_refused_after_newer_registered():
    old, new, pub = two_checkpoints()
    guard = HighWaterMark()
    assert guard.register(new.version)
    with pytest.raises(ReplayError):
        recover_state(old, pub, {}, replay_guard=guard)


def test_current_checkpoint_recovers():
    old, new, pub = two_checkpoints()
    guard = HighWaterMark(); guard.register(9)
    assert recover_state(new, pub, {"mode": "bad"}, replay_guard=guard) == {"mode": "patched"}


def test_unversioned_checkpoint_rejected_by_guard():
    priv, pub = generate_keypair()
    cp = sign_checkpoint({"x": 1}, priv)
    with pytest.raises(ReplayError):
        recover_state(cp, pub, {}, replay_guard=HighWaterMark())


def test_stripping_or_changing_version_breaks_signature():
    old, new, pub = two_checkpoints()
    stripped = type(new)(payload=new.payload, signature_b64=new.signature_b64, payload_sha256=new.payload_sha256, version=None)
    bumped = type(old)(payload=old.payload, signature_b64=old.signature_b64, payload_sha256=old.payload_sha256, version=99)
    assert verify_checkpoint(new, pub) and not verify_checkpoint(stripped, pub) and not verify_checkpoint(bumped, pub)


def test_invalid_versions_rejected():
    priv, _ = generate_keypair()
    for bad in (0, -1, True, 1.5, "1"):
        with pytest.raises(ValueError):
            sign_checkpoint({"x": 1}, priv, version=bad)


def test_register_is_strictly_monotonic():
    g = HighWaterMark()
    assert g.register(2) and not g.register(2) and not g.register(1) and g.mark == 2
    assert not g.register(True) and not g.register(0)


def test_explicit_rollback_is_allowed_and_logged():
    old, new, pub = two_checkpoints()
    guard = HighWaterMark(); guard.register(9)
    log = AuditLog()
    state = recover_state(old, pub, {}, replay_guard=guard, allow_rollback=True, audit_log=log)
    assert state == {"mode": "old-vulnerable"}
    assert any(e.details.get("rollback") is True for e in log.events)


def test_refusal_is_audited():
    old, new, pub = two_checkpoints()
    guard = HighWaterMark(); guard.register(9); log = AuditLog()
    with pytest.raises(ReplayError):
        recover_state(old, pub, {}, replay_guard=guard, audit_log=log)
    assert [e.event_type for e in log.events] == ["recovery_refused"]
    assert log.events[0].details["reason"] == "stale_or_replayed_checkpoint"


def _verify(cp, pub, guard, log, **kw):
    manifest = {"expected_record_ids": ["e1"], "expected_count": 1}
    return verify_recovery(checkpoint=cp, public_key=pub, audit_log=log, recovered_state=dict(cp.payload),
                           scope_manifest=manifest, observed_record_ids=["e1"], replay_guard=guard, **kw), manifest


def test_verifier_fails_replayed_checkpoint_even_if_recovered_with_rollback():
    old, new, pub = two_checkpoints()
    guard = HighWaterMark(); guard.register(9)
    log = AuditLog(); log.declare_scope({"expected_record_ids": ["e1"], "expected_count": 1})
    recover_state(old, pub, {}, replay_guard=guard, allow_rollback=True, audit_log=log)
    report, _ = _verify(old, pub, guard, log)
    assert report["decision"] == "FAIL" and report["gates"]["checkpoint_valid"] is False
    assert report["replay_report"]["fresh"] is False
    report2, _ = _verify(old, pub, guard, log, allow_rollback=True)
    assert report2["decision"] == "PASS"  # operator explicitly accepted the rollback


def test_verifier_passes_current_versioned_checkpoint():
    old, new, pub = two_checkpoints()
    guard = HighWaterMark(); guard.register(9)
    log = AuditLog(); log.declare_scope({"expected_record_ids": ["e1"], "expected_count": 1})
    recover_state(new, pub, {"junk": 1}, replay_guard=guard, audit_log=log)
    report, _ = _verify(new, pub, guard, log)
    assert report["decision"] == "PASS" and report["replay_report"]["high_water_mark"] == 9


def test_audit_event_for_other_version_does_not_count():
    old, new, pub = two_checkpoints()
    log = AuditLog(); log.declare_scope({"expected_record_ids": ["e1"], "expected_count": 1})
    recover_state(old, pub, {}, audit_log=log)           # recovered v1
    report, _ = _verify(new, pub, None, log)              # claims v9
    assert report["gates"]["recovery_complete"] is False


def test_sqlite_mark_persists_across_restart(tmp_path):
    db = str(tmp_path / "mark.db")
    with SqliteHighWaterMark(db) as g:
        assert g.register(3) and not g.register(3)
    with SqliteHighWaterMark(db) as g:
        assert g.mark == 3 and not g.register(2) and g.register(4)
        assert g.is_current_or_newer(4) and not g.is_current_or_newer(3)


def test_sqlite_mark_in_memory_and_invalid():
    with SqliteHighWaterMark() as g:
        assert not g.register(0) and not g.register(True) and g.mark == 0


def test_concurrent_registrations_advance_the_mark_exactly_once_per_version(tmp_path):
    import threading
    from trustsr.replay import HighWaterMark, SqliteHighWaterMark
    for guard in (HighWaterMark(), SqliteHighWaterMark(str(tmp_path / "hwm.db"))):
        wins, lock = [], threading.Lock()

        def worker(v):
            ok = guard.register(v)
            with lock:
                wins.append((v, ok))
        threads = [threading.Thread(target=worker, args=(v,)) for v in [1, 2, 3, 4, 5] * 6]
        [t.start() for t in threads]; [t.join() for t in threads]
        assert guard.mark == 5
        assert sorted(v for v, ok in wins if ok) == sorted(set(v for v, ok in wins if ok))  # no version won twice
        assert not guard.register(5) and not guard.register(1)
