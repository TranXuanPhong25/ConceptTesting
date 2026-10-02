# m5_blind_concept_spec: results

Setup: Gemini 2.5 Flash (thinking off), temperature 0, 78 focal methods from 60 Defects4J bugs, run 2026-09-30/10-01.
Both arms use m3's spec schema (C0 core logic + C1-C8), JSON table and renderer, and the unchanged Only Doc
test-generation pipeline (`WITH_CODE=0`). The spec-generation prompt has no focal method body:
- **A blind** (`m5_blind_concept`): declaration, signature and the upstream non-body class context only.
- **B blind+Javadoc** (`m5_blind_concept_javadoc`): A plus the method's original Javadoc, re-extracted from the buggy
  class code (none for Cli_15, Gson_8, Gson_12).

Counts are the upstream "reported" counters, percentages are over compiled tests, and red-prec = E / (E + FP).
Configs are compared on the **intersection of clean methods: 74 of 78**. Excluded are Cli_8 (glitched in Advanced, A
and B), Lang_11 (Only Doc, Advanced, B), Lang_12 (m3, A) and Lang_4 (Advanced). These are the same 74 methods as
m3's intersection. Everything below comes from `python3 m5_blind_concept_spec/analyze.py` (full output in
`out/analysis.txt`). The manual checks use `out/m_methods.txt` and the spec tables.

## Short answer
- **Hiding the body cuts the copying but does not stop it.** In A, methods with ≥1 M fall from 16 (m3) to 9
  (10 only in m3, 3 only in A, **p = 0.092**), and M tests fall from 48 to 29. Of the 13 methods where an m3 rule stated
  the buggy behaviour, the blind spec drops or reverses that rule in 9. In the other 4 (Codec_17, Lang_35, Lang_40,
  Lang_55) it states the same buggy behaviour without having seen the code. These are plausible defaults that happen
  to match the bug: `null → NullPointerException`, `add(null, null) → [null]`, `"Straße"` matches `"strasse"`, and
  `stop()` after `suspend()` sets a new stop time. A also adds one new case, Lang_38 (its rule ignores the time-zone
  conversion). So in 5 of A's 9 M-methods a spec rule states the asserted buggy behaviour, against 13 of 16 in m3.
  The other 4 are not attributable to the spec.
- **Blind specs do not beat Advanced Doc.**
  - A vs Advanced: methods with ≥1 E 24 vs 30 (p = 0.21), with ≥1 M 9 vs 3 (p = 0.070). FP rises to 481 (vs 266), so
    red-precision falls to 0.169 (vs 0.263). Without the code, the model guesses: "unspecified" is still rare (1.1% of
    rules, against 0.1% in m3), and the wrong guesses become FP tests.
  - B (with the Javadoc) is level with Advanced: ≥1 M 3 vs 3 (p = 1), ≥1 E 27 vs 30 (p = 0.63), red-precision 0.272 vs
    0.263, E tests 125 vs 95. The extra E tests are in Gson_4 (6 methods, one bug). Without Gson_4, B has E 60 vs 69
    and red-precision 0.159 vs 0.210.
- **The developer Javadoc is the better intent source.** B vs A: ≥1 M 3 vs 9 (8 only in A, 2 only in B,
  p = 0.11; on 67 methods without Gson_4 and Cli_1, 1 vs 8, p = 0.039). FP falls from 481 to 335 and red-precision rises
  from 0.169 to 0.272. ≥1 E is 27 vs 24 (p = 0.61). B vs m3: ≥1 M 3 vs 16 (p = 0.0023).
- **Noise.** All arms are single T=0 runs. m4 measured that 15-18 of 75 methods switch their ≥1 E status between two
  such runs. Here the discordant ≥1 E methods are 18 (A vs m3), 16 (A vs Advanced), 15 (B vs A) and 17 (B vs Advanced),
  in the same range. **None of the E differences is distinguishable from run-to-run noise.** The M-side differences
  are larger relative to their base, but only B vs m3 is clearly significant. A vs m3 (p = 0.092) is not.

