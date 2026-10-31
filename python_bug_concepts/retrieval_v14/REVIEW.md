# Independent pre-outcome review

Reviewer: fresh-context read-only agent `vr14_review`, 2026-10-30. Reviewed source,
protocol, authored fixtures, cohort preparation and engineering tests; no diagnostic
outcomes, fixture/census retrieval runs, model calls or target execution.

Initial verdict: do not freeze/run until six groups are repaired:

1. Loop-carried writes incorrectly preserved a search-to-index edge.
2. Comprehension shadows inherited an outer parameter's annotation.
3. Subscript stores were treated as reads; unknown mappings as sequences.
4. Unknown/non-string `.replace` receivers received text semantics.
5. Counter's mapping overload was treated as iterable occurrence aggregation.
6. Exact-binding scoring did not compare relations and source evidence.

All six addressed prospectively in PREREG Amendment 1. Initial 12 engineering
tests passed; expanded suite has 19 tests. Final independent review and approval
must match the exact `FREEZE.json` digest before diagnostic execution.

Second review verified all 15 frozen files and 19 tests, but rejected initial
digest `e69796917d3f12c80b22395a0b04c49ad0670d3ff4912c80e5d0f9c7f14654b0`:
Python 3.11 `TryStar` allowed a handler assignment to look dominating after join.
Amendment 2 adds this boundary, checks definition context, and records Counter's
specific domain assumption. Expanded suite: 20 tests. No outcomes read.

Final independent approval: `ce18788e8288fade79f0c53ac3a4b68a2d1241c3e9bab29e379245bf9372d09c`; all 15 hashes and 20 tests verified, no remaining must-fix in scope. Approval covers only the preregistered source-only diagnostic.

Post-outcome read-only audit passed: freeze/prediction/result seals, fixture table,
census counts and breakdowns, paired coverage, no relation/cue output, identical
structured queries, maximum three kinds/task and all three walkthrough copies
match saved artifacts. No numeric error or overclaim requiring repair. Reviewer
did not rerun extraction, diagnostic or target execution. Delivery check separately
validated 1,593 source evidence spans/expressions against the frozen inputs.
