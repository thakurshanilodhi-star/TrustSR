"""Canonical JSON checkpoint signing and verification using Ed25519.

The caller must provision and trust the public key independently. A valid signature
proves that the corresponding private key signed these bytes; it does not establish
that the key owner is trustworthy or that the checkpoint represents a clean state.
"""
import base64, hashlib, json
from dataclasses import dataclass
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


def canonical_bytes(value: Any) -> bytes:
    """Deterministic JSON bytes (sorted keys, no whitespace, UTF-8).

    NaN/Infinity are rejected (``ValueError``) because they are not valid JSON and
    would make the encoding ambiguous. This is *not* full RFC 8785 (JCS) number
    canonicalization; avoid floats in signed payloads if cross-language
    reproducibility matters.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")

def state_digest(state: Any) -> str:
    """SHA-256 (hex) of the canonical encoding of an agent-state dictionary.

    Use it on the state **as re-read from the committed store**, not on the in-memory dictionary a
    recovery function returned. Raises ``ValueError``/``TypeError`` for non-JSON data or NaN.
    """
    return hashlib.sha256(canonical_bytes(state)).hexdigest()


def valid_version(version: Any) -> bool:
    """A checkpoint version is a positive int (bool is rejected)."""
    return isinstance(version, int) and not isinstance(version, bool) and version >= 1


@dataclass(frozen=True)
class SignedCheckpoint:
    """A signed state payload.

    ``version`` is optional. When present it is covered by the signature (so it cannot be
    stripped or altered) and enables replay/rollback protection via ``trustsr.replay``.
    A checkpoint with ``version=None`` is signed over the payload alone, exactly as in 0.1.x.
    """
    payload: dict[str, Any]
    signature_b64: str
    payload_sha256: str
    version: int | None = None


def _signing_bytes(payload: dict[str, Any], version: int | None) -> bytes:
    if version is None:
        return canonical_bytes(payload)
    return canonical_bytes({"checkpoint_version": version, "payload": payload})


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def public_key_bytes(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)


def sign_checkpoint(payload: dict[str, Any], private_key: Ed25519PrivateKey, version: int | None = None) -> SignedCheckpoint:
    if version is not None and not valid_version(version):
        raise ValueError("version must be a positive int")
    signature = private_key.sign(_signing_bytes(payload, version))
    return SignedCheckpoint(payload=payload, signature_b64=base64.b64encode(signature).decode("ascii"),
                            payload_sha256=hashlib.sha256(canonical_bytes(payload)).hexdigest(), version=version)


def verify_checkpoint(checkpoint: SignedCheckpoint, trusted_public_key: Ed25519PublicKey) -> bool:
    try:
        if checkpoint.version is not None and not valid_version(checkpoint.version):
            return False
        if hashlib.sha256(canonical_bytes(checkpoint.payload)).hexdigest() != checkpoint.payload_sha256:
            return False
        signature = base64.b64decode(checkpoint.signature_b64, validate=True)
        trusted_public_key.verify(signature, _signing_bytes(checkpoint.payload, checkpoint.version))
        return True
    except Exception:
        return False