## Main table (intersection, 74 methods)

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc | 1247 / 1166 | 10 (0.86%) | 77 (6.60%) | 281 (24.10%) | 0.215 | 5 | 27 |
| Advanced Doc (best baseline) | 1217 / 1062 | 9 (0.85%) | 95 (8.95%) | 266 (25.05%) | 0.263 | 3 | 30 |
| m3 Concept-Spec (sees code) | 1582 / 1408 | 48 (3.41%) | 100 (7.10%) | 262 (18.61%) | 0.276 | 16 | 22 |
| **A blind** | 1861 / 1730 | 29 (1.68%) | 98 (5.66%) | 481 (27.80%) | 0.169 | 9 | 24 |
| **B blind+Javadoc** | 1922 / 1711 | 24 (1.40%) | 125 (7.31%) | 335 (19.58%) | 0.272 | 3 | 27 |

Without Gson_4 (one bug, 6 methods; E in every config), 68 methods:

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc | 1168 / 1090 | 10 (0.92%) | 45 (4.13%) | 266 (24.40%) | 0.145 | 5 | 21 |
| Advanced Doc | 1131 / 1003 | 9 (0.90%) | 69 (6.88%) | 260 (25.92%) | 0.210 | 3 | 25 |
| m3 Concept-Spec | 1474 / 1306 | 48 (3.68%) | 44 (3.37%) | 250 (19.14%) | 0.150 | 16 | 16 |
| A blind | 1737 / 1613 | 29 (1.80%) | 56 (3.47%) | 449 (27.84%) | 0.111 | 9 | 18 |
| B blind+Javadoc | 1791 / 1602 | 23 (1.44%) | 60 (3.75%) | 317 (19.79%) | 0.159 | 2 | 22 |

Without Gson_4 and Cli_1 (Cli_1 is M in every config: m3 17, A 12, B 22 M tests), 67 methods:

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc | 1160 / 1082 | 9 (0.83%) | 44 (4.07%) | 265 (24.49%) | 0.142 | 4 | 20 |
| Advanced Doc | 1124 / 996 | 2 (0.20%) | 69 (6.93%) | 260 (26.10%) | 0.210 | 2 | 25 |
| m3 Concept-Spec | 1457 / 1289 | 31 (2.40%) | 44 (3.41%) | 250 (19.39%) | 0.150 | 15 | 16 |
| A blind | 1721 / 1597 | 17 (1.06%) | 56 (3.51%) | 445 (27.86%) | 0.112 | 8 | 18 |
| B blind+Javadoc | 1764 / 1575 | 1 (0.06%) | 60 (3.81%) | 312 (19.81%) | 0.161 | 1 | 22 |

Each arm on its own clean methods (76 each): A M 29, E 98, FP 493, red-prec 0.166, 9 / 24 methods; B M 24, E 131,
FP 342, red-prec 0.277, 3 / 28 methods.

## Exact McNemar on per-method booleans
"x / y" = methods with the property only in the first / only in the second config.

| comparison | 74 methods: ≥1 M | 74 methods: ≥1 E | 67 methods (no Gson_4, Cli_1): ≥1 M | 67: ≥1 E |
|---|---|---|---|---|
| **A vs m3 (primary)** | 9 vs 16: 3 / 10, p = 0.092 | 24 vs 22: 10 / 8, p = 0.81 | 8 vs 15: 3 / 10, p = 0.092 | 18 vs 16: 10 / 8, p = 0.81 |
| A vs Advanced Doc | 9 vs 3: 7 / 1, p = 0.070 | 24 vs 30: 5 / 11, p = 0.21 | 8 vs 2: 7 / 1, p = 0.070 | 18 vs 25: 4 / 11, p = 0.12 |
| B vs A | 3 vs 9: 2 / 8, p = 0.11 | 27 vs 24: 9 / 6, p = 0.61 | 1 vs 8: 1 / 8, p = 0.039 | 22 vs 18: 9 / 5, p = 0.42 |
| B vs m3 | 3 vs 16: 2 / 15, p = 0.0023 | 27 vs 22: 12 / 7, p = 0.36 | 1 vs 15: 1 / 15, p = 5.2e-4 | 22 vs 16: 12 / 6, p = 0.24 |
| B vs Advanced Doc | 3 vs 3: 2 / 2, p = 1.0 | 27 vs 30: 7 / 10, p = 0.63 | 1 vs 2: 1 / 2, p = 1.0 | 22 vs 25: 6 / 9, p = 0.61 |
| A vs Only Doc | 9 vs 5: 6 / 2, p = 0.29 | 24 vs 27: 5 / 8, p = 0.58 | 8 vs 4: 6 / 2, p = 0.29 | 18 vs 20: 5 / 7, p = 0.77 |

