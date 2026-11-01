Samajh gaya bro, ab bilkul *same to same* content hai, ek word bhi change nahi kiya. Bas upar-neeche colour ke liye banner, badges aur typing animation add kiya hai. GitHub pe yahi colour dikhega.

Isko copy karke paste kar de:
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:00C9FF,100:92FE9D&height=220&section=header&text=TrustSR&fontSize=75&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Trust-Aware%20State%20Recovery&descAlignY=58" />
</p>

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=22&pause=1000&color=36BCF7&center=true&vCenter=true&width=900&lines=Recovery+is+not+merely+restoring+state...;it+is+verifying+whether+trust+can+be+reinstated.;Trust-Aware+State+Recovery+v0.3.0" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-v0.3.0-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Research-Prototype-orange?style=for-the-badge&logo=flask" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Fail_Closed-Design-red?style=for-the-badge&logo=security" />
</p>

---
# TrustSR

**Trust-Aware State Recovery — research prototype **

TrustSR explores a fail-closed recovery workflow for agent state: restore state only from a cryptographically verified (and non-replayed) checkpoint, audit the recovery, compare the result with the *signed* checkpoint, check a declared scope, and reinstate trust only when every required gate passes.

> Recovery is not merely restoring state; it is verifying whether trust can be reinstated.

## Status

Early research prototype. Tests use synthetic state and ephemeral keys. This repository does not establish production effectiveness, universal correctness, or real-world telemetry completeness. See `CHANGELOG.md` for what changed and `docs/limitations.md` for what is not solved.

## Install and run — Windows first

Your Windows Command Prompt path is shown exactly as requested: `C:\Users\shani>`.
Do not copy this Windows prompt into a Linux run record. Linux instructions and reports must name the actual Linux environment used.

### Windows 10/11 — Command Prompt (`cmd.exe`)

Open Command Prompt and enter the following commands. First `cd` into the folder where you extracted `TrustSR`.

