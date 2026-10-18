---
name: v27-codexoracle
description: v27 2026-10-18 — oracle failure is model-limited (Qwen 7B) AND prompt-limited for capable models; codex×strict property oracle precision 1.0 on pilot20
metadata:
  type: project
---

2026-10-18 (Claude): 2×2 {Qwen 7B, Codex gpt-5.6-luna low} × {original, strict prompt} on v26 fixed pools.
Report `trickcatcher_linefacts/analysis/v27_codexoracle_results.md`, code `pipelines/v27_codexoracle/`.

- pilot20 precision exact_spec: qwen .21, codex .76 → strict .90; property: qwen .15, codex .34 → strict **1.00** (0 FA,
  8/10 discrepancy tasks confirmed, 0/699 unsound checks). Qwen strict does not improve (crashes 295, recall drops).
- diag16 (novel fixtures) same direction: codex exact .86–.97, property strict .79.
- Codex CLI usable as oracle model: `codex exec --ephemeral --ignore-rules -s read-only -C <empty>` with stdin from
  /dev/null (otherwise it waits on stdin); ~6–15 s/call; quota barely used.

**Why:** user asked whether failure was the model or the prompt. **How to apply:** concept-as-property oracle is viable
with a capable model + strict rules; next step would be a matched generation run with that oracle (ask first:
memorization caveat for HumanEval, cost/quota). Related: [[v26-proporacle]], [[linefacts-v21-flowtools]].
