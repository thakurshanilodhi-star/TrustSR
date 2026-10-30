# TrustSR Adversarial Validation v1

## Purpose

This validation layer probes fail-closed behavior when recovery evidence is missing, mismatched,
malformed, or presented under an incorrect trust assumption. It supplements the existing synthetic
five-scenario comparison; it does not replace it.

## Included probes

1. Required external audit anchor is absent.
2. Supplied trusted audit head does not match the log.
3. Caller requests a recovery-attempt ID that is not in the matching completion record.
4. Observed scope identifiers contain duplicates.
5. Recovered state contains a non-canonical JSON value (`NaN`) and cannot be digest-bound.
6. Checkpoint is checked against an unrelated public key.
7. Empty audit log is presented with a purported external head.
8. Verification report internals are modified through Python introspection; the in-process seal must detect the modification.

## Run on Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_adversarial_validation.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

## Interpretation

A passing test means the implementation behaved as expected for that constructed input. It is not
proof that the control is unbypassable, that the test cases represent a realistic attacker, or that the
system is production-secure. In particular, Python introspection is available to code in the same
process; the report seal is an integrity check, not an isolation boundary. The audit head must be
stored and retrieved through an independently trusted mechanism in a real deployment.

## Not yet covered

- Property-based fuzzing across arbitrary checkpoint, manifest, and event encodings.
- Multi-process races and crash consistency under a real persistent store.
- A separately hosted anchor service with authenticated transport and access-control review.
- Real agent workflows, irreversible side effects, or attacker-informed evaluation distributions.
- Independent security review and formal verification.

Record the exact command, Python version, platform, exit code, and full test output when executing
this suite. Do not copy Linux results into a Windows run record or vice versa.
