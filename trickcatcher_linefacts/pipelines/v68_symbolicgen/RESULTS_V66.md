# v66 results — CrossHair backend, six-case CPU diagnostic (run 2, 2026-10-25)

Artifacts: `out/pipelines/v66_symbolicpath/cpu6_run2_20261025/case_*.json` (manifests pin sources/config/CrossHair 0.0.112/Z3 5.3.1.0; sandbox preflight True).
Source catalog only; no model, no hidden tests. v57's own interpreter built 0 verified inputs on all six.

| case | verified hyp / catalogued | distinct inputs | statuses | wall s |
|---|---|---|---|---|
| 61 | 20/48 | 10 | 26 cap/timeout, 2 bounded | 635 |
| 66 | 20/48 | 11 | 28 cap/timeout | 786 |
| 124 | 21/48 | 35 | 27 cap/timeout | 378 |
| 58 | 0/48 | 0 | 48 cap/timeout | 269 |
| 131 | 20/48 | 22 | 27 bounded, 1 cap | 627 |
| 85 | 3/28 | 6 | 25 cap/timeout | 523 |

**Decision (PREREG_V66): PASS — 5/6 cases ≥1 verified hypothesis** (84/268 = 31% of catalogued hypotheses).
0 symbolic witnesses rejected by native replay (all 2-process replays matched outputs, branches, site events, pre-states).
Families verified: OPERATOR 25, INDEX_SELECTION 24, LOOP_CARDINALITY 11, BOUNDARY 6, MULTIPLICITY 6, STATE_ACCUMULATION 5, VALUE 4, CALL 3.

Limits (do not over-read):
- PASS = "backend constructs real-source reach+infection+propagation witnesses". It is not concept efficacy, not bug detection.
- Many witnesses sit at domain edges the spec may forbid (`('f', '')`, `([],)`, `('i',)`, negative ints for case 85): spec validity is unknown.
- Case 58 (random shuffles, nested greedy loops over sorted keys): 17.8k paths explored, none reached a difference within 400 paths/20 s per hypothesis.
- 54% of hypotheses ended `unknown_timeout_or_cap`; exceptions (IndexError/TypeError) dominate failed paths.
- Run 1 crashed (harness, Amendment 2) and is excluded.

Next (needs its own PREREG): plug verified evidence into the v57 prompt controls (plain / concept / equal-evidence raw / inputs-only)
with a spec-validity filter, then a matched comparison against v31 fixed templates.
