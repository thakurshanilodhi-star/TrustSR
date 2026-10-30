from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint
from trustsr.recovery import recover_state, recover_state_attempt

CLEAN = {"counter": 3, "mode": "safe"}
MANIFEST = {"expected_record_ids": ["e1", "e2"], "expected_count": 2}


def make_case(current=None, keys=None, manifest=MANIFEST, anchored=False, attempt_out=None):
    private, public = generate_keypair()
    checkpoint = sign_checkpoint(dict(CLEAN), private)
    audit = AuditLog()
    audit.append("checkpoint_created", {"id": "cp-1"})
    audit.declare_scope(manifest)
    current = {"counter": 999, "mode": "unsafe"} if current is None else current
    attempt = recover_state_attempt(checkpoint, public, current, keys=keys, audit_log=audit)
    recovered = attempt.state
    if attempt_out is not None:
        attempt_out.append(attempt)
    extra = {}
    if anchored:  # test shortcut: head captured right after recovery; real code loads it from an anchor
        extra = dict(trusted_audit_head=audit.head, require_anchored_head=True)
    return dict(**extra, checkpoint=checkpoint, public_key=public, audit_log=audit, recovered_state=recovered,
                scope_manifest=manifest, observed_record_ids=["e1", "e2"], keys=keys)


def bindings(report):
    """Correct promotion bindings for a report (placeholders where a failing report has none)."""
    return dict(expected_checkpoint_sha256=report["checkpoint_sha256"],
                expected_recovery_id=report["recovery_id"] or "no-recovery",
                committed_state_sha256=report["verified_state_sha256"] or "no-state")
