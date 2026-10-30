# TrustSR 0.3.0 — final review package notes

The project name and version label are preserved as `TrustSR` / `0.3.0`.

## Included review updates

- Windows Command Prompt instructions use the requested `C:\Users\shani>` prompt.
- Linux commands remain documented separately; OS-specific reports are not relabelled.
- Added `docs/windows_linux_runbook.md` for comparable cross-platform validation.
- Added `docs/book_implementation_alignment.md` to separate monograph proposals from current implementation and evidence.
- Added an actual Linux pytest run record: 120 tests passed in the current review environment.
- Recorded honestly that notebook batch execution timed out, Windows was not executed in this environment, and online reference checking could not run without network access.
- Preserved the synthetic evaluation as explicitly synthetic and not evidence of real-agent effectiveness.

## Re-run on the user's Windows laptop

From Command Prompt, after extracting to `C:\Users\shani\TrustSR`:

```bat
C:\Users\shani> cd /d C:\Users\shani\TrustSR
C:\Users\shani> py -3.12 -m venv .venv
C:\Users\shani> .venv\Scripts\python.exe -m pip install --upgrade pip
C:\Users\shani> .venv\Scripts\python.exe -m pip install -e ".[test,labs,kernel]"
C:\Users\shani> .venv\Scripts\python.exe -m pytest -q
C:\Users\shani> .venv\Scripts\python.exe -m pytest -q -m notebook
```

Do not describe the package as fully production-secure or the book's empirical numbers as reproduced until the missing Windows, real-kernel, anchor-deployment, and benchmark evidence is available.
