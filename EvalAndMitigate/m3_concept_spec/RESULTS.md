# m3_concept_spec: results

Setup: Gemini 2.5 Flash (thinking off), temperature 0, 78 focal methods from 60 Defects4J bugs. The two arms are
**Concept-Spec** (`m3_concept_spec`: a JSON spec with facets C0 plus C1-C8, rendered to a docstring) and
**Placebo-Spec** (`m3_concept_placebo`: the same pipeline with facets C0 plus eight bug-irrelevant ones). Both use the
unchanged Only Doc test-generation prompt. Counts are the upstream "reported" counters, percentages are over compiled
tests, and red-prec = E / (E + FP). Configs are compared on the **intersection of clean methods (74 of 78)**. Excluded
are Lang_11 and Lang_12 (both m3 arms), Cli_8 (Advanced, Placebo) and Lang_4 (Advanced). Everything below comes from
`python3 m3_concept_spec/analyze.py`, and the full output is in `out/analysis.txt`.

## Short answer
- **Concept-Spec does not beat Advanced Doc. It is clearly worse on misguidance, and no better on effective tests.**
  - Methods with ≥1 M: **16 vs 3** (McNemar: 13 gained, 0 lost, **p = 2.4e-4**). This is the only significant result.
    Concept-Spec even exceeds Doc W/ Code, which has the buggy body in the prompt (8 M-methods).
  - Methods with ≥1 E: 22 vs 30 (lost 13, gained 5, p = 0.096), so within noise but in the wrong direction.
  - More E tests (100 vs 95) and a higher red-precision (0.276 vs 0.263) are driven by the six Gson_4 methods (one
    bug, 56 E tests). Without Gson_4 and Cli_1, Concept-Spec has E 44 vs 69 and red-precision 0.150 vs 0.210.
- **Against the placebo: the same on E, more M.** Methods with ≥1 E: 22 vs 21 (p = 1.0). Methods with ≥1 M: 16 vs 8
  (11 gained, 3 lost, p = 0.057, borderline). So the bug-relevant vocabulary does matter beyond "structured and
  longer", but it pushes towards misguidance, not detection.
- **Length does not explain it.** The placebo docstrings are *longer* than Concept-Spec on 73 of 78 methods
  (median 4.8k vs 3.1k chars; Advanced 1.2k, Only Doc 0.9k). The placebo is the longest arm and has the fewest
  E-methods (21), and within each arm E-methods do not rise with length tercile.
- **Why it fails.** The spec is generated from the buggy code, and the concept facets force it to commit on exactly
  the bug-relevant cases. It commits to what the buggy code does, as concrete `input → expected` rules, and "unspecified" is
  almost never used (2 of 1753 rules, 0.1%). In 13 of the 16 M-methods, a spec rule states the buggy behaviour that
  the misguided test asserts (manual check, below). The effect is concentrated in C1 null (E-methods 6 → 1 and
  M-methods 0 → 7 against Advanced), C5 format (6/1 → 3/3) and C7 characters (1/1 → 0/3). C3 boundary is the one
  concept that gains (E-methods 6 → 9).

## Main table (intersection, 74 methods)

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Doc W/ Code (reference) | 986 / 858 | 20 (2.33%) | 70 (8.16%) | 164 (19.11%) | 0.299 | 8 | 20 |
| Only Doc | 1247 / 1166 | 10 (0.86%) | 77 (6.60%) | 281 (24.10%) | 0.215 | 5 | 27 |
| Advanced Doc | 1217 / 1062 | 9 (0.85%) | 95 (8.95%) | 266 (25.05%) | 0.263 | 3 | 30 |
| **Concept-Spec** | 1582 / 1408 | **48 (3.41%)** | 100 (7.10%) | 262 (18.61%) | 0.276 | **16** | 22 |
| Placebo-Spec | 1207 / 1071 | 18 (1.68%) | 69 (6.44%) | 286 (26.70%) | 0.194 | 8 | 21 |

