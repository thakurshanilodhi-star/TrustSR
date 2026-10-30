#!/usr/bin/env python
"""Execute every lab notebook in a REAL Jupyter kernel (nbclient), one at a time, with a timeout.

Unlike ``tools/run_notebooks.py`` (a plain ``exec()`` harness) this starts an ipykernel, so it is the
evidence needed before saying "runs under Jupyter". Needs: ``pip install -e ".[labs,kernel]"``.
Works on Linux and Windows. Reports go to ``results/notebook_runs/<os>-kernel/``.

  python tools/run_notebooks_kernel.py --timeout 600
  python tools/run_notebooks_kernel.py --only Lab_00
"""
from __future__ import annotations
import argparse, json, os, pathlib, platform, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError:
        print('nbclient/nbformat/ipykernel missing: pip install -e ".[labs,kernel]"')
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--only", default="")
    ap.add_argument("--report-dir", default=str(ROOT / "results" / "notebook_runs" / f"{platform.system().lower()}-kernel"))
    a = ap.parse_args()
    os.environ["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")
    os.environ.update(MPLBACKEND="Agg", PYTHONUTF8="1")
    recs = []
    for path in sorted(p for p in (ROOT / "labs").glob("*/*.ipynb") if a.only in str(p)):
        t0 = time.perf_counter()
        status, err = "PASS", ""
        try:
            nb = nbformat.read(path, as_version=4)
            with tempfile.TemporaryDirectory(prefix="trustsr_k_", ignore_cleanup_errors=True) as wd:
                NotebookClient(nb, timeout=a.timeout, kernel_name="python3", resources={"metadata": {"path": wd}}).execute()
        except BaseException as exc:  # includes CellExecutionError, CellTimeoutError
            status, err = ("TIMEOUT" if "Timeout" in type(exc).__name__ else "FAIL"), f"{type(exc).__name__}: {exc}"[:400]
        recs.append({"notebook": path.name, "status": status, "seconds": round(time.perf_counter() - t0, 1), "error": err})
        print(f"{status:7} {recs[-1]['seconds']:7}s  {path.name}", flush=True)
    out = pathlib.Path(a.report_dir); out.mkdir(parents=True, exist_ok=True)
    meta = {"os": platform.system(), "platform": platform.platform(), "python": platform.python_version(),
            "executor": "Jupyter kernel via nbclient", "timeout_per_notebook_s": a.timeout}
    (out / "notebook_runs.json").write_text(json.dumps({"meta": meta, "results": recs}, indent=2), encoding="utf-8")
    n_ok = sum(r["status"] == "PASS" for r in recs)
    lines = ["# Notebook runs (Jupyter kernel)", "", *(f"- {k}: `{v}`" for k, v in meta.items()), "",
             "| Notebook | Status | Seconds | Error |", "|---|---|---|---|",
             *(f"| {r['notebook']} | {r['status']} | {r['seconds']} | {r['error']} |" for r in recs),
             "", f"**{n_ok}/{len(recs)} passed.**"]
    (out / "notebook_runs.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if recs and n_ok == len(recs) else 1


if __name__ == "__main__":
    sys.exit(main())
