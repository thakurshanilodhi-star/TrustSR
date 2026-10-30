# Adversarial Validation v1 — Review Environment Run

- Scope: new deterministic adversarial validation tests in `tests/test_adversarial_validation.py`.
- Command: `python -m pytest tests/test_adversarial_validation.py -q`
- Result: **8 passed**.
- Full suite command: `python -m pytest -q`
- Full suite result: **128 passed**.
- Compilation command: `python -m compileall -q src experiments tools tests`
- Compilation result: passed with no reported errors.

This run was performed in the current review environment, not on the user's Windows machine. Re-run the commands on Windows and retain its own output as a separate platform record.

These tests cover constructed negative cases only. They do not establish production security, exhaustive attack resistance, real-agent effectiveness, or formal verification. See `docs/adversarial_validation_v1.md` for scope and limitations.
