# Book-to-implementation alignment

This document separates what the monograph proposes from what this repository currently implements. A module name, design sketch, unit test, or synthetic fixture is not proof of a complete real-agent implementation.

| Monograph area | Current repository evidence | Status / gap |
|---|---|---|
| Signed checkpoints and integrity | Ed25519 signed checkpoint module and regression tests | Prototype implemented; key provisioning/rotation is deployment-specific. |
| Replay protection | In-memory and SQLite high-water marks | Implemented as reference components; production storage isolation must be designed. |
| Tamper-evident audit | Hash chain and local/signed/remote anchor abstractions | Prototype; independent authority and separate-host deployment must be verified in deployment. |
| Trust state and verified promotion | State machine, sealed verification reports, checkpoint/recovery/state digest bindings | Prototype; in-process seal is not a boundary against hostile code in the same Python process. |
| Causal State Graph | Dependency graph and conservative missing-edge handling | Partial; completeness and correctness of real-world provenance are not guaranteed. |
| Eight-layer semantic state | State comparison/reference store | Incomplete; no complete adapter/recovery implementation for every layer of a real agent. |
| External side effects and compensation | Documentation and synthetic scenarios | Incomplete; no generic real-world compensation transaction. |
| Multi-agent coordinated recovery | Design discussion and limited synthetic tests | Incomplete; no demonstrated distributed protocol across real agents. |
| Formal soundness/completeness | Invariants, assertions, unit tests and proof sketches in the monograph | Formal proof/model-checking evidence is not established by the Python test suite. |
| TrustSR-Bench and adaptive red-team claims | Five hand-constructed synthetic gate scenarios and reproducible toy evaluation | Limited exploratory evaluation; does not validate the monograph's blast-radius, valid-work-preservation, or residual-contamination figures. |

## Research-claim policy

The monograph's numeric claims (including 15–30% blast radius, 85–92% valid work preservation, and less than 3% residual contamination) must be treated as unverified until raw traces, exact baseline implementations, scenario counts, seeds, metric definitions, and analysis scripts reproduce them. If that evidence is unavailable, rewrite those statements as proposed targets or hypotheses, not observed results.

Named related-work systems and their limitations must be checked against primary papers or authoritative project pages before making novelty or comparative superiority claims. `docs/references.md` is a starting point, not evidence that every claim in the monograph is verified.
