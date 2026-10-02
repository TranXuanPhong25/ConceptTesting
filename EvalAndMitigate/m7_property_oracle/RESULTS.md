# m7_property_oracle: results

Setup:
- Gemini 2.5 Flash (thinking off), 78 focal methods from 60 Defects4J bugs, run 2026-10-02.
- Two arms, one test-generation call per method at T=0.
- Both arms get the same prompt: the upstream Advanced-Doc test-generation prompt, plus m6's blind evidence pack,
  plus relation candidates (R1 inverse, R2 overload/variant, R3-R5 generic). The arms differ only in the
  assertion-form paragraph:
  - **prop** (`m7_prop`): relation-only oracles. A literal is allowed only if it is quoted from the original Javadoc
    and marked `// from Javadoc`.
  - **example** (`m7_example`): one concrete expected value per input (control).
- Counts are the upstream "reported" counters. Percentages are over compiled tests, and red-prec = E / (E + FP).
- Configs are compared on the **intersection of clean methods: 74 of 78**. Three methods are glitched in Advanced Doc
  (Cli_8, Lang_11, Lang_4). Lang_12 is also excluded: it glitched in `m7_prop` twice, in the original run and in one
  redo. Example's Cli_8 glitched twice too.
- All numbers come from `python3 m7_property_oracle/analyze.py` (`out/analysis.txt`).

## Short answer
- **The model does not write relation-only oracles when told to.** 56.8% of `m7_prop` tests still contain an unmarked
  literal oracle of the focal method, against 74.8% for example and 75.1% for Advanced Doc. Only 22% of prop tests are
  relation-only (319 / 1449), against 7% for example and 9% for Advanced Doc. The one allowed prompt revision did not
  help: in the smoke run, v1 had 68% and v2 had 77% (3 methods). So the arm tests "relation-*encouraged*", not
  relation-only.
- **Primary, prop vs example (74 methods):**
  - ≥1 M: **4 vs 3** (3 / 2 discordant, exact McNemar p = 1.0).
  - ≥1 E: **30 vs 31** (6 / 7, p = 1.0).
  - No difference on either side.
- **Secondary.** Neither arm differs from Advanced Doc or from m6 blind:
  - ≥1 M is 2 to 4 everywhere, all p ≥ 0.6.
  - ≥1 E is 30 to 31, all p = 1.0.
  - Prop has red-precision 0.251 and 12 M tests. Example has 0.220 and 5 M tests.
- **Mechanism.** Outside Cli_1, which is M in every config, **every M test of both arms has a literal or exception
  oracle, and none is a relation.** The prop arm's M come from
  - buggy-era Javadoc (Lang_35, via the `// from Javadoc` exemption);
  - the docstring (Lang_40 `"straße"`);
  - a guessed output (Lang_63).

  Its relation tests catch bugs at a similar rate to its literal tests (E 7.9% vs 9.0%) and produce fewer FP
  (13.9% vs 24.1%). But 12 of their 21 E are Gson_4, where the buggy code throws on any top-level value.
- **Post hoc strict prop** (tests with an unmarked literal dropped): M falls to 2 tests in 1 method (Cli_1). E falls to
  24 tests in 12 methods, against 31 methods for example (p = 7e-5). Relation-only tests alone lose most of the
  detection.

## Main table (intersection, 74 methods)

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc | 1247 / 1166 | 10 (0.86%) | 77 (6.60%) | 281 (24.10%) | 0.215 | 5 | 27 |
| Advanced Doc (base prompt) | 1217 / 1062 | 9 (0.85%) | 95 (8.95%) | 266 (25.05%) | 0.263 | 3 | 30 |
| m6 blind oracle | 1318 / 1136 | 10 (0.88%) | 90 (7.92%) | 303 (26.67%) | 0.229 | 2 | 30 |
| m6 sees-code oracle | 1340 / 1223 | 26 (2.13%) | 103 (8.42%) | 266 (21.75%) | 0.279 | 8 | 28 |
| **m7 prop** | 1297 / 1225 | 12 (0.98%) | 96 (7.84%) | 286 (23.35%) | 0.251 | **4** | **30** |
| **m7 example** (control) | 1383 / 1301 | 5 (0.38%) | 85 (6.53%) | 301 (23.14%) | 0.220 | **3** | **31** |
| m7 prop strict (post hoc, unmarked-literal tests dropped) | 550 kept / ~499 | 2 (~0.40%) | 24 (~4.81%) | 92 (~18.42%) | 0.207 | 1 | 12 |

