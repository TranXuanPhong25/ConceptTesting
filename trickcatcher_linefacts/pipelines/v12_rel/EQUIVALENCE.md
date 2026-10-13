# v11_fair offline CPU equivalence

All verification ran on CPU, offline, inside this folder. No network or LLM endpoint was called; fake clients and read-only response caches supplied responses, and offline cache misses raise. No secrets or endpoint configuration were needed. Config defaults enable all four fixes; the compatibility checks override all four to false and propagate those flags to workers.

## All four flags off

- Both bundles rebuilt from mining/facts: **133/133 tasks identical** in the standard bundle and **133/133 identical** in the hybrid bundle.
- **2,793/2,793 logical first requests** (133 tasks × 7 arms × K=3) hit cache, **1,995 distinct cache keys**, zero cache misses and zero recorded-key mismatches.
- Fresh generation replay: tasks **0, 4, 16**, K=1, all seven arms; **21/21 rows**, **36 cached requests**, zero differences in assertions, selected inputs, round-1 assertions, strategy-request counts, input summaries or stage summaries.
- Oracle report: **51/51 lines byte-identical** on identical historical CPU observations and recorded cached judge decisions. Both real evaluation report implementations also produce **identical printed reports and identical returned metrics** from the full 2,793-row historical evaluation.

Task 63 toolinput samples 1 and 2 historically had classifier timeouts. As in the v7 suite, first-request verification explicitly replays those two recorded fallback errors after separately noting that fresh classification succeeds. It does not claim the historical wall-clock failures recur.

New VERSION, source provenance, run IDs and local output paths intentionally differ. The all-off equivalence is behavioral. Full K=3 round-2 regeneration and optional full fresh execution check `c` were not run. The known v7 set-order, timeout and memory boundary differences make fresh CPU execution a different question from comparator/aggregation equivalence; the report comparison supplies identical observations to the actual aggregation code. No historical output file is modified: the v7 evaluation report's metrics write is suppressed by the harness.

## Fairness tests

**18/18 tests pass**. Fake-client generation integration checks cover empty strict selections and exhausted assertion slots, exact selected-input ordering and prompt scope, rejection of extra PUT calls, missing expected-value placeholders, matching placebo counts including concept retries and already-covered/no placebo hints, large hint pools, the call cap, the twenty-first assertion and drop accounting, and legacy output shape. Scorer checks cover recursive floats, task tolerance metadata, timeout/exception distinctions, chained comparisons without duplicate evaluation, argument construction, metrics denominators including invalid inputs, and actual network-isolated evaluation/oracle workers with task atol.

Public comparison functions are `scorer.output_equal` and `scorer.outcome_equal`. Every path reads atol from the configured oracle dataset through `scorer.task_atols`; the older evaluation dataset has no atol. Relative tolerance is 1e-6. Only output comparisons receive tolerance: argument construction retains Python semantics.

## Artifacts and commands

