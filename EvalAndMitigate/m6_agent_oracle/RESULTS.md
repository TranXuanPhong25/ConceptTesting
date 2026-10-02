# m6_agent_oracle: results

Setup: Gemini 2.5 Flash (thinking off), temperature 0, 78 focal methods from 60 Defects4J bugs, run 2026-10-01.
Both arms use the same 418 neutral questions (written from the buggy code) and the same evidence pack. The arms
differ only in whether the answering agent also sees the focal method body:
- **blind** (`m6_oracle_blind`): the answerer sees the signature, the method Javadoc, the class Javadoc, constructors,
  fields, other signatures, same-name methods, and callers from the main source dir. It never sees the focal body.
- **sees-code** (`m6_oracle_sees_code`): the same pack plus the focal body.

Docstring = Advanced docstring (unchanged) + "Clarified requirements" (`input → expected`) + "Undetermined (do not
assume)". Tests come from the unchanged pipeline (`WITH_CODE=0`). Counts are the upstream "reported" counters,
percentages are over compiled tests, and red-prec = E / (E + FP). Configs are compared on the **intersection of clean
methods: 75 of 78**. Cli_8 and Lang_11 are excluded (glitched in Advanced, m4 and m5 B; Lang_11 also in Only Doc), and
so is Lang_4 (Advanced). Both m6 arms have no glitched block. All numbers come from
`python3 m6_agent_oracle/analyze.py` (`out/analysis.txt`).

## Short answer
- **Can a blind answering agent stand in for the human? It does no harm, but it adds nothing measurable over the
  Advanced docstring.**
  - Blind vs Advanced Doc: methods with ≥1 M **2 vs 3** (1 / 2 discordant, p = 1.0), methods with ≥1 E **30 vs 30**
    (9 / 9, p = 1.0). E tests 90 vs 95, red-precision 0.229 vs 0.262.
  - Its two M-methods are Cli_1 (M in every config) and Gson_4 `value(long)`. Without Gson_4 and Cli_1 it has
    **0 M tests**, against 2 for Advanced Doc.
  - It answered 83% of the questions with cited evidence. 91% of those answers cite the method's or the class's
    Javadoc. It said UNDETERMINED for the other 17%.
  - Its answers did not turn into more detection. Wrong guesses on behaviour that the bug does not change add FP
    (303 vs 278 for sees-code).
- **Does the code-reading answerer copy the bug? Yes.** This is the primary contrast, blind vs sees-code.
  - Methods with ≥1 M: **2 vs 8. All 6 discordant methods are M only in sees-code, exact McNemar p = 0.031.** The
    result is the same without Gson_4 and Cli_1 (0 vs 6), and without the 11 methods whose blind pack contains
    another buggy focal method (1 vs 7, p = 0.031).
  - In 6 of sees-code's 8 M-methods, a clarified requirement states the buggy behaviour that the M test asserts (Csv_2,
    Lang_14, Lang_19, Lang_28, Lang_35, Gson_4). The blind answerer gave the fixed answer on Csv_2 and Lang_14 and on one of
    the two Lang_19 questions, left Lang_28 UNDETERMINED, and gave the same answer as sees-code on Lang_35 and Gson_4. In those two cases it was
    quoting buggy-era Javadoc.
  - The sees-code answerer cites the implementation in **87%** of its determined answers. It says UNDETERMINED only
    **5%** of the time (blind: 17%).
  - Methods with ≥1 E are 30 vs 28 (9 / 7, p = 0.80). That is within run-to-run noise.
- **Mechanism (offline judge with the patch, validated by hand).** On the 72 questions where, according to the judge,
  the buggy and fixed versions behave differently, sees-code's determined answers match the buggy version in
  22 of 60 (37%), and blind's in 10 of 46 (22%). Per question, sees-code alone is BUGGY on 17 and blind alone on 5
  (p = 0.017). The judge's relevance labels are noisy: only 12 of 19 checked were right. The direction is the same in
  both judge versions and in my own verdicts (BUGGY: blind 2, sees-code 6 of 29 questions). So the direction holds,
  and the exact rates are rough.
- **Compared with the other intent sources.** The blind oracle is level with m5 B, the Javadoc-grounded spec
  (≥1 M 2 vs 3, ≥1 E 30 vs 28). It is better than m4 Concept-Inputs on M (2 vs 7, p = 0.12; without Gson_4 and Cli_1:
  0 vs 6, p = 0.031). Both blind arms that work (m5 B and m6 blind) get their intent from the developer Javadoc. In
  both, the remaining M comes from buggy-era documentation (Gson_4).

