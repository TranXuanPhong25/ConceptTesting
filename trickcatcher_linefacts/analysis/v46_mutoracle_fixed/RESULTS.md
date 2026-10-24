# v46 results: mutant-concept oracle with program variants and the repaired judge (2026-10-24)

PREREG + Amendment 1 (787ade3, fd7c45b). Generation: 2441/2441 Qwen2.5-Coder-32B calls (620 TC + 1821 judge),
finished 2026-10-24 20:04. The endpoint served one request at a time and went offline 3 times. The client went from 8
workers to 1 worker (f000e3d, 9e3f9e9; same messages/params/seeds, cache digests unchanged). Score:
`out/analysis/v46_mutoracle_fixed/score.json`.

**Verdict: close.** Neither concept pair meets the registered rule (concept arm ≥ 8 confirmed tasks, precision ≥ 0.5,
≥ and ≤ its counterparts, strictly better, ≥ 2 concept-only tasks).

| arm | confirmed tasks | tests | true | FA | precision | notes |
|---|---|---|---|---|---|---|
| `dpp` (v39 programs, context) | 7 | 129 | 62 | 67 | .48 | valid 75 programs; ≥1 valid on 16 tasks, ≥3 on 9 |
| `tc` | 5 | 136 | 50 | 86 | .37 | valid 198; consensus 1 task |
| `tc_concept` | 2 | 46 | 12 | 34 | .26 | valid 211; consensus 1 task |
| judge `binary` | 11 | 223 | 32 | 191 | .14 | choices put 271 / mutant 136 / neither 87 / invalid 92 / unparsed 21 |
| judge `code` | 10 | 201 | 29 | 172 | .14 | put 311 / mutant 120 / neither 82 / invalid 82 / unparsed 12 |
| judge `concept` | 10 | 216 | 28 | 188 | .13 | put 300 / mutant 121 / neither 98 / invalid 81 / unparsed 7 |

Confirmed tasks: `tc` 36, 61, 121, 131, 132; `tc_concept` 36, 131; judge `code` = judge `concept` = 36, 46, 61, 66,
85, 121, 131, 132, 163, 164 (`binary` also has 141). All of them are in the v42 D1 set (ceiling 15). Task 75 overflowed
the 8192 context in both TC arms (10 + 10 records, no programs).

## Reading
- **Program oracle + concept: worse.** `tc_concept` has more valid variants than `tc` (211 vs 198) but emits about a
  third of the tests (46 vs 136): with the fault concepts shown, Qwen's variants keep the PUT behaviour on the
  question inputs more often (more common-mode), so 3 tasks are lost.
- **Repaired judge: reach yes, precision no.** Without the "unsure" exit and with 2048 tokens, the judge confirms 10–11
  tasks (v45: 2/0/1). But precision is .13–.14, about 190 FA tests: on PUT-right questions the judge often picks the
  mutant, `neither` or `invalid`. The concept arm gives exactly the same task set as `code`, so the concept adds
  nothing.
- **What binds is the model, not the concept** (v54, same material, tasks where every v48 Qwen TC arm failed):
  - Qwen `tc` with k = 10 confirms 0/6 tasks. 47 of its variants are valid, but only 5 differ from the PUT on any
    question input.
  - Sonnet `tc` with k = 3 confirms 6/6 tasks, with 18/18 programs right, with or without the concept.
- Stated deviations as in Amendment 1. DPP validity is not comparable with v39 (the preamble is prepended).

With v42 (selection no-go), this closes the mutant concept on both the selection side and the oracle side for Qwen.
