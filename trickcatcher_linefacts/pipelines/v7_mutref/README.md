# v7_mutref

Copied with `cp -r pipelines/v7 pipelines/v7_mutref`. The method change is the
choice of the three shown hints: every fuzz-reached code fact of every kind and
every spec fact compete in one pool. `facts.pick()` uses frozen
`LR[noref+mutref]` coefficients in `config.json`, then takes the top three.
Ties use the analysis's stable score sort after `random.Random(20261010 + task)`
shuffles the complete pool (code facts in extraction order, then spec facts).
There are no kind caps, kind exclusions, block exclusions, or guard tiers in
selection; the guard tier remains a scored feature.

Registration: `/home/phong/dev/ConceptTester/trickcatcher_linefacts/PREREG_PENDING.md`
section `v7_mutref`. Evidence: `RESULTS.md` §11.29 and
`analysis/hint_rank.py`, `analysis/hint_rank_report.md`. The coefficients are
copied from that script's saved fitted model in `out/hint_rank/results.json`.
That artifact stores three-decimal coefficients; no model is fitted here.
Those saved values reproduce every recorded selection.

`hint_rank.py` adapts the analysis's method-only feature worker: same fuzz seed
and B5 validator, hit fraction, nearest-base repr comparison, crash signals,
witness-first evaluation and 40-hit-input cap. For mutant hits, `mutref` asks
whether the mutant agrees with a strict majority of the spec-only B2 programs
while the PUT does not, or only the mutant disagrees. Each reference must pass
the base tests; at least three survivors are required. This uses reference
programs in the sense of TrickCatcher. `refdis` is not scored or computed for
nonmutant facts. PF labels and HumanEval+ assertions enter only `verify.py`.

The new `refs` stage runs before generation and builds exactly the unchanged
`oracle_b01` DPP requests: ten programs per task, original templates, original
seeds, temperature 0.8, top_p 0.95, max_tokens 1024. Offline is the default;
`--reuse-from` copies historical responses, execution records and request
caches into this folder, and `refs` verifies each response by replaying its
original request hash. A fresh online run would request the same spec-only B2
programs without seeing generated tests, hints, PF labels or PUT implementation.

`bundle` computes method features in CPU workers with `unshare -rn`, ranks the
joint pool, and derives concept text/metadata, placebo text/metadata and
toolinput witnesses from the new shown hints. Code placebo matching uses v7's
same seeded kind-match/fallback pool; spec placebo uses v7's first covered
classes. Witnesses are retained in shown-hint order, filtered and deduplicated
as for v7 code hints. The extraction report's `top3` is retained as a v7 preview
for stage validation; it is not the final shown selection. Specfacts are now
built for all tasks, including tasks with code facts.

Round-one prompt formats, all round-two logic, the oracle, seeds, budgets,
validators, mutant generation and original prompt templates remain byte-identical
to v7. Operational difference: outputs live **inside this new folder**, under
`out/humaneval`, to respect the pinned run and the write boundary. Output caches
are ignored by Git. Changing ranking inputs requires a fresh output directory;
method feature jobs and bundles are immutable.

## CPU replay commands

Run from `/home/phong/dev/ConceptTester`; none of these commands calls an endpoint.
All writes stay under
`/home/phong/dev/ConceptTester/trickcatcher_linefacts/pipelines/v7_mutref`.

```bash
cd /home/phong/dev/ConceptTester
python3 -B -m trickcatcher_linefacts.pipelines.v7_mutref.run refs --reuse-from /home/phong/dev/ConceptTester/trickcatcher_linefacts/out
python3 -B -m trickcatcher_linefacts.pipelines.v7_mutref.run bundle --workers 12
python3 -B -m trickcatcher_linefacts.pipelines.v7_mutref.verify --workers 12
python3 -B -m unittest trickcatcher_linefacts.pipelines.v7_mutref.test_mutref -v
```

`bundle` reuses cached mining, code facts, spec facts and B2 responses but
recomputes method features on CPU. Missing upstream data can be built with
the `mine`, `facts`, `specfacts`, `refs`, `bundle` stages in that order.
`mine` and uncached `refs` need the model on GPU; facts/specfacts/bundle are CPU.
The copied v4 interpreter requirement remains for toolinput classification.

## GPU commands (not executed during implementation)

With the model available and a completed bundle, arms and oracle LLM stages
need GPU. The oracle recipe is the unchanged v7 recipe.

```bash
python3 -B -m trickcatcher_linefacts.pipelines.v7_mutref.run arms --online --k 3
python3 -B -m trickcatcher_linefacts.pipelines.v7_mutref.run evaluate
python3 -B -m trickcatcher_linefacts.pipelines.v7_mutref.run oracle-collect
python3 -B -m trickcatcher_linefacts.pipelines.v7_mutref.run oracle-llm --online
python3 -B -m trickcatcher_linefacts.pipelines.v7_mutref.run oracle-score
```

For uncached upstream model stages use `run mine --online` and
`run refs --online` before generation. The default selection file is the
unchanged v7 selection (pilot plus dev); these commands are mechanics, not a
claim that a new GPU experiment was run or that its registered comparisons
have been evaluated.

## Actual CPU results

- B2 replay: **1,330/1,330** requests, 133 tasks, matching historical responses.
- Bundle: **133 tasks**, including **113 dev**. Selection agrees with the
  frozen analysis on **113/113 dev tasks**; the measured cohort excludes the
  one dev task without a failing HumanEval+ input, as the analysis does.
- PF is computed as `fail_hits / (fail_hits + pass_hits)`, good if PF >= 0.5.
  Code counts are read from `out/offline_v6_report`, exactly as the analysis
  does; spec counts are recomputed from official HumanEval+ assertions in
  isolated measurement workers. **good@3 even 37/58, odd 35/54**.
- Shown hints changed on **109/113 dev tasks**, unchanged on **4**: 15, 63,
  97, 144. No changed task merely reorders the same hint set.
- Round-one check: 4 tasks × 7 arms × 3 samples = **84 requests**.
  Fresh execution matches **82/84** historical keys. Task 63 toolinput samples
  1 and 2 originally had `sandbox total timeout`, yielding no selected inputs;
  fresh classification succeeds. Replaying those two recorded failures through
  the unchanged v7 fallback gives **84/84 matching keys**, 84 cache hits,
  zero misses, zero request-construction mismatches. This is the same recorded
  execution-state replay used by v7's `test_equivalence.py`; it is reported
  separately from fresh execution.
- Reference survivor counts match historical B2 execution on **113/113 dev
  tasks**. Fuzz witnesses have **zero mismatches**. Numeric features match on
  **112/113 dev tasks**: task 83 LOOP hit counts drift (5→4 and 3→4), consistent
  with the unchanged tracer's wall-clock safety net for expensive operations.
  Its selected hint indices and good@3 do not change. No other feature drift.
- **8 tests passed**. Generation/oracle sources and copied `PREREG.md` were
  checked byte-for-byte against v7. No GPU experiment, commit or push occurred.

Full report:
`/home/phong/dev/ConceptTester/trickcatcher_linefacts/pipelines/v7_mutref/out/humaneval/checks/report.json`.
Bundles: `out/humaneval/tasks_all.json`, `out/humaneval/tasks_hybrid.json`.
The copied `test_equivalence.py` remains v7's historical equivalence harness;
use `test_mutref.py` and `verify.py` for this changed selection.
