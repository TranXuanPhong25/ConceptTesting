# v45 (renumbered from v43 on 2026-10-22; v43 is also used by v43_concept_identify) binary judge on v42 mutant-disagreement questions — results (2026-10-22)

Diagnostic (v42 was no-go; run at the user's request). Qwen2.5-Coder-32B-Instruct (vLLM AWQ, GPU endpoint), 607
questions × 3 arms = 1821 calls, 0 errors, 0 parse failures, all finish=stop. Rule: PREREG.md (eb5accd) + Amendment 1
after an independent review (20b8eff). Output `out/analysis/v43_mutjudge/score.json`.

| arm | confirmed tasks (/15 possible) | flags | true flags | FA questions | FA tasks | precision | sensitivity (mutant-right) | PUT chosen on PUT-right |
|---|---|---|---|---|---|---|---|---|
| binary (spec only) | 2 (85, 121) | 17 | 3 | 14 | 9 | 0.18 | 3/52 | 45/335 |
| code (+code, labels) | 0 | 14 | 0 | 14 | 9 | 0.00 | 0/52 | 41/335 |
| concept (+fault concept) | 1 (132) | 13 | 1 | 12 | 9 | 0.08 | 1/52 | 18/335 |

Choice distribution (all 607): binary unsure 229 / invalid 172 / neither 136 / PUT 53 / mutant 17; code unsure 367 /
invalid 132 / neither 46 / PUT 48 / mutant 14; concept unsure 380 / invalid 126 / neither 67 / PUT 21 / mutant 13.

**Verdict by the registered rule: close** (concept 1 < 8 confirmed, precision 0.08 < 0.5, below binary).

## Reading
- The model does not judge the binary question: it abstains ("unsure", "invalid") on 66–83% and picks either output on
  only 11–12%. Even when it picks, it is near chance (binary 3 right of 17 mutant picks; base rate of mutant-right 0.086).
- Showing code and the fault concept makes it *more* abstaining (unsure 229 → 367 → 380) and does not raise
  sensitivity (3 → 0 → 1). The fault concept adds nothing measurable to a binary oracle with this model.
- ~~With v42 and v37–v39 the route is closed for both selection and oracle~~ — withdrawn, see the audit below: v43 tests
  only a direct in-head judgement with this prompt, not the pipeline oracle.
- Ops note: the configured V4 venv (`config.json` V4_PYTHON, under a /tmp scratchpad) had been partly deleted by tmp
  cleanup; rebuilt in place with the same pinned versions (hypothesis 6.169.0, openai 1.109.1, mutmut 3.8.0) before
  scoring. Model calls were unaffected (cached in out/).

## Audit (2026-10-22, after the user asked whether the implementation is complete and correct)
Execution side verified: 112 re-executions on the official per-input path (all 52 mutant-right questions + 60 random)
match the batch outcomes for both mutant and PUT (112/112); all 52 mutant-right questions are officially confirmed;
package caps hold (≤ 2 per mutant, ≤ 32 per task, no duplicate inputs); all 1771 survivors ran.

Not complete / not the right instrument:
1. **The pipeline oracle was not used.** In TrickCatcher (tc-full) the expected output comes from 10 sampled programs
   (filtered by the public tests, majority group); the repo already has 240 Qwen-32B programs from v39 (TrickCatcher
   DPP prompt). v43 instead asked the model to compute the answer in its head. Its verdict applies only to that.
2. Prompt design biased toward abstention: an explicit "unsure" option, a 2-sentence reason and max_tokens 300 leave no
   room to compute; the model says "the specification does not provide enough information" on fully specified problems
   (e.g. 46, 163). Inputs were shown as a positional tuple without parameter names.
3. "neither" answers on PUT-wrong questions were not counted as detections (minor).
Ceiling for the proper oracle on these questions (join of v42 D1 tasks with v39 valid programs): only 8/15 D1 tasks
have ≥ 1 valid program and 4/15 have ≥ 3 (the v39 consensus size), so the pipeline oracle could confirm at most 8
(consensus: 4) of the 15 tasks. Not yet measured: whether the program majority picks the mutant output there.
