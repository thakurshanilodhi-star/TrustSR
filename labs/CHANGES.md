# Notebook changes in this archive (v0.2.0)

Notebook logic is otherwise unchanged from the supplied versions. Each edited notebook carries a "Revision note" cell near the top.

| Notebook | Problem found | Change |
|---|---|---|
| `01_contamination/..._01_4_...Uncertainty_Policy` | Assertion and prose said declaring both poison-source edges missing yields 5 false negatives; the code yields 0 because the edges are declared. | Assertion now expects 0; prose corrected; the real residual failure (undeclared edges) points to Lab 01.7. |
| `02_trusted_recovery/..._02_FINAL_...` | Whole-log-rewrite demo re-hashed an unchanged log, reproducing the original head, so `assert not head_matches` failed. | The first event is altered before re-hashing. |
| `03_reliability/..._03_02_...` | Expected audit-row delta of 2 for an injected pre-commit failure; the design writes 1 (rollback, then one failure record). | Expectation corrected to 1 (0 if the recorder also fails). |
| `03_reliability/..._03_07_...` | Policies used different seeds despite a comment claiming pairing, so `idempotent <= non_idempotent` failed from RNG noise even at retry_limit=1. | Shared seed per (timeout, retry) pair plus per-event common random numbers. Numeric results differ from earlier runs. |

## Saved outputs
Before this version no notebook had saved outputs. All were executed once with a plain `exec()` harness (not a Jupyter kernel): stdout, `display()` results as `text/plain`, and matplotlib figures as PNG. `%pip` lines were skipped. Environment versions are in each notebook's `metadata.trustsr_execution`.

## Added
`00_package/TRUSTSR_Lab_00_Package_Quickstart.ipynb`, which imports and exercises the `trustsr` package.

## Revision (review-hardened 0.2.0)
- `00_package/TRUSTSR_Lab_00_Package_Quickstart.ipynb`: audit head now comes from `HeadAnchor` (not `log.head`); new section 4b shows a rewritten log is caught only with the anchored head; section 5 shows a fabricated dict, a flattened real report and `apply(Trusted)` all being refused. Outputs regenerated.
- All other notebooks: logic and saved outputs unchanged.
- Re-execution record: `results/notebook_runs/` (38/38 run individually; 33 reproduce their saved text output; 5 differ only in random Ed25519 key material or in saved outputs that were truncated by the original harness's display width, e.g. `unver...`). No numeric result diverged.
- Durations: measure with `--jobs 1`. With 4 parallel jobs Labs 07/08 appear ~8x slower because they contend on SQLite fsyncs.