Each arm on its own clean methods:
- prop (76 methods): M 12, E 96, FP 290, red-prec 0.249; 4 methods with ≥1 M, 30 with ≥1 E.
- example (77 methods): M 5, E 86, FP 326, red-prec 0.209; 3 methods with ≥1 M, 32 with ≥1 E.

Compile rates are 94% for both m7 arms, against 87% for Advanced Doc and 86% for m6 blind.

## Exact McNemar on per-method booleans
"x vs y: a / b" means the first config has x methods, the second has y, a methods have the property only in the first
config and b only in the second. No correction for multiple comparisons.

| comparison | 74: ≥1 M | 74: ≥1 E | 67 (no Gson_4, Cli_1): ≥1 M | 67: ≥1 E | 63 (no other-focal packs): ≥1 M | 63: ≥1 E |
|---|---|---|---|---|---|---|
| **prop vs example (primary)** | 4 vs 3: 3 / 2, p = 1.0 | 30 vs 31: 6 / 7, p = 1.0 | 3 vs 2: 3 / 2, p = 1.0 | 24 vs 25: 5 / 6, p = 1.0 | 3 vs 3: 2 / 2, p = 1.0 | 25 vs 27: 5 / 7, p = 0.77 |
| prop vs Advanced Doc | 4 vs 3: 3 / 2, p = 1.0 | 30 vs 30: 6 / 6, p = 1.0 | 3 vs 2: 3 / 2, p = 1.0 | 24 vs 25: 5 / 6, p = 1.0 | 3 vs 3: 2 / 2, p = 1.0 | 25 vs 24: 5 / 4, p = 1.0 |
| example vs Advanced Doc | 3 vs 3: 2 / 2, p = 1.0 | 31 vs 30: 9 / 8, p = 1.0 | 2 vs 2: 2 / 2, p = 1.0 | 25 vs 25: 8 / 8, p = 1.0 | 3 vs 3: 2 / 2, p = 1.0 | 27 vs 24: 9 / 6, p = 0.61 |
| prop vs m6 blind | 4 vs 2: 3 / 1, p = 0.63 | 30 vs 30: 10 / 10, p = 1.0 | 3 vs 0: 3 / 0, p = 0.25 | 24 vs 26: 8 / 10, p = 0.82 | 3 vs 1: 2 / 0, p = 0.50 | 25 vs 25: 8 / 8, p = 1.0 |
| example vs m6 blind | 3 vs 2: 2 / 1, p = 1.0 | 31 vs 30: 10 / 9, p = 1.0 | 2 vs 0: 2 / 0, p = 0.50 | 25 vs 26: 8 / 9, p = 1.0 | 3 vs 1: 2 / 0, p = 0.50 | 27 vs 25: 9 / 7, p = 0.80 |
| strict prop vs example (post hoc) | 1 vs 3: 0 / 2, p = 0.50 | 12 vs 31: 2 / 21, **p = 7e-5** | | | | |

The two sensitivity sets:
- 67 methods: without Gson_4 (6 methods of one bug) and Cli_1 (M in every config).
- 63 methods: without the 11 methods whose m6 blind pack contains another buggy focal method of the same bug
  (Gson_4 ×5, Lang_30 ×3, Lang_35, Lang_46 ×2).

Sensitivity tables (M/E/FP per config) are in `out/analysis.txt`. Without Gson_4 and Cli_1, the M tests are:

