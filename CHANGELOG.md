# Changelog

## 0.3.0 (promotion binding, signed/remote anchor, persistent-state store, Windows/Linux tooling)
**Breaking API change.** `TrustTracker.promote_after_verification` now requires three keyword-only bindings and refuses an unanchored report by default.

**Security / correctness**
- **Mandatory bindings (P1).** `expected_checkpoint_sha256`, `expected_recovery_id` and `committed_state_sha256` are required; `None`/empty/non-string values are refused and recorded (`binding_required:<name>`). New refusal reasons: `report_for_different_recovery_attempt`, `committed_state_mismatch`, `audit_head_not_anchored` (`require_anchored_head=True` by default).
- **Report bound to the recovery attempt and the state (P1).** `verify_recovery` reports `recovery_id` (read from the audit log; optional `recovery_id=` pins one attempt) and `verified_state_sha256` (digest of the exact state verified; non-canonical/NaN state fails closed).
- **Persistent-state commit (P1).** New `recover_state_attempt` -> `RecoveryAttempt`; new `state_store.SqliteStateStore` (atomic commit, fresh re-read, digest recomputed from stored bytes, connections always closed). `recover_state` still works and returns only the state.
- **Anchor (P1).** New `SignedHeadAnchor` (records signed by a separate authority key; `load(min_sequence=)` detects restored/deleted files) and `anchor_service.AnchorServer` / `RemoteHeadAnchor` (stdlib HTTP service; signature verified on every reply; fails closed when unreachable). Deployment checklist: `docs/anchor_deployment.md`. Independence still depends on how it is deployed.
- `AuditLog.from_events`, `checkpoint.state_digest`.

**Windows / Linux**
- `tools/run_notebooks.py`: UTF-8 subprocess I/O, Windows/macOS temp-path and platform-string masking, temp directory cleanup that tolerates files still held open, reports default to `results/notebook_runs/<os>/`.
- `anchor`: `os.replace` retry for transient Windows `PermissionError`.
- New `tools/verify_install.py` (fresh venv, non-editable install, tests against the installed package), `tools/run_notebooks_kernel.py` (real Jupyter kernel via nbclient; `kernel` extra), `tools/check_references.py`.
- CI matrix: ubuntu + windows, Python 3.10/3.12, fresh install, plain notebook harness and Jupyter-kernel notebooks.

**Tests / docs**: 102 -> 120 package tests (promotion bindings, state store, signed and remote anchor, evaluation reproducibility). README example, Lab 00 and its saved outputs updated for the new API. `docs/limitations.md` items 18, 22-25 rewritten/added.

**Not verified in this revision** (see `results/sample_runs/run_v0.3.0_linux.md`): execution on Windows; real `pytest`; online fresh-venv resolution; Jupyter-kernel notebook runs; reference metadata.

## 0.2.0 (review-hardened revision)
Same version number as the first 0.2.0 archive, by request; this revision supersedes it.

**Security / correctness fixes**
- **Trust promotion can no longer be forged (P1).** `verify_recovery` now returns an immutable, HMAC-sealed `VerificationReport` (still readable like a dict). `TrustTracker.promote_after_verification` accepts only an authentic, unused, passing report, re-derives the decision from the five gates instead of trusting the `decision`/`trust_state` strings or a lone `checkpoint_valid` flag, and optionally binds to `expected_checkpoint_sha256` / `max_age_seconds`. Plain dicts, edited reports, copies/pickles and re-used reports are refused.
- **Two further bypasses closed in the same class:** `TrustTracker.apply(TrustLabel.TRUSTED, verified=True, ...)` previously promoted without any report, and `tracker.label = TrustLabel.TRUSTED` was a plain attribute write. `apply()` now refuses `Trusted`; `label` is read-only; `history` returns copies. (Confirmed against the previous archive: all three bypasses succeeded there.)
- **Independent audit head (P1).** New `anchor.HeadAnchor` (atomic, fsynced file store; `advance()` refuses logs that do not extend the stored head) and `AuditLog.extends()`. README example and Lab 00 now load the head from the anchor instead of `trusted_audit_head=log.head`, and demonstrate that a rewritten log is caught only with the anchored head. `verify_recovery(..., require_anchored_head=True)` fails closed without a head; the report always carries `audit_head_anchored` and `warnings`.
- Bare strings are rejected instead of being split into characters (`keys="mode"` in recovery/verification, `poison_sources="AB"` and string edge collections in `graph`).
- `verify_recovery` no longer raises on a malformed manifest or non-list observed IDs; it fails closed.
- Thread safety: `HighWaterMark`, `SqliteHighWaterMark` (lock + `check_same_thread=False`, rollback on any exception) and `IdempotentReceiver` (atomic check-then-insert).
- `recover_state` works on a private copy of the verified payload; the audit log is read once per verification.

**Tests / tooling**
- 72 -> 100 package tests (new: fabricated-report promotion, report immutability/copy/pickle/tamper, single use, checkpoint/age binding, `apply()` and `label` bypasses, anchor, bare-string misuse, malformed inputs, thread races, README example executes), plus 1 package-vs-Lab-01.4 equivalence test and 38 notebook tests.
- Notebook smoke tests now run **each notebook in its own subprocess with a hard timeout** (`TRUSTSR_NB_TIMEOUT`, default 300 s), so one slow notebook fails one test instead of stalling the suite.
- New `tools/run_notebooks.py`: individual runs, per-notebook status/duration, comparison with saved output, reports in `results/notebook_runs/`.
- Notebook count check is exact (38).
- Lab 00 updated for the new API (anchored head, forged-report refusal, rewritten-log detection) and its saved outputs regenerated.

**Verification status** (see `results/sample_runs/run_v0.2.0_revised.md` for the raw record)
- The 140-test result was produced by a **stand-in runner, not real pytest** (pytest could not be installed offline). Run `pytest` locally before calling this release-verified.
- 38/38 notebooks executed individually with the plain-`exec()` harness (sequential total 70 s); not executed under Jupyter/Colab.

## 0.2.0 (original archive)
**Package**
- `checkpoint`: optional signed `version`; unversioned checkpoints sign exactly as in 0.1.x.
- New `replay`: `HighWaterMark` / `SqliteHighWaterMark`; `recover_state(..., replay_guard=, allow_rollback=)` and `verify_recovery(..., replay_guard=, allow_rollback=)` refuse stale/replayed checkpoints. Recovery events record `version` and `rollback`; the verifier requires the logged version to match.
- New `graph`, `trust_machine`, `idempotent`.
- Packaging: `labs` extra and `requirements-labs.txt`; caches removed from the archive.

**Notebooks** (details in `labs/CHANGES.md`)
- Fixed 4 notebooks whose own assertions failed (Labs 01.4, 02 FINAL, 03.02, 03.07).
- All notebooks have saved outputs; added `00_package` quickstart; per-folder READMEs.

**Tests**: 41 -> 112 *as reported by a stand-in runner* (that figure was not independently confirmed by real pytest; the review run timed out on the notebook suite).

## 0.1.1
- verifier compares against the signed checkpoint payload (removed caller-supplied `expected_state`); full recovery drops injected keys; empty audit log invalid, optional `trusted_audit_head`, scope manifest bound in the log; `recovery_complete` derived from the log; NaN rejected; non-bool gates never trusted; `pythonpath = ["src"]`.
