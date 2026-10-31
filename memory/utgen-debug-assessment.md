---
name: utgen-debug-assessment
description: UTGen/UTDebug paper reviewed; relevant trained-test baseline and oracle framing, no evidence of concept benefit
metadata:
  type: reference
---

Codex, 2026-10-24: user requested an opinion on arXiv 2502.01619v3.
Assessment and source links: [research note](../research/utgen-debug/ASSESSMENT.md).
Useful for distinguishing attack rate from oracle accuracy. Training results do not establish concept value.
Compare against v48/v49/v54 before suggesting an extension. No implementation, paid calls or reproduction performed.

Follow-up artifact audit: [feasibility](../research/utgen-debug/REPRODUCTION_FEASIBILITY.md).
Unmodified author clone at `research/utgen-debug/vendor/UTGenDebug`, commit
`03bc690c28b6331e7ff0131cb001dab66f4e546f`. Three dataset counts verified (158/325/170), Python AST parse only.
No training script/data/weights in inspected author tree; trained UTGen rows need additional artifacts.
Intrinsic MBPP `--hard` selection is reversed relative to README; debugging has missing default source and loading/configuration issues.
LineFacts adapter plausible, but public base examples/MBPP validators must be defined without private-test/reference leakage.
