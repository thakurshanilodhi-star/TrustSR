# Architecture

```text
Signed (versioned) checkpoint + trusted key ──> checkpoint.py ──┐
Replay high-water mark ─────────────────────> replay.py ───────┤
Recovery operation (full / selective) ──────> recovery.py ─────┤
Hash-chained audit log + scope digest ──────> audit.py ────────┤──> verification.py ──> trust_state.py
Stored-earlier audit head (out-of-band) ────> anchor.py ───────┤      (sealed VerificationReport)
Recovered state vs signed payload ──────────> contamination.py ┤                     └─> trust_machine.py
Scope manifest + observed IDs ──────────────────────────────────┘

Dependency edges + poison source + declared missing edges ──> graph.py   (which nodes to quarantine)
Event stream with retries ──────────────────────────────────> idempotent.py
```

- `checkpoint.py`: canonical JSON (NaN rejected), SHA-256 payload digest, Ed25519 signature; optional `version` covered by the signature.
- `replay.py`: monotonic high-water mark, in memory or SQLite; recovery refuses older versions unless rollback is explicit and logged.
- `recovery.py`: full recovery replaces state with the verified payload; selective recovery restores listed keys only; both log `recovery_started`/`recovery_completed`/`recovery_refused`.
- `audit.py`: in-memory hash chain; empty log invalid; optional trusted head; `declare_scope` binds the manifest digest; `extends()` checks that a head grows from an earlier one.
- `anchor.py`: `HeadAnchor` stores/loads the audit head outside the log (atomic file write); `advance()` refuses logs that do not extend the stored head.
- `contamination.py`: exact key/value comparison; the verifier uses the signed payload as the reference.
- `graph.py`: reachability from the poison source plus an unknown boundary around declared missing edges.
- `verification.py`: five gates and a PASS/FAIL decision with diagnostics, returned as an immutable, HMAC-sealed `VerificationReport` (also carries `checkpoint_sha256`, `audit_head_anchored`, `warnings`).
- `trust_state.py` / `trust_machine.py`: the decision state, and the five-label policy machine. `transition()` is a pure predicate; `TrustTracker` is the enforcement point: private label, `apply()` cannot enter `Trusted`, and `promote_after_verification()` accepts only an authentic, unused, passing report whose gates are re-derived.
- `idempotent.py`: one record per `event_id`; conflicting payloads rejected.

The audit log is in-memory and generated keys are ephemeral in tests. This is a research scaffold, not a production security boundary.

## Recovery commit boundary

`recover_state()` returns a reconstructed mapping; it is not a transaction manager for a real agent's persistent store. The current verifier checks the mapping supplied by the caller. Before production use, an adapter must atomically commit the candidate state (or use a documented write-ahead protocol), reread the committed state from the authoritative store, compute its canonical digest, and bind that digest plus the checkpoint digest and recovery-attempt identifier to the verification evidence. Crash-before-commit, crash-after-commit, and retries must be tested against that store. This requirement is intentionally listed as not implemented rather than represented as a completed feature.

## Modules added in 0.3.0
- `state_store.py`: `SqliteStateStore` commits a `RecoveryAttempt` atomically, re-reads it and recomputes the digest used for promotion.
- `anchor.py` (`SignedHeadAnchor`) and `anchor_service.py` (`AnchorServer`, `RemoteHeadAnchor`): audit head signed by a separate authority key, optionally served from another process/host.
- `recovery.recover_state_attempt` returns `RecoveryAttempt` (recovery id, state, digests); `recover_state` is a wrapper that returns only the state.

Promotion data flow: `recover_state_attempt` -> `store.commit_recovery` -> `verify_recovery(recovered_state=<re-read>, recovery_id=..., trusted_audit_head=<anchor.load()>)` -> `store.read_committed()` again -> `TrustTracker.promote_after_verification(report, expected_checkpoint_sha256=..., expected_recovery_id=..., committed_state_sha256=...)`.