No correction for multiple comparisons. The only p-values below 0.05 are B vs m3 and, on the 67-method subset,
B vs A on M.

## Does the spec still state the bug? (manual check)

### m3's 13 spec-attributed M-methods, re-read in A and B
m3 RESULTS found an m3 rule stating the buggy behaviour in 11 M-methods, plus a looser match in 2 (Lang_30, Lang_40).
The table shows what the blind specs say for the same input class, with the method's outcome (M/E tests) in each arm.

| method | m3 rule (buggy) | A rule | A | B rule | B |
|---|---|---|---|---|---|
| Codec_7 | output chunked with CRLF | "will not contain line separators" | E9 | 76-char blocks separated by CRLF, as the buggy version's Javadoc says, but no CRLF under 76 chars | E5 |
| Codec_13 | null → NPE | null → false | E10 | null → false | E9 |
| Codec_17 | null → NPE | **null → NPE** | **M1** | null → null (Javadoc) | E1 |
| Csv_4 | internal headerMap null → NPE | "NPE … or an empty map" (hedged) | 0 | "likely NPE … or …" (hedged) | 0 |
| Lang_5 | blanket IAE that covers `_US` | no rule on a leading `_` | 0 | `_GB_…` inputs are accepted | 0 |
| Lang_19 | `"&#"` → IndexOutOfBounds | no rule on a trailing `&#` | E3 | `"abc&#"` → 0 | 0 |
| Lang_33 | null element → NPE | null element → null class | E2 | null element → null class | E3 |
| Lang_35 add(T[],int,T) | `add(null,0,null)` → `[null]` | **`add(null,0,null)` → `{null}` (Object[])** | **M1** | both null → IAE | 0 |
| Lang_35 add(T[],T) | `add(null,null)` → `[null]` | no rule for both null (non-primitive) | 0 | both null → IAE | E1 |
| Lang_47 PadLeft | null with null nullText → NPE | null obj → nullText padded | E1 | null obj → nullText padded | 0 |
| Lang_55 | stop() from SUSPENDED sets stopTime | **same** | **M1** | SUSPENDED → IllegalStateException (Javadoc: "if the StopWatch is not running"; wrong for the fixed version too) | 0 |
| Lang_30 indexOfAnyBut(String,String) | char-based surrogates (looser) | `"😀abc"`, `"😀"` → 2 (code points) | 0 | no surrogate rule | 0 |
| Lang_40 | depends on default-locale upper-casing (looser) | **`"Straße"` / `"strasse"` → true** | **M1** | unspecified | 0 |

In A, 9 of these 13 buggy rules are gone. 4 remain, and those 4 methods are still M. In B, none of these methods is
M. B's Javadoc corrected Codec_17, Lang_35 and Lang_55, and also made Lang_40 unspecified. B still states the buggy
CRLF chunking for Codec_7, because the buggy version's own Javadoc documents it; there the tests on short inputs
(which the buggy code also terminates with CRLF) caught the bug instead.

### All M-methods of the blind arms

