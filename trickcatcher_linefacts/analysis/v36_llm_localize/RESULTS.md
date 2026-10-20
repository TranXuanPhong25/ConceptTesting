# v36 LLM localization probe — results (2026-10-20)

Qwen2.5-Coder-32B-Instruct (AWQ, free GPU endpoint), vibepass_half, one call per task per arm, temperature 0.
Output `out/analysis/v36_llm_localize/score.json` (after amendment 1: harness parse fix, first score kept as
`score_parsebug.json`). Rule in PREREG.md (1dc1e73, before any call).

| arm | parsed /33 | inputs | contract-valid | tasks with a bug-revealing input /33 | hit@1 /14 | hit@3 /14 |
|---|---|---|---|---|---|---|
| code | 32 | 133 | 62 | 3 | 3 | 6 |
| cfg (code + CFG) | 33 | 120 | 62 | 2 | 3 | 6 |

Gate on the 19 CFG-supported PUTs: exposure cfg vs code 1 win (74) – 2 losses (124, 96); hit@3 5 vs 5; cfg exposure
2 vs template pool 11. **Verdict: no-go.**

Reading:
- The CFG adds nothing: same localization, slightly fewer bug-revealing inputs.
- Localization by the LLM (hit@1 3/14) is worse than the mutant ranking (rank-1 concept 6/14, v35).
- The real problem is again inputs: about half of the proposed inputs violate the spec contract, and only 2–3/33
  tasks get a bug-revealing input, far below the template pool (17/33) and plain Qwen3.5-35B with replay (19/33, v31).
- Limits: one call, ≤ 9 inputs, no execution feedback, 8192-token context; a weaker model than v31's Qwen3.5.