## Main table (intersection, 75 methods)

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc | 1269 / 1166 | 10 (0.86%) | 77 (6.60%) | 281 (24.10%) | 0.215 | 5 | 27 |
| Advanced Doc (best baseline) | 1239 / 1069 | 9 (0.84%) | 95 (8.89%) | 268 (25.07%) | 0.262 | 3 | 30 |
| m4 Concept-Inputs (same base + inputs, no outcomes) | 1788 / 1615 | 25 (1.55%) | 97 (6.01%) | 397 (24.58%) | 0.196 | 7 | 30 |
| m5 B blind spec + Javadoc | 1948 / 1736 | 24 (1.38%) | 131 (7.55%) | 337 (19.41%) | 0.280 | 3 | 28 |
| **m6 blind oracle** | 1341 / 1136 | **10 (0.88%)** | 90 (7.92%) | 303 (26.67%) | 0.229 | **2** | 30 |
| **m6 sees-code oracle** (control) | 1361 / 1243 | **26 (2.09%)** | 103 (8.29%) | 278 (22.37%) | 0.270 | **8** | 28 |

Without Gson_4 (one bug, 6 methods), 69 methods:

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc | 1190 / 1090 | 10 (0.92%) | 45 (4.13%) | 266 (24.40%) | 0.145 | 5 | 21 |
| Advanced Doc | 1153 / 1010 | 9 (0.89%) | 69 (6.83%) | 262 (25.94%) | 0.208 | 3 | 25 |
| m4 Concept-Inputs | 1682 / 1540 | 25 (1.62%) | 64 (4.16%) | 380 (24.68%) | 0.144 | 7 | 25 |
| m5 B blind spec + Javadoc | 1817 / 1627 | 23 (1.41%) | 66 (4.06%) | 319 (19.61%) | 0.171 | 2 | 23 |
| m6 blind oracle | 1249 / 1078 | 9 (0.83%) | 75 (6.96%) | 291 (26.99%) | 0.205 | 1 | 26 |
| m6 sees-code oracle | 1270 / 1166 | 25 (2.14%) | 75 (6.43%) | 269 (23.07%) | 0.218 | 7 | 24 |

Without Gson_4 and Cli_1 (Cli_1 is M in every config: blind 9, sees-code 11, Advanced 7 M tests), 68 methods:

| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |
|---|---|---|---|---|---|---|---|
| Only Doc | 1182 / 1082 | 9 (0.83%) | 44 (4.07%) | 265 (24.49%) | 0.142 | 4 | 20 |
| Advanced Doc | 1146 / 1003 | 2 (0.20%) | 69 (6.88%) | 262 (26.12%) | 0.208 | 2 | 25 |
| m4 Concept-Inputs | 1667 / 1525 | 11 (0.72%) | 64 (4.20%) | 379 (24.85%) | 0.144 | 6 | 25 |
| m5 B blind spec + Javadoc | 1790 / 1600 | 1 (0.06%) | 66 (4.12%) | 314 (19.62%) | 0.174 | 1 | 23 |
| m6 blind oracle | 1239 / 1068 | **0 (0.00%)** | 75 (7.02%) | 290 (27.15%) | 0.205 | **0** | 26 |
| m6 sees-code oracle | 1258 / 1154 | 14 (1.21%) | 75 (6.50%) | 268 (23.22%) | 0.219 | 6 | 24 |

Each arm on its own clean methods (78 each, nothing glitched): blind M 10, E 90, FP 313, red-prec 0.223, 2 / 30
methods. Sees-code: M 26, E 103, FP 284, red-prec 0.266, 8 / 28 methods.

## Exact McNemar on per-method booleans
"x / y" = methods with the property only in the first / only in the second config. No correction for multiple
comparisons.

