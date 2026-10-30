# TrustSR 0.3.0 — actual pytest run (Linux review environment)

This is a new run record for the current review. It supersedes earlier statements that pytest was unavailable for this run, but does not overwrite historical run records.

- OS: `Linux-6.18.44-x86_64-with-glibc2.41` (container used for this review; not Windows).
- Python: `3.13.5`; `cryptography`: `46.0.4`.
- Repository: extracted from the user-supplied `TrustSR_Final(2).zip`.
- Command: `python -m pytest -q`
- Result: **120 passed**, process exit code 0.
- Notebook tests: excluded by the repository's default pytest configuration (`addopts = "-q -m 'not notebook'`).
- Archive: ZIP integrity was checked before extraction.

## Not verified by this record

- Windows execution: pending; this report is not Windows evidence.
- Full notebook suite: a subsequent attempt to run all notebooks in one command exceeded the review tool's overall execution time limit. This is incomplete, not a pass.
- Real Jupyter-kernel execution of all notebooks: not established by this record.
- Networked fresh-environment dependency installation and Crossref reference checks: not established by this record.
- Two-host remote anchor deployment: not established by this record.
- Real-agent effectiveness, production readiness, and formal proof of all book claims: not established by unit tests.
- Byte compilation: `python -m compileall -q src experiments tools` — pass.
- Synthetic evaluation: `python experiments/run_synthetic_evaluation.py` — completed; 5 deterministic synthetic scenarios; output remains a toy evaluation, not production evidence.
- Reference URL check: `python tools/check_references.py` — unable to complete because DNS/network access was unavailable (`Temporary failure in name resolution`); reference verification remains pending.
- Notebook batch attempt: `python tools/run_notebooks.py --timeout 300 --jobs 1` exceeded the overall review execution limit before a complete report was written. This is a timeout/incomplete run, not a pass.
