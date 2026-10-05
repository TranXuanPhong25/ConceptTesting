# m9_concept_advanced: results

**Verdict: null.** Adding a C1-C8 concept checklist to Part 1 of the verbatim Advanced prompt does not change
misguidance or bug-catching relative to an equal-length placebo checklist: ≥1 E 23 vs 25 (p=0.80), ≥1 M 7 vs 9
(p=0.73).
- The checklist does steer the bug hunt: the bug's labelled concept is flagged far above the base rate.
- But this does not improve the Part 2 "corrected implementation" (fixed methods 14 vs 11, p=0.51).
- Neither inserted item beats the unmodified prompt. Both tend to fix fewer bugs in Part 2 than the A/A re-run (17).
- The A/A re-run shows how noisy single runs are: 11 methods flip on ≥1 E between two runs of the same Advanced
  prompt.

All numbers are from `out/analysis.txt` (`python3 m9_concept_advanced/analyze.py`). One run per arm; Gemini 2.5
Flash, thinking off.
- Docstrings: T=0, no max_tokens, as in the notebook.
- Tests: the unchanged upstream test generation (no temperature) and evaluation.
- Comparison: on the intersection of the clean methods of all four configs (70).

## Main table (intersection of clean methods, 70)
| config | generated / compiled | M | E | FP | red-prec | ≥1 M | ≥1 E |
|---|---|---|---|---|---|---|---|
| Advanced Doc (original run) | 1160 / 1016 | 9 (0.89%) | 93 (9.15%) | 256 (25.20%) | 0.266 | 3 | 29 |
| m9_adv_rerun (A/A) | 1225 / 1122 | 11 (0.98%) | 82 (7.31%) | 302 (26.92%) | 0.214 | 4 | 26 |
| **m9_concept** | 1054 / 943 | 18 (1.91%) | 94 (9.97%) | 228 (24.18%) | 0.292 | 7 | 23 |
| m9_placebo | 1147 / 1064 | 13 (1.22%) | 97 (9.12%) | 281 (26.41%) | 0.257 | 9 | 25 |

Glitched methods (empty error report), excluded from the intersection:

| config | glitched (each config on its own clean methods: n / ≥1 M / ≥1 E) |
|---|---|
| Advanced | 3 (75 / 3 / 30) |
| rerun | 2 (76 / 4 / 27) |
| concept | 4: idx 0, 5, 27, 64 (74 / 7 / 23) |
| placebo | 4 (74 / 9 / 26) |

They were not re-evaluated: a `--redo` would have run Docker while another agent was using it.

## Exact McNemar (methods with ≥1 E / ≥1 M; "only a / only b")
| contrast | ≥1 E | ≥1 M |
|---|---|---|
| **primary: concept vs placebo** | 23 vs 25: 7 / 9, **p=0.80** | 7 vs 9: 3 / 5, **p=0.73** |
| concept vs adv_rerun | 23 vs 26: 6 / 9, p=0.61 | 7 vs 4: 5 / 2, p=0.45 |
| concept vs original Advanced | 23 vs 29: 6 / 12, p=0.24 | 7 vs 3: 5 / 1, p=0.22 |
| placebo vs adv_rerun | 25 vs 26: 4 / 5, p=1 | 9 vs 4: 6 / 1, p=0.13 |
| **A/A: adv_rerun vs original Advanced** | 26 vs 29: 4 / 7, p=0.55 | 4 vs 3: 2 / 1, p=1 |

**A/A noise.** The re-run used the same prompt and the same call settings. 58/78 of its docstrings are
byte-identical to the original run, yet 11 of 70 methods flip on ≥1 E and 3 on ≥1 M. The ≥1 E flips:

| direction | methods |
|---|---|
| only rerun | Codec_6, Gson_4, Lang_57, Lang_60 |
| only original | Gson_15, Gson_7, Lang_21, Lang_46, Lang_47, Lang_63, Lang_7 |

Most of this noise comes from test generation, which upstream runs at the default temperature. Any
single-run difference of up to about 6 methods on ≥1 E is within this noise. Red-precision moved
0.266 → 0.214 between the two A/A runs.

