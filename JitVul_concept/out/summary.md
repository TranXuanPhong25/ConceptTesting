# JitVul concept harness: results

| arm | pairs | P-C % | P-V % | P-B % | P-R % | P-C strict % | F1 | func acc % | flagged % | CWE match % | no tag % | truncated % | prompt chars | tokens in/out | cost $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 879 | 16.4 | 62.9 | 11.3 | 9.4 | 16.4 | 0.630 | 53.5 | 75.8 | 12.7 | 4.6 | 2.4 | 6251 | 3722960/4806849 | 13.134 |
| concept | 874 | 13.0 | 68.8 | 10.1 | 8.1 | 13.2 | 0.632 | 52.5 | 79.3 | 14.3 | 3.4 | 1.8 | 6717 | 3996629/4442955 | 12.306 |
| placebo | 879 | 13.0 | 67.9 | 10.5 | 8.6 | 13.0 | 0.628 | 52.2 | 78.7 | 13.2 | 3.8 | 1.9 | 6742 | 4020384/4583223 | 12.664 |
| callee_code | 8 | 37.5 | 25.0 | 12.5 | 25.0 | 37.5 | 0.588 | 56.2 | 56.2 | 25.0 | 11.1 | 11.1 | 7272 | 45345/52808 | 0.146 |
| ide | 7 | 42.9 | 42.9 | 14.3 | 0.0 | 42.9 | 0.750 | 71.4 | 64.3 | 14.3 | 5.9 | 5.9 | 9436 | 51374/44728 | 0.127 |

P-C = vulnerable flagged and patched not flagged; P-V = both flagged (always-vulnerable degenerate); P-B = neither flagged; P-R = both wrong. flagged = share of all functions labelled vulnerable.

## Exact McNemar on P-C (pairs answered in both arms)

| A vs B | subset | pairs | P-C A % | P-C B % | A only | B only | p (two-sided) |
|---|---|---|---|---|---|---|---|
| concept vs placebo | all | 874 | 13.0 | 12.9 | 79 | 78 | 1 |
| concept vs placebo | callee source on both sides | 530 | 12.1 | 12.1 | 45 | 45 | 1 |
| concept vs placebo | identical target bodies | 138 | 10.9 | 8.7 | 12 | 9 | 0.6636 |
| concept vs placebo | no return-type cue | 548 | 13.0 | 12.4 | 50 | 47 | 0.8392 |
| concept vs base | all | 874 | 13.0 | 16.4 | 75 | 104 | 0.03607 |
| concept vs base | callee source on both sides | 530 | 12.1 | 17.5 | 41 | 70 | 0.007585 |
| concept vs base | identical target bodies | 138 | 10.9 | 7.2 | 12 | 7 | 0.3593 |
| concept vs base | no return-type cue | 548 | 13.0 | 15.5 | 43 | 57 | 0.1933 |
| callee_code vs base | all | 8 | 37.5 | 12.5 | 3 | 1 | 0.625 |
| callee_code vs base | callee source on both sides | 5 | 40.0 | 0.0 | 2 | 0 | 0.5 |
| callee_code vs base | no return-type cue | 3 | 66.7 | 0.0 | 2 | 0 | 0.5 |
| placebo vs base | all | 879 | 13.0 | 16.4 | 81 | 111 | 0.03608 |
| placebo vs base | callee source on both sides | 530 | 12.1 | 17.5 | 45 | 74 | 0.009966 |
| placebo vs base | identical target bodies | 142 | 8.5 | 7.7 | 11 | 10 | 1 |
| placebo vs base | no return-type cue | 552 | 12.3 | 15.6 | 48 | 66 | 0.1109 |
| concept vs ide | all | 7 | 0.0 | 42.9 | 0 | 3 | 0.25 |
| concept vs ide | callee source on both sides | 5 | 0.0 | 40.0 | 0 | 2 | 0.5 |
| concept vs ide | no return-type cue | 3 | 0.0 | 66.7 | 0 | 2 | 0.5 |
| ide vs base | all | 7 | 42.9 | 14.3 | 3 | 1 | 0.625 |
| ide vs base | callee source on both sides | 5 | 40.0 | 0.0 | 2 | 0 | 0.5 |
| ide vs base | no return-type cue | 3 | 66.7 | 0.0 | 2 | 0 | 0.5 |

base P-C by return-type cue: no cue 86/552 (15.6%), cue (vulnerable body lacks the return-type line) 58/327 (17.7%).

ide block empty (no analyzer warning on target or listed callees): 512/1758 functions (29.1%), 244/879 pairs empty on both sides.
