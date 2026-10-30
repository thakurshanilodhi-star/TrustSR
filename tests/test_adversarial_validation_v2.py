"""Adversarial Validation v2: deterministic mutation, restart, and concurrency tests.

These tests exercise specific failure modes in this research prototype. They are not
exhaustive fuzzing, a formal proof, or a production-security certification.
"""
import random
import threading

import pytest

from helpers import make_case
from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint, verify_checkpoint
from trustsr.recovery import recover_state_attempt
from trustsr.replay import HighWaterMark, SqliteHighWaterMark
from trustsr.state_store import SqliteStateStore, StateCommitError
from trustsr.verification import verify_recovery


@pytest.mark.parametrize("bad_signature", ["", "!!!", "AA==", "0" * 128, "not-base64"])
def test_mutated_signature_encodings_never_verify(bad_signature):
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"mode": "safe", "counter": 4}, private, version=4)
    mutated = type(checkpoint)(payload=checkpoint.payload, signature_b64=bad_signature,
                               payload_sha256=checkpoint.payload_sha256, version=checkpoint.version)
    assert verify_checkpoint(mutated, public) is False


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(mode="unsafe"),
    lambda p: p.update(counter=5),
    lambda p: p.update(extra="injected"),
    lambda p: p.pop("mode"),
])
def test_payload_mutations_after_signing_are_detected(mutate):
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"mode": "safe", "counter": 4}, private, version=4)
    mutate(checkpoint.payload)
    assert verify_checkpoint(checkpoint, public) is False


def test_version_fuzz_has_strict_monotonic_high_water_mark():
    rng = random.Random(20261024)
    versions = list(range(1, 101))
    rng.shuffle(versions)
    guard = HighWaterMark()
    previous = guard.mark
    for version in versions:
        accepted = guard.register(version)
        assert guard.mark >= previous
        assert accepted is (version > previous)
        previous = guard.mark
    assert guard.mark == 100
    assert not guard.register(100)
    assert not guard.register(99)
    assert not guard.register(True)


def test_sqlite_high_water_mark_is_monotonic_across_instances_and_threads(tmp_path):
    db = str(tmp_path / "shared-high-water.db")
    guards = [SqliteHighWaterMark(db) for _ in range(4)]
    try:
        versions = list(range(1, 41)) * 3
        random.Random(42).shuffle(versions)
        results = []
        result_lock = threading.Lock()
        errors = []

        def worker(index, version):
            try:
                result = guards[index % len(guards)].register(version)
                with result_lock:
                    results.append((version, result))
            except Exception as exc:  # surface cross-connection SQLite races as a test failure
                with result_lock:
                    errors.append(repr(exc))

        threads = [threading.Thread(target=worker, args=(i, v)) for i, v in enumerate(versions)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        assert all(not thread.is_alive() for thread in threads), "registration thread hung"
        assert errors == []
        assert guards[0].mark == 40
        accepted_versions = [version for version, accepted in results if accepted]
        assert len(accepted_versions) == len(set(accepted_versions))
        assert all(not guard.register(40) for guard in guards)
    finally:
        for guard in guards:
            guard.close()


def test_recovery_attempt_state_isolated_from_nested_caller_mutations():
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"profile": {"mode": "safe"}, "counter": 7}, private, version=1)
    current = {"profile": {"mode": "unsafe"}, "counter": 99}
    attempt = recover_state_attempt(checkpoint, public, current, keys=["profile"])
    current["profile"]["mode"] = "changed-after-call"
    assert attempt.state["profile"]["mode"] == "safe"  # recovery result is detached from caller state
    attempt.state["profile"]["mode"] = "changed-attempt-output"
    # The attempt is a data object and its nested dict is mutable; its recorded digest must expose that.
    from trustsr.checkpoint import state_digest
    assert state_digest(attempt.state) != attempt.state_sha256


def test_recovery_commit_survives_store_reopen_with_matching_digest_and_id(tmp_path):
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"mode": "safe", "counter": 9}, private, version=2)
    attempt = recover_state_attempt(checkpoint, public, {"mode": "unsafe", "counter": 0})
    db = tmp_path / "agent-state.db"
    committed = SqliteStateStore(db).commit_recovery(attempt)
    reopened = SqliteStateStore(db).read_committed()
    assert reopened is not None
    assert reopened.state == committed.state == attempt.state
    assert reopened.state_sha256 == committed.state_sha256 == attempt.state_sha256
    assert reopened.recovery_id == committed.recovery_id == attempt.recovery_id
    assert reopened.revision == committed.revision


def test_restart_read_detects_digest_column_tampering(tmp_path):
    import sqlite3

    store = SqliteStateStore(tmp_path / "state.db")
    store.write_state({"mode": "safe", "counter": 1})
    conn = sqlite3.connect(str(tmp_path / "state.db"))
    conn.execute("UPDATE agent_state SET state_sha256=?", ("0" * 64,))
    conn.commit()
    conn.close()
    with pytest.raises(StateCommitError):
        SqliteStateStore(tmp_path / "state.db").read_committed()


def test_state_written_after_recovery_clears_recovery_provenance(tmp_path):
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"mode": "safe"}, private, version=1)
    attempt = recover_state_attempt(checkpoint, public, {"mode": "unsafe"})
    store = SqliteStateStore(tmp_path / "state.db")
    store.commit_recovery(attempt)
    store.write_state({"mode": "later-unverified-write"})
    reopened = SqliteStateStore(tmp_path / "state.db").read_committed()
    assert reopened is not None
    assert reopened.recovery_id is None
    assert reopened.state == {"mode": "later-unverified-write"}


def test_missing_completion_event_after_state_commit_fails_verification(tmp_path):
    """Model a crash where state commit happened but completion evidence did not persist."""
    attempts = []
    case = make_case(attempt_out=attempts)
    attempt = attempts[0]
    store = SqliteStateStore(tmp_path / "state.db")
    store.commit_recovery(attempt)

    original_events = case["audit_log"].events
    assert original_events[-1].event_type == "recovery_completed"
    incomplete_log = AuditLog.from_events(original_events[:-1])
    assert incomplete_log.verify() is True
    case["audit_log"] = incomplete_log
    report = verify_recovery(**case, recovery_id=attempt.recovery_id)
    assert report["decision"] == "FAIL"
    assert report["gates"]["recovery_complete"] is False


def test_malformed_recovered_values_fail_closed_across_numeric_edge_cases():
    for value in (float("nan"), float("inf"), -float("inf")):
        case = make_case()
        case["recovered_state"] = {"counter": value, "mode": "safe"}
        report = verify_recovery(**case)
        assert report["decision"] == "FAIL"
        assert report["verified_state_sha256"] is None
        assert report["gates"]["contamination_removed"] is False
