from trustsr.checkpoint import generate_keypair, sign_checkpoint, verify_checkpoint

def test_signed_checkpoint_verifies_and_tampering_fails():
    private, public = generate_keypair()
    checkpoint = sign_checkpoint({"counter": 4, "mode": "safe"}, private)
    assert verify_checkpoint(checkpoint, public)
    tampered = type(checkpoint)(payload={"counter": 5, "mode": "safe"}, signature_b64=checkpoint.signature_b64, payload_sha256=checkpoint.payload_sha256)
    assert not verify_checkpoint(tampered, public)

def test_wrong_key_fails():
    private, _ = generate_keypair()
    _, other_public = generate_keypair()
    checkpoint = sign_checkpoint({"x": 1}, private)
    assert not verify_checkpoint(checkpoint, other_public)


def test_nan_payload_rejected():
    import pytest
    private, _ = generate_keypair()
    with pytest.raises(ValueError):
        sign_checkpoint({"x": float("nan")}, private)


def test_payload_mutation_after_signing_detected():
    private, public = generate_keypair()
    cp = sign_checkpoint({"x": 1}, private)
    cp.payload["x"] = 2
    assert not verify_checkpoint(cp, public)
