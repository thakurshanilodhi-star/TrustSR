# Evaluation protocol

## Purpose and scope

The included comparison is a deterministic software-behavior check, not an empirical benchmark of real AI agents. It asks whether the five-gate verifier rejects four synthetic invalid conditions while accepting one clean fixture.

## Run

```bash
python experiments/run_synthetic_evaluation.py
python -m pytest
python -m pytest -m notebook
```

The script writes `results/evaluations/synthetic_gate_comparison.csv` and a metadata JSON file containing the Python/platform details and the exact scope of the experiment. The fixture generation is deterministic in scenario construction; Ed25519 keys are ephemeral and no cryptographic key material is persisted. Because the scenario count is five and the cases are hand-constructed, accuracy is descriptive only and no confidence interval or population inference is warranted.

## Baselines

The deliberately weak baseline is explicitly defined as “accept if the checkpoint signature is valid, without checking the audit log, state consistency, or scope completeness.” It is included as a negative-control baseline, not as a claim about a representative production system. TrustSR acceptance is the `verify_recovery` PASS/FAIL result.

## Required next-stage study

For research claims, replace this tiny fixture suite with a pre-registered scenario matrix and a realistic agent environment. Include full rollback, selective recovery, and TrustSR; vary checkpoint corruption, stale versions, missing/duplicated events, audit truncation, dependency-edge omissions, and irreversible side effects. Report false acceptance, false rejection, recovery success, state collateral damage, and latency. Use multiple fixed seeds where randomness is part of the scenario generator; preserve raw per-run results and configuration. Compare methods on identical scenario seeds and report uncertainty intervals. Do not claim superiority from the included five cases.

## Execution evidence

Plain-Python notebook harness results are not equivalent to Jupyter/Colab kernel execution. To verify notebooks in a kernel, install the lab dependencies and run:

```bash
jupyter nbconvert --to notebook --execute --inplace labs/00_package/TRUSTSR_Lab_00_Package_Quickstart.ipynb
```

Then run each notebook (or a batch) separately and record the command, exit code, duration, Python version, and dependency versions. Do not mark the Colab/Jupyter item complete until a clean runtime actually executes the notebooks.
