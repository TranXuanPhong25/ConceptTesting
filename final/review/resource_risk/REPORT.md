# Prospective resource-risk review — 2026-11-04

Reviewed pending base-pass PUTs: 181. Identified17high-risk programs for exclusion from preparation, prompts and evaluation.
No PUT execution, reference comparison, new model call or regenerated program used in this review.

| Task | PUT IDs | Risk |
|---|---|---|
| 144 | 9 | Prime-factor trial division on unbounded integer components parsed from fraction strings. |
| 147 | 1, 2, 3, 5, 6, 7, 9 | Input n controls sequence construction and linear/cubic traversal; spec has no upper n bound. |
| 150 | 0, 2, 3, 4, 6, 7, 8, 9 | Input n controls trial-divisor search or sieve allocation; spec has no finite upper n bound. |
| 160 | 6 | eval of user-derived arithmetic permits variable exponentiation and exponent towers with very large integers. |

Keep constant-time/formula implementations147/0,4,8 and modular primality150/5. Recursive150/1 may hit recursion limits but does not have the same unbounded loop; retain with existing sandbox limits.

Task156has explicit1..1000domain; task159has0..1000bounds. String/list traversals have the existing literal-size cap. These are not proofs that all mutants are cheap.

User explicitly selected exclusion from BOTH preparation and evaluation. Excluded PUTs must also be omitted from shared generation prompts. Retain the original frozen cohort file; record the effective exclusions and revised evaluated denominator. Existing completed records are not overwritten; all17selected PUTs have no completed preparation/input record.

This prospective user-authorized adaptation is not evidence that a program is incorrect. Report skipped count separately; detailed census remains local in run output.
