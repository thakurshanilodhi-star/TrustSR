"""Out-of-band anchoring of the audit-log head (what ``trusted_audit_head`` must come from).

``verify_recovery(..., trusted_audit_head=log.head)`` proves nothing: the head is read from the
very log being checked, so any rewritten log trivially matches itself. The expected head has to
be recorded *earlier* and *somewhere else* (separate process, host, volume or service, writable
only by the recovery controller) and loaded at verification time:

    anchor = HeadAnchor("/secure/volume/audit_head.json")
    ...recover_state(..., audit_log=log)...
    anchor.advance(log)                       # recovery controller records the new head
    ...
    verify_recovery(..., trusted_audit_head=anchor.load())   # verifier reads the stored value

Three implementations of the same ``load()`` / ``advance(log)`` contract:

* ``HeadAnchor``: local file (atomic write + fsync). NOT independent: whoever can rewrite the log
  can rewrite this file. Fine for tests and demos.
* ``SignedHeadAnchor``: local file whose record is **signed by a separate anchor authority key**. The
  verifier holds only the public key, so a process that can rewrite the file but does not hold the
  private key cannot forge a head (it can still restore an older *validly signed* file; pass
  ``min_sequence`` to ``load`` to detect that).
* ``trustsr.anchor_service``: the same signed anchor behind a small HTTP service, so the head lives
  under a different OS account / host than the controller (``RemoteHeadAnchor`` is the client).

Whether the storage is *independent* is a deployment property (different account, host, key custody);
see ``docs/anchor_deployment.md``. The code cannot certify it.
"""
import base64
import json
import os
import tempfile
import time
from typing import Any, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .audit import AuditLog, GENESIS
from .checkpoint import canonical_bytes, public_key_bytes


class AnchorError(ValueError):
    """The log cannot be anchored (invalid chain, or it does not extend the stored head)."""


class AnchorBackend(Protocol):
    def load(self) -> str | None: ...
    def advance(self, log: AuditLog) -> str: ...


def _replace_with_retry(src: str, dst: str, attempts: int = 6) -> None:
    for i in range(attempts):
        try:
            os.replace(src, dst)  # atomic on POSIX and Windows
            return
        except PermissionError:   # Windows: target briefly held open by a reader / scanner
            if i == attempts - 1:
                raise
            time.sleep(0.05 * (i + 1))


def _atomic_write(path: str, text: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".anchor-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        _replace_with_retry(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _check_extends(log: AuditLog, previous: str | None) -> None:
    if not log.verify():
        raise AnchorError("refusing to anchor an empty or inconsistent audit log")
    if previous is not None and not log.extends(previous):
        raise AnchorError("log does not extend the previously anchored head (truncated or replaced?)")


class HeadAnchor:
    """Unsigned local-file anchor. Not independent of the log's controller (see module docstring)."""

    def __init__(self, path: str) -> None:
        self.path = os.fspath(path)

    def load(self) -> str | None:
        """Return the stored head, or ``None`` if nothing was ever anchored (NOT ``GENESIS``).

        ``None`` is deliberately distinguishable from a real head: passing it to ``verify_recovery``
        means "unanchored", which the report flags and ``require_anchored_head=True`` refuses.
        Raises ``AnchorError`` if the file exists but is unreadable or malformed (fail closed).
        """
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            raise AnchorError(f"anchor file unreadable: {exc}") from exc
        head = data.get("head") if isinstance(data, dict) else None
        if not isinstance(head, str) or not head:
            raise AnchorError("anchor file malformed")
        return head

    def advance(self, log: AuditLog) -> str:
        """Anchor ``log.head``. The log must be valid and must extend the previously stored head."""
        _check_extends(log, self.load())
        head = log.head
        _atomic_write(self.path, json.dumps({"head": head, "events": len(log.events), "genesis": GENESIS}))
        return head


# ---- signed anchor ---------------------------------------------------------------------------------
_PURPOSE = "trustsr-anchor-v1"


def _sign_record(record: dict[str, Any], signer: Ed25519PrivateKey) -> dict[str, Any]:
    sig = signer.sign(canonical_bytes({"purpose": _PURPOSE, "record": record}))
    return {"record": record, "signature": base64.b64encode(sig).decode("ascii")}


def verify_envelope(envelope: Any, authority_public_key: Ed25519PublicKey) -> dict[str, Any]:
    """Return the record of a signed envelope, or raise ``AnchorError`` (fail closed)."""
    try:
        record, signature = envelope["record"], base64.b64decode(envelope["signature"], validate=True)
        authority_public_key.verify(signature, canonical_bytes({"purpose": _PURPOSE, "record": record}))
    except (KeyError, TypeError, ValueError, InvalidSignature) as exc:
        raise AnchorError(f"anchor record is not validly signed by the anchor authority: {exc!r}") from exc
    if not (isinstance(record, dict) and isinstance(record.get("head"), str) and record["head"]
            and isinstance(record.get("sequence"), int) and not isinstance(record.get("sequence"), bool)):
        raise AnchorError("anchor record malformed")
    return record


class SignedHeadAnchor:
    """File anchor whose records are signed by an anchor-authority key held elsewhere.

    ``signer`` (private key) is given only to the process/account allowed to *write*; verifiers get only
    ``authority_public_key`` and can ``load`` but not ``advance``.
    """

    def __init__(self, path: str, authority_public_key: Ed25519PublicKey,
                 signer: Ed25519PrivateKey | None = None) -> None:
        self.path = os.fspath(path)
        self._pub = authority_public_key
        if signer is not None and public_key_bytes(signer.public_key()) != public_key_bytes(authority_public_key):
            raise AnchorError("signer does not match authority_public_key")
        self._signer = signer

    def envelope(self) -> dict[str, Any] | None:
        try:
            with open(self.path, encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            raise AnchorError(f"anchor file unreadable: {exc}") from exc

    def load_record(self) -> dict[str, Any] | None:
        env = self.envelope()
        return None if env is None else verify_envelope(env, self._pub)

    def load(self, min_sequence: int | None = None) -> str | None:
        """Verified head or ``None``. ``min_sequence`` rejects a restored, older (validly signed) file."""
        record = self.load_record()
        if record is None:
            if min_sequence:
                raise AnchorError("anchor missing but a previous sequence was expected (deleted or rolled back?)")
            return None
        if min_sequence is not None and record["sequence"] < min_sequence:
            raise AnchorError(f"anchor sequence {record['sequence']} is older than expected {min_sequence}")
        return record["head"]

    def advance(self, log: AuditLog) -> str:
        if self._signer is None:
            raise AnchorError("this anchor handle is read-only (no signer)")
        previous = self.load_record()
        _check_extends(log, None if previous is None else previous["head"])
        record = {"head": log.head, "events": len(log.events), "genesis": GENESIS,
                  "sequence": 1 if previous is None else previous["sequence"] + 1}
        _atomic_write(self.path, json.dumps(_sign_record(record, self._signer)))
        return log.head
