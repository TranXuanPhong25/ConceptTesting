# CHANGELOG v34_ftplacebo

Parent: `pipelines/v31_faulttemplate` (PARENT.json). Question and rule: v34 section at the end of PREREG.md.

## 2026-10-20 — placebo for fault concepts: same template inputs, no concept content

- `ft_run.py`: arm `template-placebo` (`placebo_guidance`: inputs + put_output, sorted, no concept fields); score
  reports pairs fault-template vs template-placebo, template-placebo vs plain, fault-template vs plain.
- `config.json`: VERSION v34_ftplacebo, arms + llm_arms add template-placebo, `reused_from_v31`.
- `seed_from_v31.py`: copies tool.json/tool/ and the five reused arm records from the frozen v31 run (hash-checked);
  `run_openrouter.sh` runs it first. Only template-placebo calls the model.
- `test_faulttemplate.py`: +1 test (placebo has the same inputs and no concept content). 40 tests pass.
- Status: complete 2026-10-20 ($1.56). fault-template vs placebo detection 8–2 (p≈0.11) but FA tests 27 > 23 → registered rule NOT met; placebo vs plain 2–5 (inputs alone do not explain the v31 gain). See analysis/v34_ftplacebo_results.md.
