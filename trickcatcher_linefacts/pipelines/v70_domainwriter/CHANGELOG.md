# v70_domainwriter — 2026-10-25

Implemented;133authored regression tests pass. Preflight6/6fits8192context with
1536output tokens; writer packet unchanged fromv69. CPU/fresh outcomes pending.
Basev7 + pinnedv69ports; earlier sources/outputs/vendor remain unchanged.

- domain_constraints.py: exact quoted public-constraint grammar, source binding,
  explicit unsupported-line refusal, numeric/length/element/alphabet/point rules.
- joint_constructor.py: solver domain conjunction, invalid-shape pruning before
  query/native budget, concrete model and native domain recheck; budget unchanged.
- evidence_gate.py/pipeline.py: public domain checked before writer, persisted
  receipt, independent evidence/gate/final-input domain validation.
- replay_saved.py: fixed6legacy CPU replay, v70protocol/runtime identity.
- test_domain_constraints.py:19domain tests plus114inherited/compiler regressions,133total.
- analysis/v70_domainwriter: exact preflight, detached prepare-only fresh runner
  and read-only CPU/fresh audits. No full generation or oracle/ref10 work.