| prop | example | Advanced | m6 blind |
|---|---|---|---|
| 3 | 4 | 2 | 0 |

The E tests are:

| prop | example | Advanced | m6 blind |
|---|---|---|---|
| 57 | 52 | 69 | 75 |

## Which methods are misguided, and why (`out/me_tests.txt`, read by hand)

| arm | method (M tests) | M test | oracle form | source of the wrong expectation |
|---|---|---|---|---|
| prop | Cli_1 `hasOption` (9) | 7 literal, 2 overload-agreement relations (`hasOption(String)` vs `hasOption(char)`) | LITERAL / RELATION | M in every config (Advanced 7, m6 blind 9) |
| prop | Lang_35 `add` (1) | `ArrayUtils.add(null, null) // from Javadoc`, then `assertEquals(1, newArray.length)` | LITERAL (marker on the call line, not on the assertions) | the buggy version's Javadoc example `ArrayUtils.add(null, null) = [null]` (fixed: IllegalArgumentException). The same source gave m6's Lang_35 M |
| prop | Lang_40 `containsIgnoreCase` (1) | `assertTrue(containsIgnoreCase("straße", "STRASSE"))` | LITERAL | the comment cites the docstring's upper-casing rule; buggy `toUpperCase` maps ß to SS, the fixed version does not match |
| prop | Lang_63 `formatPeriod` (1) | `assertEquals("1 years, 1 days", formatPeriod(2020-01-01, 2021-01-02, ...))` | LITERAL | a guessed output that matches the buggy version (fixed: "1 years, 2 days") |
| example | Gson_15 `value(double)` (3) | `setLenient(true); value(NaN)` → expects IllegalArgumentException | THROWS | the Advanced docstring says IllegalArgumentException for NaN or infinite values, unconditionally (buggy). The prop arm, told to test exceptions only where the original Javadoc states them, instead wrote `assertEquals("NaN", …)` and got **E** on the same method |
| example | Lang_19 `translate` (1) | `assertEquals(0, translate("&#x12g3;", 0, w))` | LITERAL | the buggy behaviour on a malformed entity |
| example | Cli_1 (1) | | | M in every config |

So the arms' M sets differ only by single methods. Every M outside Cli_1 traces to a concrete expected output or
exception: copied from the buggy-derived docstring, from buggy-era Javadoc, or guessed. No relation oracle produced an
M except Cli_1's harness case. The Gson_15 pair is the one case where the assertion-form paragraph plausibly changed
the outcome, through its **exception clause** (original Javadoc only), not through the relation form.

## Assertion form

### Compliance (`form.py`, all 78 methods)

| | @Test methods | ≥1 LITERAL | ≥1 unmarked LITERAL | ≥1 marked LITERAL | relation-only tests | THROWS-only tests | assertions L / R / T |
|---|---|---|---|---|---|---|---|
| Advanced Doc | 1359 | 75.1% | 75.1% | 0 | 119 (8.8%) | 217 (16.0%) | 1987 / 506 / 327 |
| m6 blind | 1456 | 71.0% | 71.0% | 0 | 139 (9.5%) | 281 (19.3%) | 1844 / 486 / 382 |
| **m7 prop** | 1449 | 58.9% | **56.8%** | 50 (3.5%) | **319 (22.0%)** | 277 (19.1%) | 2030 / 1173 / 328 |
| m7 example | 1519 | 74.8% | 74.8% | 0 | 102 (6.7%) | 280 (18.4%) | 2583 / 452 / 363 |

- In 66 of 78 methods, more than 30% of the prop tests have an unmarked literal. The figure is the same for Advanced
  Doc (66) and almost the same for example (71).
- The prop arm marked 72 literal assertions `// from Javadoc`. In only 32 of them (rough check) do all the string and
  number literals occur in the method's original Javadoc. The others cite the docstring or nothing real.
