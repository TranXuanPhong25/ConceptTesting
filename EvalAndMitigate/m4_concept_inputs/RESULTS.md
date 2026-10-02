# m4_concept_inputs: results

Setup: Gemini 2.5 Flash (thinking off), temperature 0, 78 focal methods from 60 Defects4J bugs. Both arms use the
Advanced docstring unchanged, with an appended list of up to 12 input classes and no expected results:
- **Concept-Inputs** (`m4_concept_inputs`): the input side of m3's C1-C8 (+C0) spec tables.
- **Placebo-Inputs** (`m4_placebo_inputs`): the same method's placebo spec (naming, performance, logging, …), stripped the
  same way and matched in item count.

Tests are generated with the unchanged pipeline (`WITH_CODE=0`). Counts are the upstream "reported" counters,
percentages are over compiled tests, and red-prec = E / (E + FP). Configs are compared on the **intersection of clean
methods: 75 of 78**. Excluded are Cli_8 (glitched in Advanced and in both arms), Lang_11 (all configs) and Lang_4
(Advanced). Everything below comes from `python3 m4_concept_inputs/analyze.py`; the full output is in `out/analysis.txt`.

## Short answer
**Concept-guided inputs do not help.** Taking the expected outcomes out of m3's rules removes most of m3's
misguidance, but the inputs alone do not add detection.
- **Against Advanced Doc.** Methods with ≥1 E are **30 vs 30** (9 gained, 9 lost, p = 1.0). The list makes the model
  write **51% more compiled tests** (1615 vs 1069), yet E barely moves (97 vs 95). FP rises by 129 and M by 16, so
  **red-precision falls from 0.262 to 0.196**. Methods with ≥1 M: 7 vs 3 (4 gained, 0 lost, p = 0.125, not significant).
  M tests: 25 vs 9. Most of that sits in Cli_1 (14 vs 7), which is M in every config. Without Cli_1 and Lang_57 the
  M tests are 5 vs 1.
- **Against the placebo.** Methods with ≥1 E: 30 vs 29 (8 gained, 7 lost, p = 1.0). Methods with ≥1 M: 7 vs 4
  (p = 0.375). The placebo is level with Advanced Doc: ≥1 E 29 vs 30 and ≥1 M 4 vs 3, with red-prec 0.227. So the
  bug-relevant input classes give no measurable detection gain over an irrelevant list of the same length. If
  anything, they cost precision.
- **Against m3 (same tables used as oracles).** Methods with ≥1 M fall from 16 to 7, and M tests from 48 to 25
  (74-method intersection). Methods with ≥1 E rise from 22 to 30. So m3's harm came from the expected-outcome side of
  the rules, as m3 concluded. With that side removed, the arm returns to Advanced Doc's level, not above it.
- **Noise.** Advanced Doc and each arm are single runs. Between any two of Advanced Doc, Concept-Inputs and
  Placebo-Inputs, 15-18 of 75 methods switch their ≥1 E status (in both directions), while the totals stay within ±1.
  All E differences here are within that run-to-run noise. The M-method difference (4 vs 0 discordant) is small
  too, and only suggestive.

## Main table (intersection, 75 methods)

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc (reference) | 1269 / 1166 | 10 (0.86%) | 77 (6.60%) | 281 (24.10%) | 0.215 | 5 | 27 |
| Advanced Doc | 1239 / 1069 | 9 (0.84%) | 95 (8.89%) | 268 (25.07%) | 0.262 | 3 | 30 |
| **Concept-Inputs** | 1788 / 1615 | **25 (1.55%)** | 97 (6.01%) | 397 (24.58%) | **0.196** | 7 | 30 |
| Placebo-Inputs | 1372 / 1235 | 8 (0.65%) | 83 (6.72%) | 282 (22.83%) | 0.227 | 4 | 29 |

