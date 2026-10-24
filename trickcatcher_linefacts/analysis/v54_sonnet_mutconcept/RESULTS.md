# v54 results (ex-v53_sonnet_mutconcept): Sonnet TC variants with/without the mutant fault concept (pilot, 2026-10-24)

PREREG + Amendments 1–2 (commits 7d17ce2, 11a3acb, ffbb9e8). 36 Sonnet subagents (`claude-sonnet-5-5`), k = 3 per
arm × 6 tasks; all 36 clean under the leakage rule (32 under the strict rule). Score: `out/analysis/v54_sonnet_mutconcept/score.json`.
Qwen arms (`qwen`, run after the v46 score; k = 10 matches v46 per task): `out/analysis/v54_sonnet_mutconcept/qwen.json`.

| arm | confirmed tasks | tests | true | FA | precision | valid | differ from PUT | right programs |
|---|---|---|---|---|---|---|---|---|
| Sonnet `tc` | **6/6** | 19 | 16 | 3 | .84 | 18/18 | 18 | 18/18 |
| Sonnet `tc_concept` | **6/6** | 16 | 16 | 0 | 1.00 | 18/18 | 16 | 16/18 |
| `tc` strict rule | 6/6 | 19 | 16 | 3 | .84 | 15 | 15 | 15 |
| `tc_concept` strict rule | 6/6 | 16 | 16 | 0 | 1.00 | 17 | 15 | 15 |
| Qwen `tc` k = 3 | 0/6 | 15 | 0 | 15 | .00 | 15 | 2 | 0 |
| Qwen `tc_concept` k = 3 | 0/6 | 11 | 0 | 11 | .00 | 14 | 1 | 0 |
| Qwen `tc` k = 10 | 0/6 | 17 | 0 | 17 | .00 | 47 | 5 | 0 |
| Qwen `tc_concept` k = 10 | 0/6 | 11 | 0 | 11 | .00 | 50 | 5 | 0 |

Consensus (≥ 3 valid, all agree, ≠ PUT, confirmed): `tc` 6/6 tasks, `tc_concept` 5/6 (not 101).
Per task: `tc` FA all on task 46 (3 of 10 tests); `tc_concept` task 101: 2 of 3 programs keep the PUT's behaviour on
every question input (common-mode), 1 repairs it.
Mechanism: no program in either arm contains a shown `before -> after` edit (exact-line check, approximate); a D1 edit
was among the shown concepts on all 6 tasks.

## Reading
- **Concept effect: none measurable (ceiling).** Both arms confirm 6/6; the registered signal (≥ +3 tasks or ≥ 6 more
  right programs) is not met: right programs 16 vs 18 go the other way, FA 0 vs 3 favour the concept arm. Neither
  difference is evidence at k = 3 × 6 tasks.
- **Writer strength is the effect.** These 6 tasks were chosen because the Qwen TC oracle failed on them in v48
  (common-mode or no valid variant). Sonnet repairs the bug in 18/18 `tc` programs without any concept, so the oracle
  works at the ceiling. This repeats v27/v28 (Codex ≫ Qwen, ceiling, no concept gain) on VibePass. Not a cohort
  estimate (selected on Qwen failure); recall of the LeetCode problems is possible.
- The concept did not steer the repair: Sonnet never applied a shown mutant edit, and on task 101 the concept block
  coincided with 2 programs keeping the bug.

Qwen on the same tasks: valid variants but common-mode. Of 47 valid `tc` variants, 5 differ from the PUT on any question
input, and none is right.

## Status
Complete. Concept not supported for a strong writer on the oracle side (no headroom); Qwen fails for model reasons
(common-mode) with or without the concept. v52 (definitional concept, other session) asks the same question.
