# v64 results: plain-implementation and brute oracles vs defn, Claude Haiku writer (dev, 33 tasks / 24 problems)

Source: `out/analysis/v64_haiku_plainoracle/score.json`. 144 new Haiku answers (18 subagents) + v55h defn/open/plain
answers byte-identical (defn per-task metrics reproduce v55h exactly). k = 3, primary quorum, cap 20, same inputs and
filter for every arm. PREREG + Amendment 1 committed before execution (f150d45, c418e3a).

| arm | valid programs | confirmed tasks /33 | tests | FA (all wrong value) | precision | exposing inputs with no vote | non-finishing program calls |
|---|---|---|---|---|---|---|---|
| `defn` (v49 headings + brute force) | 99 | 21 | 411 | 0 | 1.00 | 1297 / 5155 | 15766 |
| `brute` (brute force, no headings) | 99 | 21 | 417 | 0 | 1.00 | 828 / 5155 | 13639 |
| `plainimpl` ("write a correct implementation") | 98 | **25** | 511 | 19 (4 tasks, 3 problems) | 0.96 | 6 / 5155 | 0 |

Paired (confirmed task): defn vs plainimpl 0 wins / 4 losses (61, 65, 66 = one problem `minCostGoodCaption`; 141 =
`maxWeight`); brute vs plainimpl the same 0/4; defn vs brute 0/0. Common-mode problems 0 in every arm.
plainimpl FA tasks: 36 (2), 87 (5) — both also confirmed — and 69, 70 (6 each, one problem `minDifference`, 0 confirmed).

**Registered decision: inconclusive.** Net defn − plainimpl = −4 (not ≥ 2, so the family effect does not hold), but
plainimpl precision is .037 below defn (> .02), so the "weak-writer artefact" branch does not apply either.

## Reading
- The v49 direction **reverses** with a stronger writer: with Qwen-32B the brute-force families beat plain
  implementation (12/10 vs 5), with Haiku plain implementation confirms 4 more tasks than both brute-force families.
  v49's gap came from plain-implementation yield of a weak writer (38/165 valid); Haiku's plain programs are valid
  (98/99) and fast.
- The 4 losses are **abstention**, not reach: on those tasks defn has 3 valid programs but none finishes on any exposing
  input (145, 28, 144, 91 exposing inputs, all no vote), because brute force over 26^n strings / all pizza groupings
  is too slow. So part of v55h's "unreached" list (61/65/66/141) was oracle abstention.
- The price is precision: plain implementations are optimised algorithms that can be wrong (heuristic minDifference
  gives 12 wrong-value tests on 69/70), while brute force is slow but literal (0 FA).
- Headings add nothing for Haiku (defn = brute on every task), as for Qwen (v49) and Sonnet (v52).
- Consequence for the thesis: "definitional / brute-force oracle family is better" is **not robust across writer
  strength**. It is a precision-vs-abstention trade-off, not a dominance. v56 should not be spent confirming the
  family effect as stated.
