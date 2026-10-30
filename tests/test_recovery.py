import pytest
from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint
from trustsr.recovery import recover_state


def test_full_recovery_restores_checkpoint_values():
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"x": 1, "y": 2}, private)
    assert recover_state(checkpoint, public, {"x": 99, "y": 2}) == {"x": 1, "y": 2}


# regression: problem 2 (injected keys survived full recovery)
def test_full_recovery_drops_injected_keys():
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"x": 1, "y": 2}, private)
    assert recover_state(checkpoint, public, {"x": 99, "y": 2, "backdoor": True}) == {"x": 1, "y": 2}


def test_selective_recovery_keeps_other_keys():
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"x": 1, "y": 2}, private)
    assert recover_state(checkpoint, public, {"x": 99, "y": 50, "z": 3}, keys=["x"]) == {"x": 1, "y": 50, "z": 3}


def test_recovery_does_not_alias_checkpoint_payload():
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"x": {"a": 1}}, private)
    restored = recover_state(checkpoint, public, {})
    restored["x"]["a"] = 2
    assert checkpoint.payload == {"x": {"a": 1}}


def test_recovery_refuses_invalid_checkpoint_and_logs_it():
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"x": 1}, private)
    bad = type(checkpoint)(payload={"x": 2}, signature_b64=checkpoint.signature_b64,
                           payload_sha256=checkpoint.payload_sha256)
    log = AuditLog()
    with pytest.raises(ValueError):
        recover_state(bad, public, {"x": 99}, audit_log=log)
    assert [e.event_type for e in log.events] == ["recovery_refused"]


def test_requested_missing_key_fails():
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"x": 1}, private)
    with pytest.raises(KeyError):
        recover_state(checkpoint, public, {"y": 2}, keys=["y"])
