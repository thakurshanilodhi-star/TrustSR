#!/usr/bin/env python
"""Run every lab notebook *individually* (one subprocess each, with a hard timeout).

Records status, wall-clock duration and, optionally, whether the freshly produced stdout
matches the stdout saved in the notebook. Writes a JSON + Markdown report.

Runs identically on Linux and Windows. Reports default to ``results/notebook_runs/<linux|windows|darwin>/``
so one platform never overwrites another's evidence. Executor: a plain-Python ``exec()`` of the code cells (same as ``tests/test_labs_smoke.py``);
IPython magics (``%``/``!`` lines) are skipped and matplotlib uses Agg. It is NOT a Jupyter
kernel. For kernel execution use ``jupyter nbconvert --execute`` (see README).

Usage:
  python tools/run_notebooks.py                      # all notebooks, 300 s timeout each
  python tools/run_notebooks.py --timeout 120 --jobs 4 --compare
  python tools/run_notebooks.py --only 02_trusted    # substring filter
  python tools/run_notebooks.py --report-dir results/notebook_runs/custom
  python tools/run_notebooks.py --child PATH         # internal: execute one notebook
"""
from __future__ import annotations
import argparse, re, contextlib, datetime as dt, io, json, os, pathlib, platform, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
LABS = ROOT / "labs"


def _code_source(cell) -> str:
    text = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
    return "".join(l for l in text.splitlines(True) if not l.lstrip().startswith(("%", "!")))


def execute_notebook(path: str) -> dict:
    """Execute code cells in a temp dir; return {'stdout': [per-cell text]} or raise."""
    import matplotlib
    matplotlib.use("Agg")
    try:  # wide, untruncated tables so text output is comparable with a notebook's saved output
        import pandas as pd
        pd.set_option("display.width", 250); pd.set_option("display.max_columns", None)
        pd.set_option("display.max_colwidth", None); pd.set_option("display.max_rows", 200)
    except ImportError:
        pass
    with open(path, encoding="utf-8") as fh:
        nb = json.load(fh)
    cwd = os.getcwd()
    ns = {"__name__": "__main__", "display": print}
    per_cell = []
    # ignore_cleanup_errors: on Windows a file still held open by a notebook (e.g. an unclosed SQLite
    # connection) cannot be deleted; that must not turn a passing notebook into a failure.
    with tempfile.TemporaryDirectory(prefix="trustsr_nb_", ignore_cleanup_errors=True) as workdir:
        os.chdir(workdir)
        try:
            for i, cell in enumerate(nb["cells"]):
                if cell["cell_type"] != "code":
                    continue
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    exec(compile(_code_source(cell), f"{os.path.basename(path)}[cell {i}]", "exec"), ns)
                per_cell.append((i, buf.getvalue()))
        finally:
            ns.clear()   # drop notebook objects (and any open handles) before the temp dir is removed
            import gc; gc.collect()
            os.chdir(cwd)
            import matplotlib.pyplot as plt
            plt.close("all")
    return {"cells": per_cell}


