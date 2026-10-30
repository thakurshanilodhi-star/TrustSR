# Adversarial Validation v2 — Run Record

- Project version: `0.3.0` (unchanged)
- Run platform: Linux x86_64, Python 3.13.5
- Test command: `python -m pytest tests/test_adversarial_validation_v2.py -q`
- v2 tests: **17 passed**, exit code 0
- Full suite: **145 passed**, exit code 0
- Compilation: `python -m compileall -q src experiments tools tests` completed with exit code 0
- Synthetic evaluation: completed; 5 deterministic scenarios; baseline accuracy 0.2 and TrustSR gate accuracy 1.0 on this tiny fixture set.

## Limits

This record applies to the Linux review environment only. Windows results must be run and recorded separately by the project owner. The deterministic tests do not constitute exhaustive fuzzing, a formal proof, production security certification, or evidence of effectiveness on real agents. The five-scenario synthetic evaluation is not statistically meaningful.
