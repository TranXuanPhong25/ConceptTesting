---
name: v36-llm-localize
description: v36 2026-10-20 Qwen2.5-Coder-32B (GPU endpoint) LLM localization code vs code+CFG on vibepass_half — no-go; CFG adds nothing, inputs 2–3/33
metadata:
  type: project
---

2026-10-20 (Claude): `trickcatcher_linefacts/analysis/v36_llm_localize/` (PREREG, probe.py, RESULTS.md). User asked
whether "LLM reads CFG / concept–code relations to locate the fault" was tried (yes: v13, v21, v28, v23/v33) and to try
qwen2.5-coder-32b-instruct on the ngrok GPU endpoint (vLLM AWQ, **8192-token context**).

- One call per task per arm: hit@3 6/14 both arms, hit@1 3/14 (< mutant rank-1 6/14); bug-revealing inputs code 3/33,
  cfg 2/33; ~half the inputs contract-invalid. Gate (19 CFG-supported PUTs) → **no-go**.
- CFG supported for only 19/33 VibePass PUTs (nested functions unsupported).
- Lesson: my first scorer dropped string inputs and unpacked one-arg lists (amendment 1); always reuse
  `flow_tools.parse_call` for model inputs.

**Why:** with v35, two independent checks say locating the fault is not the bottleneck; reaching valid bug-revealing
inputs is. **How to apply:** next concept must target input generation (validity + reaching the bug), not localization.
Related: [[v34-ftplacebo]], [[check-version-tree-before-proposing]], [[signal-not-more-data]].
