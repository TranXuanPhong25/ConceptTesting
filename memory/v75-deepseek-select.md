---
name: v75-deepseek-select
description: 2026-10-25 v47 concept selection with DeepSeek-V4-Flash (relace/fp4): final no-go 17/15 vs random 18.25/17.96 after 65k-token re-call (9/66 still empty); ≈$0.33
metadata:
  type: project
---

`trickcatcher_linefacts/analysis/v75_deepseek_select/`. Same frozen v47 menus/prompt/scorer as [[v74-oss-select]].
Provider only relace/fp4: `reasoning.enabled` → 31/31 empty at 8192 (model hand-enumerates examples; even 32768 empty);
`effort: low` ignored; amendment 1 `reasoning.max_tokens=4096`, max_tokens 16384 → still 28/66 length/empty.
covered@3 spec+code 10 (parsed 15), spec-only 12 (parsed 23) vs random 18.25/17.96. Parsed subset ≈ random
(10 vs 9.43; 12 vs 13.68). Total ≈ $0.18.

Amendment 2 (user: raise token cap): 28 empty calls re-called at max_tokens 65536 → 19 stop, 9 still empty
(mostly v44-unreachable tasks). Final covered@3 spec+code 17 / spec-only 15 vs random 18.25/17.96, first3 18; parsed
subset 17 vs random 16.25 (best of 3 models, Qwen 14) but ≈ random. Total ≈ $0.33.

**Why:** user asked to try DeepSeek with that provider after GPT-OSS no-go.
**How to apply:** three models (Qwen, GPT-OSS, DeepSeek) all ≈ random → menu selection is not model-limited; stop
model swapping. DeepSeek V4 Flash on relace needs `reasoning.enabled=false` or a hard cap for short-answer tasks.
