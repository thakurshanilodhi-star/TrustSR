import json, pathlib
from trustsr.verification import verify_recovery
from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint
from trustsr.recovery import recover_state

DATA = pathlib.Path(__file__).resolve().parent.parent / "datasets" / "synthetic"


def run(name):
    sc = json.loads((DATA / name).read_text())
    private, public = generate_keypair()
    cp = sign_checkpoint(sc["clean_state"], private)
    log = AuditLog(); log.declare_scope(sc["scope_manifest"])
    rec = recover_state(cp, public, sc["observed_state"], audit_log=log)
    return verify_recovery(checkpoint=cp, public_key=public, audit_log=log, recovered_state=rec,
                           scope_manifest=sc["scope_manifest"], observed_record_ids=sc["observed_record_ids"])


def test_clean_scenario_passes():
    assert run("scenario_clean.json")["decision"] == "PASS"


def test_incomplete_scope_scenario_fails_only_on_scope():
    r = run("scenario_incomplete_scope.json")
    assert r["decision"] == "FAIL"
    assert [g for g, ok in r["gates"].items() if not ok] == ["scope_complete"]