| comparison | 75: ≥1 M | 75: ≥1 E | 68 (no Gson_4, Cli_1): ≥1 M | 68: ≥1 E |
|---|---|---|---|---|
| **blind vs sees-code (primary)** | 2 vs 8: 0 / 6, **p = 0.031** | 30 vs 28: 9 / 7, p = 0.80 | 0 vs 6: 0 / 6, **p = 0.031** | 26 vs 24: 8 / 6, p = 0.79 |
| **blind vs Advanced Doc** | 2 vs 3: 1 / 2, p = 1.0 | 30 vs 30: 9 / 9, p = 1.0 | 0 vs 2: 0 / 2, p = 0.50 | 26 vs 25: 9 / 8, p = 1.0 |
| sees-code vs Advanced Doc | 8 vs 3: 6 / 1, p = 0.12 | 28 vs 30: 7 / 9, p = 0.80 | 6 vs 2: 5 / 1, p = 0.22 | 24 vs 25: 6 / 7, p = 1.0 |
| blind vs m4 Concept-Inputs | 2 vs 7: 1 / 6, p = 0.12 | 30 vs 30: 9 / 9, p = 1.0 | 0 vs 6: 0 / 6, p = 0.031 | 26 vs 25: 9 / 8, p = 1.0 |
| blind vs m5 B | 2 vs 3: 1 / 2, p = 1.0 | 30 vs 28: 11 / 9, p = 0.82 | 0 vs 1: 0 / 1, p = 1.0 | 26 vs 23: 11 / 8, p = 0.65 |
| blind vs Only Doc | 2 vs 5: 1 / 4, p = 0.38 | 30 vs 27: 11 / 8, p = 0.65 | 0 vs 4: 0 / 4, p = 0.12 | 26 vs 20: 11 / 5, p = 0.21 |

Sensitivity check. 11 blind packs contain another focal method of the same bug as a same-name method (Gson_4 ×5,
Lang_30 ×3, Lang_35 ×1, Lang_46 ×2; see "Evidence packs"). Without them, 64 methods remain: blind vs sees-code ≥1 M
1 vs 7 (0 / 6, p = 0.031), ≥1 E 25 vs 25 (6 / 6, p = 1.0). Blind vs Advanced: ≥1 M 1 vs 3, ≥1 E 25 vs 24.

## Which methods are misguided, and why (manual check, `out/m_methods.txt`)

| method | sees-code clarified rule (M test asserts it) | blind answer to the same question |
|---|---|---|
| Csv_2 `get(String)` | mapping index out of bounds → `ArrayIndexOutOfBoundsException` (fixed: IllegalArgumentException) | IllegalArgumentException (Javadoc, caller, class context) |
| Lang_14 `equals(CharSequence, CharSequence)` (5 M) | `equals(new StringBuilder("abc"), "abc")` → false (fixed: true) | true (Javadoc) |
| Lang_19 `translate` | `"abc&#x"`, `"abc&#123"` → IndexOutOfBoundsException (fixed: return 0 and write nothing; return 5 and write `{`) | `"abc&#123"`: return 5 and write `{` (= fixed); `"abc&#x"`: return 0 but also write `&#x` (neither version) |
| Lang_28 `translate` | `&#1114111;` → writes the lower 16 bits (fixed: a surrogate pair) | UNDETERMINED |
| Lang_35 `add(T[], int, T)` | `add(null, 0, null)` → `[null]` (fixed: IllegalArgumentException) | `[null]` too, quoting the buggy version's Javadoc example `ArrayUtils.add(null, 0, null) = [null]`; the blind arm's tests did not assert it |
| Gson_4 `value(long)` (both arms M) | `value(123L)` at top level → IllegalStateException (fixed: writes 123) | the same, quoting the class Javadoc "Each JSON document must contain one top-level array or object" |
| Lang_57 `isAvailableLocale` | no rule: the tests assume particular locales are unavailable (M in Only Doc, Advanced, m4 too) | |
| Cli_1 `hasOption` | no rule: M in every config | |

In 6 of sees-code's 8 M-methods, the misguided test comes from a clarified rule that states the buggy behaviour. In
4 of those 6 (Csv_2, Lang_14, Lang_19, Lang_28), that rule cites `implementation`, and the blind answerer, without
the body, gave the fixed behaviour (Csv_2, Lang_14, one Lang_19 question), a wrong answer (the other Lang_19
question) or no answer (Lang_28). In the remaining 2 (Lang_35, Gson_4), the buggy behaviour is
written in the buggy version's own documentation, so both arms state it. The blind arm's only M besides Cli_1 is
Gson_4. m5 B has the same Gson_4 M, for the same reason.

Some cases go the other way. The sees-code answerer is right where the blind one is wrong: Lang_40 Q2 (Turkish
locale: blind `false`, sees-code `true` = fixed), and Cli_32 `findWrapPos("abc", 3, 0)` (blind 3 from the Javadoc
sentence "it will return startPos+width", sees-code −1, which is correct in both versions). The blind arm's extra FP
come from such guesses.

