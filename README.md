# TrustSR

**Trust-Aware State Recovery — research prototype (v0.3.0)**

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
```

If you extracted the project directly to `C:\Users\shani\TrustSR`, use this first command instead:

```bat
C:\Users\shani> cd /d C:\Users\shani\TrustSR
```

If `py -3.12` is not installed, check `py --list` or use `python` for the Python version you have installed. Python 3.10+ is required. Reference checking requires internet access. Notebook execution may take several minutes; do not treat a timeout as a pass.

### Linux

Run these commands from the extracted repository directory. They intentionally use the actual Linux shell prompt/environment, not the Windows path above.

```bash
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
```

### What each check proves

- `python -m pytest -q`: unit and regression tests; notebook tests are excluded by default.
- `python -m pytest -q -m notebook`: notebook smoke tests through the test harness.
- `tools/run_notebooks.py`: executes code cells in a plain-Python subprocess harness; **not** a Jupyter kernel.
- `tools/run_notebooks_kernel.py`: executes notebooks in a real Jupyter kernel.
- `tools/verify_install.py`: creates a fresh virtual environment and verifies a non-editable package install; online dependency resolution requires network access.
- `tools/check_references.py`: checks reference metadata against Crossref; requires internet access.

Run notebook checks separately if the combined run takes too long. A timeout is an incomplete result, not a pass. Each run record must include OS, Python version, dependency versions, exact command, exit code, and raw output. Never copy a Linux run record into the Windows results folder or vice versa.

## Minimal example

```python
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
```

Pass `keys=[...]` to both `recover_state` and `verify_recovery` for selective recovery (only those keys are verified). Use `SqliteHighWaterMark(path)` for a transactional mark that survives restart, and store the replay mark out-of-band too.

**Why the anchor matters.** `trusted_audit_head=log.head` is circular: the head is read from the log being checked, so a wholesale-rewritten log trivially matches itself. Three anchors share one contract (`load()` / `advance(log)`): `HeadAnchor` (plain local file, **not** independent), `SignedHeadAnchor` (records signed by a separate authority key; the verifier holds only the public key), and `anchor_service.AnchorServer` / `RemoteHeadAnchor` (the same signed anchor behind a small HTTP service, so the head lives under another OS account or host). `advance()` refuses a log that does not extend the stored head; `load(min_sequence=...)` detects a restored older file. Independence is a deployment property: see `docs/anchor_deployment.md`. If no head is supplied the report says so (`audit_head_anchored: False`, `warnings`); `require_anchored_head=True` makes that a failure and promotion requires an anchored report by default.

**Why a passing report is not enough.** A passing report says an in-memory dictionary matched the signed checkpoint; it does not say the agent's *persistent* state is that dictionary. `SqliteStateStore.commit_recovery` writes the recovered state, its `recovery_id` and digest in one transaction, re-reads it and recomputes the digest. `verify_recovery(recovered_state=<state re-read from the store>, recovery_id=...)` records `recovery_id` (taken from the audit log) and `verified_state_sha256` in the report, and `promote_after_verification` now **requires** `expected_checkpoint_sha256`, `expected_recovery_id` and `committed_state_sha256` (a fresh re-read digest). A report for another checkpoint, another recovery attempt, or state that changed afterwards cannot promote.

**Initial state invariant.** `TrustTracker(TrustLabel.TRUSTED)` raises `ValueError`; a tracker cannot begin trusted without passing the promotion flow.

**Why promotion is bound to the report.** `verify_recovery` returns an immutable, sealed `VerificationReport`. `TrustTracker.promote_after_verification` rejects plain dicts, edited or copied reports, reports already used, unanchored reports, and reports not bound to the given checkpoint, recovery attempt and committed state (all three bindings are mandatory); it re-derives the decision from the five gates instead of trusting the `decision` string, and `TrustTracker.apply()` cannot enter `Trusted` at all. This is an in-process integrity seal, not a security boundary.

## Modules (`src/trustsr/`)

| Module | Purpose |
|---|---|
| `checkpoint.py` | Canonical JSON, Ed25519 signing/verification, optional signed `version` |
| `replay.py` | `HighWaterMark` / `SqliteHighWaterMark`: refuse stale or replayed checkpoints |
| `recovery.py` | Full (replacing) or selective recovery, optional audit logging and replay guard |
| `audit.py` | Hash-chained audit log: non-empty, trusted-head check, scope-manifest binding |
| `anchor.py` | `HeadAnchor`, `SignedHeadAnchor`: store/load the audit head out-of-band; refuse non-extending logs |
| `anchor_service.py` | `AnchorServer` / `RemoteHeadAnchor`: signed anchor in a separate process/host |
| `state_store.py` | `SqliteStateStore`: atomic commit of a recovery, fresh re-read, state digest for promotion |
| `contamination.py` | Exact key/value comparison against a reference |
| `graph.py` | Dependency-graph contamination with a declared uncertainty boundary (Lab 01.4) |
| `verification.py` | The five gates and the PASS/FAIL decision, issued as a sealed `VerificationReport` |
| `trust_state.py` | Three decision states (`UNKNOWN`, `TRUSTED`, `QUARANTINED`) |
| `trust_machine.py` | Five-label state machine; `TrustTracker` promotes only from an authentic, unused report (Lab 09) |
| `idempotent.py` | Idempotent event receiver and reconciliation (Labs 03.04-03.07) |

## Verification gates

1. **checkpoint_valid** – signature and digest verify under the trusted key; with a `replay_guard`, the signed version is present and not older than the high-water mark (unless `allow_rollback=True`).
2. **audit_valid** – the audit chain is non-empty and consistent (and equals `trusted_audit_head` if supplied).
3. **recovery_complete** – derived from the audit log: a matching started/completed pair for this checkpoint, version and key scope, with no refusal.
4. **contamination_removed** – the recovered state equals the **signed checkpoint payload** (restricted to `keys` for selective recovery).
5. **scope_complete** – observed record IDs match the manifest exactly and the manifest digest was recorded in the audit log.

A missing or failed gate yields `FAIL`; `TRUSTED` requires all five. The scope gate checks consistency with a declared manifest; it does not prove real-world completeness.

## Repository layout

- `src/trustsr/` – package. `tests/` – automated tests. `tools/` – notebook runner. `docs/` – threat model, architecture, limitations.
- `labs/` – 37 research notebooks with saved synthetic outputs, plus `00_package` which uses the package. See `labs/README.md` and `labs/CHANGES.md`.
- `datasets/synthetic/` – declared synthetic scenarios. `results/sample_runs/` – recorded test runs.

## Research integrity

Do not report synthetic fixtures as real-agent experiments. Record Python version, dependency versions, commands, raw output, and deviations for each run. Notebook outputs in this archive were produced by a plain-Python harness, not a Jupyter kernel (see `labs/CHANGES.md`); `tools/run_notebooks.py` re-executes them and compares with the saved text. Re-run in your own environment (ideally with `jupyter nbconvert --execute`) before citing numbers. Run `python experiments/run_synthetic_evaluation.py` to generate a small, explicitly synthetic baseline comparison CSV. It is a test harness, not evidence of real-agent effectiveness. See `docs/evaluation_protocol.md` and `docs/references.md`. Claims about baseline superiority, causal recovery, or production readiness require additional experiments.

## CI and release checklist

`.github/workflows/tests.yml` runs, on `ubuntu-latest` **and** `windows-latest`: the fast suite (Python 3.10 and 3.12), a fresh-venv install check, the notebook suite with the plain harness, and the notebook suite in a real Jupyter kernel.

Verification status is recorded separately per environment in `results/sample_runs/`; the latest actual Linux pytest run is `results/sample_runs/run_v0.3.0_linux_actual_pytest.md`. Windows remains pending until a Windows run or green Windows CI log is recorded. Do not treat CI configuration or valid notebook JSON as a successful execution result: a job counts only when its run record or CI log exists. Windows, a real `pytest` run, a networked fresh-venv install and a Jupyter-kernel run are listed there as pending unless a record says otherwise.
