> Historical record from the supplied archive. The `stand-in runner` results below are not real pytest results and are superseded for package tests by `review_run_2026-10-11.md`. The notebook harness report remains an earlier run, not a current Jupyter/Colab validation.

# Test run record — v0.2.0 (review-hardened revision)

This is a software test run, not a benchmark or real-agent experiment.

- Date: 2026-10-11
- Python 3.12.3, cryptography 46.0.6, numpy 2.4.4, scipy 1.17.1; pandas/networkx/matplotlib as recorded in each notebook's `metadata.trustsr_execution`
- Network: none. **pytest is not installed in this environment and could not be installed.**

## What was actually run

The suite was executed with a small stand-in runner (supports `pytest.raises`, `parametrize`, `importorskip`, `skipif`, `tmp_path` only; it is *not* pytest and was not shipped). Test files are written against the real pytest API but have **not** been executed by real pytest.

```text
python run.py "tests/test_*.py"
{'passed': 140}
wall: 74 s
```

Breakdown: 100 package/regression tests (72 from the earlier archive + 28 new, incl. the README-example test), 1 package-vs-Lab-01.4 equivalence, 38 notebook subprocess tests, 1 notebook-count check = 140.

## Not verified

- Real `pytest` run. Command to run locally: `python -m pip install -e ".[test,labs]" && pytest`. Replace this file with its raw output before citing a pytest result.
- Execution in Jupyter/Colab kernels, or in a clean virtualenv with freshly resolved dependencies.

## Before/after evidence for the trust-promotion fix

Previous archive, same Python:

```text
OLD code: (True, 'accepted_by_policy') TrustLabel.TRUSTED      # fabricated dict promoted
OLD direct label assignment: TrustLabel.TRUSTED                 # tracker.label = TRUSTED
OLD apply bypass: (True, 'accepted_by_policy') TrustLabel.TRUSTED
```

This revision:

```text
NEW code: (False, 'report_not_issued_by_verify_recovery') TrustLabel.RECOVERED
```

Notebook runs: see `results/notebook_runs/notebook_runs.md` (38/38 passed, sequential total 70 s, slowest Lab 08 at 21 s).