| arm | M-method (M tests) | spec rule stating the asserted buggy behaviour? |
|---|---|---|
| A | Codec_17 (1) | yes: `bytes` null → NPE (fixed: returns null) |
| A | Lang_35 add(T[],int,T) (1) | yes: `add(null, 0, null)` → `{null}` with Object component type (fixed: IAE) |
| A | Lang_38 format(Calendar, StringBuffer) (2) | yes: `new GregorianCalendar(2023, OCT, 26, 10, 30)` with a UTC FastDateFormat → `"2023-10-26 10:30:00"`. This ignores the conversion from the calendar's zone, which the fixed version does |
| A | Lang_40 (1) | yes: `"Straße"` contains `"strasse"` → true (the test copies the rule) |
| A | Lang_55 (1) | yes: stop() from SUSPENDED sets stopTime to now (the test asserts a new, later stop time) |
| A | Cli_1 (12), Lang_57 (9) | no: the tests manipulate internal maps/sets via reflection (M in m3 and Advanced too) |
| A | Gson_8 (1) | no: the test assumes InstantiationException for an interface; the spec is silent |
| A | Lang_36 isNumber (1) | no: `"123."` → false is the test's own assumption |
| B | Gson_4 value(String) (1) | yes: C4 "value() without beginArray()/beginObject() → IllegalStateException" (pre-RFC 7159 behaviour; not in the Javadoc). In the same method, 11 E tests assert the fixed top-level behaviour |
| B | Cli_1 (22) | no (as above) |
| B | Lang_36 createNumber (1) | no: `"123."` → NFE is the test's own assumption |

So a spec rule matching the bug is behind 13 of 16 M-methods in m3, 5 of 9 in A and 1 of 3 in B. Without the body,
such rules come from defaults that coincide with the buggy behaviour, not from reading it.

## "Unspecified" and the spec tables (all 78 methods)

| | m3 Concept-Spec | A blind | B blind+Javadoc |
|---|---|---|---|
| rules (per method) | 1753 (22.5) | 1655 (21.2) | 1725 (22.1) |
| `expected` = "unspecified" | 2 (0.1%), 2 methods | 19 (1.1%), 8 methods | 19 (1.1%), 9 methods |
| `expected` mentions unspecified / undefined / implementation-dependent | 14 (0.8%) | 41 (2.5%) | 52 (3.0%) |
| facets "not applicable" (methods) | C1 3, C2 19, C3 12, C5 23, C6 50, C7 20 | C1 5, C2 16, C3 15, C5 13, C6 53, C7 21 | C1 7, C2 15, C3 9, C4 1, C5 20, C6 49, C7 19 |
| source field (top) | name-context 1034, assumed 366, framework 217 | name-context 397, assumed 271, name-context+assumed 251, framework 205 | **javadoc 730**, name-context 399, assumed 332 |
| missing keys | 0 | 0 | 0 |

The stronger encouragement ("prefer unspecified to an expectation that the evidence does not support") raised the
explicit "unspecified" share from 0.1% to 1.1%. The model still writes concrete expectations for almost everything,
even without the code. A's rules more often cite combined or "assumed" sources. In B, 42% of the rules cite the
Javadoc.

## Per bug concept (manual labels, `m2_concept_diag/manual_labels.json`, intersection)

Cells: methods with ≥1 E / ≥1 M, then (M/E/FP tests; red-prec). A method can be in more than one row.

