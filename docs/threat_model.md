# Threat Model

## Objective
Explore whether a recovery controller can refuse to reinstate trust unless independent verification gates pass.

## In scope
- Modified checkpoint payloads and invalid signatures.
- Wrong verification key.
- Tampered or internally inconsistent local hash-chain audit records.
- State keys changed, missing, or added relative to an explicit clean reference.
- Missing, duplicate, or unexpected record IDs relative to a declared synthetic scope manifest.
- Replay of an old but validly signed checkpoint (rollback), and stripping/altering the signed version.
- Incomplete or unlogged recovery (completion is derived from the audit log).
- Injected extra keys surviving recovery; recovered state that differs from the signed checkpoint.
- Empty, truncated (given a trusted head) or unrelated audit logs; manifest not bound to the log.
- A caller (or buggy integration) that hands the trust machine a **fabricated or edited verification report**, reuses a report, bypasses verification through `TrustTracker.apply()`, assigns `tracker.label` directly, or attempts to initialize `TrustTracker` in `Trusted`. Constructor-level `Trusted` initialization is rejected; promotion accepts only an authentic, unused, passing `VerificationReport`.
- A verifier that passes the audit head from the log under test (circular). `HeadAnchor` + `require_anchored_head` make the independent-head requirement explicit.
- A **passing report that is not about the persistent state**: promotion must be bound (mandatory) to the checkpoint digest, the recovery-attempt id found in the audit log, and the digest of the state freshly re-read from the committed store; a report for another checkpoint/attempt, or for state that changed afterwards, is refused. Unanchored reports are refused by default.
- An attacker who can rewrite the log and a local anchor file but does **not** hold the anchor authority key (`SignedHeadAnchor`, `AnchorServer`).
- Bare-string misuse (`keys="mode"`, `poison_sources="AB"`) that would silently split into characters; these now raise.

## Out of scope
- Compromised trusted signing key or malicious authorized signer.
- A malicious or compromised **in-process** caller: the report seal is a per-process HMAC with an in-memory key. Code that can introspect the interpreter (or run in the same process as the verifier) can mint a seal. It is protection against forgery by data, not against hostile code. Cross-process or cross-host use would need a signed report under a key the verifier alone holds.
- Proof that a checkpoint was clean when signed.
- Complete capture of all real-world events or sensor telemetry.
- Compromise of the anchor authority key or host; availability of the anchor service; distributed consensus, general remote append-only audit storage, trusted timestamps, or Byzantine fault tolerance.
- Reconciliation of irreversible actions in external systems.
- Production agent deployment or adversarial red-team validation.

## Security assumptions
The verifier receives the intended public key through an independently trusted channel. The signed checkpoint is clean and the scope manifest is accurate for the experiment, the party that writes the audit log is not compromised, and the replay high-water mark is stored where the attacker cannot lower it. These assumptions are not established by this scaffold.

## Fail-closed policy
Missing required verification inputs or failed gates must not result in `TRUSTED`. `UNKNOWN` is distinct from `TRUSTED`.
