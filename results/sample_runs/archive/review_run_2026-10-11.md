# TrustSR review run — 2026-10-11

This file records the available-container validation performed while preparing the package. It is not a Windows laptop or Google Colab run.

- Python: 3.13.5
- Platform: Linux x86_64 (container)
- Command: `python -m pytest -q -m 'not notebook' -o addopts=''`
- Result: **102 passed, 39 deselected in 0.49 s**
- `python -m compileall -q src experiments tools`: passed
- Notebook JSON parsing: 38 files found, 0 JSON errors
- `python experiments/run_synthetic_evaluation.py`: completed; wrote CSV + metadata JSON
- Full suite without excluding notebook-marked tests: timed out in this environment. Notebook tests therefore remain unverified in this run.
- Jupyter/Colab kernel execution: not performed in this run.

Synthetic evaluation results are in `results/evaluations/`. Five hand-built cases are descriptive software checks only, not evidence of real-world effectiveness or statistically meaningful superiority.
- Fresh virtual-environment editable installation: **not verified**. `pip install -e '.[test]'` failed because this review environment could not resolve the package index while trying to obtain the isolated build dependency `setuptools>=68`. This is an environment/network limitation; it is not evidence that installation works or fails on the user's laptop.
