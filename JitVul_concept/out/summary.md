# JitVul concept harness: results

| arm | pairs | P-C % | P-V % | P-B % | P-R % | P-C strict % | F1 | func acc % | flagged % | CWE match % | no tag % | truncated % | prompt chars | tokens in/out | cost $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 5 | 0.0 | 80.0 | 20.0 | 0.0 | 0.0 | 0.615 | 50.0 | 80.0 | 20.0 | 0.0 | 0.0 | 5262 | 18775/24308 | 0.066 |
| concept | 5 | 0.0 | 80.0 | 20.0 | 0.0 | 0.0 | 0.615 | 50.0 | 80.0 | 40.0 | 0.0 | 0.0 | 5848 | 20810/21453 | 0.060 |
| placebo | 5 | 20.0 | 60.0 | 20.0 | 0.0 | 20.0 | 0.667 | 60.0 | 70.0 | 20.0 | 0.0 | 0.0 | 5827 | 20668/19173 | 0.054 |
| callee_code | 5 | 40.0 | 40.0 | 20.0 | 0.0 | 40.0 | 0.727 | 70.0 | 60.0 | 20.0 | 10.0 | 10.0 | 5848 | 20937/30784 | 0.083 |
| ide | 5 | 40.0 | 40.0 | 20.0 | 0.0 | 40.0 | 0.727 | 70.0 | 60.0 | 20.0 | 10.0 | 10.0 | 5793 | 20271/32992 | 0.089 |

P-C = vulnerable flagged and patched not flagged; P-V = both flagged (always-vulnerable degenerate); P-B = neither flagged; P-R = both wrong. flagged = share of all functions labelled vulnerable.

## Exact McNemar on P-C (pairs answered in both arms)

| A vs B | subset | pairs | P-C A % | P-C B % | A only | B only | p (two-sided) |
|---|---|---|---|---|---|---|---|
| concept vs placebo | all | 5 | 0.0 | 20.0 | 0 | 1 | 1 |
| concept vs placebo | callee source on both sides | 5 | 0.0 | 20.0 | 0 | 1 | 1 |
| concept vs placebo | no return-type cue | 2 | 0.0 | 50.0 | 0 | 1 | 1 |
| concept vs base | all | 5 | 0.0 | 0.0 | 0 | 0 | 1 |
| concept vs base | callee source on both sides | 5 | 0.0 | 0.0 | 0 | 0 | 1 |
| concept vs base | no return-type cue | 2 | 0.0 | 0.0 | 0 | 0 | 1 |
| callee_code vs base | all | 5 | 40.0 | 0.0 | 2 | 0 | 0.5 |
| callee_code vs base | callee source on both sides | 5 | 40.0 | 0.0 | 2 | 0 | 0.5 |
| callee_code vs base | no return-type cue | 2 | 100.0 | 0.0 | 2 | 0 | 0.5 |
| placebo vs base | all | 5 | 20.0 | 0.0 | 1 | 0 | 1 |
| placebo vs base | callee source on both sides | 5 | 20.0 | 0.0 | 1 | 0 | 1 |
| placebo vs base | no return-type cue | 2 | 50.0 | 0.0 | 1 | 0 | 1 |
| concept vs ide | all | 5 | 0.0 | 40.0 | 0 | 2 | 0.5 |
| concept vs ide | callee source on both sides | 5 | 0.0 | 40.0 | 0 | 2 | 0.5 |
| concept vs ide | no return-type cue | 2 | 0.0 | 50.0 | 0 | 1 | 1 |
| ide vs base | all | 5 | 40.0 | 0.0 | 2 | 0 | 0.5 |
| ide vs base | callee source on both sides | 5 | 40.0 | 0.0 | 2 | 0 | 0.5 |
| ide vs base | no return-type cue | 2 | 50.0 | 0.0 | 1 | 0 | 1 |

base P-C by return-type cue: no cue 0/2 (0.0%), cue (vulnerable body lacks the return-type line) 0/3 (0.0%).

ide block empty (no analyzer warning on target or listed callees): 512/1758 functions (29.1%), 244/879 pairs empty on both sides.
