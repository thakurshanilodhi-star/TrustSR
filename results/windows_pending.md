# Windows run: PENDING (must be executed on Windows or proven by green CI)

Do not copy Linux results into this file. The following commands use the user's requested Windows Command Prompt prompt `C:\Users\shani>`.

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

When the commands finish, record exact OS build, Python/dependency versions, command output and exit codes in `results/sample_runs/run_v0.3.0_windows.md`. Do not mark any check passed just because it is configured in `.github/workflows/tests.yml`; only a green CI run/log or actual Windows run is evidence.
