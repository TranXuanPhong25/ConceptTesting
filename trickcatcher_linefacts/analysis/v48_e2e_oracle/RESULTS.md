# v48 results: v47 concept picks end to end with the v46 TC-full variant oracle (vibepass_half, 33 PUTs)

Source: `out/analysis/v48_e2e_oracle/score.json` (frozen; execute + score 2026-10-23 21:47–22:06, rc 0, 0 reference
skips). Upstream: 310/310 v46 `tc` program records (478,840 input / 232,216 output tokens), v47 picks 33 + 33 calls.
PREREG: `PREREG.md` (amendments 1–2). Rule: GO iff `llm_code` confirmed tasks ≥ E[random3] + 3, ≥ E[menu_matched] + 3,
≥ E[pool_matched] + 3, ≥ E[kind_matched] + 2, ≥ heuristic + 2, and FA tests ≤ E[random3 FA].

## Headline (vote rule, cap 20 tests/task, 33 tasks)

| arm | confirmed tasks | correct assertions | tests | FA tests | FA tasks | precision |
|---|---|---|---|---|---|---|
| **llm_code** (v47 spec+code picks) | **6** | 50 | 202 | 152 | 10 | 0.25 |
| llm_spec (spec-only picks) | 6 | 53 | 189 | 136 | 9 | 0.28 |
| first3 | 6 | 62 | 186 | 124 | 10 | 0.33 |
| heuristic | 6 | 69 | 217 | 148 | 12 | 0.32 |
| all_menu (every menu input) | 6 | 67 | 287 | 220 | 12 | 0.23 |
| random3 (exact mean) | 6.37 | 64.60 | 210.97 | 146.37 | 10.65 | 0.31 |
| kind_matched | 6.22 | 65.74 | 225.41 | 159.67 | 10.62 | 0.29 |
| menu_matched | 6.38 | 61.09 | 220.80 | 159.71 | 11.51 | 0.28 |
| pool_matched (v41 pool, no concept) | 5.87 | 62.53 | 204.33 | 141.80 | 10.32 | 0.31 |

Consensus rule (all valid variants agree): every arm confirms 1 task.

**Verdict: NO-GO** (every check fails: 6 < 9.37 / 9.38 / 8.87 / 8.22 / 8; FA 152 > 146.37). `llm_code` and `all_menu`
confirm the same six tasks (36, 61, 121, 131, 132, 164), and random3 / pool_matched get the same six plus fractions of
3, 77, 89. Once a TC-full oracle sits behind the inputs, which concept instance is picked does not change the outcome.

## Failure decomposition (`all_menu`, one primary class per task)

| primary failure | tasks | ids |
|---|---|---|
| confirmed | 6 | 36, 61, 121, 131, 132, 164 |
| lost_to_cap (confirmable beyond 20 tests) | 3 | 3, 77, 89 |
| **b_common_mode** (all variants return the PUT's wrong value) | **9** | 65, 66, 85, 87, 96, 101, 124, 141, 161 |
| **e_no_valid_program** (0 of 10 variants pass the public tests) | **7** | 6, 56, 69, 73, 75, 103, 163 |
| a_no_exposing_input (no menu input exposes the bug) | 7 | 39, 48, 58, 70, 74, 168, 171 |
| d_vote_wrong_value | 1 | 46 |

Per exposing input (all_menu): vote right 765, common-mode 530, vote wrong value 377, variants failed 213.
`llm_code` inputs: 12 tasks without an exposing input (vs 7 for all_menu), common-mode 7, no valid program 7.

FA split (capped): `llm_code` put_right 83 (55%), invalid_input 58 (38%), wrong value 11; `all_menu` put_right 123,
invalid_input 77, wrong value 20. Most false alarms come from variants that disagree with a correct PUT, not from
invalid inputs.

## Reading
- The oracle, not input choice, is binding: 16/33 tasks fail at the oracle (9 common-mode + 7 without any valid
  variant) against 7 reach failures, and every selection arm lands at ≈ 6 tasks. This matches v47 (picks ≈ random) and
  closes concept-guided input selection on this cohort.
- Common-mode is the plurality failure, which is branch A of `PLAN_NEXT_v49.md` → v49 (definitional brute-force oracle,
  a different algorithm family from PUT-guided variants) is the registered follow-up; its execute/score runs next.
- FA is driven by wrong variants (put_right), so an input validator alone (branch B) would remove at most 38% of FA.