Without Gson_4 (one bug, 6 methods), which leaves 69 methods:

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc (reference) | 1190 / 1090 | 10 (0.92%) | 45 (4.13%) | 266 (24.40%) | 0.145 | 5 | 21 |
| Advanced Doc | 1153 / 1010 | 9 (0.89%) | 69 (6.83%) | 262 (25.94%) | 0.208 | 3 | 25 |
| Concept-Inputs | 1682 / 1540 | 25 (1.62%) | 64 (4.16%) | 380 (24.68%) | 0.144 | 7 | 25 |
| Placebo-Inputs | 1291 / 1160 | 8 (0.69%) | 50 (4.31%) | 271 (23.36%) | 0.156 | 4 | 23 |

Gson_4 accounts for E 33 of Concept-Inputs' 97, 33 of the placebo's 83, 26 of Advanced's 95 and 32 of Only Doc's 77.
All four configs have no M there. Without Gson_4 the E-test picture turns against both arms: Concept-Inputs has
64 vs 69 E tests and red-prec 0.144 vs 0.208. Method-level E is still equal (25 vs 25).

Each arm on its own clean methods (76 each; Cli_8 and Lang_11 glitched): Concept-Inputs M 25, E 97, FP 401,
red-prec 0.195, 7 / 30 methods. Placebo-Inputs M 8, E 83, FP 286, red-prec 0.225, 4 / 29 methods.
Raw (78, glitched included): Concept-Inputs M 34, E 97; Placebo-Inputs M 17, E 83.

## Exact McNemar on per-method booleans (intersection; "lost" = only the second config has it)

| comparison | methods ≥1 E | methods ≥1 M |
|---|---|---|
| Concept-Inputs vs Advanced Doc | 30 vs 30: lost 9, gained 9, p = 1.000 | 7 vs 3: lost 0, gained 4, p = 0.125 |
| Concept-Inputs vs Placebo-Inputs | 30 vs 29: lost 7, gained 8, p = 1.000 | 7 vs 4: lost 1, gained 4, p = 0.375 |
| Placebo-Inputs vs Advanced Doc | 29 vs 30: lost 8, gained 7, p = 1.000 | 4 vs 3: lost 0, gained 1, p = 1.000 |
| Concept-Inputs vs Only Doc | 30 vs 27: lost 6, gained 9, p = 0.607 | 7 vs 5: lost 3, gained 5, p = 0.727 |
| *without Gson_4 (69):* Concept-Inputs vs Advanced | 25 vs 25: lost 9, gained 9, p = 1.000 | 7 vs 3: lost 0, gained 4, p = 0.125 |
| *without Gson_4 (69):* Concept-Inputs vs Placebo | 25 vs 23: lost 6, gained 8, p = 0.791 | 7 vs 4: lost 1, gained 4, p = 0.375 |

## Which methods moved (vs Advanced Doc)
- Concept-Inputs, ≥1 E gained (9): Codec_6.read, Csv_16.iterator, Lang_38.format, Lang_3.createNumber,
  Lang_46.escapeJava, Lang_47.appendFixedWidthPadRight, Lang_51.toBoolean, Lang_60.indexOf, Lang_60.contains.
  ≥1 E lost (9): Gson_15.value, Gson_7.nextInt, Lang_19.translate, Lang_1.createNumber, Lang_21.isSameLocalTime,
  Lang_28.translate, Lang_35.add, Lang_46.escapeJava (the other overload), Lang_7.createNumber.
- Placebo-Inputs, ≥1 E gained (7): Cli_1, Codec_18, Codec_6, Gson_4 (a sixth method), Lang_47, Lang_51, Lang_59.
  Lost (8): Gson_15, Gson_7, Lang_21, Lang_28, Lang_35, Lang_45, Lang_46, Lang_63. Codec_6, Lang_47 and Lang_51 are
  gained by both arms, and Gson_15, Gson_7, Lang_21, Lang_28, Lang_35 and Lang_46 are lost by both. This pattern
  looks like "any appended list changes the test mix", not like a concept effect.
