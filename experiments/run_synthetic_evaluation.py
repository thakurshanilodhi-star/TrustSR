#!/usr/bin/env python3
"""Deterministic synthetic comparison: no-verification baseline vs TrustSR gates.

This experiment measures only whether the gate implementation rejects four deliberately
invalid synthetic cases. It does not model a real agent, an attacker distribution, or production
performance. Output is written to results/evaluations/synthetic_gate_comparison.csv.
"""
from __future__ import annotations
import csv, json, os, platform, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint
from trustsr.recovery import recover_state
from trustsr.verification import verify_recovery

MANIFEST = {"expected_record_ids": ["e1", "e2"], "expected_count": 2}
CLEAN = {"step": 4, "mode": "safe"}

def build_case(kind: str):
    private, public = generate_keypair()
    checkpoint = sign_checkpoint(dict(CLEAN), private, version=1)
    log = AuditLog()
    log.append("checkpoint_created", {"id": "synthetic-checkpoint"})
    log.declare_scope(MANIFEST)
    restored = recover_state(checkpoint, public, {"step": 999, "mode": "unsafe", "injected": True}, audit_log=log)
    observed = ["e1", "e2"]
    manifest = dict(MANIFEST)
    if kind == "contaminated_state":
        restored["mode"] = "unsafe"
    elif kind == "incomplete_scope":
        observed = ["e1"]
    elif kind == "audit_tampered":
        # Deliberately corrupt an event in this synthetic fixture; verifier should fail the chain.
        log._events[0].details["id"] = "tampered"
    elif kind == "missing_recovery_events":
        log = AuditLog()
        log.append("checkpoint_created", {"id": "synthetic-checkpoint"})
        log.declare_scope(manifest)
    return dict(checkpoint=checkpoint, public_key=public, audit_log=log, recovered_state=restored,
                scope_manifest=manifest, observed_record_ids=observed)

def main():
    scenarios = ["clean", "contaminated_state", "incomplete_scope", "audit_tampered", "missing_recovery_events"]
    rows = []
    for scenario in scenarios:
        case = build_case(scenario)
        report = verify_recovery(**case)
        # Baseline definition: accepts state if checkpoint signature verifies; it ignores audit,
        # scope and recovered-state consistency. This deliberately weak baseline is explicit.
        baseline_accept = True
        trustsr_accept = report["decision"] == "PASS"
        expected_accept = scenario == "clean"
        rows.append({"scenario": scenario, "expected_accept": expected_accept,
                     "baseline_accept": baseline_accept, "trustsr_accept": trustsr_accept,
                     "baseline_correct": baseline_accept == expected_accept,
                     "trustsr_correct": trustsr_accept == expected_accept,
                     "failed_gates": ";".join(k for k, v in report["gates"].items() if not v),
                     "note": "synthetic fixture; not real-agent evidence"})
    out = ROOT / "results" / "evaluations" / "synthetic_gate_comparison.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    metadata = {"python": platform.python_version(), "platform": platform.platform(),
                "scenarios": len(rows), "baseline_accuracy": sum(r["baseline_correct"] for r in rows) / len(rows),
                "trustsr_accuracy": sum(r["trustsr_correct"] for r in rows) / len(rows),
                "seed": "not applicable: deterministic scenarios; cryptographic keys are ephemeral",
                "limitations": "Tiny synthetic fixture set; no statistical inference or production claim."}
    (out.parent / "synthetic_gate_comparison_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    print(json.dumps(metadata, indent=2))

if __name__ == "__main__":
    main()