```bat
C:\Users\shani> cd path\to\TrustSR
C:\Users\shani> py -3.12 -m venv .venv
C:\Users\shani> .venv\Scripts\python.exe -m pip install --upgrade pip
C:\Users\shani> .venv\Scripts\python.exe -m pip install -e ".[test,labs,kernel]"
C:\Users\shani> .venv\Scripts\python.exe -m pytest -q
C:\Users\shani> .venv\Scripts\python.exe -m pytest -q -m notebook
C:\Users\shani> .venv\Scripts\python.exe tools\run_notebooks.py --timeout 300 --jobs 1
C:\Users\shani> .venv\Scripts\python.exe tools\run_notebooks_kernel.py --timeout 600
C:\Users\shani> .venv\Scripts\python.exe tools\verify_install.py --extras test,labs
C:\Users\shani> .venv\Scripts\python.exe tools\check_references.py
If you extracted the project directly to `C:\Users\shani\TrustSR`, use this first command instead:
C:\Users\shani> cd /d C:\Users\shani\TrustSR
If `py -3.12` is not installed, check `py --list` or use `python` for the Python version you have installed. Python 3.10+ is required. Reference checking requires internet access. Notebook execution may take several minutes; do not treat a timeout as a pass.

### Linux

Run these commands from the extracted repository directory. They intentionally use the actual Linux shell prompt/environment, not the Windows path above.
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test,labs,kernel]"
python -m pytest -q
python -m pytest -q -m notebook
python tools/run_notebooks.py --timeout 300 --jobs 1
python tools/run_notebooks_kernel.py --timeout 600
python tools/verify_install.py --extras test,labs
python tools/check_references.py
### What each check proves

- `python -m pytest -q`: unit and regression tests; notebook tests are excluded by default.
- `python -m pytest -q -m notebook`: notebook smoke tests through the test harness.
- `tools/run_notebooks.py`: executes code cells in a plain-Python subprocess harness; *not* a Jupyter kernel.
- `tools/run_notebooks_kernel.py`: executes notebooks in a real Jupyter kernel.
- `tools/verify_install.py`: creates a fresh virtual environment and verifies a non-editable package install; online dependency resolution requires network access.
- `tools/check_references.py`: checks reference metadata against Crossref; requires internet access.

Run notebook checks separately if the combined run takes too long. A timeout is an incomplete result, not a pass. Each run record must include OS, Python version, dependency versions, exact command, exit code, and raw output. Never copy a Linux run record into the Windows results folder or vice versa.

## Minimal example
import os, tempfile
from trustsr.anchor import SignedHeadAnchor
from trustsr.audit import AuditLog
from trustsr.checkpoint import generate_keypair, sign_checkpoint
from trustsr.recovery import recover_state_attempt
from trustsr.replay import HighWaterMark
from trustsr.state_store import SqliteStateStore
from trustsr.trust_machine import TrustLabel, TrustTracker
from trustsr.verification import verify_recovery

private_key, public_key = generate_keypair()           # demo only: provision real keys independently
checkpoint = sign_checkpoint({"step": 4, "mode": "safe"}, private_key, version=2)

guard = HighWaterMark(); guard.register(2)             # newest checkpoint version ever issued
manifest = {"expected_record_ids": ["e1", "e2"], "expected_count": 2}
log = AuditLog()
log.append("checkpoint_created", {"id": "cp-2"})
log.declare_scope(manifest)                            # binds the manifest digest into the audit chain

work = tempfile.mkdtemp()
store = SqliteStateStore(os.path.join(work, "agent_state.db"))   # the agent's persistent state
store.write_state({"step": 999, "mode": "unsafe", "x": 1})

# --- recovery controller -------------------------------------------------------------------
attempt = recover_state_attempt(checkpoint, public_key, store.read_committed().state,
                                audit_log=log, replay_guard=guard)
committed = store.commit_recovery(attempt)             # atomic write, then an independent re-read
assert committed.state == {"step": 4, "mode": "safe"}  # full recovery drops injected keys

# The audit head is recorded by an anchor AUTHORITY (own key, ideally own account/host; see
# docs/anchor_deployment.md). Verifiers hold only its public key. Never pass `log.head` from the log under test.
anchor_private, anchor_public = generate_keypair()     # demo only: in real use this key never touches the controller
anchor = SignedHeadAnchor(os.path.join(work, "audit_head.json"), anchor_public, signer=anchor_private)
anchor.advance(log)

# --- verifier (separate component/process): loads the previously stored head ---------------
report = verify_recovery(checkpoint=checkpoint, public_key=public_key, audit_log=log,
                         recovered_state=committed.state, scope_manifest=manifest,
                         observed_record_ids=["e1", "e2"], replay_guard=guard,
                         recovery_id=attempt.recovery_id,
                         trusted_audit_head=anchor.load(), require_anchored_head=True)
assert report["decision"] == "PASS" and report["recovery_id"] == attempt.recovery_id

# --- promotion: bound to checkpoint, recovery attempt AND the state freshly re-read from the store ---
tracker = TrustTracker(TrustLabel.RECOVERED)
fresh = store.read_committed()
binding = dict(expected_checkpoint_sha256=attempt.checkpoint_sha256, expected_recovery_id=fresh.recovery_id,
               committed_state_sha256=fresh.state_sha256)
assert not tracker.promote_after_verification({"decision": "PASS", "trust_state": "trusted",
                                               "gates": {"checkpoint_valid": True}}, **binding)[0]   # forged dict
assert tracker.promote_after_verification(report, **binding)[0] and tracker.label is TrustLabel.TRUSTED
Pass `keys=[...]` to both `recover_state` and `verify_recovery` for selective recovery (only those keys are verified). Use `SqliteHighWaterMark(path)` for a transactional mark that survives restart, and store the replay mark out-of-band too.

*Why the anchor matters.* `trusted_audit_head=log.head` is circular: the head is read from the log being checked, so a wholesale-rewritten log trivially matches itself. Three anchors share one contract (`load()` / `advance(log)`): `HeadAnchor` (plain local file, *not* independent), `SignedHeadAnchor` (records signed by a separate authority key; the verifier holds only the public key), and `anchor_service.AnchorServer` / `RemoteHeadAnchor` (the same signed anchor behind a small HTTP service, so the head lives under another OS account or host). `advance()` refuses a log that does not extend the stored head; `load(min_sequence=...)` detects a restored older file. Independence is a deployment property: see `docs/anchor_deployment.md`. If no head is supplied the report says so (`audit_head_anchored: False`, `warnings`); `require_anchored_head=True` makes that a failure and promotion requires an anchored report by default.

*Why a passing report is not enough.* A passing report says an in-memory dictionary matched the signed checkpoint; it does not say the agent's _persistent_ state is that dictionary. `SqliteStateStore.commit_recovery` writes the recovered state, its `recovery_id` and digest in one transaction, re-reads it and recomputes the digest. `verify_recovery(recovered_state=<state re-read from the store>, recovery_id=...)` records `recovery_id` (taken from the audit log) and `verified_state_sha256` in the report, and `promote_after_verification` now *requires* `expected_checkpoint_sha256`, `expected_recovery_id` and `committed_state_sha256` (a fresh re-read digest). A report for another checkpoint, another recovery attempt, or state that changed afterwards cannot promote.

*Initial state invariant.* `TrustTracker(TrustLabel.TRUSTED)` raises `ValueError`; a tracker cannot begin trusted without passing the promotion flow.

*Why promotion is bound to the report.* `verify_recovery` returns an immutable, sealed `VerificationReport`. `TrustTracker.promote_after_verification` rejects plain dicts, edited or copied reports, reports already used, unanchored reports, and reports not bound to the given checkpoint, recovery attempt and committed state (all three bindings are mandatory); it re-derives the decision from the five gates instead of trusting the `decision` string, and `TrustTracker.apply()` cannot enter `Trusted` at all. This is an in-process integrity seal, not a security boundary.

## Modules (`src/trustsr/`)
Module | Purpose
`checkpoint.py` | Canonical JSON, Ed25519 signing/verification, optional signed `version`
`replay.py` | `HighWaterMark` / `SqliteHighWaterMark`: refuse stale or replayed checkpoints
`recovery.py` | Full (replacing) or selective recovery, optional audit logging and replay guard
`audit.py` | Hash-chained audit log: non-empty, trusted-head check, scope-manifest binding
`anchor.py` | `HeadAnchor`, `SignedHeadAnchor`: store/load the audit head out-of-band; refuse non-extending logs
`anchor_service.py` | `AnchorServer` / `RemoteHeadAnchor`: signed anchor in a separate process/host
`state_store.py` | `SqliteStateStore`: atomic commit of a recovery, fresh re-read, state digest for promotion
`contamination.py` | Exact key/value comparison against a reference
`graph.py` | Dependency-graph contamination with a declared uncertainty boundary (Lab 01.4)
`verification.py` | The five gates and the PASS/FAIL decision, issued as a sealed `VerificationReport`
`trust_state.py` | Three decision states (`UNKNOWN`, `TRUSTED`, `QUARANTINED`)
`trust_machine.py` | Five-label state machine; `TrustTracker` promotes only from an authentic, unused report (Lab 09)
`idempotent.py` | Idempotent event receiver and reconciliation (Labs 03.04-03.07)
## Verification gates

1. *checkpoint_valid* – signature and digest verify under the trusted key; with a `replay_guard`, the signed version is present and not older than the high-water mark (unless `allow_rollback=True`).
2. *audit_valid* – the audit chain is non-empty and consistent (and equals `trusted_audit_head` if supplied).
3. *recovery_complete* – derived from the audit log: a matching started/completed pair for this checkpoint, version and key scope, with no refusal.
4. *contamination_removed* – the recovered state equals the *signed checkpoint payload* (restricted to `keys` for selective recovery).
5. *scope_complete* – observed record IDs match the manifest exactly and the manifest digest was recorded in the audit log.

A missing or failed gate yields `FAIL`; `TRUSTED` requires all five. The scope gate checks consistency with a declared manifest; it does not prove real-world completeness.

## Repository layout

- `src/trustsr/` – package. `tests/` – automated tests. `tools/` – notebook runner. `docs/` – threat model, architecture, limitations.
- `labs/` – 37 research notebooks with saved synthetic outputs, plus `00_package` which uses the package. See `labs/README.md` and `labs/CHANGES.md`.
- `datasets/synthetic/` – declared synthetic scenarios. `results/sample_runs/` – recorded test runs.

## Research integrity

Do not report synthetic fixtures as real-agent experiments. Record Python version, dependency versions, commands, raw output, and deviations for each run. Notebook outputs in this archive were produced by a plain-Python harness, not a Jupyter kernel (see `labs/CHANGES.md`); `tools/run_notebooks.py` re-executes them and compares with the saved text. Re-run in your own environment (ideally with `jupyter nbconvert --execute`) before citing numbers. Run `python experiments/run_synthetic_evaluation.py` to generate a small, explicitly synthetic baseline comparison CSV. It is a test harness, not evidence of real-agent effectiveness. See `docs/evaluation_protocol.md` and `docs/references.md`. Claims about baseline superiority, causal recovery, or production readiness require additional experiments.

## CI and release checklist

`.github/workflows/tests.yml` runs, on `ubuntu-latest` *and* `windows-latest`: the fast suite (Python 3.10 and 3.12), a fresh-venv install check, the notebook suite with the plain harness, and the notebook suite in a real Jupyter kernel.

Verification status is recorded separately per environment in `results/sample_runs/`; the latest actual Linux pytest run is `results/sample_runs/run_v0.3.0_linux_actual_pytest.md`. Windows remains pending until a Windows run or green Windows CI log is recorded. Do not treat CI configuration or valid notebook JSON as a successful execution result: a job counts only when its run record or CI log exists. Windows, a real `pytest` run, a networked fresh-venv install and a Jupyter-kernel run are listed there as pending unless a record says otherwise.

# TrustSR: Why Rollback Is Not Recovery

TrustSR (Trust-Aware State Recovery) is a research-oriented framework that explores trusted recovery for long-horizon AI agent systems.

Traditional recovery mechanisms focus on rollback, assuming that reverting to an earlier checkpoint is sufficient after compromise. TrustSR investigates a different question:

> How can an AI system recover to a state that is demonstrably trustworthy, rather than simply reverting to an earlier state?

The project combines contamination analysis, selective recovery, trust-state modeling, verification pipelines, audit mechanisms, authenticated checkpoints, and reproducible laboratory experiments.

---

## Core Idea

Traditional recovery:
Compromise
↓
Rollback
↓
Resume
TrustSR:
Compromise
↓
Detection
↓
Contamination Analysis
↓
Trust Classification
↓
Selective Recovery
↓
Audit Validation
↓
Recovery Verification
↓
Trusted State
TrustSR treats trust as a recovery objective rather than an assumption.

---

## Problem Statement

Long-horizon AI agents maintain:

- Memory
- Context
- Plans
- Tool usage
- Environment state
- External side effects
- Inter-agent communication

When compromise occurs, rollback may not be sufficient because:

- Contaminated memories may persist
- External effects cannot be undone
- Permissions may remain compromised
- Other agents may already be affected
- Re-execution may reproduce the attack

TrustSR explores mechanisms for recovering to a trusted operational state.

---

## Framework Components

### Contamination Analysis

Models the propagation of compromise through dependency graphs and causal relationships.

Topics:

- Contamination closure
- Dependency analysis
- Missing-edge failures
- Uncertainty-aware recovery
- Adversarial observability gaps

---

### Selective Recovery

Instead of restoring everything:
Rollback:
Restore entire checkpoint
TrustSR attempts:
Restore only affected components
Preserve unaffected work
Goals:

- Reduce recovery cost
- Preserve clean progress
- Maintain trust guarantees

---

### Trust-State Model

TrustSR defines explicit recovery states:
Trusted
Recovered
Unknown
Suspect
Contaminated
Key principles:

- Recovered is not automatically Trusted
- Trusted requires verification
- Unknown is not treated as clean
- Contaminated states cannot directly become Trusted

---

### Verification Engine

Recovery is considered successful only if all verification gates pass:
Checkpoint Validation
+
Audit Validation
+
Recovery Completion
+
Contamination Removal
=
PASS
Otherwise:
FAIL
TrustSR follows a fail-closed design.

---

### Authenticated Recovery

TrustSR explores:

- Authenticated checkpoints
- Manifest validation
- Version control
- Replay protection
- Signature verification
- Recovery provenance

---

### Audit and Evidence

TrustSR includes mechanisms for:

- Tamper-evident audit logs
- Failure recording
- Independent evidence channels
- Reconciliation
- Verification auditing

Recovery actions should be explainable and reviewable.

---

## Laboratory Series

The repository includes a complete set of reproducible experimental notebooks.

### Lab 01 Series

Contamination Analysis

- Memory poisoning
- Dependency propagation
- Missing-edge failures
- Uncertainty handling
- Robustness studies

### Lab 02 Series

Trusted Recovery Foundations

- Selective recovery
- Checkpoint integrity
- Signature validation
- Replay protection
- Transactional persistence

### Lab 03 Series

Reliability and Recovery Infrastructure

- Journaling
- Restart recovery
- Failure recording
- Reconciliation
- Hard crash recovery

### Lab 04 Series

Recovery Evaluation

- Recovery effectiveness
- Uncertainty-aware classification
- Adversarial observability attacks
- Policy benchmarks

### Lab 05 Series

Recovery Execution

- End-to-end recovery execution
- Recovery interruption
- Resume and completion

### Lab 09

Trust-State Model

Formal state definitions and transition rules.

### Lab 10

Trust-State Invariant Validation

Adversarial transition testing and exhaustive policy evaluation.

### Lab 11

Recovery Verification Engine

Verification gates and fail-closed recovery decisions.

### Lab 12

End-to-End TrustSR Capstone

Complete recovery workflow demonstration.

### Lab 13

Authenticated Checkpoints and Inventory Validation

Cryptographic verification and recovery-scope validation.

---

## Repository Structure
TrustSR/
│
├── README.md
├── LICENSE
│
├── book/
│   ├── TrustSR_Why_Rollback_Is_Not_Recovery.pdf
│   ├── manuscript/
│   ├── figures/
│   ├── diagrams/
│   ├── charts/
│   └── qr_codes/
│
├── labs/
│
│   ├── 01_Contamination_Analysis/
│   │
│   ├── TRUSTSR_Lab_01_Memory_Poisoning_and_Contamination_Graph.ipynb
│   ├── TRUSTSR_Lab_01_1_Missing_Edge_Failure_Test.ipynb
│   ├── TRUSTSR_Lab_01_2_Systematic_Missing_Edge_Experiments.ipynb
│   ├── TRUSTSR_Lab_01_3_Conservative_Unknown_Dependency_Handling.ipynb
│   ├── TRUSTSR_Lab_01_4_Observable_Only_Conservative_Policy.ipynb
│   ├── TRUSTSR_Lab_01_5_Recovery_Strategy_Comparison.ipynb
│   ├── TRUSTSR_Lab_01_6_Randomized_Recovery_Benchmark.ipynb
│   ├── TRUSTSR_Lab_01_7_Blind_Missing_Edge_Detection.ipynb
│   └── TRUSTSR_Lab_01_8_Sensitivity_Analysis.ipynb
│
│
│   ├── 02_Trusted_Recovery/
│   │
│   ├── TRUSTSR_Lab_02_01_Selective_Recovery_Prototype.ipynb
│   ├── TRUSTSR_Lab_02_02_Checkpoint_Integrity_and_Provenance.ipynb
│   ├── TRUSTSR_Lab_02_03_Digital_Signature_Verification.ipynb
│   ├── TRUSTSR_Lab_02_04_Replay_Protection.ipynb
│   ├── TRUSTSR_Lab_02_05_Atomic_Version_Advancement.ipynb
│   ├── TRUSTSR_Lab_02_06_SQLite_Transactional_Persistence.ipynb
│   ├── TRUSTSR_Lab_02_07_Tamper_Evident_Audit_Trail.ipynb
│   └── TRUSTSR_Lab_02_FINAL_Integrated_Recovery_and_Audit_Validation.ipynb
│
│
│   ├── 03_Reliability_and_Recovery_Engineering/
│   │
│   ├── TRUSTSR_Lab_03_01_Atomic_Checkpoint_and_Audit_Persistence.ipynb
│   ├── TRUSTSR_Lab_03_02_Failure_Recording_and_Recovery.ipynb
│   ├── TRUSTSR_Lab_03_03_Independent_Failure_Journal.ipynb
│   ├── TRUSTSR_Lab_03_04_Retry_and_Idempotency.ipynb
│   ├── TRUSTSR_Lab_03_05_Retry_Policy_Benchmark.ipynb
│   ├── TRUSTSR_Lab_03_06_Correlated_Outages.ipynb
│   ├── TRUSTSR_Lab_03_07_Reliability_Capstone.ipynb
│   └── TRUSTSR_Lab_03_08_Hard_Crash_Recovery.ipynb
│
│
│   ├── 04_Recovery_Evaluation/
│   │
│   ├── TRUSTSR_Lab_04_01_Selective_Recovery_Effectiveness.ipynb
│   ├── TRUSTSR_Lab_04_02_Uncertainty_Aware_Recovery.ipynb
│   ├── TRUSTSR_Lab_04_03_Coverage_Signal_Robustness.ipynb
│   └── TRUSTSR_Lab_04_04_Adversarial_Observability_Stress_Test.ipynb
│
│
│   ├── 05_Recovery_Execution/
│   │
│   ├── TRUSTSR_Lab_05_01_Recovery_Execution_and_Verification.ipynb
│   ├── TRUSTSR_Lab_05_02_Recovery_Retry_and_Idempotence.ipynb
│   ├── TRUSTSR_Lab_05_03_Persistent_Recovery_Resume.ipynb
│   ├── TRUSTSR_Lab_05_04_Trust_State_Model.ipynb
│   ├── TRUSTSR_Lab_05_05_Trust_State_Invariants.ipynb
│   └── TRUSTSR_Lab_05_06_Recovery_Verification_Engine.ipynb
│
│
│   └── 06_Capstone/
│       │
│       ├── TRUSTSR_Lab_12_End_to_End_TrustSR.ipynb
│       └── TRUSTSR_Lab_13_Authenticated_Checkpoints_and_GroundTruth_Completeness.ipynb
│
│
├── datasets/
│   ├── synthetic_graphs/
│   ├── recovery_benchmarks/
│   └── evaluation_inputs/
│
├── results/
│   ├── contamination_analysis/
│   ├── recovery_evaluation/
│   ├── verification_results/
│   ├── benchmark_exports/
│   └── figures/
│
├── docs/
│   ├── architecture/
│   ├── threat_model/
│   ├── trust_state_model/
│   ├── verification_engine/
│   ├── recovery_pipeline/
│   └── publication_materials/
│
├── diagrams/
│   ├── TrustSR_Architecture.png
│   ├── Trust_State_Model.png
│   ├── Recovery_Pipeline.png
│   ├── Verification_Engine.png
│   └── End_to_End_Workflow.png
│
├── papers/
│   ├── technical_report/
│   ├── whitepaper/
│   └── future_publications/
│
└── examples/
    ├── quick_start/
    ├── tutorial/
    └── sample_runs/
---

## Research Goals

TrustSR investigates the following questions:

1. Why is rollback not equivalent to recovery?
2. How can contamination be identified?
3. How can clean work be preserved?
4. How should trust be represented?
5. How can recovery success be verified?
6. How can recovery evidence be audited?
7. What assumptions are required for trusted recovery?

---

## Limitations

TrustSR is an educational and research-oriented framework.

Current limitations include:

- Synthetic evaluation environment
- Simplified threat models
- No production deployment claims
- No guarantees of real-world effectiveness
- No formal proof of universal correctness
- No distributed consensus implementation
- No complete external trust-anchor system

TrustSR should be viewed as a research framework prototype and learning resource.

---

## Intended Audience

- AI Security Researchers
- AI Agent Developers
- Cybersecurity Students
- Graduate Researchers
- Distributed Systems Engineers
- Trust and Safety Practitioners

---

## Citation

If you use TrustSR in academic, research, or educational work, please cite the framework and repository.
TrustSR: Why Rollback Is Not Recovery
Trust-Aware State Recovery Framework
Author: [Shani]
Year: 2026
---

## License

MIT License

See LICENSE for details.

---

## Author

[Shani]

B.Tech CSE (Artificial Intelligence & Machine Learning)

TrustSR is an independent educational and research project exploring trust-aware recovery for AI agent systems.

---

## Motto

> Recovery is not the restoration of state. 
>
> Recovery is the restoration of trust.

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:00C9FF,100:92FE9D&height=120&section=footer&text=Recovery%20is%20the%20restoration%20of%20trust.&fontSize=20&fontColor=ffffff&animation=fadeIn" />
</p>

