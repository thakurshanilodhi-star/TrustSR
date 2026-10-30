# Windows and Linux verification runbook

The project is intended to be portable, but portability is a testable claim, not a guarantee from reading code. Run the same logical checks on both operating systems and save separate records.

## Windows Command Prompt

Use the user's requested prompt/path in Windows instructions: `C:\Users\shani>`.

```bat
C:\Users\shani> cd /d C:\Users\shani\TrustSR
C:\Users\shani> py -3.12 -m venv .venv
C:\Users\shani> .venv\Scripts\python.exe -m pip install --upgrade pip
C:\Users\shani> .venv\Scripts\python.exe -m pip install -e ".[test,labs,kernel]"
C:\Users\shani> .venv\Scripts\python.exe -m pytest -q
C:\Users\shani> .venv\Scripts\python.exe -m pytest -q -m notebook
C:\Users\shani> .venv\Scripts\python.exe tools\run_notebooks.py --timeout 300 --jobs 1
C:\Users\shani> .venv\Scripts\python.exe tools\run_notebooks_kernel.py --timeout 600
C:\Users\shani> .venv\Scripts\python.exe tools\verify_install.py --extras test,labs
```

If the project is in another folder, replace only the `cd` path. Keep the `C:\Users\shani>` prompt as an example, not as a claim that the command was executed here.

## Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test,labs,kernel]"
python -m pytest -q
python -m pytest -q -m notebook
python tools/run_notebooks.py --timeout 300 --jobs 1
python tools/run_notebooks_kernel.py --timeout 600
python tools/verify_install.py --extras test,labs
```

## Evidence rules

- Save Windows results under `results/sample_runs/` with `windows` in the filename and Windows results under `results/notebook_runs/windows/`.
- Save Linux results under `results/sample_runs/` with `linux` in the filename and Linux results under `results/notebook_runs/linux/`.
- Never relabel the OS of a report. A Linux pass is not evidence of a Windows pass.
- Include the raw command, return code, Python version, dependency versions, and output.
- Mark unavailable network install, reference validation, real-kernel execution, or remote-anchor tests as pending; do not mark them passed.
- This repository's synthetic tests do not establish production security or formal correctness.
