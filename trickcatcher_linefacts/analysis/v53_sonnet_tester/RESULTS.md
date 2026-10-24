# v53 results: Claude Sonnet as test writer in the v34 fault-concept loop (6 tasks, K = 1)

Source: `out/analysis/v53_sonnet_tester/score.json` (frozen; `score` re-validated all 54 answers against the records,
tool.json = v34). PREREG + amendment 1. 54 calls, one fresh Sonnet subagent each; 54/54 answers schema-valid; tool use
3 per call (Read, Write, hand-back), 2 for the 3 calls resumed after a rate limit.

| arm | tasks confirmed /6 | confirmed tests | FA tests | discrepancy tasks | confirmed from guidance inputs | Qwen3.5 (v34): tasks / tests / FA |
|---|---|---|---|---|---|---|
| plain | 5 | 18 | 0 | 5 | 0 | 3 / 7 / 2 |
| fault-template | 5 | 25 | 0 | 5 | 1 (4%) | 2 / 3 / 10 |
| template-placebo | 5 | 24 | 0 | 5 | 1 (4%) | 1 / 2 / 7 |

Per task (confirmed tests plain / fault-template / placebo): 36 3/5/5, 39 0/0/0, 56 1/5/3, 70 4/5/6, 132 5/6/5, 141 5/4/5.

## Signal rule: **no signal**
All three arms confirm the same 5 tasks with 0 false alarms (paired wins/losses 0/0 everywhere). Task 39 is missed by
every arm (v45: no functional exposure, likely time-limit only).

## Reading
- A stronger writer removes the gap Qwen had on these tasks: Sonnet plain 5/6 vs Qwen plain 3/6, and the FA problem
  disappears (0 vs 2–10). The concept is not what closes it.
- fault-template gives more confirmed tests than plain (25 vs 18) but placebo gives the same (24): the extra comes from
  seeing the template inputs/PUT outputs, not from the concept content (site, fault type, alternative).
- Only 1 confirmed test per arm reuses a tool input: Sonnet writes its own bug-revealing inputs (as Qwen in v34).
- Same picture as v28 (Codex on HumanEval: ceiling in every arm, no concept gain). For a strong model this concept is
  redundant; for a weak model (v34) it did not pass the placebo control. Recall of these LiveCodeBench problems cannot
  be excluded.