## Sensitivity (same contrasts)
| subset | n | Adv ≥1 M / ≥1 E | rerun | concept | placebo | concept vs placebo: ≥1 E p / ≥1 M p |
|---|---|---|---|---|---|---|
| all clean | 70 | 3 / 29 | 4 / 26 | 7 / 23 | 9 / 25 | 0.80 / 0.73 |
| without Gson_4 and Cli_1 | 63 | 2 / 24 | 3 / 20 | 6 / 17 | 8 / 18 | 1 / 0.73 |
| without the 7 body-in-test-prompt methods | 63 | 3 / 28 | 4 / 25 | 7 / 23 | 9 / 25 | 0.80 / 0.73 |
| without both | 56 | 2 / 23 | 3 / 19 | 6 / 17 | 8 / 18 | 1 / 0.73 |

- The body-in-test-prompt methods are those whose docstring carries ≥40-char windows of the buggy focal body
  (m5 `body_leaks`). They are dropped for all arms: Gson_8, Lang_1, Lang_27, Lang_36, Lang_3, Lang_44, Lang_58.
  Per arm, concept has 7, placebo 3 and rerun 3, the same 3 as the original Advanced run. They are mostly the
  repetition-loop fallbacks, where the whole analysis becomes the "docstring".
- Dropping them leaves the concept and placebo method-level counts unchanged; rerun and Advanced lose one ≥1 E
  method each. The concept arm's extra M methods (Codec_17, Lang_19, Lang_35 ×2, Lang_47) are not caused by the
  leaked body.
- concept vs Advanced, without both: ≥1 E 17 vs 23 (p=0.21), ≥1 M 6 vs 2 (p=0.22).

M methods (M tests):

| config | methods |
|---|---|
| Advanced | Cli_1:7, Lang_57:1, Lang_5:1 |
| rerun | Cli_1:7, Lang_40:1, Lang_5:2, Lang_63:1 |
| concept | Cli_1:11, Codec_17:1, Lang_19:2, Lang_35:1+1, Lang_47:1, Lang_5:1 |
| placebo | Cli_1:1, Codec_7:5, Lang_35:1+1, Lang_41:1, Lang_57:1, Lang_5:1, Lang_63:1, Lang_7:1 |

## Mechanism 1: does Part 1 name the bug's concept? (`m2_concept_diag/manual_labels.json`, 70 methods with a C1-C8 label)
- **Checklist output.** Parsed in 72/78 concept completions. It flags 3.5 of 8 concepts per method:
  C4 59, C1 50, C3 39, C2 34, C8 29, C5 23, C7 22, C6 19.
- **It targets the bug's concept.** The labelled concept is flagged in 52/75 (method, labelled concept) pairs
  (0.69). The other concepts of the same methods are flagged in 192/437 (0.44); Fisher p=5e-5. In 44/70 methods,
  at least one labelled concept is flagged.
- **Keyword proxy** (weak; it saturates on null/exception): items 1-2 mention the labelled concept in 58 (rerun),
  50 (concept), 52 (placebo) of 70 methods.
- The flags are approximate: free-text findings are classed as "no issue" by phrase matching
  (`analyze.checklist_flags`).

## Mechanism 2: Part 2 fix rate (`fixrate.py`; trigger tests used offline only)
**Harness check.** Substituting the fixed checkout's focal methods fixes 50/60 bugs. The other 10 need changes
outside the focal methods: Cli_1, Codec_13, Csv_16, Gson_4, Gson_7, Gson_8, Lang_30, Lang_46, Lang_4, Lang_64.
Substituting the buggy methods fixes 0/60. All 120 shared checkouts were unmodified afterwards
(`git diff --quiet HEAD -- <src dir>`).

| arm | Part 2 found | compiled | fixed methods (of 78) | any trigger passes | bugs fixed (of 60) | bugs fixed (of 50 reproducible) |
|---|---|---|---|---|---|---|
| adv_rerun | 74 | 68 | **17** | 19 | **19** | 19 |
| concept | 72 | 64 | **14** | 17 | **14** | 14 |
| placebo | 75 | 70 | **11** | 17 | **12** | 11 |

| contrast | fixed methods: only first / only second | p | fixed bugs: only first / only second | p |
|---|---|---|---|---|
| concept vs placebo | 6 / 3 | 0.51 | 6 / 4 | 0.75 |
| concept vs rerun | 3 / 6 | 0.51 | 3 / 8 | 0.23 |
| placebo vs rerun | 3 / 9 | 0.15 | 3 / 10 | 0.09 |

**Does a fixed Part 2 lead to E?** Within each arm, compare methods whose Part 2 fixes the bug with those whose
Part 2 does not (clean intersection; Fisher test on ≥1 E):

