# v49 results: definitional-concept brute-force oracle vs brute vs plain spec programs vs TC variants (33 PUTs)

Source: `out/analysis/v49_defn_oracle/score.json` (frozen, sha256 d9b0e216…; execute 22:06–22:17, score 22:17–23:15,
rc 0, 0 reference skips) and `plan_v50_rules.json`. 495/495 Qwen2.5-Coder-32B-AWQ calls (all `stop`; the last 57 on a
second endpoint with the same weights, see CHANGELOG), 5 programs per arm per task; `tc` = the 10 v46 variants.
PREREG: `PREREG.md` (amendments 1–2). Decisive inputs = v48 universe (menu ∪ ≤ 600 v41 pool inputs per task).

## Headline (decisive inputs, primary quorum rule: ≥ 2 and > V/2 valid programs agree on a value ≠ PUT; cap 20)

| family | calls/task | valid programs (tasks ≥ 2) | confirmed tasks | correct | tests | FA tests | precision |
|---|---|---|---|---|---|---|---|
| **defn** (ENUMERATE/CHECK/AGGREGATE + brute force) | 5 | 93/165 (23) | **12** | 207 | 352 | 145 | 0.59 |
| brute (same, no concept headings) | 5 | 78/165 (18) | 10 | 166 | 266 | 100 | 0.62 |
| plain ("correct implementation") | 5 | 38/165 (10) | 5 | 79 | 165 | 86 | 0.48 |
| tc (v46 TC-full variants) | 10 | 198/330 (25) | 1 | 20 | 74 | 54 | 0.27 |
| tc, its native tc_full rule (report) | 10 | — | 7 | 66 | 287 | 221 | 0.23 |

`llm_code` inputs (report only): defn 9, brute 9, plain 3, tc 1 confirmed tasks.

## Registered decisions
- **Primary (concept effect, defn vs brute): NO-GO.** Margin 2 (< 3; tasks 103, 124), 2 problems (< 3), FA 145 > 100.
  Paired on the tasks where both have ≥ 2 valid programs: defn 10 / brute 10 tasks, FA 99 / 100 — identical. The +2
  comes only from **valid-program yield**: the concept headings give 93 vs 78 valid programs and 23 vs 18 eligible tasks
  (103: 2 vs 0 valid; 124: 4 vs 1).
- Manual audit of the defn-only wins (registered): both pass. 103: the majority programs enumerate every sequence of
  operations (comment says "at most k", code does exactly k — equivalent, since an AND merge never raises the OR); 124:
  `combinations` over index subsequences, CHECK/AGGREGATE match the statement.
- **Secondary (family effect, brute vs plain): NO-GO** only on FA (margin 5 on 7 problems; FA 100 > 86).
- defn vs tc (report only): margin 11 on 11 problems, FA 145 > 54 (tc emits few tests under the quorum rule).
- **v50 branch rules (`plan_rules.py`, fixed before output): R7 fired** — plurality miss class among defn-eligible tasks
  is `a_no_exposing_input` (8 tasks: 6, 39, 48, 58, 69, 70, 168, 171); others: confirmed 12, vote wrong value 2 (46, 77),
  lost to cap 1. R1/R1b/R6/R3/R5 false (R3: 20/24 capable problems, wrong-value share 0.32; R5: invalid 47 of 145 FA).

## Diagnostics
- Common-mode share on exposing inputs (all finishing valid programs equal the PUT): defn 3.0%, brute 4.9%, plain 0.5%,
  **tc 28.2%** — the PUT-guided variants copy the bug; the spec-only brute-force family does not.
- Exposing inputs with no finishing program: defn 298/1889, brute 352, plain 1410, tc 213; abstention rate defn 0.17.
- defn FA split (eligible tasks): PUT right 82, invalid input 47, wrong value 16.
- Every defn program carries the three concept headings (165/165); no `length` finishes in any arm.

## Reading
- The binding result is a **family effect, not a concept effect**: brute-force spec programs written without the PUT
  (defn/brute) confirm 10–12 tasks at 5 calls/task with precision ≈ 0.6, against TC-full's 7 tasks (native rule,
  precision 0.23, FA 221) at 10 calls, and they remove common-mode (3–5% vs 28%). This is report-only — the registered
  family comparisons fail on the absolute FA count, which penalises the family that emits more tests; R6 therefore did
  not fire (a gap in the rule, noted, not re-scored).
- The definitional concept helps only by making more programs valid; given valid programs it changes nothing.
- Per the registered rules (R7): no new input selection on this cohort; small-scope exhaustion only on a fresh cohort.
  The 8 R7 tasks have ≥ 2 valid defn programs but no exposing input in the universe (48 and 168 are v47's large-value
  tasks), so the next lever is inputs the brute-force oracle can judge, tested on fresh tasks.