_VOLATILE = [(re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?"), "<TS>"),
             (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<UUID>"),
             (re.compile(r"\b[0-9a-f]{32,64}\b"), "<HEX>"),
             (re.compile(r"/tmp/[^\s'\"]+"), "<TMP>"),
             (re.compile(r"/(?:var/folders|private/var)/[^\s'\"]+"), "<TMP>"),                # macOS
             (re.compile(r"[A-Za-z]:[\\/][^\s'\"]*?[Tt]emp[\\/][^\s'\"]+"), "<TMP>"),        # Windows
             (re.compile(r"\b(?:Linux|Windows|Darwin|macOS)-[^\s'\"]+"), "<PLATFORM>")]


def normalize(text: str) -> str:
    """Mask volatile values (timestamps, hashes, temp paths) and compare layout-insensitively."""
    for rx, repl in _VOLATILE:
        text = rx.sub(repl, text)
    text = re.sub(r"<Figure[^>]*>", " ", text)  # figure reprs are not data
    # Compare the multiset of tokens, so pandas line-wrapping/column-width differences do not matter.
    # Bare integers of up to 3 digits are ignored: they are mostly DataFrame row indices that repeat in wrapped tables.
    toks = [t for t in re.findall(r"[A-Za-z0-9_.;<>+\-]+", text) if not re.fullmatch(r"\d{1,3}", t)]
    return " ".join(sorted(toks))


def saved_stdout(path: str) -> dict[int, str]:
    nb = json.load(open(path, encoding="utf-8"))
    out = {}
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        text = ""
        for o in cell.get("outputs", []):
            if o.get("output_type") == "stream" and o.get("name") == "stdout":
                text += "".join(o["text"]) if isinstance(o["text"], list) else o["text"]
            elif o.get("output_type") == "display_data":
                text += "".join(o.get("data", {}).get("text/plain", "")) + "\n"
        out[i] = text
    return out


def child(path: str) -> int:
    t0 = time.perf_counter()
    try:
        res = execute_notebook(path)
    except BaseException as exc:  # report any failure, including AssertionError
        print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"[:500],
                          "seconds": round(time.perf_counter() - t0, 2)}))
        return 1
    saved = saved_stdout(path)
    # compare only stream stdout; display_data text is collapsed into stdout by the harness
    match_cells, diff_cells = 0, []
    for i, text in res["cells"]:
        if normalize(text) == normalize(saved.get(i, "")):
            match_cells += 1
        else:
            diff_cells.append(i)
    print(json.dumps({"status": "PASS", "seconds": round(time.perf_counter() - t0, 2),
                      "cells": len(res["cells"]), "cells_matching_saved": match_cells,
                      "cells_differing_from_saved": diff_cells}))
    return 0


def run_one(path: pathlib.Path, timeout: int) -> dict:
    rel = str(path.relative_to(ROOT))
    t0 = time.perf_counter()
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""),
           "MPLBACKEND": "Agg", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        proc = subprocess.run([sys.executable, __file__, "--child", str(path)], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout, env=env)
        line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            rec = {"status": "FAIL", "error": (proc.stderr or proc.stdout)[-400:]}
    except subprocess.TimeoutExpired:
        rec = {"status": "TIMEOUT", "seconds": round(time.perf_counter() - t0, 2), "error": f">{timeout}s"}
    rec["notebook"] = rel
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--compare", action="store_true", help="(always recorded; flag kept for clarity)")
    ap.add_argument("--report-dir", default=str(ROOT / "results" / "notebook_runs" / platform.system().lower()))
    ap.add_argument("--child")
    a = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if a.child:
        return child(a.child)
    nbs = sorted(p for p in LABS.glob("*/*.ipynb") if a.only in str(p))
    started = dt.datetime.now(dt.timezone.utc)
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        recs = list(ex.map(lambda p: run_one(p, a.timeout), nbs))
    total = round(sum(r.get("seconds", 0) for r in recs), 1)
    out = pathlib.Path(a.report_dir); out.mkdir(parents=True, exist_ok=True)
    meta = {"started_utc": started.isoformat(timespec="seconds"), "python": platform.python_version(),
            "platform": platform.platform(), "os": platform.system(), "executor": "plain exec() harness (not a Jupyter kernel)",
            "timeout_per_notebook_s": a.timeout, "jobs": a.jobs, "total_notebook_seconds": total}
    (out / "notebook_runs.json").write_text(json.dumps({"meta": meta, "results": recs}, indent=2), encoding="utf-8")
    lines = ["# Notebook runs (individual subprocesses)", "", *(f"- {k}: `{v}`" for k, v in meta.items()), "",
             "| Notebook | Status | Seconds | Cells matching saved stdout | Differing cells |", "|---|---|---|---|---|"]
    for r in recs:
        lines.append(f"| {pathlib.Path(r['notebook']).name} | {r['status']} | {r.get('seconds','')} | "
                     f"{r.get('cells_matching_saved','')}/{r.get('cells','')} | {r.get('cells_differing_from_saved','') or r.get('error','')} |")
    n_ok = sum(r["status"] == "PASS" for r in recs)
    lines += ["", f"**{n_ok}/{len(recs)} passed.** Matching saved stdout is a reproducibility signal only; "
              "unseeded or timing-dependent cells legitimately differ."]
    (out / "notebook_runs.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-(len(recs) + 4):]))
    return 0 if n_ok == len(recs) else 1


if __name__ == "__main__":
    sys.exit(main())
