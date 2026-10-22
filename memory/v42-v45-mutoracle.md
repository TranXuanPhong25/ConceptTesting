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
  networkx 3.4.2). Do not edit v34 config.json (protocol hashes .json).

- 2026-10-22 audit (user: "impl đủ và đúng chưa?"): execution verified 112/112 on official path; BUT v43 did not use
  the pipeline oracle (TrickCatcher: 10 sampled programs, majority; v39 has 240 Qwen-32B DPP programs) and its prompt
  invited abstention ("unsure", 300 tokens). v43 verdict only covers direct in-head judgement. Proper-oracle ceiling:
  8/15 D1 tasks have ≥1 valid v39 program, 4/15 have ≥3. Also: v43 number collides with v43_concept_identify (other session).

**Why:** v42 closes mutant-disagreement *selection*; the oracle side is untested with the pipeline oracle.
**How to apply:** an oracle diagnostic in this repo must use program variants (v39 programs / tc-full), never an
in-head LLM judgement with an "unsure" exit. Related: [[v41-iorel]], [[v34-ftplacebo]], [[check-version-tree-before-proposing]].
