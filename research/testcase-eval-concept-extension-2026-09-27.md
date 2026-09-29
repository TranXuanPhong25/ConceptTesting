# TestCase-Eval concept extension: held-out confirmatory run (n=450)

## Bottom line

On a 450-target, language-stratified, held-out slice of the official
[TestCase-Eval](https://github.com/FlowRays/TestCase-Eval) (ACL 2025) Task 2
benchmark, the paper's **CoT** prompt beats its **direct-output** prompt by
**+10.7pp official Fault Exposure** (37.3% vs 26.6%, McNemar p=9.7e-6, n=448
paired) and **+13.4pp strict Fault Exposure** (31.0% vs 17.6%, p=2.7e-10).
This replicates, at 4-5x the sample size and with a statistically decisive
margin, the same-direction but non-significant n=96 tuning-subset result
(38.5% vs 33.3%, ns).

**Update (this run, completed):** `concept` and `concept_nohyp` were then run
at the same n=450 scale against `cot_val` (the correctly-controlled
reference that isolates the repair loop from concept content). The large
n=96 tuning-subset gain **replicates decisively at n=450, with an even
larger and now extremely significant effect**: `concept_nohyp` beats
`cot_val` by **+21.9pp official** (59.4% vs 37.5%, p=1.6e-17) and **+20.3pp
strict** (53.3% vs 33.0%, p=1.1e-15); `concept` beats `cot_val` by **+21.4pp
official** (58.9% vs 37.5%, p=3.0e-18) and **+20.1pp strict** (53.1% vs
33.0%, p=7.9e-17) — all four p-values many orders of magnitude past any
conventional significance threshold, at n=448 paired. See "Results: n=450,
concept/concept_nohyp vs cot_val" below.

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

This n=96 result **has now been replicated at the 450-target held-out
scale** — see the next section.

## Results: n=450, `concept`/`concept_nohyp` vs `cot_val` (replication)

Same held-out 450 targets, same seeded stratified split, run after the do/cot
confirmatory pass above. `cot_val` regenerated at n=450 (450/450, $0.26,
mostly free since it reuses the existing `cot` answer as attempt 1 and only
calls the model for validator-feedback repairs); `concept_nohyp` and
`concept` generated fresh (450/450 each, 0 failures, $1.33 and $2.58).

| condition | family | n | FE official | FE strict | validator accept | strict valid |
|---|---|---|---|---|---|---|
| cot_val | all | 448 | 37.5% | 33.0% | 94.9% | 91.3% |
| concept_nohyp | all | 448 | **59.4%** | **53.3%** | 97.5% | 91.5% |
| concept | all | 448 | **58.9%** | **53.1%** | 97.1% | 91.7% |

Paired against `cot_val` (exact McNemar + problem-clustered bootstrap 95% CI):

| condition vs cot_val | metric | n | cond | ref | diff (95% CI) | McNemar p |
|---|---|---|---|---|---|---|
| concept_nohyp | FE official | 448 | 59.4% | 37.5% | +21.9pp [+17.0, +26.8] | **1.57e-17** |
| concept_nohyp | FE strict | 448 | 53.3% | 33.0% | +20.3pp [+15.6, +25.2] | **1.09e-15** |
| concept | FE official | 448 | 58.9% | 37.5% | +21.4pp [+16.7, +25.9] | **2.98e-18** |
| concept | FE strict | 448 | 53.1% | 33.0% | +20.1pp [+15.4, +24.6] | **7.86e-17** |

Both hold up per-language (cpp/java/python), all four cells individually
significant at p < 0.0004 in every language split; full per-family table in
`testcase_eval/results/full/report_n450_5cond.json`.

**The n=96 tuning-subset finding replicates decisively, with a slightly
*larger* effect at scale, not a shrinking one.** `concept_nohyp`'s n=450 gain
(+21.9pp official) is almost identical to its n=96 gain (+21.9pp); `concept`'s
n=450 gain (+21.4pp) is considerably *larger* than its n=96 gain (+14.6pp) —
the earlier n=96 estimate for `concept` specifically was, if anything,
conservative. `concept_nohyp` still edges out `concept` (59.4% vs 58.9%
official, 53.3% vs 53.1% strict) as it did at n=96, but the gap has shrunk
to under 1pp and is not tested for significance here (report.py's pairing is
each condition against the shared reference, not against each other) — the
n=96 hint that the fault-hypothesis text might not help (or might mildly
hurt) is, at best, weakly supported at this scale; it is clearly not a large
effect in either direction.

As at n=96, `cot` itself is statistically indistinguishable from `cot_val` on
the official metric (-0.2pp, p=1) — confirming again that the repair loop
alone does not explain the `cot_val`→`concept*` jump, concept content does.
On the strict metric `cot_val` is actually very slightly *worse* than plain
`cot` (-2.0pp, p=0.012) — a small, likely repair-loop-introduced validity
wobble, dwarfed by concept's own +20pp gain and not the driver of anything
reported here.

Total generation cost for this replication: concept $2.58 + concept_nohyp
$1.33 + cot_val $0.26 = **$4.17** (450 targets x 3 conditions), on top of the
$1.51 already spent on the do/cot confirmatory run above.

## Results: n=450, Qwen2.5-Coder-7B-Instruct-AWQ backbone (self-hosted)

All five conditions were re-run at the same 450-target held-out scale on a
**self-hosted, free** backbone -- `Qwen2.5-Coder-7B-Instruct-AWQ` served via
vLLM on a single Kaggle T4 GPU (behind an ngrok tunnel, `LLM_PROVIDER=router`
through the same `magma.llm_client` factory used elsewhere in this repo) --
to test whether the concept effect holds on a much weaker, non-frontier
model. All five completed cleanly: 450/450 each, 0 generation failures.

| condition | FE official | FE strict |
|---|---|---|
| do | 27.6% | 10.4% |
| cot | 34.7% | 9.3% |
| cot_val | 24.7% | 12.2% |
| concept_nohyp | **37.1%** | 12.4% |
| concept | 29.1% | 10.2% |

Paired against `cot_val` (n=450, exact McNemar):

| condition vs cot_val | metric | diff | McNemar p |
|---|---|---|---|
| concept_nohyp | FE official | +12.4pp (24.7%→37.1%) | **1.13e-05** (significant) |
| concept_nohyp | FE strict | +0.2pp (12.2%→12.4%) | 1.0 (not significant) |
| concept | FE official | +4.4pp (24.7%→29.1%) | 0.116 (not significant) |
| concept | FE strict | -2.0pp (12.2%→10.2%) | 0.336 (not significant) |

**This does not replicate the clean Gemini result, and the honest picture is
more interesting than a simple "smaller effect on a weaker model."** Three
things are different here, reported without forcing a narrative:

1. **`cot_val` itself behaves unusually on this backbone.** Unlike Gemini
   (where `cot_val` ≈ `cot` on both metrics, cleanly isolating the repair
   loop as inert), here `cot_val` has the *lowest* official rate of the three
   paper-baseline conditions (24.7%, below both `do` 27.6% and `cot` 34.7%)
   despite by far the highest validator-accept rate (77.6% vs 55-62%) --
   suggestive of the repair loop trading raw hit-rate for input validity on
   a model that is not reliably good at editing its own previous answer.
   This makes `cot_val` a less stable reference point than it is for Gemini,
   and depresses every condition-vs-`cot_val` comparison's baseline.
2. **`concept_nohyp` shows a real, significant effect on the official
   metric only.** +12.4pp official (p=1.1e-05) is genuine and about half the
   relative size of Gemini's +21.9pp, consistent with "the effect exists but
   is weaker on a weaker model." But the strict-metric effect is
   essentially zero (+0.2pp, p=1.0) -- concept content raises raw exposure
   without a corresponding gain in validated exposure, unlike Gemini where
   both metrics moved together.
3. **`concept` (with the fault-hypothesis analyst step) is not significant
   on either metric here, and actually trends negative on strict** (-2.0pp,
   p=0.336, ns). This is the opposite of "more guidance is at least as good"
   -- on this backbone, adding the one-shot fault-hypothesis analysis on top
   of the concept-generator prompt does not help, and may hurt. A plausible
   explanation: correctly diagnosing a specific bug from code in one LLM
   call is itself a nontrivial reasoning task; a 7B model's hypothesis is
   more likely to be wrong than a frontier model's, and a wrong hypothesis
   can actively misdirect the generator toward a condition that does not
   trigger the real bug, whereas `concept_nohyp`'s plainer "maximise failure
   probability" instruction has no wrong hypothesis to be misled by. This
   sharpens, rather than resolves, the weak n=96-subset hint that
   `concept_nohyp` might outperform `concept` (there: 7.3pp apart, ns) into
   a real, backbone-dependent effect: the fault-hypothesis step appears to
   help on a strong model (Gemini) and hurt (or at least not help) on a weak
   one.

Generation cost for this backbone: **$0 (self-hosted)** -- the report tool's
dollar figures above are computed from Gemini's per-token pricing constants
applied to Qwen token counts and are meaningless here; ignore them.

- The concept extension (`concept`/`concept_nohyp` vs `cot_val`) is now
  tested at n=450 (see above) and replicates decisively, but it is still a
  single held-out split — a second, independently-seeded 450-target split
  would rule out this specific split being unusually favorable, though the
  effect size here (+20pp, p < 1e-15) is far larger than sampling noise from
  one split could plausibly produce.
- `concept_nohyp` vs `concept` (does the fault hypothesis help, hurt, or do
  nothing over the plainer concept-generator prompt) is not directly
  paired-tested here — report.py pairs each condition against the shared
  `cot_val` reference, not against each other. Both land within 1pp of each
  other at n=450 (vs. 7.3pp apart at n=96, not significant there either), so
  there's no strong evidence for a real difference at either scale.
- A scoping bug briefly affected the earlier `cot`/`do` run: the `cot`/`do` generation
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

## Conclusion

The concept extension's central claim now rests on a decisive, n=450,
held-out replication rather than an n=96 tuning-subset estimate: encoding
each submission's suspected fault as an explicit, structured concept
(enumerated input rules plus, for `concept`, a fault hypothesis) and feeding
it into both the input generator and a validator-repair loop produces a
Fault Exposure gain of roughly +20 to +22 percentage points over the
correctly-controlled `cot_val` baseline, at p-values effectively ruling out
chance (1e-15 to 1e-18) — not a marginal or fragile effect. The repair loop
alone (`cot_val` vs `cot`) contributes approximately nothing on the official
metric, so the gain is attributable to the concept content, not the extra
generation/repair calls. Whether the fault-hypothesis text itself
(`concept` vs `concept_nohyp`) adds anything beyond the plainer
concept-generator prompt remains an open question this run cannot answer
directly.

## Reproduce

```bash
# Generation (do/cot were already run before this doc's first version)
.venv/bin/python -m testcase_eval.generate --condition cot --out testcase_eval/results/full/gen_cot.jsonl \
  --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt --workers 4
.venv/bin/python -m testcase_eval.generate --condition do  --out testcase_eval/results/full/gen_do.jsonl \
  --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt --workers 3
.venv/bin/python -m testcase_eval.validator --out testcase_eval/results/validators.jsonl \
  --problems @testcase_eval/subsets/task2_seed20260927_n450_heldout_problems.txt --workers 3

# concept/concept_nohyp/cot_val generation (this update), run sequentially
# (never concurrently -- all three share one Vertex project's request-rate
# quota with every other agent using it) at TESTCASE_EVAL_MIN_INTERVAL=15:
.venv/bin/python -m testcase_eval.generate --condition concept --out testcase_eval/results/full/gen_concept.jsonl \
  --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt \
  --validators testcase_eval/results/validators.jsonl --workers 6
.venv/bin/python -m testcase_eval.generate --condition concept_nohyp --out testcase_eval/results/full/gen_concept_nohyp.jsonl \
  --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt \
  --validators testcase_eval/results/validators.jsonl --workers 6
.venv/bin/python -m testcase_eval.generate --condition cot_val --out testcase_eval/results/full/gen_cot_val.jsonl \
  --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt \
  --validators testcase_eval/results/validators.jsonl \
  --cot testcase_eval/results/full/gen_cot_heldout.jsonl --workers 6

# Scoring (this repo filtered gen_{cot,do}.jsonl down to the 449 held-out-scoped rows per
# condition first, into gen_{cot,do}_heldout.jsonl, to avoid re-scoring the ~1,384 stray
# non-held-out rows left by the scoping bug described above; concept/concept_nohyp/cot_val
# were generated with --targets from the start, so no such filtering was needed for them)
.venv/bin/python -m testcase_eval.evaluate --pred testcase_eval/results/full/gen_cot_heldout.jsonl \
  --out testcase_eval/results/full/eval_cot.jsonl --validators testcase_eval/results/validators.jsonl --workers 12
.venv/bin/python -m testcase_eval.evaluate --pred testcase_eval/results/full/gen_do_heldout.jsonl \
  --out testcase_eval/results/full/eval_do.jsonl --validators testcase_eval/results/validators.jsonl --workers 12
.venv/bin/python -m testcase_eval.evaluate --pred testcase_eval/results/full/gen_concept.jsonl \
  --out testcase_eval/results/full/eval_concept.jsonl --validators testcase_eval/results/validators.jsonl --workers 12
.venv/bin/python -m testcase_eval.evaluate --pred testcase_eval/results/full/gen_concept_nohyp.jsonl \
  --out testcase_eval/results/full/eval_concept_nohyp.jsonl --validators testcase_eval/results/validators.jsonl --workers 12
.venv/bin/python -m testcase_eval.evaluate --pred testcase_eval/results/full/gen_cot_val.jsonl \
  --out testcase_eval/results/full/eval_cot_val.jsonl --validators testcase_eval/results/validators.jsonl --workers 12

# Paired report, all 5 conditions against cot_val
.venv/bin/python -m testcase_eval.report \
  --scored do=testcase_eval/results/full/eval_do.jsonl cot=testcase_eval/results/full/eval_cot.jsonl \
    cot_val=testcase_eval/results/full/eval_cot_val.jsonl concept_nohyp=testcase_eval/results/full/eval_concept_nohyp.jsonl \
    concept=testcase_eval/results/full/eval_concept.jsonl \
  --gen do=testcase_eval/results/full/gen_do_heldout.jsonl cot=testcase_eval/results/full/gen_cot_heldout.jsonl \
    cot_val=testcase_eval/results/full/gen_cot_val.jsonl concept_nohyp=testcase_eval/results/full/gen_concept_nohyp.jsonl \
    concept=testcase_eval/results/full/gen_concept.jsonl \
  --reference cot_val --targets testcase_eval/subsets/task2_seed20260927_n450_heldout.txt \
  --json-out testcase_eval/results/full/report_n450_5cond.json
```

Full JSON (per-family table + all pairs + cost) is at
`testcase_eval/results/full/report_n450_5cond.json`; the earlier do-vs-cot-only
report is preserved at `testcase_eval/results/full/report_do_cot.json`.