## Mechanism

### The answers (all 78 methods, 418 questions)

| | blind | sees-code |
|---|---|---|
| UNDETERMINED | **71 (17.0%)**; 4 methods all undetermined, 38 none | **22 (5.3%)**; 0 all, 64 none |
| determined answers citing (share of determined) | javadoc **91%**, class_context 22%, caller 9%, overload 8%, naming 4%, standard 3% | implementation **87%**, javadoc 59%, class_context 23%, standard 4%, caller 3%, overload 2% |
| evidence items of determined answers | 706: javadoc 68%, class_context 16%, caller 7%, overload 5%, naming 2%, standard 2% | 943: implementation 50%, javadoc 33%, class_context 13%, others ≤2% each |
| most common source combination | javadoc only 224 of 347 | implementation + javadoc 137, implementation only 90 of 396 |
| quotes found in the pack (whitespace, case, `*`, HTML and `...` ignored) | 629 / 680 (92%) | 894 / 926 (97%) |
| UNDETERMINED by question concept | C1 null 17/55, C7 chars 9/29, C0 14/103, C3 13/64, C5 7/48, C8 5/37, C2 2/31, C4 2/29, C6 2/22 | at most 6 per concept |

- **Answers without the body rest on the developer Javadoc.** Callers and overloads, which were collected at
  some cost, are cited in only 9% and 8% of determined blind answers. In 10 methods the pack has neither, and in 17
  methods the caller search found no mention outside the method itself.
- **With the body, the answerer reads the answer off the code.** 87% of its determined answers cite the
  implementation. It almost never says UNDETERMINED: 5%, against 17% blind. Both arms give identical expected text on
  136 of the 341 questions they both answered.
- The unverified quotes are mostly paraphrases or merged lines. Two blind evidence items carry an unexpected source
  label (the orchestrator asked me to check them). Codec_6 Q4 is labelled `implementation` but quotes the sentence
  "// The method's own implementation is not shown.", not body text. Lang_4 Q4 is labelled `other` and quotes the
  method's declaration, which is in the blind pack. I checked every blind evidence item, determined or not, for text
  that occurs in the focal body but not in the blind pack: **there is none.**

### Do the answers match the buggy or the fixed behaviour? (offline judge; the patch is used here only)
The judge (`judge.py`) is one call per method. It sees the buggy body, the fix hunk and the trigger tests, plus the
questions with both arms' answers as A/B in a seeded random order. For each question, it traces both versions on the
input and decides whether they differ ("relevant"). It then labels each answer BUGGY / FIXED / NEITHER, or SAME /
NEITHER when the behaviour is not relevant. UNDETERMINED answers are not judged.

| judge v2 (used) | blind | sees-code |
|---|---|---|
| relevant questions (72 in 49 methods): BUGGY / FIXED / NEITHER / UNDETERMINED | **10** / 36 / 13 / 13 | **22** / 38 / 8 / 4 |
| determined relevant answers matching buggy | **10 / 46 (22%)** | **22 / 60 (37%)** |
| methods with ≥1 BUGGY / ≥1 FIXED relevant answer | 8 / 26 | 18 / 27 |
| other questions (346): SAME / NEITHER / UNDETERMINED | 242 (70%) / 46 (13%) / 58 (17%) | 296 (86%) / 32 (9%) / 18 (5%) |
| methods with ≥1 BUGGY answer: ≥1 M among them, vs among the rest | 0/7 vs 2/68 | **5/16 vs 3/59** |
| methods with ≥1 FIXED answer: ≥1 E among them, vs among the rest | 16/25 vs 14/50 | 14/26 vs 14/49 |

The two arms disagree on the relevant questions as follows. On 10 questions blind is FIXED and sees-code BUGGY. On 4
questions blind is BUGGY and sees-code FIXED. On 4 questions blind is UNDETERMINED and sees-code BUGGY. On 6 questions
blind is UNDETERMINED and sees-code FIXED. Exact McNemar on "answered BUGGY": sees-code only 17, blind only 5,
**p = 0.017**. The table above (methods with ≥1 BUGGY answer, row 5) links the BUGGY answers to the tests. In
sees-code, 5 of the 16 methods with a BUGGY answer have ≥1 M, against 3 of the other 59.

