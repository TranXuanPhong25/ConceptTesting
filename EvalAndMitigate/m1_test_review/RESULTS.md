# m1_test_review: results

Setup: Gemini 2.5 Flash, thinking off, temperature 0. 78 focal methods / 60 Defects4J bugs. The reviewer is blind
to execution results and to the focal body (see README). Percentages are over compiled tests,
red-prec = E / (E + FP), and the counts are the upstream "reported" counters (same as `run/summarize.py`).
Everything below is produced by `python3 m1_test_review/analyze.py <baseline> <arm>`. The full output is in
`out/analysis_onlydoc.txt` and `out/analysis_advdoc.txt`.

## Short answer
- **Only Doc: review hurts.** E falls from 77 to 39 and methods with ≥1 E from 27 to 18 (McNemar: 9 lost,
  0 gained, p=0.004). Random abstention at the same rate would keep about 23.7 methods, and the chance that it
  loses ≥9 E-methods is 0.0016. M is unchanged (10 → 8; methods ≥1 M 5 → 4, p=1.0). Red-precision falls from
  0.193 to 0.177 instead of rising.
- **Advanced Doc: within noise, no better than random abstention.** Methods with ≥1 E go from 30 to 27
  (p=0.375) and red-precision from 0.262 to 0.276 (clean subset). Random abstention gives the same expected
  picture: 26.8 methods with ≥1 E and red-precision unchanged. The headline M drop (33 → 6) is mostly an
  artifact of the baseline log (see caveats). On the clean subset it is 9 → 6 (methods 3 → 2, p=1.0).

Why it fails: a docstring generated from the buggy code is silent on exactly the edge cases where the bug lives
(null/empty input, unstated modes, boundary widths). A spec-entailment filter therefore removes E tests at about
twice the base rate:

| arm | abstain rate | share of recoverable baseline E tests abstained | share of FP tests abstained |
|---|---|---|---|
| Only Doc | 24.4% | **47%** (33/70), P(random ≥33) < 1e-4 | 44% (99/227) |
| Advanced Doc | 23.5% | 28% (30/107), P(random ≥30) = 0.16 | 32% (61/193), P = 0.007 |

Typical reasons given for abstaining on E tests: "does not define the behavior for a null input", "does not define
the expected return value when empty strings are passed", "does not mention lenient mode". The Only Doc losses are
concentrated in Gson_4 (12 E tests), Codec_13 (8), Cli_32 (4), Csv_4, Lang_19, Lang_33 (2 each).
REWRITE never created an E test. In Advanced Doc it destroyed 4 E tests (4 E → 4 FP). Examples: "width must be
a positive integer" was turned into "expect IllegalArgumentException" (Cli_8), and an arithmetic re-derivation of
a return value changed a correct expected value (Lang_19).

## Only Doc: `m1_review_onlydoc` vs `unified_invoked_docstring_prompt`

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| baseline (Only Doc) | 1326 / 1222 | 10 (0.82%) | 77 (6.30%) | 321 (26.27%) | 0.193 | 5 | 27 |
| **review** | 1005 / 906 | 8 (0.88%) | 39 (4.30%) | 181 (19.98%) | 0.177 | 4 | 18 |
| random abstain r=0.244 (expected, analytic) | 1003 / 924 | 7.6 (0.82%) | 58.2 (6.30%) | 242.7 (26.27%) | 0.193 | 4.0 | 23.7 |

- Decisions on 1365 `@Test` methods: KEEP 1007, REWRITE 25 (1.8%), ABSTAIN 333 (24.4%). 30 expected-value changes
  were logged.
- Baseline outcomes of the abstained tests: E 33, M 2, FP 99, TN/not-compiled 199. Random abstention would
  remove E 18.8, M 2.4 and FP 78.3.
- Rewritten tests: baseline FP 9, TN/nc 16 → arm FP 11, TN/nc 14 (E 0 → 0).
- All 1007 kept tests have the same outcome in the arm run as in the baseline run, so the difference comes
  entirely from which tests were removed or rewritten.
- McNemar vs baseline: ≥1 E lost 9, gained 0, **p=0.004**. ≥1 M lost 1, gained 0, p=1.000.
- Excluding the one baseline block with an infrastructure failure (Lang_11 RandomStringUtils, 77 methods): baseline
  E 77, FP 300, red-prec 0.204 vs review E 39, FP 181, red-prec 0.177. McNemar is unchanged.

