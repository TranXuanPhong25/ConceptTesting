---
name: v34-ftplacebo
description: v34 2026-10-20 placebo for v31 fault concepts (same template inputs, no concept) — detection 8–2 for concept but FA tests 27>23, rule not met; v35 ceiling → stop
metadata:
  type: project
---

2026-10-20 (Claude): `pipelines/v34_ftplacebo/` (copy of v31 + arm `template-placebo`; other arms copied from frozen v31
via `seed_from_v31.py`). User asked whether v31 even involved concepts → placebo isolates concept content from inputs.

- vibepass_half, K=1, Qwen3.5-35B OpenRouter, $1.56. Confirmed tasks: fault-template 18, plain 15, placebo 12.
- Primary (registered): fault-template vs placebo detection **8–2** (p≈0.11) but FA tests 27 > 23 → **rule not met**.
  Tasks with FA 11 vs 14, precision equal (.67/.66). Placebo vs plain 2–5: bare inputs do not help.
- Placebo probes hit 16k tokens 5× (finish=length); 2 of the 8 wins overlap.
- Report `trickcatcher_linefacts/analysis/v34_ftplacebo_results.md`.
- OpenRouter workspace has both monthly and **daily** $2 caps (403); resume prep must archive 403 attempt logs and
  unrecorded-arm ledgers outside the pipeline (fingerprint hashes all .py).

- Post-hoc mechanism (no API, scratch script): concept inputs expose the bug in only 11/33 tasks, top concept 6/33; in 5/8 wins the concepts point at no failing input, and all 16 confirmed tests in wins are new inputs (0 reused). → the specific fault hypothesis is rarely right; gain is not "concept locates bug". Lever = tool-side concept accuracy (CPU-measurable).

- v35 CPU go/no-go (`trickcatcher_linefacts/analysis/v35_concept_ceiling/`): ceiling 14/33 < 17 → registered verdict **stop**. Cause: template pool exposes only 17/33; given exposure, mutants locate 14/17, concepts hit 11/14. Loss is reaching bug-revealing inputs, not locating sites.

**Why:** first evidence that the fault concept itself (not its inputs) drives the v31 gain, but under the registered
FA unit it does not pass.
**How to apply:** before any larger run (other 33 PUTs ≈ $3.9 or K=3 ≈ $7.7), register precision or tasks-with-FA as
the false-alarm unit, and ask about budget. Related: [[v31-faulttemplate]], [[thesis-concept-requirement]].

- 2026-10-20 Codex review (`trickcatcher_linefacts/analysis/fault_localization_review_2026-10-20.md`): step a = sound candidate-hypothesis enumeration, NOT MBFL (no failing tests) and survivors are not correct fixes; v35 14/17 = partial correction only, regression-free on whole valid pool just 4/33 (46,85,121,132); 3/17 no correcting survivor. Stop verdict stands, "single-edit can't represent bugs" not established. Join: 0 pool-only tasks, 8 LLM-only, 8 neither (3,6,39,48,58,61,65,66). Domain filter halved pilot20 exposure 8→4. Literature: genuinely new step-b mechanism = joint path + fault/error-condition solving (UnitCon FSE'25, SAVIOR); also Mokav (paired-execution diff feedback, Python), NeuroTestGen, CASCADE, HGFuzzer — none with Qwen/Python-function evidence; CPU eligibility gates on pilot20 only, no reimplementation.
- 2026-10-20 v37 (pilot20, CPU, EvalPlus pool): surviving mutants witness bug in 3/20 → Mokav-over-mutants no-go. v38: Qwen-7B DPP spec programs = canonical in 182/183 → registered "go" is contamination, spec-alternative route untestable on HumanEval/MBPP sets; Java/C paper artifacts not eligible. Plan `trickcatcher_linefacts/PLAN_STEP_A_FIX.md` (A1 two-phase: localize with SBFL/MUSE only after a failing candidate; A2 mutants as adequacy probes; A3 code fixes; A4 non-memorized eval). Not implemented.
- 2026-10-20 v39 launched: v38 gate on vibepass_half (LeetCode, less memorized) with 10 fresh Qwen-32B DPP programs/question (240 calls, GPU endpoint); PREREG 4b4bc42. Plan revision: A1 cannot raise task detection (localizes after failure) → deprioritized; next = v40 Mokav-style DET search if v39 go.
- 2026-10-21 v39 final (240/240 calls after one transport retry): C' 12/33, H' 2 (tasks 73/74, one question), consensus precision 0.77; amended rule → **no-go G1/G2**; DET-search run not started. Spec programs wrong for 9/24 questions (newer ids solved less: 24/45 vs 30/39 correct). Paper route closed (v37/v38/v39); bottleneck = step b input reach. Gotcha: `ft_run.execute` caches result.json per dir → rescoring with new programs needs a fresh cases/ dir.
