# v54_sonnet_mutconcept CHANGELOG

## 2026-10-24 (Claude)
Created from v46 (`analysis/v46_mutoracle_fixed`): same TC prompts (`tc`, `tc_concept`), program loading, validity,
question inputs, vote and judging; writer = Claude Sonnet subagents (k = 3 per arm) on 6 tasks fixed in PREREG.md.
Pilot requested by the user.

## 2026-10-24 renumber
Renamed from `v53_sonnet_mutconcept` to `v54_sonnet_mutconcept` after scoring (another session created
`v53_sonnet_tester` at the same time). No code logic or result changed. The task-selection key `sha256("v53/<task>")`
stays as registered. Subagent transcripts record the old path; `audit` maps it.
