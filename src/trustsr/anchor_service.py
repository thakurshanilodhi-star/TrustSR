"""Anchor-as-a-service: the audit head lives in a *different process / account / host* than the log.

``AnchorServer`` owns the anchor-authority private key and the storage file; the recovery controller and
the verifier only know a bearer token and the authority's **public** key. A controller compromised after
the fact can still ask the service to advance (it must present a log that extends the stored head), but it
cannot rewrite or roll back what the service stored, and cannot forge a head the verifier will accept.

Standard library only (``http.server`` / ``urllib``), identical on Linux and Windows. The transport is
plain HTTP: bind to localhost or put TLS in front (reverse proxy / service mesh) for anything else.
Run it under its own OS account with the key and the file readable only by that account
(``docs/anchor_deployment.md``). Single-purpose reference service: no rate limiting, no multi-tenant auth.
"""
import hmac
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .anchor import AnchorError, SignedHeadAnchor, verify_envelope
from .audit import AuditLog

_MAX_BODY = 4 * 1024 * 1024


class AnchorServer:
    def __init__(self, store_path: str, token: str, authority_key: Ed25519PrivateKey,
                 host: str = "127.0.0.1", port: int = 0) -> None:
        if not isinstance(token, str) or len(token) < 16:
            raise ValueError("token must be a string of at least 16 characters")
        self._token = token.encode("utf-8")
        self._anchor = SignedHeadAnchor(store_path, authority_key.public_key(), signer=authority_key)
        self._lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # silence default stderr logging
                pass

            def _send(self, code: int, body: dict) -> None:
                data = json.dumps(body).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _authorized(self) -> bool:
                header = self.headers.get("Authorization", "")
                return header.startswith("Bearer ") and hmac.compare_digest(header[7:].encode("utf-8"), outer._token)

            def do_GET(self):
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized"})
                if self.path != "/head":
                    return self._send(404, {"error": "not found"})
                try:
                    with outer._lock:
                        env = outer._anchor.envelope()
                    self._send(200, {"envelope": env})
                except AnchorError as exc:
                    self._send(500, {"error": str(exc)})

            def do_POST(self):
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized"})
                if self.path != "/advance":
                    return self._send(404, {"error": "not found"})
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= _MAX_BODY:
                        return self._send(413, {"error": "bad body size"})
                    events = json.loads(self.rfile.read(length))["events"]
                    log = AuditLog.from_events(events)
                    with outer._lock:
                        outer._anchor.advance(log)
                        env = outer._anchor.envelope()
                    self._send(200, {"envelope": env})
                except AnchorError as exc:
                    self._send(409, {"error": str(exc)})
                except (KeyError, TypeError, ValueError):
                    self._send(400, {"error": "malformed request"})

        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> "AnchorServer":
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


class RemoteHeadAnchor:
    """Client with the same ``load()`` / ``advance(log)`` contract; verifies every reply's signature."""

    def __init__(self, url: str, token: str, authority_public_key: Ed25519PublicKey, timeout: float = 5.0) -> None:
        self.url, self._token, self._pub, self._timeout = url.rstrip("/"), token, authority_public_key, timeout

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.url + path, data=data, method=method,
                                     headers={"Authorization": f"Bearer {self._token}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read()).get("error", "")
            except ValueError:
                detail = ""
            raise AnchorError(f"anchor service refused ({exc.code}): {detail}") from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise AnchorError(f"anchor service unreachable or invalid reply: {exc}") from exc  # fail closed

    def load_record(self) -> dict | None:
        env = self._call("GET", "/head").get("envelope")
        return None if env is None else verify_envelope(env, self._pub)

    def load(self, min_sequence: int | None = None) -> str | None:
        record = self.load_record()
        if record is None:
            if min_sequence:
                raise AnchorError("anchor empty but a previous sequence was expected")
            return None
        if min_sequence is not None and record["sequence"] < min_sequence:
            raise AnchorError(f"anchor sequence {record['sequence']} is older than expected {min_sequence}")
        return record["head"]

    def advance(self, log: AuditLog) -> str:
        events = [{"sequence": e.sequence, "event_type": e.event_type, "details": e.details,
                   "previous_hash": e.previous_hash, "event_hash": e.event_hash} for e in log.events]
        record = verify_envelope(self._call("POST", "/advance", {"events": events}).get("envelope"), self._pub)
        if record["head"] != log.head:
            raise AnchorError("anchor service returned a head that is not this log's head")
        return record["head"]
