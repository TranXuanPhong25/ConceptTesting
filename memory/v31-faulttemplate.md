---
name: v31-faulttemplate
description: v31 2026-10-19 — explicit fault-type concepts (mutmut sites + ManySStuBs types, ranked by surviving alternatives) + per-type input templates vs plain; Qwen3.5-35B-A3B via OpenRouter; complete, rule met but weak (18 vs 15, 4–1)
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

- 2026-10-20: run paused — OpenRouter **workspace** monthly budget $2.00 (org admin, resets 2026-11-01) is a second cap below the key limit ($5); 403 PermissionDenied. 149 responses all finish=stop DeepInfra fp8, $1.95 (~$0.013/call, ~12k reasoning tokens). 10 cases missing; resume needs ~$0.65.

- 2026-10-20 result (vibepass_half, K=1, $2.56): fault-template 18/33 confirmed (FA tests 27) vs plain 15 (32); paired 4–1 → registered rule met. Weak: p≈0.38; win 103 = plain schema failure; template-only 11 vs template-random 9 tasks (ranking ≈ random). Report `trickcatcher_linefacts/analysis/v31_faulttemplate_results.md`.
- Lesson: `flow_tools` fingerprint hashes every pipeline .py → never edit code mid-run (ledger_context_drift); fix resume state outside the pipeline.

**How to apply:** after the run, score, report vs rule (wins>losses and FA ≤ plain), update artifact. Next: unlabeled-template-inputs placebo + K≥3 or full 66 before any claim. Related: [[v29-vibepass]].
