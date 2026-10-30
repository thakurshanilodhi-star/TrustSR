# Research notebook index

All notebooks in this archive were executed with the harness described in `CHANGES.md`; their saved outputs are **synthetic simulation output**, not real-agent or production evidence. Every notebook records its execution metadata under `metadata.trustsr_execution`. Re-run in your own environment (`python -m pip install -e ".[labs]"`) before citing any number.

Labs 01-13 are self-contained prototypes that re-implement their logic inline; they do **not** import `trustsr`. Lab 00 does. The package's graph policy is checked against Lab 01.4 by `tests/test_lab_equivalence.py`, and every notebook's assertions run as `tests/test_labs_smoke.py`.

## 00_package

Uses the tested `trustsr` package.

- `TRUSTSR_Lab_00_Package_Quickstart.ipynb`

## 01_contamination

Contamination graphs, missing-edge detection and recovery policies (self-contained).

- `TRUSTSR_Lab_01_1_Missing_Edge_Failure_Test.ipynb`
- `TRUSTSR_Lab_01_2_Systematic_Missing_Edge_Experiments.ipynb`
- `TRUSTSR_Lab_01_3_Conservative_Unknown_Dependency_Handling.ipynb`
- `TRUSTSR_Lab_01_4_Ground_Truth_Independent_Uncertainty_Policy.ipynb`
- `TRUSTSR_Lab_01_5_Recovery_Strategy_Comparison.ipynb`
- `TRUSTSR_Lab_01_6_Randomized_Recovery_Evaluation.ipynb`
- `TRUSTSR_Lab_01_7_Blind_Missing_Edge_Detection.ipynb`
- `TRUSTSR_Lab_01_8_Threshold_Sensitivity_and_Stress_Testing.ipynb`
- `TRUSTSR_Lab_01_Memory_Poisoning_and_Contamination_Graph.ipynb`

## 02_trusted_recovery

Signed checkpoints, replay protection, SQLite persistence, tamper-evident audit (self-contained).

- `TRUSTSR_Lab_02_01_Selective_Recovery_Prototype.ipynb`
- `TRUSTSR_Lab_02_02_Checkpoint_Integrity_and_Provenance.ipynb`
- `TRUSTSR_Lab_02_03_Signed_Checkpoint_Manifest.ipynb`
- `TRUSTSR_Lab_02_04_Checkpoint_Versioning_and_Replay_Protection.ipynb`
- `TRUSTSR_Lab_02_05_Concurrent_Checkpoints_Atomic_High_Water_Mark.ipynb`
- `TRUSTSR_Lab_02_06_SQLite_Transactional_Persistence_and_Restart_Recovery.ipynb`
- `TRUSTSR_Lab_02_07_Tamper_Evident_Audit_Trail.ipynb`
- `TRUSTSR_Lab_02_FINAL_Integrated_Recovery_and_Audit_Validation.ipynb`

## 03_reliability

Atomic persistence, failure journals, retry/idempotency, outage simulation (self-contained).

- `TRUSTSR_Lab_03_01_Atomic_Checkpoint_and_Audit_Persistence.ipynb`
- `TRUSTSR_Lab_03_02_Failure_Recording_and_Recovery.ipynb`
- `TRUSTSR_Lab_03_03_Independent_Failure_Journal_and_Reconciliation.ipynb`
- `TRUSTSR_Lab_03_04_Retry_Idempotency_and_Reconciliation.ipynb`
- `TRUSTSR_Lab_03_05_Parameterized_Retry_Stress_Test.ipynb`
- `TRUSTSR_Lab_03_06_Correlated_Outages_and_Ambiguous_Timeouts.ipynb`
- `TRUSTSR_Lab_03_07_Final_Integrated_Reliability_Benchmark.ipynb`

## 04_evaluation

Selective-recovery effectiveness and observability stress tests (self-contained).

- `TRUSTSR_Lab_04_01_Selective_Recovery_Effectiveness.ipynb`
- `TRUSTSR_Lab_04_02_Uncertainty_Aware_Recovery.ipynb`
- `TRUSTSR_Lab_04_03_Coverage_Signal_Robustness.ipynb`
- `TRUSTSR_Lab_04_Final_Adversarial_Observability_Stress_Test.ipynb`

## 05_execution

Recovery execution, interruption/retry, journals and crash recovery (self-contained).

- `TRUSTSR_Lab_05_Recovery_Execution_and_Independent_Verification.ipynb`
- `TRUSTSR_Lab_06_Recovery_Interruption_Retry_and_Idempotence.ipynb`
- `TRUSTSR_Lab_07_Persistent_Journal_and_Restart_Recovery.ipynb`
- `TRUSTSR_Lab_08_Hard_Crash_Recovery_and_Integrity_Validation.ipynb`

## 06_capstone

Trust-state model, invariants, verification engine, authenticated checkpoints (self-contained).

- `TRUSTSR_Final_Capstone_Lab_12_Adaptive_Recovery_Trust_Reinstatement.ipynb`
- `TRUSTSR_Lab_09_Trust_State_Model_and_Transition_Validation.ipynb`
- `TRUSTSR_Lab_10_Trust_State_Sequence_and_Invariant_Testing.ipynb`
- `TRUSTSR_Lab_11_Recovery_Verification_Engine.ipynb`
- `TRUSTSR_Lab_13_Authenticated_Checkpoints_and_GroundTruth_Completeness.ipynb`