| concept | n | Only Doc | Advanced Doc | m3 Concept-Spec | A blind | B blind+Javadoc |
|---|---|---|---|---|---|---|
| C0 | 7 | E3 M1 (1/3/13; 0.19) | E3 M1 (7/3/11; 0.21) | E1 M1 (17/6/14; 0.30) | E2 M1 (12/5/37; 0.12) | E2 M1 (22/3/17; 0.15) |
| C1 null | 12 | E6 M1 (1/15/19; 0.44) | E6 M0 (0/11/29; 0.28) | E1 M7 (9/4/22; 0.15) | E3 M2 (2/13/38; 0.25) | E5 M0 (0/15/35; 0.30) |
| C2 empty | 2 | E1 M0 (0/8/9; 0.47) | E2 M0 (0/5/5; 0.50) | E2 M1 (2/5/12; 0.29) | E1 M0 (0/10/8; 0.56) | E1 M0 (0/9/9; 0.50) |
| C3 boundary | 16 | E6 M1 (1/15/105; 0.12) | E6 M0 (0/22/100; 0.18) | E9 M1 (2/29/116; 0.20) | E6 M0 (0/15/171; 0.08) | E5 M0 (0/23/100; 0.19) |
| C4 error contract | 17 | E7 M2 (2/33/79; 0.29) | E9 M1 (1/32/68; 0.32) | E6 M3 (3/56/69; 0.45) | E7 M2 (2/43/120; 0.26) | E7 M1 (1/67/81; 0.45) |
| C5 format | 10 | E2 M0 (0/8/50; 0.14) | E6 M1 (1/27/36; 0.43) | E3 M3 (12/3/51; 0.06) | E2 M1 (1/13/86; 0.13) | E4 M1 (1/8/65; 0.11) |
| C6 numeric | 4 | E3 M1 (1/3/21; 0.12) | E3 M0 (0/6/28; 0.18) | E2 M0 (0/2/10; 0.17) | E2 M0 (0/4/29; 0.12) | E2 M0 (0/4/37; 0.10) |
| C7 chars/locale | 11 | E0 M0 (0/0/36; 0.00) | E1 M1 (1/1/33; 0.03) | E0 M3 (3/0/18; 0.00) | E1 M1 (1/4/74; 0.05) | E1 M0 (0/2/51; 0.04) |
| C8 state | 6 | E1 M1 (6/1/13; 0.07) | E0 M1 (1/0/16; 0.00) | E1 M2 (6/1/16; 0.06) | E1 M3 (12/1/26; 0.04) | E2 M0 (0/4/13; 0.24) |