Sensitivity check. The table below drops the 6 Gson_4 methods (one bug, E in every config) and Cli_1 (M in every
config; 17 of Concept-Spec's 48 M are there), which leaves 67 methods:

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Doc W/ Code (reference) | 904 / 781 | 12 (1.54%) | 35 (4.48%) | 156 (19.97%) | 0.183 | 7 | 14 |
| Only Doc | 1160 / 1082 | 9 (0.83%) | 44 (4.07%) | 265 (24.49%) | 0.142 | 4 | 20 |
| Advanced Doc | 1124 / 996 | 2 (0.20%) | 69 (6.93%) | 260 (26.10%) | 0.210 | 2 | 25 |
| Concept-Spec | 1457 / 1289 | 31 (2.40%) | 44 (3.41%) | 250 (19.39%) | 0.150 | 15 | 16 |
| Placebo-Spec | 1120 / 988 | 13 (1.32%) | 48 (4.86%) | 262 (26.52%) | 0.155 | 7 | 16 |

Exact McNemar on per-method booleans (intersection, 74 methods; "lost" = only the first config has it):

| comparison | methods ≥1 E | methods ≥1 M |
|---|---|---|
| Concept-Spec vs Advanced Doc | 22 vs 30: lost 13, gained 5, p = 0.096 | 16 vs 3: lost 0, gained 13, **p = 2.4e-4** |
| Concept-Spec vs Placebo-Spec | 22 vs 21: lost 5, gained 6, p = 1.000 | 16 vs 8: lost 3, gained 11, p = 0.057 |
| Concept-Spec vs Only Doc | 22 vs 27: lost 11, gained 6, p = 0.332 | 16 vs 5: lost 2, gained 13, **p = 0.007** |
| Placebo-Spec vs Advanced Doc | 21 vs 30: lost 15, gained 6, p = 0.078 | 8 vs 3: lost 1, gained 6, p = 0.125 |
| Placebo-Spec vs Only Doc | 21 vs 27: lost 12, gained 6, p = 0.238 | 8 vs 5: lost 2, gained 5, p = 0.453 |

Each config on its own clean methods: Concept-Spec (77 methods) M 48, E 100, FP 264, red-prec 0.275, 16 / 22 methods;
Placebo-Spec (75 methods) M 18, E 69, FP 293, red-prec 0.191, 8 / 21 methods. The baselines are as in `run/BASELINES.md`.

## Per bug concept (manual labels from `m2_concept_diag/manual_labels.json`, intersection)

Cells: methods with ≥1 E / ≥1 M, then (M/E/FP tests; red-prec). A method can appear in more than one row.

| concept | n | Doc W/ Code | Only Doc | Advanced Doc | Concept-Spec | Placebo-Spec |
|---|---|---|---|---|---|---|
| C0 | 7 | E2 M1 (8/2/7; 0.22) | E3 M1 (1/3/13; 0.19) | E3 M1 (7/3/11; 0.21) | E1 M1 (17/6/14; 0.30) | E2 M2 (6/4/10; 0.29) |
| C1 null | 12 | E3 M3 (4/7/14; 0.33) | E6 M1 (1/15/19; 0.44) | E6 M0 (0/11/29; 0.28) | **E1 M7** (9/4/22; 0.15) | E2 M2 (3/9/19; 0.32) |
| C2 empty | 2 | E2 M0 (0/6/3; 0.67) | E1 M0 (0/8/9; 0.47) | E2 M0 (0/5/5; 0.50) | E2 M1 (2/5/12; 0.29) | E2 M0 (0/11/3; 0.79) |
| C3 boundary | 16 | E5 M1 (2/19/62; 0.23) | E6 M1 (1/15/105; 0.12) | E6 M0 (0/22/100; 0.18) | **E9 M1** (2/29/116; 0.20) | E6 M2 (4/18/127; 0.12) |
| C4 error contract | 17 | E6 M3 (4/35/40; 0.47) | E7 M2 (2/33/79; 0.29) | E9 M1 (1/32/68; 0.32) | E6 M3 (3/56/69; 0.45) | E5 M3 (6/21/47; 0.31) |
| C5 format | 10 | E3 M0 (0/6/33; 0.15) | E2 M0 (0/8/50; 0.14) | E6 M1 (1/27/36; 0.43) | **E3 M3** (12/3/51; 0.06) | E4 M0 (0/13/45; 0.22) |
| C6 numeric | 4 | E1 M1 (2/1/13; 0.07) | E3 M1 (1/3/21; 0.12) | E3 M0 (0/6/28; 0.18) | E2 M0 (0/2/10; 0.17) | E1 M1 (3/2/18; 0.10) |
| C7 chars/locale | 11 | E0 M0 (0/0/14; 0.00) | E0 M0 (0/0/36; 0.00) | E1 M1 (1/1/33; 0.03) | **E0 M3** (3/0/18; 0.00) | E0 M0 (0/0/45; 0.00) |
| C8 state | 6 | E0 M1 (3/0/0; 0.00) | E1 M1 (6/1/13; 0.07) | E0 M1 (1/0/16; 0.00) | E1 M2 (6/1/16; 0.06) | E1 M1 (2/2/14; 0.12) |

- C7 still gets no effective test in any config. The C7 facet made the model write rules about surrogates and locale,
  but they describe the buggy char-wise, default-locale semantics (Lang_30, Lang_40).
- In 66 of the 67 methods whose bug concept is in C1-C8, the spec states at least one concrete rule in that facet.
  "Taking a position" therefore happened almost always, and it did not produce effective tests: Concept-Spec gets
  21 E-methods and 15 M-methods among these 66, against Advanced's 27 and 2.

### Manual check of the 16 Concept-Spec M-methods
For each, I compared the misguided tests with the spec rules and the fix (m2 notes). In **11** methods a spec rule
states the buggy behaviour that the M test asserts:

| method | spec rule |
|---|---|
| Codec_7 | output "with line breaks (CRLF)" |
| Codec_13 | null → NPE |
| Codec_17 | null → NPE |
| Csv_4 | null header map → NPE |
| Lang_5 | a blanket "does not conform → IAE" rule covering `_US` |
| Lang_19 | `"&#"` → IndexOutOfBoundsException |
| Lang_33 | a null element → NPE |
| Lang_35 ×2 | null array + null element → `[null]` |
| Lang_47 | null nullText → NPE |
| Lang_55 | stop() from SUSPENDED sets stopTime to now |

In **2** more the match is looser: Lang_30 ("assuming char-based iteration" for surrogates) and Lang_40 ("depends on
the default locale's toUpperCase"). **3** are not attributable to the spec: Cli_1 and Lang_57, which are M in every
config, and Gson_7 (`+123`, where the test argues from "the current implementation").

The placebo gets some of these same methods right *because* nothing forces it to reason about the concept. Its C0
rules state unchunked Base64 for Codec_7 ("SQAA", 8 E) and null → false for Codec_13 (8 E), where Concept-Spec
wrote CRLF chunking and NPE and got M.

## Docstring length (chars of the rendered `generated_docstring`, all 78 methods)

| config | min | Q1 | median | Q3 | max | mean |
|---|---|---|---|---|---|---|
| Only Doc (basic) | 334 | 641 | 921 | 1288 | 2401 | 1038 |
| Advanced Doc | 424 | 815 | 1153 | 1654 | 68108 | 3802 |
| Concept-Spec | 1138 | 2181 | 3067 | 4040 | 7451 | 3298 |
| Placebo-Spec | 2696 | 3938 | 4800 | 5779 | 8745 | 4943 |

The placebo is not shorter: it is longer than Concept-Spec on 73 of 78 methods. It writes more core-logic rules
(579 vs 376) and fills all eight irrelevant facets. Advanced's mean is inflated by one degenerate 68k-char docstring.
Methods with ≥1 E by the arm's own length tercile (short / mid / long): Only Doc 10/24, 10/25, 7/25; Advanced 11/23,
8/25, 11/26; Concept-Spec 6/24, 7/25, 9/25; Placebo 8/24, 7/25, 6/25. There is no consistent length effect.

## Spec tables (`out/specs_spec.jsonl`, `out/specs_placebo.jsonl`)

| | Concept-Spec | Placebo-Spec |
|---|---|---|
| rules (per method) | 1753 (22.5) | 2030 (26.0) |
| "unspecified" rules | **2 (0.1%)**, in 2 methods | 0 |
| facets "not applicable" (methods) | C1 3, C2 19, C3 12, C5 23, C6 50, C7 20; C0/C4/C8 0 | none |
| source field | name-context 1034, assumed 366, framework 217, type 62, mixed/other 74 | assumed 954, name-context 759, framework 221, type 75, other 21 |
| missing keys | 0 | 0 |

The explicit permission (and encouragement) to write "unspecified" was ignored. The rendered "Unspecified (do not
assume)" section appears in 2 docstrings only. Despite the instruction, some rules still narrate the code (for
example, in Lang_19: "Returns 0 (due to 'index < seqEnd - 1' check failing)").

