# v65 evidence gate

Isolated v7 package with pinned v63 ports and repairs to hypothesis admission,
public-example consistency, evidence selection and generation gating. Oracle
unchanged. See PREREG_V65.md, REVIEW_V65.md and CHANGELOG.md; inherited versioned
reports describe historical parents, not v65 results.

Public-only path: semantic_contract -> joint_constructor -> evidence_gate ->
pipeline. A claimed alternative must explain its spec relation and pass every
public example under repeated uninstrumented execution. Construction seeks
behavioral witnesses under unchanged case caps. Non-public sensitive witnesses
are shown first; the gate inspects that exact context for every fixed case.
Public consistency and sensitivity do not prove hypothesis/input validity.

Run authored regression tests from the repository root:

```bash
/tmp/concepttester-v57-venv/bin/python -B -m pytest -q trickcatcher_linefacts/pipelines/v65_evidencegate/test_evidence_gate.py trickcatcher_linefacts/pipelines/v65_evidencegate/test_contractfix.py trickcatcher_linefacts/pipelines/v65_evidencegate/test_compositional.py trickcatcher_linefacts/pipelines/v65_evidencegate/test_pipeline.py trickcatcher_linefacts/pipelines/v65_evidencegate/test_scopeguard.py
```

Runner: `python -m trickcatcher_linefacts.pipelines.v65_evidencegate.pipeline`.
For a future reviewed run, `--online --prepare-only --requests ... --out ...
--approval ...` dispatches only six shared writers, construction and gate. A fresh
readiness identity is required; old v63 approvals cannot authorize this version.
Omitting --prepare-only permits generation only after every fixed case passes.
No endpoint/model run was started during this engineering task.

Ref10 follow-up: oracle_b01.py preserves v7's rule (ten spec-only programs,
base-test survivors, at least three and unanimous outputs, otherwise abstain).
Its combined execution/scoring path also loads canonical solutions. A future
integration must isolate prediction and bind programs to this cohort/spec; never
reuse mismatched task IDs or expose private outcomes to hypothesis/gate construction.
