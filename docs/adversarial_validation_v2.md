# TrustSR Adversarial Validation v2

**Project version:** 0.3.0  
**Validation layer:** deterministic mutation, persistence/restart, and concurrency checks

## Scope added in v2

- Invalid and mutated Ed25519 signature encodings are rejected.
- Payload mutation after signing is detected.
- A deterministic shuffled sequence of versions checks the in-memory high-water mark's monotonicity.
- Multiple SQLite high-water-mark instances concurrently register versions against one database; errors, hangs, duplicate accepted versions, or a wrong final maximum fail the test.
- Recovery state digest is checked against mutations to the mutable attempt state, making the mutation visible rather than silently treating the original digest as current.
- SQLite state commit is re-read after opening a fresh store instance.
- Tampering with the stored digest is detected on a fresh read.
- Ordinary writes clear recovery provenance.
- A simulated crash window (state committed, final `recovery_completed` event absent) must fail the recovery-complete verification gate.
- NaN and infinities in recovered state fail closed.

## Run on Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_adversarial_validation_v2.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src experiments tools tests
```

## Interpretation and limits

These are deterministic adversarial tests, not coverage-complete fuzzing. The shuffled version test uses a fixed seed. The SQLite concurrency test checks a bounded local workload and does not prove correctness under all OS/filesystem/database failure modes. The crash-window test models missing completion evidence in the log; it does not kill a real process at every possible instruction boundary. The SQLite file remains mutable by a sufficiently privileged attacker, and the in-process verification-report seal is not a security boundary against hostile code in the same process. Passing these tests does not establish production security, formal correctness, or real-agent effectiveness.