Note for the next method that reuses these tables: the C1-C8 rules are a good map of *which* inputs matter (the
C3 gain, and 66/67 facets hit), but their *expected* values are largely the buggy code's behaviour. Treat them as
input generators, not as oracles.

## LLM calls

| arm | spec generation | test generation | total | notes |
|---|---|---|---|---|
| Concept-Spec | 87 (78 + 9 re-asks in 5 methods) | 78 | 165 | Re-asks happen only on unparsable replies (Gemini repetition loops such as `bbbb…`, `0000…`). Lang_27 and Lang_7 needed 4 calls: T 0, 0.5, 0.5, then 1.0 |
| Placebo-Spec | 82 (78 + 4 re-asks in 4 methods) | 78 | 160 | |
| smoke | 3 (prompt v1, discarded) + 3 (v2, reused) + 3 placebo (reused) | 3 | | v1 replies in `out/smoke_v1_specs_spec.jsonl` |
| Advanced Doc (for reference) | 78 docstring | 78 | 156 | |

The placebo control has the same call budget up to the re-asks (160 vs 165). 429 retries inside the shim and the
test-generation notebook's own error retries are not counted.

## Caveats
- n = 74 methods in the intersection, from 56 bugs. The methods are not independent (Gson_4 contributes 6,
  Lang_30 5). The M result against Advanced (13 vs 0 discordant) survives this. The E differences and the
  Concept-Spec vs placebo M difference (p = 0.057) do not reach significance.