**Judge validation (`manual_judge.json`, 29 questions read with the patch; 1 more was undecidable).**
- v1 (m2-style, thinking off, relevance asked first; `out/judge_v1.jsonl`) marked all 20 of my first-set questions
  relevant, but only 10 were.
- v2 traces both versions before deciding relevance and runs with dynamic thinking (offline only). Its first pass hit
  `max_tokens=8000` on 23 methods, because thinking counts against the limit. Those methods were re-judged with 32,000
  tokens, and all 418 questions are now judged.
- v2 against my verdicts:
  - relevance agrees on 21/29;
  - of its relevant questions, 12/19 really are relevant, and it finds 12 of my 13;
  - answer verdicts agree on 36/54 (39/54 with FIXED and SAME both counted as "correct");
  - BUGGY labels: blind judge 3 vs me 2 (1 shared), sees-code judge 8 vs me 6 (4 shared).
  - On a uniform sample of its relevant questions (outside my first set), only 3 of 9 were really relevant: for
    example Gson_15 NaN without lenient mode, and Lang_30 where 'c' occurs before the emoji. The false relevance
    produces spurious BUGGY labels in both arms (blind 3, sees-code 4 in that sample).

So the absolute BUGGY rates above are inflated. The direction is the same in v1 (determined relevant answers matching
buggy: blind 18/65, sees-code 32/78; BUGGY only in sees-code 27 vs only in blind 13, p = 0.038), in v2, and in my
own 29 verdicts (BUGGY: blind 2, sees-code 6). The test outcomes, which are execution-based, agree with it too.

## Questions and evidence packs

- **Questions.** There are 418 questions in 78 methods (1-6 per method; 47 methods have 6). By concept: C0 103,
  C3 64, C1 55, C5 48, C8 37, C2 31, C4 29, C7 29, C6 22. The guard rejected 30 question instances:
  - 19 named identifiers that occur only in the body (`readResults`, `setInitialBuffer`, `getDefault`, …);
  - 11 used hinting wording (currently, still, instead, implementation).
  11 methods were re-asked once with the rejected questions listed. The guard is conservative. For example, it
  rejected Lang_50 questions that use `Locale.getDefault()` as an input, and those questions were about the actual
  bug. I read all 418 accepted questions. About 7 still hint at the mechanism without stating any outcome:
  - Cli_8 Q5: "if findWrapPos repeatedly returns a wrap position that does not advance … infinite loop";
  - Lang_11 Q6: "… or will it … loop indefinitely?";
  - Codec_6 Q3/Q4 and Codec_8 Q2: an internal buffer primed with the caller's array;
  - Lang_50 Q3: the cast to SimpleDateFormat;
  - Lang_51 Q1: "not the interned literal".
  None of these 7 methods is M in either arm.
- **Evidence packs.**
  - 39 methods have ≥1 same-name method, 61 have ≥1 caller snippet, and 10 have neither. The blind pack median is
    7.3k chars (max 25.5k, Lang_35 `add` with 6 overloads).
  - Strict blindness: 31 same-name methods or snippets in 15 methods were dropped because they share a 40-char window
    with the focal body. Example: the other buggy `join` overload of Lang_20 duplicates the focal loop.
  - No blind pack, blind answer prompt or blind appended section contains a focal-body window (asserted).
  - Every snippet comes from tracked files of the main source directory, and the tracked main sources are
    unmodified in all 60 checkouts.
  - Offline, other buggy code still reaches the blind pack:
    - 11 packs contain another focal method of the same bug as a same-name method (Gson_4 ×5, Lang_30 ×3,
      Lang_35 ×1, Lang_46 ×2). The sensitivity check above excludes these.
    - 5 packs contain a line that the fix changes outside the focal method. These are field declarations (Cli_1,
      Lang_4) and delegating overloads (Lang_35, Lang_46 ×2). The field declarations are also in the upstream prompt.
- **Test-generation prompts.** Both arms have the same 4 prompts with a focal-body window (Gson_8, and Lang_36/3/44
  `createNumber`). These windows are inherited unchanged. Gson_8's is in the upstream "Other methods" context, and
  the `createNumber` ones are in the upstream Advanced docstrings, which quote the body. The Advanced Doc baseline
  prompts contain them too. The appended sections add no body window in either arm.

## LLM calls