- C1 null, where m3 failed worst (E1 M7), recovers with the body hidden (A E3 M2) and recovers fully with the Javadoc (B E5 M0,
  near Advanced's E6 M0). Commons Javadocs usually state the null contract, and B's rules follow it.
- C3 boundary, m3's one gain (E9), drops back to Advanced's level or below (A E6 with 171 FP, B E5).
- C8 state: A has the most M-methods (Lang_38, Lang_55, Lang_57), and B has none.
- C7 chars/locale gets at most one E-method in any arm.

## Spec length (chars of the rendered `generated_docstring`, all 78 methods)

| config | min | Q1 | median | Q3 | max | mean |
|---|---|---|---|---|---|---|
| Only Doc | 334 | 641 | 921 | 1288 | 2401 | 1038 |
| Advanced Doc | 424 | 815 | 1153 | 1654 | 68108 | 3802 |
| m3 Concept-Spec | 1138 | 2181 | 3067 | 4040 | 7451 | 3298 |
| A blind | 1249 | 2512 | 3384 | 4376 | 6309 | 3469 |
| B blind+Javadoc | 885 | 2581 | 3512 | 4807 | 7756 | 3714 |

The blind specs are slightly longer than m3's, and they produce more tests (A 1730 and B 1711 compiled, vs m3 1408).
Within the arms, methods with ≥1 E by length tercile (short/mid/long) are A 6/24, 6/25, 12/25 and B 6/23, 8/25, 13/26.
Longer specs go with more E-methods here, unlike m3. This is probably confounded by method complexity.

## LLM calls

| arm | spec generation | test generation | total |
|---|---|---|---|
| A blind | 79 (78 + 1 re-ask: Lang_45) | 78 | 157 |
| B blind+Javadoc | 82 (78 + 4 re-asks in Codec_7, Lang_16, Lang_7) | 78 | 160 |
| m3 Concept-Spec (reference) | 87 | 78 | 165 |
| Advanced Doc (reference) | 78 | 78 | 156 |
| smoke (Cli_32, Lang_20, Lang_40), per arm | 3 (cached and reused by the full run, so already in the totals above) | 3 | |

Re-asks only happen on unparsable replies (same policy as m3). B's second spec run, after the guard fix, made 0 calls
because every spec was cached. All 78 test-generation completions of each arm contain a Java block. 429 retries
inside the shim and the notebook's own retries are not counted. The matched control is by design: A vs m3 differs
only in the body (same schema, renderer, re-ask policy and test pipeline, 157 vs 165 calls), and B vs A differs only
in the Javadoc (160 vs 157). No separate placebo arm was run (m3's placebo already covers the facet vocabulary).

## Caveats
- **Single runs, small n.** 74 methods from 56 bugs, one T=0 run per arm. The methods are not independent (Gson_4 has
  6 methods, Lang_30 has 5). E-method differences of a few methods are within the measured run-to-run noise (15-18 of
  75 methods flip ≥1 E between runs). The A vs m3 M reduction (10 vs 3 discordant, p = 0.092) is suggestive, not
  significant. Several comparisons are reported, with no multiple-comparison correction.
- **The "spec states the bug" attribution** is a manual reading by one reader (me), using the m2 fix notes. Lang_38's
  attribution relies on the test running in a time zone other than UTC (Defects4J's test environment). The M outcome
  confirms that the fixed version disagrees with the rule.
- **The Javadoc is not neutral.** In Codec_7 the buggy version's Javadoc documents the buggy behaviour (CRLF chunking).
  In Lang_55, B read "throws IllegalStateException if the StopWatch is not running" as covering the suspended state,
  which is wrong for the fixed version too. Arm B is the first configuration in this replication whose prompts
  contain developer-written method documentation. The upstream prompts (basic and advanced docstring generation, m3,
  and test generation) never include `source:source_method_docstring`. B's advantage over A therefore partly comes
  from information that no baseline has.
- **Context choice.** The class Javadoc is not used in either arm (it is not in the upstream prompt either), so that each
  contrast changes one thing. Upstream's "Other methods" list is duplicated for some classes, in m3 and here alike.
- **Body-leak guard.** The guard stopped the first arm-B run at Lang_63 on an English list of time units ("years,
  months, days, hours, minutes, seconds") that matched a call in the body. This was a false positive. The guard now
  ignores windows made only of words, spaces and commas. No spec was edited or regenerated. All 78 prompts and
  docstrings of both arms pass the check. No prompt or docstring contains the patch, fixed code, trigger tests or labels.
- **Infrastructure.** Arm A evaluated in 2 parts: Cli_15, which ended in the upstream `ZeroDivisionError` (16 tests, 0
  compiled), then methods 2-78. Arm B hit 4 transient ENOENT crashes. m3/m4's resume heuristic counted the crashed
  blocks as finished, because those blocks also had (all-zero) counter lines. This happened for idx 49 (Lang_36
  createNumber), 50 (Lang_36 isNumber), 51 (Lang_38) and 59 (Lang_46 escapeJava(String)). After the fix in
  `eval_parts.py`, these 4 were re-evaluated in one redo part without a crash (`out/m5_blind_concept_javadoc_parts.json`
  has a note on each part). Arm A had no such block, and m3's/m4's plans show no case of it. Zero-test blocks caused by
  the upstream test extractor ("Could not find the class name", "No code block found"), such as Gson_14 in every
  config and Lang_24 in A, are kept, as in the baselines. Glitched blocks (Cli_8 in both arms, Lang_12 in A, Lang_11 in
  B) are excluded per the BASELINES rule and were not re-run.
- **Prompt tuning: none.** The prompt was fixed before the smoke run, and nothing was changed after it. Smoke on Cli_32,
  Lang_20, Lang_40 gave A M 1, E 0, FP 39 and B M 1, E 1, FP 13. Both M tests are the Lang_40 `"Straße"` rule.
- Files written outside this folder: `data/prompts/*m5_blind_concept*`, `data/prompts/rq1/*m5_*`,
  `data/rq1/logs/*m5_*`, `data/rq1/results_test/chatgpt/*m5_*` and the pipeline's own `run/out/{prompt,testgen,eval}_m5_*`.
  No change to `run/`, upstream files or other method folders.
