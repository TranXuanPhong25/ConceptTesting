# v11_fair

Copy of v7 implementing Final comparison protocol fixes 2, 3, 4 and 6 from `PREREG_PENDING.md`. Defaults enable all four fixes. The original v7 sources, vendor code and historical datasets remain read-only.

| config.json flag | Default | Behavior |
| --- | --- | --- |
| `strict_round2` | true | Hybrid round 2 keeps only new, tool-verified selected calls; one exact expected-value request, skipped if none fit/remain. |
| `placebo_matched` | true | Placebo matches concept-hybrid's actual strategy-request count, including retries, targeting placebo hints. |
| `caps` | true | Every sample in the seven-arm pipeline gets at most eight logical LLM calls and twenty assertions, in generation order. |
| `shared_scorer` | true | Evaluation, oracle and exported analyses use recursive output comparison with task atol and relative tolerance 1e-6; reports add D_I, D_IO and bug-report precision. |

Set all four flags to false to reproduce v7 behavior. The package/version provenance and output location necessarily differ. `LINEFACTS_FAIR_FLAGS` accepts a JSON object of boolean flag overrides for CPU tests; workers receive those exact flags through their sanitized environment, and enabled overrides are recorded in generation manifests.

Outputs for this copy live under `pipelines/v11_fair/out/<dataset>/`, so running its stages and tests stays inside this folder. The orchestration and stage ordering otherwise follow `pipelines/README.md`; invoke `python -B -m trickcatcher_linefacts.pipelines.v11_fair.run <stage>` from the repository root. Offline cache replay remains the default and raises `CacheMiss`; no credentials or endpoint are needed for the tests.

Generation records `dropped_assertions` for actual assertions discarded by the cap, including shared round-1 drops attributed to hybrid samples. Strict mode filters selected calls already present in round 1, preserves selection order, and rejects extra PUT calls in expected-value responses. If assertion slots are exhausted, `dropped_round2_inputs` records selected inputs excluded before the expected-value request. An omitted/unusable expected value becomes a recorded `assert <selected call> == None` placeholder, exactly as in v8's CPU construction; `strict_missing_expected` records its count. It never substitutes the reference answer during generation.

Placebo requests cycle through missed placebo hints. If all placebo hints are covered, they cycle through the available placebo hints; if none exist they use the existing control strategy prompt, while retaining the matched request count. Concept-hybrid's request count remains the actual count of its strategy calls, including verification retries. Caps reserve one expected-value call slot.

`scorer.output_equal(left, right, atol)` and `scorer.outcome_equal((status,value), (status,value), atol)` are the public analysis API. Lists and tuples retain their Python type distinctions, dictionary keys compare exactly, and nested float values use tolerance. Timeout spellings are normalized to one timeout outcome; different exception types, timeouts and successful outputs remain distinct. `scorer.task_atols()` uses the configured oracle dataset for every scoring path: the historical evaluation dataset lacks atol.

The report stage prints per-arm D_I (distinct contract-valid inputs within each sample with PUT/reference outcome disagreement), D_IO (assertions on those inputs with correct expected values), detecting-sample counts, and precision (`correct_failing / failing`). Contract-invalid failures stay in the denominator and never enter the numerator. `false_alarm_rate` uses the same failing-assertion denominator; it complements precision and is null when there are no failures. The historical `false_alarm` column retains its old all-assertion denominator for compatibility. Evaluation metrics are written beside `eval.jsonl` as `eval.metrics.json`. Oracle scoring also writes `fair_metrics.json` with these quantities for the own assertions and each replacement oracle (B1, ref, full, etc.). D_I is input-level, so it remains meaningful when an expected value is wrong or an oracle abstains.

CPU verification, from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest trickcatcher_linefacts.pipelines.v11_fair.test_fair
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v11_fair.test_equivalence --checks a,b,l,d --workers 8
```

`a` rebuilds both bundles. `b` checks all first cache keys and freshly replays tasks 0, 4 and 16 at K=1. `l` compares the full report on identical recorded CPU observations, plus real v7/v11 evaluation aggregation; historical output writes are suppressed. `d` executes every cached assertion in a network-isolated CPU worker, scores the same captured outcomes with both comparators, and writes the complete changed-assertion list to `EQUIVALENCE.md`. Optional `c` retains v7's full fresh execution check, which may differ at its documented set-order/deadline/memory boundaries. `--checks b` needs the bundles produced by `a` in the same output directory. No expected CPU outputs are substituted in `b` or `d`.

Status: **implemented, not yet run on GPU**. See `CHANGELOG.md` and `EQUIVALENCE.md` for measured verification and limits.