- Concept-only E gains that trace to a listed item (manual check of the E tests against the list): Csv_16
  (bug C8; item "calling iterator() multiple times" → `testIterator_MultipleCalls`), Lang_38 (C8; items with
  `mTimeZoneForced` true → 2 E), Lang_60.indexOf (item "empty StrBuilder"), and Lang_60.contains (item "internal
  buffer is null"; the buggy loop runs to capacity). Lang_3, Lang_46 and Lang_51 are not traceable to an item.
  So the list does steer the model to bug-relevant inputs in a few methods. It loses a similar number of methods
  elsewhere, and the net is zero.

### Misguided methods (M tests per method)
- Advanced Doc: Cli_1 7, Lang_57 1, Lang_5 1.
- Concept-Inputs: Cli_1 14, Lang_57 6, Lang_5 1, plus 4 new methods with 1 M each. By manual check:
  - **Gson_12.skipValue**: from the item "Internal `stack` or `pathNames` arrays are null". The stripped
    parenthetical said "though this should not happen". The test nulls the field by reflection and asserts
    NPE ("Assuming NullPointerException").
  - **Lang_40.containsIgnoreCase**: from the C7 item `str = "Straße", searchStr = "strasse"`. The model
    supplied its own oracle, `assertTrue` (full case folding), which matches the buggy `toUpperCase` implementation.
  - **Lang_41.getShortClassName**: `"[]" → "[]"`, next to the item "array type encoding".
  - **Lang_63.formatPeriod**: "30 days across months". It is not tied to an item.

  None of these comes from a stated expected outcome (there are none in the list). Two are an input item plus the
  model's own assumption about an unstated case. That is the same mechanism m1 found, now triggered by the list.
- Placebo-Inputs: Cli_1 1, Lang_57 5, Lang_5 1, Lang_24 1 (an `isNumber` edge-case test under the "readability" item).
- Lang_5 `toLocale("_US") → IAE` is M in all three runs, so it comes from the Advanced docstring, not from the list.
  M tests without the two methods that are M in every config (Cli_1, Lang_57): Only Doc 3, Advanced 1,
  Concept-Inputs 5, Placebo-Inputs 2.

## Per bug concept (manual labels, `m2_concept_diag/manual_labels.json`, intersection)

Cells: methods with ≥1 E / ≥1 M, then (M/E/FP tests; red-prec). A method can be in more than one row.

| concept | n | Only Doc | Advanced Doc | Concept-Inputs | Placebo-Inputs |
|---|---|---|---|---|---|
| C0 | 7 | E3 M1 (1/3/13; 0.19) | E3 M1 (7/3/11; 0.21) | E3 M2 (15/6/27; 0.18) | E3 M1 (1/8/27; 0.23) |
| C1 null | 12 | E6 M1 (1/15/19; 0.44) | E6 M0 (0/11/29; 0.28) | E6 M0 (0/11/29; 0.28) | E6 M0 (0/13/22; 0.37) |
| C2 empty | 3 | E1 M0 (0/8/9; 0.47) | E2 M0 (0/5/7; 0.42) | E2 M0 (0/6/8; 0.43) | E2 M0 (0/6/10; 0.38) |
| C3 boundary | 17 | E6 M1 (1/15/105; 0.12) | E6 M0 (0/22/102; 0.18) | E7 M1 (1/15/151; 0.09) | E8 M0 (0/17/106; 0.14) |
| C4 error contract | 18 | E7 M2 (2/33/79; 0.29) | E9 M1 (1/32/70; 0.31) | E6 M1 (1/34/108; 0.24) | E8 M1 (1/35/62; 0.36) |
| C5 format | 10 | E2 M0 (0/8/50; 0.14) | E6 M1 (1/27/36; 0.43) | E5 M2 (2/24/38; 0.39) | E4 M2 (2/10/27; 0.27) |
| C6 numeric | 4 | E3 M1 (1/3/21; 0.12) | E3 M0 (0/6/28; 0.18) | E2 M0 (0/5/50; 0.09) | E2 M0 (0/2/19; 0.10) |
| C7 chars/locale | 11 | E0 M0 (0/0/36; 0.00) | E1 M1 (1/1/33; 0.03) | E0 M2 (2/0/53; 0.00) | E0 M1 (1/0/42; 0.00) |
| C8 state | 6 | E1 M1 (6/1/13; 0.07) | E0 M1 (1/0/16; 0.00) | **E2** M1 (6/3/14; 0.18) | E0 M1 (5/0/24; 0.00) |

(The C1 row of Advanced Doc and Concept-Inputs is identical by coincidence; the per-method values differ.)
- C8 state is the only concept where Concept-Inputs is ahead of both Advanced and the placebo (2 vs 0 vs 0 E-methods:
  Csv_16 and Lang_38, both traced to items above). That is 2 methods.
- C3 boundary, m3's one gain, does not repeat: E-methods 7 vs Advanced 6 and placebo 8, with 49 more FP.
- C7 still gets no effective test. Its M-methods are Lang_40 (the listed Straße input, new) and Lang_5 (M in all three runs).
- C4 loses E-methods against both Advanced and the placebo (6 vs 9 vs 8). This is within noise, but it is not a gain.
- Is the bug's own concept in the list? For 63 of the 68 methods whose bug concept is in C1-C8, the list has at least
  one item of that concept. On those 63, E-methods are Concept-Inputs 23, Placebo 22, Advanced 23, and M-methods
  5, 3, 2. Listing the right concept does not turn into detection.

## Appended section

| | items per method (min / median / max, total) | chars (min / median / max, mean) |
|---|---|---|
| Concept-Inputs | 4 / 12 / 12, 872 | 401 / 1073 / 2058, 1076 |
| Placebo-Inputs | 4 / 12 / 12, 872 | 378 / 774 / 1221, 793 |
| Advanced docstring (unchanged prefix) | | 424 / 1153 / 68108, 3802 |

Item counts are matched per method. C0 items are 129 vs 122: where the placebo's own C0 had too few items, P items
fill the gap. The placebo section is shorter (its items, such as "Method name `create`", are shorter), and it
produces fewer extra tests (+16% compiled vs +51%). A length effect therefore cannot be ruled out as part of the
concept arm's extra FP. Within each arm, E-methods by section-length tercile are not monotone:
Concept-Inputs 8/25, 12/25, 10/25; Placebo-Inputs 14/25, 11/25, 4/25.

Stripping check. `inputs.py selftest` asserts that no outcome wording survives in any selected item of either arm
(all 78 methods), that totals match, and that the Advanced docstring is a byte-exact prefix. I also read all 20
sections of a random 10-method sample (`out/sample_check.txt`) and a keyword scan of all 872 concept items. Two
leaks found in development were fixed before any generation: "(and not caught by noOfItems <= 0)" and "The method
does not modify the state of …". What remains are input-class labels such as "invalid number format (e.g., \"abc\")"
("valid/invalid" were kept on purpose), setup preconditions naming internal fields (`mTimeZoneForced`,
`pathNames`), and some vacuous items ("Method call").

## Reference: the same spec tables as oracles (m3) vs as inputs (74 methods, also excluding m3's Lang_12)

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Advanced Doc | 1217 / 1062 | 9 (0.85%) | 95 (8.95%) | 266 (25.05%) | 0.263 | 3 | 30 |
| Concept-Inputs | 1768 / 1595 | 25 (1.57%) | 97 (6.08%) | 395 (24.76%) | 0.197 | 7 | 30 |
| Placebo-Inputs | 1353 / 1216 | 8 (0.66%) | 83 (6.83%) | 279 (22.94%) | 0.229 | 4 | 29 |
| m3 Concept-Spec | 1582 / 1408 | 48 (3.41%) | 100 (7.10%) | 262 (18.61%) | 0.276 | 16 | 22 |

## LLM calls

| arm | new calls in m4 | reused inputs (calls made earlier) | total per arm |
|---|---|---|---|
| Concept-Inputs | 78 test generation; input extraction 0 (deterministic) | m3 `specs_spec.jsonl` 87, Advanced docstrings 78 | 243 |
| Placebo-Inputs | 78 test generation; 0 | m3 `specs_placebo.jsonl` 82, Advanced docstrings 78 | 238 |
| smoke (Cli_32, Lang_20, Lang_40) | 3 test generation | | |
| Advanced Doc (reference) | | docstrings 78 + test generation 78 | 156 |

All 78 completions of each arm contain a Java block. 429 retries inside the shim are not counted (the placebo
generation logged 2 `RESOURCE_EXHAUSTED` retries). The evaluation's `_err_msg_with_completion` file holds the same
completions, so it adds no calls. The placebo control has the same budget up to m3's spec re-asks (238 vs 243).

## Caveats
- **Single runs.** Advanced Doc, both arms and m3 are one T=0 run each. With 15-18 of 75 methods flipping ≥1 E
  between any two of them, method-level E differences of a few methods are noise. Nothing here reaches significance.
  The M-side count (4 new M-methods, 0 lost) is suggestive at best, with p = 0.125.
- n = 75 methods / 57 bugs in the intersection, and the methods are not independent. Gson_4 has 6 methods (reported
  with and without it) and Lang_30 has 5. Cli_1 and Lang_57 are M in every config. Cli_1 alone accounts for 14 of the
  concept arm's 25 M tests.
- The stripping is a keyword filter. It is conservative (it drops 5.8% of concept rules and 10.9% of placebo rules
  whole), but "valid/invalid" labels and internal field names survive, and so do facet labels such as
  "invalid or unusual inputs", which hint at error handling. A stricter neutralisation would be a different arm.
- The placebo is matched in item count, not in section length (793 vs 1076 chars on average), and its own C0 core
  logic can contain relevant inputs (for example `str = null` for Lang_16/Lang_27). This makes the placebo slightly
  "less irrelevant" than its P facets suggest.
- No prompt tuning. The cap (12) and the header wording were fixed before the smoke run and not changed after it.
  The smoke run (3 methods) gave M 3, E 2 (Cli_32 E 2 / M 1; Lang_40 M 2 via the Straße item). It was used only to
  check the pipeline.
- Infrastructure. The Concept-Inputs evaluation ran as a single pass over all 78 methods. The host-side driver
  (`eval_parts.py` and the docker client) died with my session partway through. The container finished on its own,
  and I registered its complete log by hand as one part (`out/m4_concept_inputs_parts.json`, after checking that the
  78 block signatures match the records and that the last block has its counters). Its console capture
  (`out/eval_m4_concept_inputs.console`) is therefore truncated. The placebo evaluation hit the known upstream
  `ZeroDivisionError` right after Cli_15 (no test compiled). `eval_parts.py` kept that finished block and resumed at
  method 2 (`out/m4_placebo_inputs_parts.json`: Cli_15; methods 2-78). Glitched blocks (Cli_8 and Lang_11 in both
  arms) are excluded per the BASELINES rule and were not re-run.
- Leakage: the prompts contain the Advanced docstring and the input items only, derived from the buggy-code context.
  No patch, fixed version, trigger test or label is in them. The pipeline uses `WITH_CODE=0`. None of the 78 prompts of either arm contains a 60-char window from the middle
  of the focal body (whitespace-normalised check).
- Files written outside `m4_concept_inputs/`: `data/prompts/*m4_{concept,placebo}_inputs*.jsonl`,
  `data/prompts/rq1/*m4_*`, `data/rq1/logs/*m4_*`, `data/rq1/results_test/chatgpt/*m4_*`, and the pipeline's own
  `run/out/{prompt,testgen,eval}_m4_*`. No change to `run/`, upstream files or other method folders.
