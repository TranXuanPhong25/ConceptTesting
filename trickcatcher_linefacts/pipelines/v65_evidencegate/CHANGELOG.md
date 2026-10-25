# v65_evidencegate — 2026-10-25

Status: implemented; 88 offline regression tests passed; no model run or efficacy claim.

Base: best packaged v7 plus pinned v63 files, recorded in PARENT_V65.json. Earlier
v31/v63 and the separate v64 symbolic branch are preserved.

- semantic_contract.py: mismatch/alternative rationale, conservative constant
  predicate checks, no-op/None rejection; module sites unsupported.
- evidence_gate.py: repeated public consistency, sensitivity-first selection,
  exact displayed evidence receipts and per-case generation gate.
- joint_constructor.py: public checks before search, shared budget accounting
  and allocation across hypotheses; rationale retained on revalidation.
- pipeline.py: every-case gate, direct-entry enforcement, delivery hash,
  configuration-bound resume, fresh readiness and prepare-only mode.
- run_ngrok.sh/ngrok_run.py/config.json: correct v65 module and output identity;
  inherited CLI delegates to the integrated gate.
- test_evidence_gate.py and inherited contract/compositional/pipeline/scope
  fixtures: authored regression checks, not simulated benchmark/paper outcomes.
- PREREG_V65.md/REVIEW_V65.md/README.md/VERSION_TREE.md: protocol, limits, status.
  Ref10 adapter left for a separate oracle change.

Validation: 88 passed in10.62s. Parent inventories unchanged (v7:51files, v63:100files).
See RESULTS_ENGINEERING_V65.md; owner source review only, no independent run readiness issued.
