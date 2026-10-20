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
