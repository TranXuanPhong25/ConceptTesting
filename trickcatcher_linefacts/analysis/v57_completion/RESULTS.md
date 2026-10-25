# v57 frozen run — reviewed instrumentation, retrospective labels

2026-10-24. Scorer instrumentation independently reviewed before fresh execution into `out_reviewed/`; prior failed/provisional directories remain preserved. All144raw final slots parsed, no unresolved workers in this fresh output. Generation was unchanged and previously froze78response slots/79attempts.

|Arm|Confirmed tasks /6|Confirmed final tests|Valid-input false alarms|Invalid inputs|Revealing inputs with wrong expected|
|---|---:|---:|---:|---:|---:|
|plain|1|2|8|7|8|
|concept|1|2|9|0|3|
|equal-evidence raw|1|2|3|6|3|
|inputs-only|1|3|6|4|4|

The confirmed task is85 in every arm. Task-discordance comparisons have zero wins/losses. Per-problem OR tables, raw denominators, conditional attack/output/joint metrics, duplicate/conflicting expectations and actual model usage are in `out_reviewed/score.json`; public-witness-only labels are recorded there as well.

This is a six-case development diagnostic, not confirmation/generalization. The old solver produced zero witnesses for all six cases, so this cannot reject or validate the new executable construction mechanism. Concept/raw treatment can still supply textual hypotheses; no causal claim is made about why tests were generated. Input discrepancies with wrong expected outputs are an explicit oracle loss, not confirmed bugs.

Scorer metadata retains `provisional:true`/`review_required:true` as a conservative result-release flag. Instrumentation readiness passed independent review; result adjudication is not an independently blinded semantic review of every reference. Do not remove historical limitations or treat the numbers as a paper-level efficacy result.