- One run per arm at T=0. The Concept-Spec vs placebo contrast is partly stochastic: Codec_7 and Codec_13 flip on
  whether the model happened to commit to the buggy or the fixed behaviour.
- The prompt was tuned once, on the 3 smoke methods (Cli_32, Lang_20, Lang_40) of the Concept-Spec arm, before any
  evaluation (see README). The placebo was not tuned. The smoke evaluation gave E 10, M 0 on those 3 methods (Cli_32 only).
- The manual attribution of M-methods to spec rules is by one reader (me), using the m2 fix notes.
- Glitched blocks (a run that "failed" with an empty error report) are excluded per the BASELINES rule.
  Lang_12 fails that way in *both* m3 arms, with different test files, so the cause is deterministic (probably a
  hanging or out-of-memory test), not Docker flakiness. Its counters are 0 M / 0 E in both arms anyway. Placebo's Cli_8 and
  Lang_11 are glitched just like Advanced Doc's.
- Infrastructure: the Concept-Spec evaluation first crashed right after Cli_15 with an upstream
  `ZeroDivisionError` (`reported_passed_on_fixed / test_compiled`). The per-item log line divides by the
  *cumulative* compiled-test count, which is still 0 when the first evaluated method has no compiling test (none of
  Cli_15's 17 tests compiled in this arm). My copy of `eval_parts.py` counts a crashed part's last block as finished
  when its counter lines ("Total test generated") were written, so that Cli_15 block is used and evaluation resumed
  at the next method. Record order is unchanged, and `run/` and the upstream files are untouched. The one resume
  attempt made before this fix crashed at Cli_15 again; it was moved to
  `out/crashed_m3_concept_spec_part2_log_1.log` / `.console` and is not used. The arm then finished in 3 parts
  (`out/m3_concept_spec_parts.json`: Cli_15; methods 1-39, which ended in the known transient ENOENT crash; methods
  40-77). The placebo was evaluated in one pass.
- Leakage: no prompt contains the patch, the fixed version, trigger tests or labels. The test-generation prompts
  contain no focal body (checked on all 78 prompts of both arms).
