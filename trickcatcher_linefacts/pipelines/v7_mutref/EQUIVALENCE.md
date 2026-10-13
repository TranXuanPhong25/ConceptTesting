# v7 equivalence results

All tests ran on CPU, offline. No endpoint was called. The original modules, vendor code and historical outputs were not edited. Cached clients raise on a missing request and do not read credentials.

## a: bundles

Both `tasks_v7_all.json` and `tasks_v7hyb_v4.json` are exactly equal after JSON loading: 133/133 tasks each, zero differences. The bundles were reconstructed from the B5 preconditions, v4c strategies, v6 facts and v7 spec facts, rather than copied from the expected bundles.

## b: requests and generation

113 dev + 20 pilot tasks × 7 arms × K=3 = 2,793 logical first requests: 2,793 cache hits, 1,995 distinct keys, zero misses and zero recorded-key mismatches. Messages, seeds, model and sampling settings all contribute to the original SHA256 request key.

For toolinput task 63 samples 1 and 2, the historical classifier failed with `sandbox total timeout`, selecting no inputs. Fresh classification succeeds. The first-request test explicitly replays those two recorded errors through the copied fallback and reports the two fresh-versus-recorded differences; it does not claim the wall-clock failures recur. The literal stage-0 assertion requests have no such dependency.

End-to-end replay: tasks 0, 4 and 16, K=1, all seven arms; 21/21 completed rows, 36 cached requests, zero misses, zero differences in assertions, selected inputs, round-1 assertions, strategy-request counts or input/stage summaries. Full K=3 round-2 regeneration was not attempted.

Hypothesis 6.169.0 automatically mines local source literals. Added packaging literals initially changed string draws despite identical jobs/seeds. `hypothesis_constants.json` pins the original 11-module pool, restored by `hypothesis_replay.py` using the same sorted sets as Hypothesis. The previously failing task-16 draw result then matched exactly. The pool was checked against the historical worker’s constants snapshots; the original modules are not imported at runtime.

## c: fresh evaluation and oracle execution

Evaluation recomputed all 2,793 rows: 2,764 exact matches, 29 different rows, 72 different fields. All differences fall into the following categories; budgets and original PUTs were preserved.

| Task | Different rows | Different fields | Cause |
| --- | ---: | ---: | --- |
| 34 | 14 | 38 | `unique` returns `list(set(l))`. Randomized string hash order changes 19 assertion PUT statuses and 19 input bug labels. The run did not persist its hash state. |
| 58 | 1 | 1 | `common` returns a list from a set intersection. String order changes one assertion PUT status. |
| 83 | 13 | 30 | The exhaustive count for n=7 straddles the five-second assertion deadline: four PUT statuses change; 13 related input records acquire `trace_skipped` and change `put_status` from deterministic step-budget `timeout` to wall-clock `Timeout`. |
| 160 | 1 | 3 | The enormous exponent expression reaches the memory limit instead of the historical timeout. Two diagnostic statuses and one input canonical status change. |

Oracle collection matches exactly: 133 tasks, 13,282 distinct calls. B1/ref/post/judge response lists are exactly equal: 4,152 / 1,330 / 665 / 22 responses. The full recomputation replayed 6,169 requests with zero misses. The final resume replayed 6,147 B1/ref/post requests and reused its already verified 22 cached judge decisions, again with zero misses.

All 133 oracle execution tasks were recomputed. Differences are confined to four tasks:

| Task | Different execution fields | Cause |
| --- | ---: | --- |
| 34 | 63 | String set order changes oracle agreement, comparison with PUT output and related emission fields. |
| 58 | 9 | String set-intersection order changes comparison/agreement fields. |
| 59 | 8 | The three-second program deadline changes whether a canonical factorization finishes for 9,699,690 and whether DPP programs agree for 31,398,446. |
| 160 | 7 | Huge exponentiation straddles execution/postcondition deadlines, changing canonical status, TC emission and one B1-first postcondition decision. |

The fresh oracle report matches 43/51 lines; eight lines differ: 5, 13, 14, 16, 17, 18, 19, 50. Dev concept-hybrid ref/ref+judge detecting samples/K are 66.7 versus historical 67.0; full is 65.3 versus 65.7. Any-of-K counts remain 78 for ref/ref+judge and 77 for full. These differences were not hidden by copying historical execution results into the fresh computation.

The copied scorer, when supplied the identical historical CPU observations and cached judge decisions, reproduces **all 51/51 report lines exactly**. The causal check substitutes each group of freshly recomputed observations separately:

| Observation group | Report lines changed |
| --- | --- |
| evaluation_set_order | 5 |
| evaluation_deadline | none |
| evaluation_memory | none |
| oracle_set_order | 5, 13, 14, 16, 17, 18, 19 |
| oracle_deadline | 13, 14, 18, 50 |

Substituting all four evaluation tasks and all four oracle tasks reproduces the entire fresh report exactly. Thus every changed report line is accounted for by the recorded set-order/deadline/memory differences, and the scoring refactor itself matches the historical scorer. No PUTs, budgets or expected labels were changed to force equality.

Complete field paths, values and report-line comparisons:

- [Final test results](../../out/pipelines/v7/humaneval/equivalence/equivalence.json)
- [All 72 evaluation field differences and causal report checks](../../out/pipelines/v7/humaneval/equivalence/difference_causes.json)
- [First full CPU recomputation, including all 6,169 request replays](../../out/pipelines/v7/humaneval/equivalence/first_full_equivalence.json)
- [Fresh oracle report](../../out/pipelines/v7/humaneval/equivalence/oracle/report.txt)

The strict-equality suite exits 1 because c has the documented environment-dependent differences. The causal explanation check exits 0. New run manifests/IDs intentionally reflect this package’s sources, config and VERSION; generation output equivalence compares behavior rather than those new provenance identifiers.

## Optional strict and held-out checks

The strict construction on the run of record exactly matches all 2,793 historical v8-strict generation rows. It retains selected round-2 calls; placeholders match the original construction (44 concept-hybrid, 129 plain-hybrid, 4 placebo-hybrid). The held-out adapter resolves the 12 real-bug MBPP+ tasks, their heldout split and all six configured dataset paths; no MBPP+ mining or model calls were performed.

## Commands actually run

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v7.test_equivalence --checks c
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v7.test_equivalence --checks a,b,c --resume
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v7.explain_differences
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v7.run mine --reuse-from trickcatcher_linefacts/out
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v7.run facts
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v7.run specfacts
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v7.run bundle
```

The strict check used the same `strict_stage(Layout(root=paths.DATA_OUT / 'equivalence'))` callable as the CLI. Fresh test runs without `--resume` recompute all CPU observations; they may differ again at the documented nondeterministic boundaries.