| arm | ≥1 E: fixed / not fixed | p | ≥1 M: fixed / not fixed |
|---|---|---|---|
| rerun | 9/16 vs 17/54 | 0.085 | 0/16 vs 4/54 |
| concept | 6/11 vs 17/59 | 0.16 | 0/11 vs 7/59 |
| placebo | 4/9 vs 21/61 | 0.71 | 1/9 vs 8/61 |

The direction supports the "corrected implementation" hypothesis: a correct Part 2 tends to give an E and almost
never an M. Only about a fifth of methods get a correct Part 2, though, and the inserted checklists lower that
rate rather than raise it.

## Repetition loops and cost (cap: $5, raised to $8 by the user mid-run)
**Docstring loops.** Some completions run into a `000…` loop and hit the 65,536-token output limit. The notebook
then uses the whole text as the docstring. Upstream behaviour is kept for all arms: no max_tokens, no re-ask.

| arm | methods with a loop | cost |
|---|---|---|
| rerun | 3: Lang_36, Lang_3, Lang_44 (the same 3 as the original run) | $0.494 |
| concept | 6: Lang_1, Lang_27, Lang_36, Lang_3, Lang_44, Lang_58 | $0.989 |
| placebo | 3: Lang_1, Lang_36, Lang_58 | $0.495 |

**Runaway test completions** (>50k chars, mostly digits):

| arm | methods |
|---|---|
| rerun | 2: Lang_3, Lang_44 |
| concept | 4: Lang_1, Lang_36, Lang_3, Lang_44 |
| placebo | 2: Lang_16, Lang_3 |
| original | 3: Lang_16, Lang_36, Lang_58 |

**Spend.** Docstring spend is exact, from the logged `usage_metadata`. Test-generation spend is estimated, with
digits at one token each; the estimate is within 4% of `count_tokens` on the baseline
(`out/count_tokens_baseline_testgen.json`).

| item | spend |
|---|---|
| docstrings, rerun | $0.948 (82 API attempts, 4 × 429) |
| docstrings, concept | $1.517 |
| docstrings, placebo | $1.074 |
| test generation, rerun | $0.816 |
| test generation, concept | $1.219 |
| test generation, placebo | $0.849 |
| smoke test generation | $0.047 |
| **total** | **$6.47** |

**Calls.** One docstring call per method and arm (78 × 3). One test-generation call per method and arm (78 × 3),
plus 3 × 3 smoke calls. There were no re-asks.

**Budget history.**
- The $5 cap held through concept test generation, which ended at $4.81.
- The user then approved a raise to $8. The coordinator made the edit in its session; `m9.py` CAP is 8.0.
- Placebo and rerun test generation ran after that.
- Internal limits: the docstring stop went 2.5 → 3.9 and the test-generation reserve 0.8 → 1.1 per arm.

## Caveats
- Single runs; n=70 methods. The A/A noise (11 ≥1 E flips) is as large as every contrast here.
- The concept arm had more repetition loops (6 vs 3). They cost money and put the body into the test prompt, but
  the sensitivity rows show no effect on the method-level counts.
- The Part 1 flags are parsed from free text; the keyword proxy is weak.
- Fix rate is defined on trigger tests only. 10 bugs cannot be fixed by focal-only substitution (see the
  harness check).
- Gson_4 (6 methods) and Cli_1 (M in every config) are handled in the sensitivity rows.

## Written outside this folder
All new files with the `m9_` name; no existing file was changed. Nothing was committed.
- `data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m9_{adv_rerun,concept,placebo}[_smoke].jsonl`;
- `data/prompts/rq1/*m9_*`;
- `data/rq1/logs/*m9_*`;
- `data/rq1/results_test/chatgpt/*m9_*`;
- `run/out/{prompt,testgen,eval}_m9_*`;
- the Docker volume `m9scratch`.

The evaluations, like every pipeline evaluation, write generated tests into the checkouts' test directories. Main
sources were verified unchanged.

## Reproduce
See `README.md`. The full sequence:
- `run.sh smoke`;
- `run.sh docs`;
- `run.sh tests concept`, then `run.sh evals concept`;
- `run.sh tests placebo`, then `run.sh evals placebo`;
- `run.sh tests adv_rerun`, then `run.sh evals adv_rerun`;
- `run.sh fixrate`;
- `run.sh analyze`.
