# v56 fresh LiveCodeBench — pipeline-arm results (2026-10-25)

Frozen runner `arms.py` (sha256 289570e6ad1ab493…), PREREG Amendments 4–8; no post-outcome change.
Metrics: `out/v56_lcb_fresh/arms/metrics.json` (sha256 aa123cb8c238c2fb…, git-ignored).
Writer Qwen2.5-Coder-32B-Instruct-AWQ, 121/121 calls ok (0 missing). Scoring reference: Codex, certified 11/11
on all public+hidden tests; validator certified 10/11 (3784: 3 Codex calls failed rc=1/turn.failed, no answer;
cap reached, not resent → validity = "reference does not raise" for 3784).

## Totals (11 tasks, reach 11/11)

| arm | confirmed tasks | tests | confirmed tests | precision | FA invalid / wrong / unknown | valid programs (tasks) |
|---|---|---|---|---|---|---|
| defn  | 5 | 61 | 56 | .918 | 0 / 5 / 0  | 20 (7) |
| brute | 6 | 96 | 49 | .510 | 0 / 47 / 0 | 23 (8) |
| plain | 4 | 61 | 25 | .410 | 0 / 36 / 0 | 18 (6) |

## Decisions (GO iff tasks A ≥ B+2, paired wins > losses, FA A ≤ B)

| comparison | tasks | wins–losses | sign p | FA | verdict |
|---|---|---|---|---|---|
| concept: defn vs brute (primary) | 5 vs 6 | 0–1 (3776) | 1.00 | 5 vs 47 | NO-GO |
| family: brute vs plain | 6 vs 4 | 4–2 | .69 | 47 vs 36 | NO-GO |
| defn vs plain | 5 vs 4 | 3–2 | 1.00 | 5 vs 36 | NO-GO |

Per task (confirmed): 3750 all; 3784 all; 3788 defn+brute; 3562 defn (20) + brute (1, 19 FA); 3634 defn+brute (1 each);
3776 brute only (18; defn/plain 0 valid-finishing); 3705, 3770 plain only; 3771, 3677, 3720 none.

## Mechanism notes (descriptive, not pre-registered tests)

- Concept effect on tasks not replicated (fresh cohort, Qwen). The defn advantage is precision only: 5 vs 47 FA,
  concentrated in 3562 (brute 19 FA), 3784 (12), 3771 (11, defn no_quorum/abstains). Partly abstention, partly a
  real oracle win on 3562 (defn 20 confirmed vs brute 1).
- Oracle still binds: 3677 and 3720 have exposing inputs in the pool (110, 5) but ~0 valid programs in every arm.
- Qwen v53 input generator failed on 4/11 (3705/3770/3771 MemoryError: exhaustive itertools lists materialised before
  slicing; 3634 TypeError) → those tasks used public + tool inputs only. Writer failure, not harness.
- v49 family effect (brute ≈ 2× plain) is directionally present (4–2) but below the rule; v64 Haiku reversed it.
- 11 tasks is underpowered: nulls are "not replicated", not evidence of no effect.