| step | blind | sees-code | notes |
|---|---|---|---|
| questions (shared by both arms) | 100 | 100 (the same) | 78 + 11 guard re-asks + 11 parse re-asks (Lang_16/27/36/7: 3 calls). The first question run crashed on an exhausted 429 retry. The questions it had generated after method 14 were not saved, so an unknown number of calls (at most about 80) was spent and discarded. All saved questions come from the second run. |
| answers | **78** | **82** | sees-code: Gson_7 made 3 unparsable calls (the reply quoted Java `\'`, which is an invalid JSON escape), then 1 at T=0 after the parser fix. Lang_30 `indexOfAnyBut` (idx 42) uses its T=0.5 re-ask. |
| test generation | 78 | 78 | all 78 completions of each arm contain a Java block |
| Advanced docstrings (reused, made earlier) | 78 | 78 | |
| **total per arm** | **334** | **338** | Matched by design: same questions and pack, one answer call per method. |
| smoke (Cli_32, Lang_20, Lang_40) | 3 questions + 3 answers per arm (cached, reused) + 3 test generation | same | |
| offline judge | v1 78, v2 134 (78 + 32 re-asks of truncated replies + 24 re-runs) | | not part of the method |

429 retries inside the shim are not counted. The smoke evaluation of the sees-code arm completed (3 methods: M 0, E 4,
FP 16). The blind smoke evaluation hit the known ENOENT on Cli_32 ("Project directory … not found. Skipping."). It
was not re-run, because the full blind run evaluated those methods without error.

## Caveats
- **Single runs, small n.** 75 methods from 57 bugs, one T=0 run per arm. The methods are not independent: Gson_4 has
  6 methods and Lang_30 has 5. m4 measured that 15-18 of 75 methods flip their ≥1 E status between two single T=0
  runs. The E-side differences here are inside that range: blind vs sees-code has 16 discordant methods, blind vs
  Advanced 18. **No E difference is distinguishable from noise.** The M difference (0 vs 6 discordant, p = 0.031) is
  the only significant result. It is not corrected for the six comparisons in the table. Its support is that each of
  the 6 methods traces to a clarified rule that states the buggy behaviour.
- **What the blind agent knows.** Its intent comes almost entirely from the developer Javadoc, which no upstream
  prompt contains (see m5). The comparison with Advanced Doc therefore mixes two changes: "an answering agent" and
  "the Javadoc enters". m5 B, a spec written from the same Javadoc, gives the same picture. Where the buggy version's
  documentation describes the bug (Gson_4, Lang_35), the blind agent copies it, as any reader of that documentation
  would.
- **The judge.** Its relevance decision is the weak point (precision about 12/19 on my set, 3/9 on a uniform sample),
  and that inflates BUGGY counts in both arms. Treat the judge figures as direction only. The validation is by one
  reader (me), using the patch, the trigger tests and the code.
- **Questions are written from the buggy code.** They point both arms at bug-prone inputs, as m4's inputs did. The
  question writer can only hint at the code. The deterministic guard plus a manual read leave about 7 soft mechanism
  hints and no stated outcome.
- **Answer prompt.** The source list adds `implementation` to the requested six types ("only if it is shown above"),
  in both arms, so that the control's use of the body is measurable. The prompt text is identical across arms.
- **Prompt tuning: none.** The question, answer and docstring formats were fixed before the smoke run and not changed.
  Two parser fixes were made after the smoke run. The first makes the LLM pool tolerate a failed method instead of
  aborting. The second accepts invalid `\'` JSON escapes. The second applies to both arms; only Gson_7's sees-code
  answer was affected.
- **Infrastructure.** Each arm was evaluated in 2 parts. Cli_15, the first method, compiled no test, and the upstream
  `ZeroDivisionError` followed. `eval_parts.py` kept that finished block and resumed at method 2. There was no ENOENT
  crash and no glitched block in either arm. During the first blind test generation, the judge ran at the same time
  and both competed for the Vertex quota; after the orchestrator's note, every later step ran strictly one at a time.
  Generation is at T=0 and the prompts do not depend on timing, so this only slowed generation.
- **Leakage.** No method prompt contains the patch, the fixed version, trigger tests or labels, and nothing from a
  test directory. The Defects4J checkouts' git history contains the fixed version, but only the working tree is read.
- Files written outside this folder: `data/prompts/*m6_oracle_*`, `data/prompts/rq1/*m6_*`, `data/rq1/logs/*m6_*`,
  `data/rq1/results_test/chatgpt/*m6_*`, and the pipeline's `run/out/{prompt,testgen,eval}_m6_*`. No change to `run/`,
  upstream files or other method folders.
