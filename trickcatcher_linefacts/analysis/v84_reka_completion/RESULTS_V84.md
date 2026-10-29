# V84 Reka completion addendum for the V83 two-arm quarter

## Completion

The user's follow-up authorized continuing after V83's terminal 26/28 partial. V83 remains immutable. V84 reran task 154 from scratch in both arms because OpenRouter confirmed its missing generation had finished (Reka, `stop`, $0.0051955) but the stored completion text returned 404. Task 158 had no prior generation. Both were run with the same Reka route, model, prompts, seeds, K=1, and 24k output cap. No old task-154 arm output was spliced into the addendum.

All 28 fixed HumanEval tasks now have one output per arm (56 rows total): 26 pairs from V83 plus fresh pairs for tasks 154 and 158 from V84. V84 completed 13 physical attempts, with 13 received, zero unknown, and known cost $0.05421496. Its isolated cap was $0.50.

## Descriptive scoring across the 28 tasks

| Oracle | FT wins | FT losses | Ties | FT false positives | Control false positives |
|---|---:|---:|---:|---:|---:|
| o0 | 4 | 4 | 20 | 9 | 6 |
| Reference | 3 | 4 | 21 | 2 | 0 |
| Full | 3 | 4 | 21 | 2 | 0 |

The merged table is exploratory only: it combines 26 V83 pairs with two V84 addendum pairs after the original run stopped on unknown accounting. The scoring artifact therefore sets `partial=true` and `rule_met=null`; do not treat this as a confirmatory efficacy result.

## Accounting and integrity

Previous v81/v82 known bills plus reserves: $0.74708916. V83 known cost: $0.68198775. The unresolved V83 reserve remains fully charged at $0.0642930 even though generation metadata later reported $0.0051955 for the unknown request. V84 known cost: $0.05421496. Conservative cumulative exposure is $1.54758487 of the $4.20 cap, leaving $2.65241513. V84's 90 frozen generation/scoring-input entries all match their hashes; V83's frozen root was not modified.

Machine-readable summary: `RESULTS_V84.json`. Frozen generation outputs and full scores are under `pipelines/v84_reka_completion/out/reka_completion_154_158/` (local output directory, excluded from source commit). The addendum protocol is `pipelines/v84_reka_completion/PREREG_V84.md`.
