"""Executes every notebook, each in its own subprocess with a hard per-notebook timeout.

One slow or hung notebook now fails *one* test (with its name and duration) instead of freezing the
whole suite. Override the limit with ``TRUSTSR_NB_TIMEOUT`` (seconds, default 300). Skipped
automatically if the optional lab dependencies are missing. A notebook's own assertions act as
regression tests. Executor: plain ``exec()`` of code cells (not a Jupyter kernel); ``%``/``!`` lines
are skipped. For per-notebook timing and saved-output comparison run ``tools/run_notebooks.py``.
"""
import json, os, pathlib, subprocess, sys
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
LABS = ROOT / "labs"
NOTEBOOKS = sorted(str(p) for p in LABS.glob("*/*.ipynb"))
TIMEOUT = int(os.environ.get("TRUSTSR_NB_TIMEOUT", "300"))


def run_notebook(path: str) -> None:
    pytest.importorskip("matplotlib"); pytest.importorskip("pandas")
    pytest.importorskip("networkx"); pytest.importorskip("numpy")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""),
           "MPLBACKEND": "Agg", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    name = os.path.basename(path)
    try:
        proc = subprocess.run([sys.executable, str(ROOT / "tools" / "run_notebooks.py"), "--child", path],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        raise AssertionError(f"{name}: exceeded {TIMEOUT}s per-notebook limit (set TRUSTSR_NB_TIMEOUT to raise it)")
    lines = proc.stdout.strip().splitlines()
    try:
        rec = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        raise AssertionError(f"{name}: no result from child. stderr: {proc.stderr[-500:]}")
    assert rec["status"] == "PASS", f"{name} failed after {rec.get('seconds')}s: {rec.get('error')}"


@pytest.mark.notebook
@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: os.path.basename(p)[:60])
def test_notebook_runs_and_its_assertions_hold(path):
    run_notebook(path)


@pytest.mark.notebook
def test_notebooks_were_found():
    assert len(NOTEBOOKS) == 38, f"expected 37 labs + Lab 00, found {len(NOTEBOOKS)}"