- The prop tests do contain relations: 1173 relation assertions against 452 for example. Typical ones are overload
  agreement (`join(a, ';')` vs `join(a, ';', 0, a.length)`), round trips (`decodeBase64(encodeBase64String(x))`), and
  metamorphic or JDK agreement (`createNumber(s)` vs `Integer.valueOf(s)`). Most of them sit **next to** literal
  assertions in the same test.
- The prop smoke completions show the pattern: the model labels plain example assertions with relation names
  (`// R4: …` above `assertEquals(9, findWrapPos(...))`).

### Outcome by test form (intersection, 74 methods)

| arm | label (tests) | M | E | FP | red-prec |
|---|---|---|---|---|---|
| prop | LITERAL (804) | 10 (1.2%) | 72 (9.0%) | 194 (24.1%) | 0.27 |
| prop | LITERAL-marked (30) | 0 | 2 | 1 | |
| prop | RELATION-only (266) | 2 (0.8%, both Cli_1) | 21 (7.9%) | 37 (13.9%) | 0.36 |
| prop | THROWS-only (254) | 0 | 1 | 52 | 0.02 |
| example | LITERAL (1076) | 2 (0.2%) | 76 (7.1%) | 225 (20.9%) | 0.25 |
| example | RELATION-only (84) | 0 | 2 | 19 | 0.10 |
| example | THROWS-only (260) | 3 (Gson_15) | 7 | 57 | 0.11 |
| Advanced Doc | LITERAL (984) | 8 | 86 | 201 | 0.30 |
| Advanced Doc | RELATION-only (87) | 0 | 3 | 27 | 0.10 |

- The prop arm's relation-only tests are cleaner: their FP rate is about half that of the literal tests. They detect
  at a similar rate per test, but 12 of their 21 E are Gson_4 (`value` at top level). The others: Lang_45 3, Codec_7 2
  (round trip and append-metamorphic over `encodeBase64String`), Lang_33 2, Lang_3 1, Lang_41 1.
- That is why the post hoc strict subset keeps few E-methods (12).

## LLM calls

| | prop | example | notes |
|---|---|---|---|
| test generation (full run, incl. the 3 v2 smoke methods reused from the cache) | **86** | **91** | 78 + re-asks for unparsable replies |
| re-asks | Lang_36 `isNumber` +2; Gson_14 ×2: +3 each | Codec_9, Lang_1, Lang_27, Lang_45, Lang_58 +1 each; Lang_44 +2; Gson_14 ×2: +3 each | see below |
| v1 smoke (prompt before the revision, discarded) | 3 | 3 | |
| **total** | **89** | **94** | |

- **Gson_14 (2 methods, both arms).** My parse check required `public class \w+`. The test class
  `$Gson$TypesSubtypeOfTest` failed it, so the reply was re-asked twice and then dropped. The check was fixed to
  `[\w$]+`, and the two methods were generated again at T=0 (+1 call each). The rejected replies were not stored. The
  upstream evaluator cannot read `$` class names either ("Could not find the class name"), so Gson_14 has no evaluated
  test in any config, the baselines included.
- **Lang_44 `createNumber`, example arm.** Three unparsable replies, at T=0 and at 0.5 twice. The run took minutes per
  call, probably long degenerate output; the pipeline sets no `max_tokens`, and neither did I. It was not retried, to
  stay under the cost limit, so the example arm has no test for it. No arm has ≥1 E or ≥1 M on Lang_44, so the
  method-level comparisons are unaffected.
- The other re-asks also followed unparsable replies; most produced a valid reply at T=0.5.
- 429 retries inside the shim are not counted. There were many, with the generation running 4 threads.
- Estimated Vertex cost (not metered): $1.5-2.5. That is under the $3 stop limit but above the expected $1.
  - The parsed replies are 1.36M chars of output (about 0.4M tokens, about $1.0) and 3.3M chars of prompts (about
    $0.25).
  - The ~6 very long unparsable replies (Lang_36, Lang_44, Lang_58 and others) could add up to about $1.

