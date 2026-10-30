import json
import pytest
from helpers import bindings, make_case
from trustsr.anchor import AnchorError, HeadAnchor
from trustsr.audit import AuditLog, GENESIS
from trustsr.trust_machine import TrustLabel as L, TrustTracker
from trustsr.verification import verify_recovery


def test_load_returns_none_when_nothing_anchored(tmp_path):
    assert HeadAnchor(tmp_path / "h.json").load() is None


def test_advance_then_load_roundtrip_and_growth(tmp_path):
    a = HeadAnchor(tmp_path / "sub" / "h.json"); log = AuditLog()
    log.append("a", {})
    h1 = a.advance(log); assert a.load() == h1 == log.head
    log.append("b", {})
    h2 = a.advance(log); assert h2 != h1 and a.load() == h2


def test_advance_refuses_empty_replaced_or_truncated_log(tmp_path):
    a = HeadAnchor(tmp_path / "h.json"); log = AuditLog(); log.append("a", {}); log.append("b", {})
    a.advance(log)
    with pytest.raises(AnchorError):
        a.advance(AuditLog())                       # empty
    other = AuditLog(); other.append("x", {}); other.append("y", {}); other.append("z", {})
    with pytest.raises(AnchorError):
        a.advance(other)                            # wholesale replacement
    shorter = AuditLog(); shorter.append("a", {})
    with pytest.raises(AnchorError):
        a.advance(shorter)                          # truncation
    assert a.load() == log.head                     # untouched


def test_malformed_anchor_file_fails_closed(tmp_path):
    p = tmp_path / "h.json"
    for content in ("not json", json.dumps({"head": ""}), json.dumps([1]), json.dumps({"x": 1})):
        p.write_text(content)
        with pytest.raises(AnchorError):
            HeadAnchor(p).load()


def test_extends():
    log = AuditLog(); assert log.extends(GENESIS)
    e = log.append("a", {}); log.append("b", {})
    assert log.extends(e.event_hash) and not log.extends("deadbeef")


def test_anchored_head_detects_wholesale_log_rewrite(tmp_path):
    case = make_case()
    anchor = HeadAnchor(tmp_path / "h.json"); anchor.advance(case["audit_log"])
    ok = verify_recovery(**case, trusted_audit_head=anchor.load(), require_anchored_head=True)
    assert ok["decision"] == "PASS" and ok["audit_head_anchored"] is True and ok["warnings"] == []
    # attacker rebuilds a self-consistent log with a doctored first event
    forged = AuditLog(); forged.append("checkpoint_created", {"id": "attacker"})
    for e in case["audit_log"].events[1:]:
        forged.append(e.event_type, e.details)
    case["audit_log"] = forged
    assert forged.verify() is True                                           # internally consistent...
    bad = verify_recovery(**case, trusted_audit_head=anchor.load())          # ...but not the anchored head
    assert bad["gates"]["audit_valid"] is False and bad["decision"] == "FAIL"
    # circular use (head read from the same log) is blind to the rewrite -- and is flagged as unanchored
    circular = verify_recovery(**case, trusted_audit_head=forged.head)
    assert circular["gates"]["audit_valid"] is True
    # but the unanchored default is visible in the report
    plain = verify_recovery(**case)
    assert plain["audit_head_anchored"] is False and plain["warnings"] == ["audit_head_not_anchored"]


def test_require_anchored_head_fails_closed_without_head():
    report = verify_recovery(**make_case(), require_anchored_head=True)
    assert report["gates"]["audit_valid"] is False and report["decision"] == "FAIL"
    assert not TrustTracker(L.RECOVERED).promote_after_verification(report, **bindings(report))[0]


# ---- signed + remote anchors ------------------------------------------------------------------------
from trustsr.anchor import SignedHeadAnchor
from trustsr.anchor_service import AnchorServer, RemoteHeadAnchor
from trustsr.checkpoint import generate_keypair

TOKEN = "t" * 24


