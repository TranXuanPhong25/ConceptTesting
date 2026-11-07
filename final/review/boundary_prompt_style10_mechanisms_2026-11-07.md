# Full10 prompt-style diagnostic: gains and losses

Saved run: `final/out/boundary_prompt_style10_20261107_120909`.
Exact guidance: `final/review/prompts/prompt_style_v1.json`.
Evidence: `boundary_prompt_style10_mechanisms_2026-11-07.json` contains the
per-arm witnesses, reference outputs and both saved native-repeat outcomes.
No new model or native execution in this analysis.

| Arm | Detected PUTs/tasks | Valid novel inputs | Benchmark-failing inputs |
|---|---:|---:|---:|
| direct | 6 | 199 | 30 |
| soft_bva | 7 | 192 | 19 |
| worksheet | 7 | 189 | 49 |

One PUT per task. Net gain is one PUT/task for either guided arm, not one input.
Many witnesses expose the same bug; worksheet's20task16witnesses illustrate why
input counts are not independent bug counts. Direct is the matched one-PUT plain
control here, distinct from the historical naive baseline with multiple visible PUTs.
These input totals include two timeout inputs for direct, one for soft and one
for worksheet on task76. All witnesses in the five gain/loss tasks below are
value mismatches in both saved native repeats.

## Worksheet gains over direct

**16: code-induced character partition.** PUT only counts a character when
`ord(char) < 256`, after lowercasing. Worksheet supplies `"€"` (8364): reference1,
PUT0; `"abc€"`: reference4, PUT3. All20worksheet inputs expose the bug. Direct
and soft BVA supply ASCII characters only. This is consistent with code-transition
inspection (worksheet steps2–3), but the witnesses are far above256. There is no
255/256/257 triplet: evidence of reaching the excluded character partition, not
evidence of precise boundary placement. Repeated emoji spend budget on one fault.

**72: equality with negative context.** Spec checks palindrome and final sum<=w;
PUT exits when any prefix sum>w. Worksheet `([-1,-1],-2)` has final sum=-2=w,
but first prefix=-1>-2, so referenceTrue/PUTFalse. Soft BVA similarly uses
`([-1,-2,-1],-4)`. Direct already has negative values: `([-1,-1],0)` passes both,
and `([-1,-1],-3)` fails both. Its missing ingredient is the joint negative
context and threshold, not negative values alone. This fits boundary placement
plus reach/infect/propagate; soft guidance suffices in this sample.

**99: concrete floating precision at a rounding boundary.** PUT rounds using
`int(num+0.5)` for nonnegative values and `int(num-0.5)` otherwise. Worksheet's
`"0.49999999999999994"` should round to0, but the float addition rounds to1.0,
so PUT returns1. Negative counterpart gives expected0/actual-1. Direct already
tests `"0.4999999999"`; soft tests `"0.499999"`. Those are too far from0.5 to
trigger this float-addition error. All arms test boundaries; worksheet alone
places these two concrete values sufficiently close. This matches order and
sensitive-neighborhood guidance; precise internal reasoning is unobserved.

## Worksheet losses to direct

**2: boundary recognized, distance inadequate.** Fraction.limit_denominator()
can approximate a float just below an integer as the integer, making its returned
fractional part0. Direct `0.999999999` gives expected0.999999999/actual0.0;
soft has `999.9999999999999` and `2.9999999999999996`. Worksheet has
`0.9/1.0/1.1`, small values near zero, near-third values and `999999.999999`.
None is an exposing near-integer-below value under the benchmark tolerance.
One raw float duplicate is discarded, but no exposing witness is discarded.
Failure is concrete-value placement, despite the worksheet explicitly mentioning
integer crossings. Worksheet succeeds at precision in99but does not do so here.

**124: incomplete coverage of format constraints.** PUT validates month/day
widths and calendar limits but never requires a four-digit year. Direct
`"01-01-20"` and `"01-01-202"` give expectedFalse/actualTrue. Soft
`"01-01-2000 "` also gives False/True because int() accepts trailing whitespace.
Worksheet devotes19of20calls to standard-width strings with day/month/calendar
variations; its remaining `"01-1-2020"` is rejected by the existing day-width
check. It misses year width and year whitespace. This is compatible with an
attention/budget tradeoff toward prominent calendar thresholds. The output does
not prove that step5's selection priority caused the omission. A proper BVA
analysis could also catch the missing format-width check.

## What the worksheet flow explains

The observed gains fit its guidance: inspect code-induced partitions, combine
boundary values with a context that propagates differences, and choose sensitive
neighbors. Its losses show incomplete coverage and inconsistent concrete-value
precision. Direct itself generates boundary tests, so this is an instruction-style
comparison, not presence versus absence of boundary knowledge.

Worksheet is an instruction to reason internally and return JSON inputs. It has
no separate selection API, constructor, intermediate step logs or tool feedback
in this diagnostic. Thus the trace is request→concrete inputs→saved outcomes;
attributing a result to a particular internal step remains a hypothesis. No
causal claim about prompt length or step ordering follows from one sample.

Soft vs direct: wins72, losses none. Worksheet vs direct: wins16/72/99,
losses2/124. All miss11. These are outcome-selected known-bug tasks used during
development, with one response per task/arm and12historical responses reused;
the +1 net result is descriptive and does not establish general superiority.
