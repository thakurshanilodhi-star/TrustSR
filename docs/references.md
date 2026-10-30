# References and relationship to TrustSR

These sources provide background standards and algorithm specifications. They do **not** validate TrustSR's novelty or prove that this prototype is secure.

1. Regenscheid, A. (2018). *Platform Firmware Resiliency Guidelines*. NIST Special Publication 800-193. https://doi.org/10.6028/NIST.SP.800-193. Relevance: resilience framing that includes protection, detection, and secure recovery. The publication addresses platform firmware; TrustSR is not a firmware implementation.
2. Ross, R. and Pillitteri, V. (2020; see NIST's current publication page for updates). *Security and Privacy Controls for Information Systems and Organizations*. NIST SP 800-53 Rev. 5. https://doi.org/10.6028/NIST.SP.800-53r5. Relevance: SI-7 software, firmware, and information integrity controls. This is a control catalogue, not a validation of TrustSR.
3. Josefsson, S. and Liusvaara, I. (2017). *RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)*. RFC Editor. https://www.rfc-editor.org/rfc/rfc8032. Relevance: algorithm specification for Ed25519/Ed448; TrustSR uses a library implementation of Ed25519 for checkpoint signatures.

## Research integrity

These are contextual primary sources, not a literature review. Before claiming novelty, add and compare peer-reviewed work on checkpointing and rollback recovery, stateful AI-agent reliability, event sourcing/audit integrity, trusted execution and anti-rollback mechanisms. Verify each source's bibliographic metadata and describe the precise overlap and difference. No novelty claim is made here.

## Verification status (honest record)

| Item | Status |
|---|---|
| Bibliographic metadata of refs 1-3 vs Crossref / RFC Editor | **Not verified by the authors of this revision** (no network in the build environment). Run `python tools/check_references.py` online and compare by hand. |
| Relevance claims ("Relevance: ...") | Written from background knowledge, not independently reviewed. |
| Novelty / related-work comparison | **Not done.** No claim is made. |
| Synthetic baseline (`experiments/run_synthetic_evaluation.py`) | Deterministic decisions are checked by `tests/test_evaluation_reproducible.py` (two runs, fresh keys, same outcome). It is a five-case software check; it is not a research baseline and says nothing about real agents. |