## Advanced Doc: `m1_review_advdoc` vs `unified_invoked_advanced_docstring_prompt`

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| baseline (Advanced Doc) | 1308 / 1138 | 33 (2.90%) | 95 (8.35%) | 313 (27.50%) | 0.233 | 5 | 30 |
| **review** | 1001 / 890 | 6 (0.67%) | 75 (8.43%) | 232 (26.07%) | 0.244 | 2 | 27 |
| random abstain r=0.235 (expected, analytic) | 1000 / 870 | 25.2 (2.90%) | 72.6 (8.35%) | 239.3 (27.50%) | 0.233 | 4.5 | 26.8 |
| *clean subset, 75 methods:* baseline | 1239 / 1069 | 9 (0.84%) | 95 (8.89%) | 268 (25.07%) | 0.262 | 3 | 30 |
| *clean subset, 75 methods:* review | 959 / 848 | 6 (0.71%) | 75 (8.84%) | 197 (23.23%) | 0.276 | 2 | 27 |

- Decisions on 1359 `@Test` methods: KEEP 1014, REWRITE 25 (1.8%), ABSTAIN 320 (23.5%). 33 expected-value changes
  were logged.
- Baseline outcomes of the abstained tests: E 30, M 3, FP 61, TN/nc 226. Random abstention would remove E 22.4,
  M 7.8 and FP 73.7.
- Rewritten tests: baseline E 4, FP 9, TN/nc 12 → arm E 0, FP 13, TN/nc 12.
- 1008 of 1014 kept tests have the same outcome as in the baseline run.
- McNemar vs baseline: ≥1 E lost 4, gained 1, p=0.375. ≥1 M lost 3, gained 0, p=0.250. On the clean subset,
  ≥1 M: lost 1, gained 0, p=1.000.
- The clean subset excludes Cli_8 HelpFormatter, Lang_11 RandomStringUtils and Lang_4 LookupTranslator. In the
  baseline log each of these has a run that "failed" with an empty error report. Upstream then counts every
  passing test as M: 11 M in Cli_8 and 13 M in Lang_4, where the per-test lists show 14 and 4 E tests. This
  flaw sits in the baseline log itself, so the baseline Advanced Doc M=33 in `run/BASELINES.md` is inflated.

## LLM calls and evaluations
| arm | reviewer calls | files reviewed | notes |
|---|---|---|---|
| m1_review_onlydoc | 79 | 78 | 1 retry. Codec_6 JSON was malformed twice; decisions were salvaged by regex and its rewrite became ABSTAIN |
| m1_review_advdoc | 78 | 75 | 3 truncated completions have no code block and passed through without a call. 3 retries; Gson_7, Lang_30 and Lang_44 salvaged (6 rewrites → ABSTAIN, 5 Lang_44 tests had no decision → KEEP) |
| smoke (2 runs of 3 records) | 6 | | prompt tuned once between them (README) |
| random-abstain control | 0 | | analytic, no evaluation |

Test generation was not rerun: the arms reuse the baseline completions, so the only added LLM cost is the
reviewer (about 1 call per file). The control needs no LLM calls, so rule 3 (same call budget) cannot apply
literally. The control is analytic, as the task specified. Per-test baseline categories for the abstained tests
come from the failing-test lists in the existing baseline logs, so no extra evaluation was run for them.

## Caveats
- n=78 methods and 60 bugs. The Only Doc loss is large and consistent (0 methods gained, and p=0.0016 against
  random abstention). The Advanced Doc differences are within noise.
- The review prompt was tuned once, on the 3 smoke records (Codec_7 Base64 values), before the full runs.
  Arm 2 was not tuned on arm-1 results: its review ran before arm 1 was evaluated.
- Infrastructure: evaluations crashed repeatedly in this session with transient ENOENT errors on checkout
  directories that exist. The cause is unknown. Containers from an unrelated project were running in the same
  Docker VM (7.6 GB) at the same time. `eval_parts.py` resumes after a crash with a new part (`<arm>_part<k>`) and keeps only finished log
  blocks. Two Only Doc blocks (Cli_1, Lang_45) had a run that "failed" with an empty error report and were
  re-evaluated once (`m1_review_onlydoc_redo1`); `analyze.py` uses the redo blocks. The first two whole-arm
  Only Doc attempts crashed early (Cli_15, Lang_14). Their logs were moved to
  `out/crashed_onlydoc_log_{1,2}.log` and are not used. The first of them overlapped with the Advanced Doc review
  container (LLM calls only, no checkout access).
- The upstream "reported" counters have a counting quirk: a failed run with an empty error report turns passing
  tests into M. `analyze.py` flags these blocks and reports the clean-subset sensitivity.
- Nothing outside `m1_test_review/` was changed except the new `data/prompts/rq1/*m1_review_*` completion files
  and their `data/rq1/logs`/results outputs. No change to `run/` or upstream files.