def test_signed_anchor_roundtrip_and_read_only_handle(tmp_path):
    priv, pub = generate_keypair(); log = AuditLog(); log.append("a", {})
    writer = SignedHeadAnchor(tmp_path / "s.json", pub, signer=priv)
    assert writer.load() is None and writer.advance(log) == log.head
    reader = SignedHeadAnchor(tmp_path / "s.json", pub)               # verifier: public key only
    assert reader.load() == log.head and reader.load_record()["sequence"] == 1
    with pytest.raises(AnchorError):
        reader.advance(log)
    with pytest.raises(AnchorError):
        SignedHeadAnchor(tmp_path / "x.json", generate_keypair()[1], signer=priv)   # mismatched key


def test_signed_anchor_rejects_forged_edited_and_rolled_back_files(tmp_path):
    priv, pub = generate_keypair(); log = AuditLog(); log.append("a", {})
    a = SignedHeadAnchor(tmp_path / "s.json", pub, signer=priv); a.advance(log)
    old = (tmp_path / "s.json").read_text()
    log.append("b", {}); a.advance(log)
    # attacker without the authority key writes a different head -> signature fails
    env = json.loads((tmp_path / "s.json").read_text()); env["record"]["head"] = "0" * 64
    (tmp_path / "s.json").write_text(json.dumps(env))
    with pytest.raises(AnchorError):
        a.load()
    other_priv, _ = generate_keypair()                                # self-signed by the attacker's own key
    forged = SignedHeadAnchor(tmp_path / "f.json", other_priv.public_key(), signer=other_priv); forged.advance(log)
    with pytest.raises(AnchorError):
        SignedHeadAnchor(tmp_path / "f.json", pub).load()
    # restoring an older, validly signed file is caught by min_sequence
    (tmp_path / "s.json").write_text(old)
    assert a.load() is not None
    with pytest.raises(AnchorError):
        a.load(min_sequence=2)


def test_signed_anchor_deleted_file_is_detected_with_min_sequence(tmp_path):
    priv, pub = generate_keypair(); log = AuditLog(); log.append("a", {})
    a = SignedHeadAnchor(tmp_path / "s.json", pub, signer=priv); a.advance(log)
    (tmp_path / "s.json").unlink()
    with pytest.raises(AnchorError):
        a.load(min_sequence=1)


def test_remote_anchor_service_end_to_end(tmp_path):
    priv, pub = generate_keypair()
    with AnchorServer(str(tmp_path / "svc" / "a.json"), TOKEN, priv) as srv:
        client = RemoteHeadAnchor(srv.url, TOKEN, pub)
        assert client.load() is None
        case = make_case(); log = case["audit_log"]
        assert client.advance(log) == log.head == client.load()
        ok = verify_recovery(**case, trusted_audit_head=client.load(), require_anchored_head=True)
        assert ok["decision"] == "PASS" and ok["audit_head_anchored"] is True
        # a rewritten log is refused by the service and caught by the verifier
        forged = AuditLog(); forged.append("checkpoint_created", {"id": "attacker"})
        for e in log.events[1:]:
            forged.append(e.event_type, e.details)
        with pytest.raises(AnchorError):
            client.advance(forged)
        case["audit_log"] = forged
        assert verify_recovery(**case, trusted_audit_head=client.load())["gates"]["audit_valid"] is False


def test_remote_anchor_rejects_bad_token_wrong_authority_and_dead_server(tmp_path):
    priv, pub = generate_keypair()
    with AnchorServer(str(tmp_path / "a.json"), TOKEN, priv) as srv:
        log = AuditLog(); log.append("a", {})
        RemoteHeadAnchor(srv.url, TOKEN, pub).advance(log)
        with pytest.raises(AnchorError):
            RemoteHeadAnchor(srv.url, "x" * 24, pub).load()                     # wrong token
        with pytest.raises(AnchorError):
            RemoteHeadAnchor(srv.url, TOKEN, generate_keypair()[1]).load()       # reply not signed by expected key
        url = srv.url
    with pytest.raises(AnchorError):
        RemoteHeadAnchor(url, TOKEN, pub, timeout=1).load()                      # server down -> fail closed
    with pytest.raises(ValueError):
        AnchorServer(str(tmp_path / "b.json"), "short", priv)
