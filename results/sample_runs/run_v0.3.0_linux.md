# Run record: TrustSR 0.3.0, Linux

Environment (this record applies to this environment only, not to Windows or Colab):

- OS: Linux x86_64 container (`Linux-6.18.44-fc-v114-x86_64-with-glibc2.39`), no network
- Python 3.12.3; cryptography 46.0.6, numpy 2.4.4, pandas 3.0.2, networkx 3.6.1, matplotlib 3.10.8
- `pytest` was **not installed and could not be installed** (offline). Package tests were run with a small
  stand-in runner (supports `raises`, `parametrize`, `importorskip`, `tmp_path`); it is not pytest.

| What | Command | Result |
|---|---|---|
| Byte-compile | `python -m compileall -q src experiments tools` | pass |
| Package + notebook tests | stand-in runner over `tests/test_*.py` | **159 passed, 0 failed** (120 package tests + 39 notebook tests), ~73 s |
| 38 notebooks, plain `exec()` harness, one subprocess each | `python tools/run_notebooks.py --timeout 300 --jobs 1` | **38/38 PASS**, 72 s wall; slowest Lab 08 (~21 s). Report: `results/notebook_runs/linux/` |
| Fresh venv, non-editable install, **offline** | `python tools/verify_install.py --offline` | PASS (install, import from `site-packages`, README example). Test step skipped: no pytest in venv. Report: `results/install_runs/linux-offline/` |
| Synthetic evaluation | `python experiments/run_synthetic_evaluation.py` | completed; reproducibility test passes |

## Not verified (pending, do not claim)

- **Windows**: nothing executed. Commands and the Windows-sensitive code paths are listed in `results/windows_pending.md`.
- **Real `pytest`** (use `python -m pytest -q`, then replace the stand-in row with its raw output).
- **Online fresh-venv install** with dependency resolution (`python tools/verify_install.py --extras test,labs`).
- **Jupyter-kernel notebook run** (`python tools/run_notebooks_kernel.py`; written but never executed, `nbclient` was unavailable).
- **Reference metadata** (`python tools/check_references.py`, needs internet).
- Real two-host/two-account deployment of the anchor service (only localhost was exercised).

Notebook "matching saved stdout" is a signal only; 6 notebooks have cells whose output differs because of random keys / timing (Labs 02.03, 04.03, 10, 11, 12), unchanged from the previous run.
