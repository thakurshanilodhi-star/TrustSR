#!/usr/bin/env python
"""Fresh-virtual-environment installation check (Linux and Windows).

Creates a brand-new venv in a temp directory, installs TrustSR *non-editable* into it, then verifies
the **installed** package (not ``src/``):

  1. ``import trustsr`` from a neutral working directory resolves inside the venv's ``site-packages``;
  2. the README "Minimal example" runs against the installed package;
  3. (if pytest is available in the venv) the package test-suite runs against the installed package with
     ``src/`` removed from the import path.

  python tools/verify_install.py                       # online: pip resolves everything from the index
  python tools/verify_install.py --extras test,labs    # also install notebook dependencies
  python tools/verify_install.py --offline             # no network: reuse already-installed deps
                                                       # (venv sees system site-packages; --no-build-isolation)
  python tools/verify_install.py --report-dir results/install_runs/windows

``--offline`` is weaker evidence: dependencies are NOT freshly resolved. The report records which mode ran.
Exit code 0 only if every executed step passed.
"""
from __future__ import annotations
import argparse, json, os, pathlib, platform, re, subprocess, sys, tempfile, time, venv

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(cmd, cwd=None, timeout=900):
    t0 = time.perf_counter()
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout,
                       env={**os.environ, "PYTHONUTF8": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
    return {"cmd": " ".join(str(c) for c in cmd), "returncode": p.returncode, "seconds": round(time.perf_counter() - t0, 1),
            "tail": (p.stdout + p.stderr)[-1500:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extras", default="test", help="comma list of extras: test, labs")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--report-dir", default=str(ROOT / "results" / "install_runs" / platform.system().lower()))
    a = ap.parse_args()
    steps, ok = [], True
    with tempfile.TemporaryDirectory(prefix="trustsr_venv_", ignore_cleanup_errors=True) as tmp:
        tmp = pathlib.Path(tmp)
        env_dir, neutral = tmp / "venv", tmp / "neutral"
        neutral.mkdir()
        venv.EnvBuilder(with_pip=True, system_site_packages=a.offline, clear=True).create(env_dir)
        py = env_dir / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
        spec = f".[{a.extras}]" if a.extras else "."
        pip = [py, "-m", "pip", "install"] + (["--no-build-isolation", "--no-deps", "."] if a.offline else [spec])
        steps.append({"step": "pip install (non-editable)", **run(pip, cwd=ROOT)})
        if steps[-1]["returncode"] == 0:
            probe = "import trustsr, sys; print(trustsr.__file__); print(trustsr.__version__)"
            r = run([py, "-c", probe], cwd=neutral)
            path = (r["tail"].splitlines() or [""])[0]
            r["step"] = "import from installed location"
            r["returncode"] = r["returncode"] or (0 if "site-packages" in path and str(ROOT / "src") not in path else 1)
            steps.append(r)
            text = (ROOT / "README.md").read_text(encoding="utf-8")
            example = re.search(r"## Minimal example\s+```python\n(.*?)```", text, re.S).group(1)
            (neutral / "readme_example.py").write_text(example + "\nprint('README example OK')\n", encoding="utf-8")
            steps.append({"step": "README example against installed package",
                          **run([py, neutral / "readme_example.py"], cwd=neutral)})
            if run([py, "-c", "import pytest"])["returncode"] == 0:
                steps.append({"step": "package tests against installed package",
                              **run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "pythonpath=",
                                     "--rootdir", ROOT, ROOT / "tests"], cwd=neutral, timeout=1800)})
            else:
                steps.append({"step": "package tests against installed package", "returncode": None,
                              "tail": "SKIPPED: pytest is not installed in the venv (offline mode without pytest)"})
        pipfreeze = run([py, "-m", "pip", "freeze"])["tail"] if py.exists() else ""
    ok = all(s["returncode"] in (0, None) for s in steps) and all(s["returncode"] == 0 for s in steps[:3])
    meta = {"os": platform.system(), "platform": platform.platform(), "python": platform.python_version(),
            "mode": "offline (system site-packages, no fresh dependency resolution)" if a.offline else "online (fresh resolution)",
            "extras": a.extras, "result": "PASS" if ok else "FAIL"}
    out = pathlib.Path(a.report_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "install_run.json").write_text(json.dumps({"meta": meta, "steps": steps, "pip_freeze": pipfreeze}, indent=2), encoding="utf-8")
    lines = ["# Fresh-venv install run", "", *(f"- {k}: `{v}`" for k, v in meta.items()), "",
             "| Step | Return code | Seconds |", "|---|---|---|"]
    lines += [f"| {s['step']} | {s['returncode']} | {s.get('seconds', '')} |" for s in steps]
    (out / "install_run.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    for s in steps:
        if s["returncode"] not in (0, None):
            print(f"\n--- {s['step']} (tail) ---\n{s['tail']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