## Caveats
- **Compliance failure limits the question.** At equal information, a prompt asking for relation-only oracles produced
  mostly literal oracles: 57% of tests, against 75% for the control. The primary contrast therefore compares
  "relation-encouraged" with "example" tests, not "relation-only" with "example". The post hoc strict subset is the
  closest to relation-only. It is not randomised: which tests survive depends on what the model chose to write.
- **Single runs, small n.** 74 methods from 56 bugs, one run per arm. The methods are not independent: Gson_4 has 6
  methods and Lang_30 has 5. m4 measured that 15-18 of 75 methods flip their ≥1 E status between single runs. All E
  differences here are within that range (13 discordant methods for prop vs example). The M side has 3 to 4 methods
  per arm, too few for any test.
- **Temperature.** Both m7 arms use T=0, as specified, so the primary contrast is clean. The upstream test-generation
  cell (`UT_Test_Generation.ipynb`, cell 34, used for Only Doc, Advanced Doc and m6) passes no temperature
  (`# temperature=0.0` is commented out), so those baselines use the model's default temperature. The secondary
  comparisons therefore also differ in temperature.
- **Prompt differences from the baselines.** The m7 prompts are longer than Advanced Doc: they add the evidence pack,
  the relations and the paragraph. They compile better (94% vs 87%). Any m7-vs-baseline difference mixes all of these.
- **Paragraph lengths.** The paragraphs are 1,276 (prop) vs 1,100 (example) characters. They share the same structure:
  header, allowed and forbidden forms, coverage sentence, self-check.
- **The revision.** v2 added the same structural elements to both paragraphs after the v1 smoke run. This was the
  single allowed revision, and nothing else was tuned. The v1 text and outputs are in `out/v1_smoke/`.
- **The classifier is a heuristic.** `form.py` resolves local variables, test-class fields, helpers and side effects
  by regex.
  - On a read sample of prop and Advanced tests, the labels matched my reading.
  - It treats factory or helper calls with literal arguments as literal only when they are test-class helpers or
    boxing or constructor calls. `Fraction.getFraction(1, 2)` used as an expected value, for example, counts as a
    relation.
  - `assertNotNull`, bounds such as `x <= n`, and identities such as `assertEquals(in, f(in))` count as relations, as
    pre-registered.
- **Leakage.** No prompt contains the patch, the fixed version, trigger tests or labels, and the appended blocks
  contain no focal-body window (asserted). Three base Advanced-Doc prompts (Lang_36, Lang_3, Lang_44 `createNumber`)
  contain body windows, because the Advanced docstrings quote the body. These are inherited unchanged and are also in
  the baseline. Buggy-era Javadoc reaches the prompts through the evidence pack, as in m6. It caused the prop arm's
  Lang_35 M.
- **Security.** Every evaluation, smoke included, ran with `NO_ADC=1`. `eval_parts.py` sets it, and I checked that the
  container had no gcloud mount and no `GOOGLE_APPLICATION_CREDENTIALS`. Only the generation steps ran with
  credentials.
- **Infrastructure.** Each arm was evaluated in 2 parts. Cli_15 compiled no test, which leads to the known upstream
  `ZeroDivisionError`, and the run resumed at method 2. There was no ENOENT crash. The glitched blocks (prop Lang_11
  and Lang_12, example Cli_8) were re-evaluated once with `--redo` and glitched again.
- **Files written outside this folder** (all new):
  - `data/prompts/rq1/*m7_*`;
  - `data/rq1/logs/*m7_*`;
  - `data/rq1/results_test/chatgpt/*m7_*`;
  - the pipeline's `run/out/eval_m7_*`.

  Like every earlier evaluation, the pipeline also overwrites the shared
  `data/rq1/results_test/chatgpt/buggy_gen_test_results.json`. There was no change to `run/`, upstream files or other
  method folders.
