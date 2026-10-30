"""Committed-state binding: the digest that promotion uses comes from a fresh re-read of the store."""
import sqlite3
import pytest
from helpers import CLEAN, MANIFEST
from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint, state_digest
from trustsr.recovery import recover_state_attempt
from trustsr.state_store import SqliteStateStore, StateCommitError
from trustsr.trust_machine import TrustLabel as L, TrustTracker
from trustsr.verification import verify_recovery


def flow(tmp_path, keys=None):
    private, public = generate_keypair()
    checkpoint = sign_checkpoint(dict(CLEAN), private, version=1)
    log = AuditLog(); log.append("checkpoint_created", {"id": "cp-1"}); log.declare_scope(MANIFEST)
    store = SqliteStateStore(tmp_path / "state.db")
    store.write_state({"counter": 999, "mode": "unsafe", "backdoor": True})
    current = store.read_committed().state
    attempt = recover_state_attempt(checkpoint, public, current, keys=keys, audit_log=log)
    committed = store.commit_recovery(attempt)
    head = log.head                                                   # stands in for an independent anchor
    report = verify_recovery(checkpoint=checkpoint, public_key=public, audit_log=log,
                             recovered_state=committed.state, scope_manifest=MANIFEST,
                             observed_record_ids=["e1", "e2"], keys=keys, recovery_id=attempt.recovery_id,
                             trusted_audit_head=head, require_anchored_head=True)
    return store, attempt, report


def test_commit_reread_verify_promote_roundtrip(tmp_path):
    store, attempt, report = flow(tmp_path)
    assert report["decision"] == "PASS"
    fresh = store.read_committed()
    assert fresh.state == CLEAN and fresh.recovery_id == attempt.recovery_id
    tr = TrustTracker(L.RECOVERED)
    assert tr.promote_after_verification(report, expected_checkpoint_sha256=attempt.checkpoint_sha256,
                                         expected_recovery_id=fresh.recovery_id,
                                         committed_state_sha256=fresh.state_sha256)[0]


def test_write_after_verification_blocks_promotion(tmp_path):
    store, attempt, report = flow(tmp_path)
    store.write_state({**CLEAN, "mode": "unsafe"})                    # agent state changes after the report
    fresh = store.read_committed()
    assert fresh.recovery_id is None                                  # no recovery vouches for it any more
    tr = TrustTracker(L.RECOVERED)
    ok, reason = tr.promote_after_verification(report, expected_checkpoint_sha256=attempt.checkpoint_sha256,
                                               expected_recovery_id=attempt.recovery_id,
                                               committed_state_sha256=fresh.state_sha256)
    assert (ok, reason) == (False, "committed_state_mismatch") and tr.label is L.RECOVERED


def test_edited_database_row_is_detected_on_read(tmp_path):
    store, _, _ = flow(tmp_path)
    con = sqlite3.connect(str(tmp_path / "state.db"))
    con.execute("UPDATE agent_state SET state_json = '{\"counter\":1,\"mode\":\"evil\"}'"); con.commit(); con.close()
    with pytest.raises(StateCommitError):
        store.read_committed()


def test_selective_recovery_state_digest_covers_the_whole_store(tmp_path):
    store, attempt, report = flow(tmp_path, keys=["mode"])
    fresh = store.read_committed()
    assert fresh.state["counter"] == 999 and fresh.state["mode"] == "safe"   # other keys untouched/unverified
    assert report["verified_state_sha256"] == fresh.state_sha256 == state_digest(fresh.state)


def test_commit_requires_a_recovery_attempt_and_rejects_non_json(tmp_path):
    store = SqliteStateStore(tmp_path / "s.db")
    with pytest.raises(TypeError):
        store.commit_recovery({"state": {}})
    with pytest.raises(ValueError):
        store.write_state({"x": float("nan")})
    assert store.read_committed() is None


def test_store_releases_the_file_so_it_can_be_deleted(tmp_path):
    import os
    store, _, _ = flow(tmp_path)
    store.read_committed()
    os.remove(tmp_path / "state.db")                                  # would fail on Windows if a handle leaked
