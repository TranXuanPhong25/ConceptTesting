---
name: coverup-concept-verdict
description: "CoverUp_concept seed 1 shows no concept effect; the site-hint smoke \"hint beats control p=7e-6\" is an artifact (one truncated function + mutant-level stats)"
metadata:
  node_type: memory
  type: project
  originSessionId: c7ea6648-d230-4c4d-8eab-acba360b8de8
  modified: 2026-10-08T17:09:40.558Z
---

As of 2026-10-08, CoverUp_concept seed 1 (58 modules x 5 arms) shows no arm differs on mutation score (all p >= 0.33; concept_reason 47.7 vs placebo_reason 45.2), and concept arms have slightly lower coverage than stock. Per-module diff SD is 15-22pp with median 0, so detecting 2.5pp needs ~200 modules x 3 seeds; 58 x 3 detects only >= ~4.7pp. Seed 2 was started and then stopped (only pysnooper/apimd done).

The site-hint smoke summary (`CoverUp_concept/out/smoke_sitehint/summary.md`, "hint vs control 83/34, p=7e-6") is not a real effect:
- 45 of hint's extra kills come from one function, `flutils._wrap_chunks` (85 mutants). In control and placebo, all 3 Gemini replies hit the 8192-token cap, so no code was extracted.
- At the function level (24 functions with hints), hint beat control in 3 functions and lost in 6 (p=0.5).
- A/A check: functions without hints get identical prompts in every arm, yet still show control vs placebo 13/0 (mutant-level p=2e-4). So mutant-level binomial tests are invalid because mutants are clustered.
- The hint arm also wrote about 60% more tests per function, a confound.

**Why:** the user asked whether to keep pursuing concept-guided test generation measured by coverage and mutation score. My recommendation was no; I suggested a placebo-controlled negative-results chapter, or a pivot to surviving-mutant feedback (as in MuTAP and ACH).

**How to apply:** before trusting any mutation result in this repo, cluster by function or module, and retry or exclude replies truncated at max_tokens. Don't re-derive this analysis. Related: [[concept-placebo-findings]].

Two more facts:
- **A strengthening round helps, but it isn't budget-matched yet.** One round per function with surviving mutants, using the site_hint `control` arm (it names the weak lines and has no concept text), raised mutation score on flutils from 51.3 to 56.7 and on string_utils from 52.3 to 59.9. That round cost $0.68, more than stock CoverUp on those two packages ($0.55).
- **mutmut marks some covered code as "no tests".** In the stock CoverUp arm, every mutant in `__str__` methods and in `pysnooper.tracer` (code run via `sys.settrace`) is marked "no tests", even where line coverage is 100% (pymonet.*). This sets a fixed floor that applies to every arm the same way.

Plan proposed on 2026-10-09, waiting for the user to approve: stop the concept arms; run a budget-matched strengthening round with arms more / lines / diff, plus diff+concept vs diff+placebo if concepts are required; score on held-out mutant lines; write a negative-results chapter. AGENTS rule 2 means the user must approve reimplementing MuTAP/ACH-style mutant feedback.
