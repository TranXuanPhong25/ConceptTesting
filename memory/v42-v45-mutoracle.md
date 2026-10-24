---
name: v42-v45-mutoracle
description: v42 mutant-disagreement oracle questions CPU ceiling no-go (D1 15/33, lift 0.62); v43 Qwen32B binary judge close (concept 1/15, model abstains 66–83%)
metadata:
  type: project
---

2026-10-21/22 (Claude): idea = move mutants to the oracle side (MutGen gap: MutGen assumes original code correct).
- v42 `trickcatcher_linefacts/analysis/v42_mutoracle/` (CPU, v41 Hypothesis pool × v34 surviving mutants): D1 15/33
  (uncapped 19), D2 15 vs random-k 13.3, median lift 0.62 → **no-go**. On valid package inputs the mutant is right in
  52 questions, PUT 335, neither 46.
- v45 `analysis/v45_mutjudge/` (renumbered from v43) (diagnostic at user request, Qwen2.5-Coder-32B GPU endpoint, 607 q × binary/code/concept):
  confirmed tasks 2/0/1, precision .18/.00/.08; model answers unsure/invalid 66–83% → **close**. Code + fault concept
  increase abstention.
- Gotcha: V4_PYTHON venv lives in an old /tmp scratchpad; tmp cleanup deletes it piecemeal. Rebuilt in place 2026-10-22
  (py 3.12.2, hypothesis 6.169.0, openai 1.109.1, mutmut 3.8.0, httpx 0.27.2, jinja2 3.1.4, jsonschema 4.23.0,
  networkx 3.4.2, sortedcontainers 2.4.0 — PUT 171 imports it). Rebuilt venv reproduces v41 PUT outcomes 1320/1320.
  Do not edit v34 config.json (protocol hashes .json).

- 2026-10-22 audit (user: "impl đủ và đúng chưa?"): execution verified 112/112 on official path; BUT v43 did not use
  the pipeline oracle (TrickCatcher: 10 sampled programs, majority; v39 has 240 Qwen-32B DPP programs) and its prompt
  invited abstention ("unsure", 300 tokens). v43 verdict only covers direct in-head judgement. Proper-oracle ceiling:
  8/15 D1 tasks have ≥1 valid v39 program, 4/15 have ≥3. Also: v43 number collides with v43_concept_identify (other session).

**Why:** v42 closes mutant-disagreement *selection*; the oracle side is untested with the pipeline oracle.
**How to apply:** an oracle diagnostic in this repo must use program variants (v39 programs / tc-full), never an
in-head LLM judgement with an "unsure" exit. Related: [[v41-iorel]], [[v34-ftplacebo]], [[check-version-tree-before-proposing]].

v46 (`analysis/v46_mutoracle_fixed`, PREREG + amendment 1, the repaired oracle diagnostic) status 2026-10-23 19:00: the
endpoint serves one request at a time. 8 client workers livelocked it, so oracle.py uses 1 worker (`V46_WORKERS`) with a
1200 s timeout (f000e3d, 9e3f9e9; a vLLM restart had left a 3600 s client hanging). Alone on the server it does ~38 calls/h.
The tunnel went offline about 18:55. Cached: TC 492/620 (tc 250, tc_concept 242; up to task 132), judge 1/1821. Rerun
`generate` to resume from the cache. The other session's v48 orchestrator waits for tc 310 and reads it read-only.

**v46 RESULT (2026-10-24): close.**
- Neither concept pair passes. Confirmed tasks / precision: `tc` 5 / .37, `tc_concept` 2 / .26 (46 vs 136 tests,
  so the concept made Qwen variants more common-mode), `dpp` 7 / .48.
- Repaired judge: binary 11, code 10, concept 10 (same set as code), precision .13–.14, FA ~170–190. Reach is up from
  v45 (2/0/1), but the judge picks mutant/neither/invalid on PUT-right questions.
- On the 6 Qwen-failed tasks of v54 (ex-v53_sonnet_mutconcept): Qwen k = 10 gets 0/6 (47 valid variants, only 5
  differ from the PUT); Sonnet k = 3 gets 6/6. The model binds, not the concept.
- Mutant concept closed on both the selection side (v42) and the oracle side (v46) for Qwen. See [[v54-sonnet-mutconcept]].
