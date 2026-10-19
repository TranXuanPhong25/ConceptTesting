---
name: v31-faulttemplate
description: v31 2026-10-19 — explicit fault-type concepts (mutmut sites + ManySStuBs types, ranked by surviving alternatives) + per-type input templates vs plain; Qwen3.5-35B-A3B via OpenRouter; waiting for key
metadata:
  type: project
---

2026-10-19 (Claude): `pipelines/v31_faulttemplate/`, plan `trickcatcher_linefacts/PLAN_FAULT_TEMPLATES.md`, PREREG in folder.
User asked: split implicit LLM reasoning into (a) fault site/type ranking from code relations, (b) per-fault-type input
templates; compare with **plain only** to save cost; model `qwen/qwen3.5-35b-a3b` on OpenRouter.

- Key goes in gitignored `scripts/openrouter_env.sh` (template `scripts/openrouter_env.example.sh`, cap OPENROUTER_MAX_USD).
- Launch: `bash trickcatcher_linefacts/pipelines/v31_faulttemplate/run_openrouter.sh` (default MVP `vibepass_half`, 33 PUTs stratified, ≈$0.8).
- CPU: pilot20 template inputs expose bugs in 8/20 tasks (= v7 fuzz); VibePass 65/66 tasks get site concepts.
- Lesson: mutmut `enumerate_mutants` chdirs → needs a lock under threads.

**How to apply:** after the run, score, report vs rule (wins>losses and FA ≤ plain), update artifact. Positive result
still needs an unlabeled-template-inputs control. Related: [[v29-vibepass]].
