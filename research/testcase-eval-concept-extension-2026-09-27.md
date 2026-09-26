# TestCase-Eval concept extension: held-out confirmatory run (n=450)

## Bottom line

On a 450-target, language-stratified, held-out slice of the official
[TestCase-Eval](https://github.com/FlowRays/TestCase-Eval) (ACL 2025) Task 2
benchmark, the paper's **CoT** prompt beats its **direct-output** prompt by
**+10.7pp official Fault Exposure** (37.3% vs 26.6%, McNemar p=9.7e-6, n=448
paired) and **+13.4pp strict Fault Exposure** (31.0% vs 17.6%, p=2.7e-10).
This replicates, at 4-5x the sample size and with a statistically decisive
margin, the same-direction but non-significant n=96 tuning-subset result
(38.5% vs 33.3%, ns). This run did **not** re-test this repo's own
concept-guided condition at the 450-target scale — see Limitations.

## Method

Two-phase design, both on `gemini-3-flash-preview` (native Vertex,
`LLM_THINKING_BUDGET=0`, official generation settings: temperature 1.0,
max_tokens 2048 for the paper's `do`/`cot` prompts). Sandbox covers C++,
Java, Python, and PyPy, mirroring the official multi-language Task 2 harness
(`testcase_eval/sandbox.py`).

**Metric.** Official Fault Exposure (`exposed_official`): the target
(a known-wrong submission) crashes, times out, exceeds memory, or its output
disagrees with the first pair of `right_submission`s (any language) that
agree with each other (ports `stat_task2.py`'s gmpy2-equivalent numeric
comparison via 60-digit `Decimal`). This extension adds a stricter variant,
`exposed_strict`: additionally requires an LLM-written, per-problem input
validator (calibrated against `submission_lite` samples) to accept the
generated input, **and** *every* accepted submission (not just one agreeing
pair) to run successfully and agree.

**Phase 1 — n=96 tuning subset** (already reported in `testcase_eval/RESULTS.md`
before this run; summarized below for context). Five conditions: `do`, `cot`
(paper baselines), `cot_val` (the `cot` answer plus up to 2 validator-feedback
repairs — isolates the repair loop from concept content), `concept_nohyp`
(concept-style generator prompt without a fault hypothesis, same repair
loop), `concept` (fault-hypothesis analyst → hypothesis-conditioned generator
→ same repair loop).

**Phase 2 — n=450 held-out** (this run). Seeded (`20260927`),
language-stratified 150 targets per family (cpp/java/python), one target per
problem, every `submission_id` used in the n=96 tuning subset excluded
(`testcase_eval/subsets/task2_seed20260927_n450_heldout.txt`, added in
`a983caa`). This confirmatory run reran only the two **paper baselines**,
`do` and `cot`, at scale — it does not include this repo's concept
conditions (see Limitations).

**Coverage.** 449/450 targets produced a scoreable input for `do` and for
`cot` after retries (1 permanent post-retry generation failure per
condition, on different targets — transient LLM-call failures that did not
recover within the run). 448 targets are paired across both conditions.
Validators were calibrated for 441/450 held-out problems (9 `rejects_sample`:
the LLM-written validator itself failed calibration against known-good
samples), so `exposed_strict`/`strict_valid` are unavailable for targets on
those 9 problems; `exposed_official` is unaffected.

## Results: n=450 held-out, `cot` vs `do`

| condition | family | n | FE official | FE strict | validator accept | official consensus | strict valid | FE strict\|valid |
|---|---|---|---|---|---|---|---|---|
| cot | all | 448 | 37.3% | 31.0% | 87.5% | 95.3% | 84.8% | 36.6% |
| cot | cpp | 150 | 31.3% | 24.7% | 83.3% | 97.3% | 81.3% | 30.3% |
| cot | java | 148 | 42.6% | 37.2% | 87.8% | 93.2% | 85.8% | 43.3% |
| cot | python | 150 | 38.0% | 31.3% | 91.3% | 95.3% | 87.3% | 35.9% |
| do | all | 448 | 26.6% | 17.6% | 83.5% | 95.8% | 80.1% | 22.0% |
| do | cpp | 150 | 17.3% | 11.3% | 82.0% | 96.0% | 80.0% | 14.2% |
| do | java | 148 | 32.4% | 22.3% | 81.1% | 92.6% | 77.7% | 28.7% |
| do | python | 150 | 30.0% | 19.3% | 87.3% | 98.7% | 82.7% | 23.4% |

Paired comparison (`cot` vs `do`, exact McNemar + problem-clustered
bootstrap 95% CI of the difference):

| metric | family | n | cot | do | diff (95% CI) | cot-only | do-only | McNemar p |
|---|---|---|---|---|---|---|---|---|
| FE official | all | 448 | 37.3% | 26.6% | +10.7pp [+6.2, +15.2] | 82 | 34 | **9.7e-06** |
| FE official | cpp | 150 | 31.3% | 17.3% | +14.0pp [+8.0, +20.7] | 25 | 4 | **1.0e-04** |
| FE official | java | 148 | 42.6% | 32.4% | +10.1pp [+1.4, +18.2] | 30 | 15 | **0.036** |
| FE official | python | 150 | 38.0% | 30.0% | +8.0pp [+0.0, +16.0] | 27 | 15 | 0.088 (ns) |
| FE strict | all | 448 | 31.0% | 17.6% | +13.4pp [+9.4, +17.4] | 77 | 17 | **2.7e-10** |
| FE strict | cpp | 150 | 24.7% | 11.3% | +13.3pp [+7.3, +19.3] | 23 | 3 | **8.8e-05** |
| FE strict | java | 148 | 37.2% | 22.3% | +14.9pp [+6.8, +22.3] | 29 | 7 | **3.1e-04** |
| FE strict | python | 150 | 31.3% | 19.3% | +12.0pp [+5.3, +18.7] | 25 | 7 | **0.0021** |

`cot` wins on every family under both metrics; the only non-significant cell
is `python`/official (p=0.088, still directionally positive and significant
under the stricter metric). Cost for the 449-target runs: `cot` 468 Gemini
calls, 725k input + 225k output tokens, $1.04 total ($0.0023/target); `do`
614 calls (more helper-LLM extraction fallbacks needed on its terser output),
777k input + 29k output tokens, $0.47 total ($0.0011/target) — `cot` costs
~2.2x per target for a +10.7 to +13.4pp Fault Exposure gain.

## Context: n=96 tuning subset (prior evidence, not yet scaled to n=450)

From the earlier 5-condition tuning run (`testcase_eval/results/subset/`,
n=96 paired, one target per problem, disjoint from the 450 held-out set):

| condition | FE official | FE strict |
|---|---|---|
| do | 33.3% | 24.0% |
| cot | 38.5% | 33.3% |
| cot_val (repair loop only, no concept) | 38.5% | 34.4% |
| concept_nohyp (concept generator, no fault hypothesis) | 60.4% | 55.2% |
| concept (fault-hypothesis + concept generator) | 53.1% | 47.9% |

Against the correctly-controlled reference `cot_val` (isolates the
validator-repair loop from concept content): `concept_nohyp` +21.9pp official
/ +20.8pp strict (p=4.9e-05 / 8.8e-05); `concept` +14.6pp official / +13.5pp
strict (p=0.020 / 0.024). `cot` itself shows **no** difference from `cot_val`
(0.0pp official, p=1.0), which is evidence the repair loop alone is not
responsible for the `cot_val`→`concept*` jump — concept content appears to be
doing the work. `concept_nohyp` outperforms `concept` (the version *with* the
fault hypothesis) by 7.3pp both metrics, but this is not significant at n=96
(p=0.21) — i.e. no evidence yet that adding the hypothesis text helps over
the plainer concept-generator prompt, and a hint that it might even hurt.

**This n=96 result has not been replicated at the 450-target held-out
scale** — the run reported here reran only `do`/`cot`. The concept pipeline
is markedly more expensive (fault-hypothesis analyst call, generator call,
up to 2 validator-feedback repairs vs. `do`/`cot`'s one call), which is
presumably why it wasn't included in this first held-out pass.

## Limitations

- **The actual "concept extension" is untested at n=450.** Everything in the
  headline results section above is a `cot`-vs-`do` **paper-baseline**
  replication, not a concept-vs-baseline result. The concept pipeline's large
  n=96 gain over the correct `cot_val` control is promising but n=96-only and
  needs its own held-out run before it can be reported as an effect at scale.
- A scoping bug briefly affected this run: the `cot`/`do` generation
  processes were first launched without `--targets`, so for about 2.5 hours
  they generated against the full 10,000-item Task 2 corpus instead of the
  450-target held-out list, before being killed and relaunched correctly
  scoped to the held-out file. No incorrect data resulted — generation is
  resumable and keyed by `(condition, submission_id)` — but `gen_cot.jsonl`/
  `gen_do.jsonl` on disk contain ~1,384 extra non-held-out rows from that
  window; only the 449 held-out-scoped rows per condition were used for this
  analysis (`testcase_eval/results/full/gen_{cot,do}_heldout.jsonl`).
- 1/450 targets failed to produce a scoreable input for each of `do` and
  `cot` (different targets, after retries) — excluded, leaving n=448 paired.
- 9/450 held-out problems have no calibrated validator (`rejects_sample`),
  so `exposed_strict` is undefined for those targets; `exposed_official` is
  unaffected.
- Single model (`gemini-3-flash-preview`), single sample per
  `(condition, target)` — no repeated-sampling variance estimate beyond the
  paired McNemar/cluster-bootstrap statistics shown.
- Several agents in this repo share one Vertex project's quota; generation
  ran at reduced, explicitly paced concurrency (`TESTCASE_EVAL_MIN_INTERVAL`,
  10 total workers across `cot`+`do`+validator) to avoid contributing to
  429s in other concurrent runs, which is why this took ~4.5 hours wall time
  for generation once correctly scoped, plus ~5 hours for validator
  calibration on the 450 held-out problems.

## Next step implied by this result

Run `concept` (and `concept_nohyp`, since it outperformed `concept` at n=96
though not significantly) on the same 450 held-out targets, using `cot_val`
— not `do`/`cot` — as the reference condition, to test whether the large
n=96 concept gain replicates at scale.

## Reproduce

```bash
# Generation (already run for do/cot on the held-out set; concept/concept_nohyp/cot_val not yet run at n=450)
.venv/bin/python -m testcase_eval.generate --condition cot --out testcase_eval/results/full/gen_cot.jsonl \
  --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt --workers 4
.venv/bin/python -m testcase_eval.generate --condition do  --out testcase_eval/results/full/gen_do.jsonl \
  --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt --workers 3
.venv/bin/python -m testcase_eval.validator --out testcase_eval/results/validators.jsonl \
  --problems @testcase_eval/subsets/task2_seed20260927_n450_heldout_problems.txt --workers 3

# Scoring (this repo filtered gen_{cot,do}.jsonl down to the 449 held-out-scoped rows per
# condition first, into gen_{cot,do}_heldout.jsonl, to avoid re-scoring the ~1,384 stray
# non-held-out rows left by the scoping bug described above)
.venv/bin/python -m testcase_eval.evaluate --pred testcase_eval/results/full/gen_cot_heldout.jsonl \
  --out testcase_eval/results/full/eval_cot.jsonl --validators testcase_eval/results/validators.jsonl --workers 12
.venv/bin/python -m testcase_eval.evaluate --pred testcase_eval/results/full/gen_do_heldout.jsonl \
  --out testcase_eval/results/full/eval_do.jsonl --validators testcase_eval/results/validators.jsonl --workers 12

# Paired report
.venv/bin/python -m testcase_eval.report \
  --scored cot=testcase_eval/results/full/eval_cot.jsonl do=testcase_eval/results/full/eval_do.jsonl \
  --gen cot=testcase_eval/results/full/gen_cot_heldout.jsonl do=testcase_eval/results/full/gen_do_heldout.jsonl \
  --reference do --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt \
  --json-out testcase_eval/results/full/report_do_cot.json
```

Full JSON (per-family table + pairs + cost) is at
`testcase_eval/results/full/report_do_cot.json`.
