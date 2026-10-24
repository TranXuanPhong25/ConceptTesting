# v53 pre-registration diagnostics ($0, CPU, existing v49/v52 data) — 2026-10-24 (Claude)

Asked before writing a v53 PREREG (user approved): with a strong writer the spec brute-force oracle is right on valid
inputs (v52), so (D1) can the remaining FA be removed from the spec alone, and (D2) are bug-exposing inputs small
enough for brute force? Scripts: `diag_d1_d2.py`, `diag_relations.py` (read-only over v49 records, v49 reference cache,
v52 exec cache). Output: `out/analysis/v53_validity_smallscope/diag_d1_d2.json`.

## D1 — FA inputs vs the spec's Constraints section
Every FA test whose input is invalid by the hidden reference contract, checked against constraints written in the
problem statement:
- **Sonnet defn (v52, 6 tasks): 56/56 FA caught** — 20 by numeric bounds parsed with `menu_fixed.constraints_report`
  (141: `4 <= len`), 36 by **relational** constraints the numeric parser does not handle (87 `nums1.length ==
  nums2.length` 11/11, 103 `k < nums.length` 11/11, 161 "same number of digits" 14/14). Confirmed tests removed: 0.
- Qwen defn (v49, 33 tasks): numeric bounds catch 20/47 invalid FA (all on 171); the rest are wrong-program FA anyway.
- The v48 universe is full of relation-violating inputs (87: 1114/1787, 103: 396/1063, 161: 342/609): the v41
  Hypothesis pool samples arguments independently.

## D2 — size of exposing inputs (size = elements in containers + string lengths)
- 23/33 tasks have exposing inputs in the universe; **21/23 have one of size ≤ 10, 15/23 of size ≤ 6**. Exceptions:
  141 (smallest 16; Sonnet defn times out on 62/62) and 56 (smallest 25).
- 10 tasks have no exposing input at all (8 R7 tasks + 73, 74): whether small exposing inputs exist is unknown — the
  universe has none; only small-scope generation can tell (fresh cohort per R7).

## Implication for v53
1. **Validity concept**: translate each spec constraint (including relations between arguments) into an executable
   predicate, verified on public inputs (B5/F1b step 4). On v52 this alone would make Sonnet's tests 62/62 correct.
   Prior art: v3m/v3m2/F1b (RBCTest-style), F4/F4b (concept-guided, worse with Qwen 7B); new: relational constraints
   and a strong writer.
2. **Small-scope generation**: bugs show up at size ≤ 10 on 21/23 reachable tasks, so exhaustive small valid inputs +
   the brute-force oracle should keep reach while avoiding abstention; it cannot help 141/56-type tasks.