- [Compatibility results](out/humaneval/equivalence_final/equivalence.json)
- [Exact legacy oracle report](out/humaneval/equivalence_final/legacy_report/report.txt)
- [Exact evaluation report](out/humaneval/equivalence_final/legacy_report/evaluation_report.txt)
- [Scorer audit summary](out/humaneval/scorer_equivalence/equivalence.json)
- [Every changed assertion, with compared values and atol](out/humaneval/scorer_equivalence/scorer_changes.json)
- [Unit test results](out/unit_tests/results.json) and [log](out/unit_tests/log.txt)

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest trickcatcher_linefacts.pipelines.v11_fair.test_fair
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v11_fair.test_equivalence --checks a,b,l --output-name equivalence_final
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v11_fair.test_equivalence --checks b,l --resume --output-name equivalence_final
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v11_fair.test_equivalence --checks d --workers 8 --output-name scorer_equivalence
```

The unit runner was also executed with its real output captured under `out/unit_tests/`. Earlier tests used `--output-name equivalence`; final results above reflect the final implementation. The assertion audit executes all 29,224 assertions (15,026 unique sources across tasks), scores both versions against the same captured CPU outcomes, and asserts that every changed comparison involves a float. It is not a comparison against historical nondeterministic hash/deadline state.

## Shared scorer only: complete assertion verdict audit

Every assertion in all cached generation rows was scored with v7 equality and the shared scorer on identical CPU observations. Only `shared_scorer` was enabled. This isolates scoring from nondeterministic set order and deadlines.

{"all_changes_involve_float": true, "assertions": 29224, "changed_assertions": 64, "rows": 2793, "tasks": 133, "unique_assertions": 15026}

| Task | Arm | Sample | Assertion index (0-based) | Assertion | v7 → shared (canonical, PUT) |
| --- | --- | --- | --- | --- | --- |
| 2 | plain | 0 | 2 | `assert truncate_number(100.1) == 0.1` | put: fail → ok, canon: fail → ok |
| 2 | plain | 0 | 5 | `assert truncate_number(1.0000000001) == 1e-10` | put: fail → ok, canon: fail → ok |
| 2 | plain | 0 | 7 | `assert truncate_number(123456789.12345679) == 0.123456789` | put: fail → ok, canon: fail → ok |
| 2 | concept | 0 | 5 | `assert truncate_number(1.001) == 0.001` | put: fail → ok, canon: fail → ok |
| 2 | concept | 0 | 7 | `assert truncate_number(123.0001) == 0.0001` | put: fail → ok, canon: fail → ok |
| 2 | concept | 0 | 8 | `assert truncate_number(123.9999) == 0.9999` | put: fail → ok, canon: fail → ok |
| 2 | toolinput | 0 | 4 | `assert truncate_number(999.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | toolinput | 0 | 7 | `assert truncate_number(2.1) == 0.1` | put: fail → ok, canon: fail → ok |
| 2 | toolinput | 0 | 8 | `assert truncate_number(2.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | toolinput | 0 | 9 | `assert truncate_number(10.01) == 0.01` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 0 | 0 | `assert truncate_number(49.14528996107593) == 0.14528996107593` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 0 | 1 | `assert truncate_number(92.2778021929504) == 0.2778021929504` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 0 | 2 | `assert truncate_number(4.2553838010983895) == 0.2553838010983895` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 0 | 8 | `assert truncate_number(123456789.12345679) == 0.123456789` | put: fail → ok, canon: fail → ok |
| 2 | concept-hybrid | 0 | 5 | `assert truncate_number(1.001) == 0.001` | put: fail → ok, canon: fail → ok |
| 2 | concept-hybrid | 0 | 7 | `assert truncate_number(123.0001) == 0.0001` | put: fail → ok, canon: fail → ok |
| 2 | concept-hybrid | 0 | 8 | `assert truncate_number(123.9999) == 0.9999` | put: fail → ok, canon: fail → ok |
| 2 | placebo-hybrid | 0 | 4 | `assert truncate_number(100.123) == 0.123` | put: fail → ok, canon: fail → ok |
| 2 | placebo-hybrid | 0 | 5 | `assert truncate_number(1.0001) == 0.0001` | put: fail → ok, canon: fail → ok |
| 2 | placebo-hybrid | 0 | 8 | `assert truncate_number(1000.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 0 | 2 | `assert truncate_number(100.1) == 0.1` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 0 | 5 | `assert truncate_number(1.0000000001) == 1e-10` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 0 | 7 | `assert truncate_number(123456789.12345679) == 0.123456789` | put: fail → ok, canon: fail → ok |
| 2 | plain | 1 | 2 | `assert truncate_number(25.123) == 0.123` | put: fail → ok, canon: fail → ok |
| 2 | plain | 1 | 5 | `assert truncate_number(999.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | plain | 1 | 7 | `assert truncate_number(12345.6789) == 0.6789` | put: fail → ok, canon: fail → ok |
| 2 | plain | 1 | 9 | `assert truncate_number(100.001) == 0.001` | put: fail → ok, canon: fail → ok |
| 2 | concept | 1 | 3 | `assert truncate_number(2.999999) == 0.999999` | put: fail → ok, canon: fail → ok |
| 2 | concept | 1 | 5 | `assert truncate_number(123456789.12345679) == 0.123456789` | put: fail → ok, canon: fail → ok |
| 2 | toolinput | 1 | 3 | `assert truncate_number(10.01) == 0.01` | put: fail → ok, canon: fail → ok |
| 2 | toolinput | 1 | 8 | `assert truncate_number(999.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | toolinput | 1 | 9 | `assert truncate_number(1.1) == 0.1` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 1 | 1 | `assert truncate_number(2.628359714861843) == 0.628359714861843` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 1 | 2 | `assert truncate_number(9.90987367969459) == 0.90987367969459` | put: fail → ok, canon: fail → ok |
| 2 | concept-hybrid | 1 | 3 | `assert truncate_number(2.999999) == 0.999999` | put: fail → ok, canon: fail → ok |
| 2 | concept-hybrid | 1 | 5 | `assert truncate_number(123456789.12345679) == 0.123456789` | put: fail → ok, canon: fail → ok |
| 2 | placebo-hybrid | 1 | 3 | `assert truncate_number(1.001) == 0.001` | put: fail → ok, canon: fail → ok |
| 2 | placebo-hybrid | 1 | 9 | `assert truncate_number(1.23456789) == 0.23456789` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 1 | 2 | `assert truncate_number(25.123) == 0.123` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 1 | 5 | `assert truncate_number(999.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 1 | 7 | `assert truncate_number(12345.6789) == 0.6789` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 1 | 9 | `assert truncate_number(100.001) == 0.001` | put: fail → ok, canon: fail → ok |
| 2 | plain | 2 | 5 | `assert truncate_number(123456789.12345679) == 0.123456789` | put: fail → ok, canon: fail → ok |
| 2 | plain | 2 | 6 | `assert truncate_number(1.000001) == 1e-06` | put: fail → ok, canon: fail → ok |
| 2 | plain | 2 | 7 | `assert truncate_number(1000000.000001) == 1e-06` | put: fail → ok, canon: fail → ok |
| 2 | concept | 2 | 6 | `assert truncate_number(999.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | toolinput | 2 | 8 | `assert truncate_number(99.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 2 | 2 | `assert truncate_number(999.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 2 | 5 | `assert truncate_number(123456.789) == 0.789` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 2 | 7 | `assert truncate_number(1.0000001) == 1e-07` | put: fail → ok, canon: fail → ok |
| 2 | gen-plain | 2 | 8 | `assert truncate_number(999999.999999) == 0.999999` | put: fail → ok, canon: fail → ok |
| 2 | concept-hybrid | 2 | 6 | `assert truncate_number(999.999) == 0.999` | put: fail → ok, canon: fail → ok |
| 2 | placebo-hybrid | 2 | 7 | `assert truncate_number(1.0000000000000002) == 0` | put: fail → ok, canon: fail → ok |
| 2 | placebo-hybrid | 2 | 8 | `assert truncate_number(1.0000000000000004) == 0` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 2 | 5 | `assert truncate_number(123456789.12345679) == 0.123456789` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 2 | 6 | `assert truncate_number(1.000001) == 1e-06` | put: fail → ok, canon: fail → ok |
| 2 | plain-hybrid | 2 | 7 | `assert truncate_number(1000000.000001) == 1e-06` | put: fail → ok, canon: fail → ok |
| 4 | gen-plain | 0 | 5 | `assert mean_absolute_deviation([-1.1, 1.1, 0.0]) == 0.7333333333333333` | put: fail → ok, canon: fail → ok |
| 4 | toolinput | 1 | 8 | `assert mean_absolute_deviation([1.1, 1.9]) == 0.4` | put: fail → ok, canon: fail → ok |
| 20 | concept-hybrid | 1 | 19 | `assert find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 1.00000000000001, 1.0]) == (1.0, 1.00000000000001)` | put: fail → fail, canon: fail → ok |
| 20 | concept-hybrid | 2 | 19 | `assert find_closest_elements([-1.0, -0.9999999999999999]) == (-1.0, -0.9999999999999999)` | put: fail → ok, canon: ok → ok |
| 42 | concept-hybrid | 1 | 17 | `assert incr_list([-2.2, -3.8]) == [-1.2, -2.8]` | put: fail → fail, canon: fail → ok |
| 42 | plain-hybrid | 2 | 10 | `assert incr_list([-1.7976931348623157e+308]) == [-1.7976931348623155e+308]` | put: fail → ok, canon: fail → ok |
| 71 | placebo-hybrid | 0 | 9 | `assert triangle_area(1000, 1000, 1000) == 433012.71` | put: fail → ok, canon: fail → ok |
