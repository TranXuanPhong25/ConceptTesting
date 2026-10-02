# m2_concept_diag: results

This is a diagnostic only. There are no arms, no test generation and no evaluation. It uses 78 focal methods from
60 Defects4J bugs. Outcomes are the existing clean per-method outcomes (glitched methods are excluded per config:
Only Doc Lang_11; Advanced Doc Cli_8, Lang_11, Lang_4; m1 Adv Doc Lang_11). The full output is in
`out/analysis.txt` (`python3 m2_concept_diag/analyze.py`).

## Short answer
- **Coverage.** When I read the fixes myself, 70 of 78 methods (90%) and 53 of 60 bugs (88%) concern at least one of
  C1-C8. Only 8 methods are "other logic" (C0). The simple rules reach **60%** (47/78 methods, 36/60 bugs), and only
  41/78 (53%) get at least one *correct* C1-C8 label. The micro precision and recall of the rules are both 0.56.
  The rules find the syntactic concepts reliably: C1 null (P 0.80), C4 throw/catch (P 1.00 but R 0.53), C7 characters
  (R 0.91). They miss the semantic ones: C5 format/escaping (R 0.10), C6 numeric (0/4) and C8 state (R 0.17). C3
  over-fires (P 0.43), because almost any rewritten line contains `<`, `+1`, `charAt` or an index.
  The concepts themselves therefore cover the bugs well. A regex-level "concept diff" does not recover them well.
- **Judge.** Gemini judged the basic docstrings as 37% BUGGY, **4% FIXED** and 59% NEITHER, and the advanced ones as
  41% / 17% / 42%. That is far from the paper's manual 15% / 62% (see caveats). The judge agrees with me on
  17/26 = 65% of the cases I checked (20/26 on the binary BUGGY-vs-not and FIXED-vs-not questions).
- **Docstring verdict vs outcome: no association in any config.** The Fisher p-values are all ≥ 0.24. A BUGGY
  docstring does not predict a misguided method: Doc W/ Code 4/29 vs 4/49, Only Doc 2/29 vs 3/48, Advanced 1/31 vs
  2/44. A FIXED advanced docstring is only weakly and non-significantly linked to an effective method: 6/12 vs 24/63,
  p=0.53. For most methods the docstring is silent on the changed behaviour, and E tests appear anyway (Only Doc: 16 of
  its 27 E-methods have a NEITHER docstring).
- **Concepts.** Effective methods fall mostly in C4 error contract, C1 null and C3 boundary. C7 characters (11
  methods: surrogates, locale, case) almost never gets an E: 0 in Doc W/ Code and Only Doc, 1 in Advanced. C8 state
  gets at most 1 E per config. The misguided methods are few (8 / 5 / 3). They cluster in C1+C4: Lang_35 `add` ×2,
  Lang_33, Lang_7, where the buggy code's null/error behaviour gets copied. Lang_57 (C8) and Cli_1 (C0) are M in
  every config.
- **Config differences.** Doc W/ Code has the most M-methods in C1/C4 (3 and 3, vs 1/2 in Only Doc and 0/1 in
  Advanced), which is consistent with the buggy code in the prompt spreading its null/error behaviour. Advanced beats
  Only Doc in C5 (6 vs 2 E-methods) and C4 (9 vs 7). Advanced docstrings describe the fixed behaviour more often
  (13 vs 3 FIXED). But on the same methods, the 11 methods that moved to FIXED gain only 2 E-methods and lose 1, so
  the docstring verdict does not explain the Advanced gain.

## 1. Rule labels (`labels.jsonl`) vs my reading of all 78 in-method diffs (`manual_labels.json`)

Validation covers all 78 methods (the task asked for ≥30). I labelled "the concept the bug concerns" from the
in-method diff, the trigger-test names and the failure messages. Rule labels are from the first rule version; the rules
were not tuned after this reading.

| concept | rule+ | manual+ | TP | FP | FN | precision | recall | agreement | kappa |
|---|---|---|---|---|---|---|---|---|---|
| C0 | 31 | 8 | 6 | 25 | 2 | 0.19 | 0.75 | 0.65 | 0.17 |
| C1 null | 10 | 12 | 8 | 2 | 4 | 0.80 | 0.67 | 0.92 | 0.68 |
| C2 empty | 3 | 3 | 2 | 1 | 1 | 0.67 | 0.67 | 0.97 | 0.65 |
| C3 boundary | 35 | 19 | 15 | 20 | 4 | 0.43 | 0.79 | 0.69 | 0.35 |
| C4 error contract | 10 | 19 | 10 | 0 | 9 | 1.00 | 0.53 | 0.88 | 0.63 |
| C5 format/escaping | 2 | 10 | 1 | 1 | 9 | 0.50 | 0.10 | 0.87 | 0.13 |
| C6 numeric | 2 | 4 | 0 | 2 | 4 | 0.00 | 0.00 | 0.92 | -0.04 |
| C7 chars/locale | 19 | 11 | 10 | 9 | 1 | 0.53 | 0.91 | 0.87 | 0.59 |
| C8 state | 3 | 6 | 1 | 2 | 5 | 0.33 | 0.17 | 0.91 | 0.18 |

- Micro over C1-C8 label instances: precision 47/84 = 0.56, recall 47/84 = 0.56. The label sets match exactly for
  20/78 methods. When a rule emits ≥1 C1-C8 label (47 methods), at least one of them is right in 41.
- Coverage (≥1 of C1-C8): rules 47/78 methods (60%), 36/60 bugs (60%). Manual 70/78 methods (90%), 53/60 bugs (88%).
  Manual labels per method: 8 have none (C0), 58 have one concept, 10 have two, 2 have three. Per bug (manual): C3 18,
  C4 13, C1 8, C5 7, C7 7, C0 7, C8 6, C6 4, C2 3.
- Where the false positives come from: C3 relational-operator (11), charAt/substring/indexOf (11), ±1 (10), array
  index (10), length/size (8). C7 char literals such as `'.'`, `'-'`, `' '` (7). These fire on any rewritten
  condition.
- Where the misses come from, all needing semantics:
  - C4: Gson_4's `beforeValue(false)` → `beforeValue()` (6 methods; the effect is a spurious IllegalStateException),
    and Lang_7's deleted `return null`.
  - C5: flag arguments (`encodeBase64(.., true→false)`, `escapeJavaStyleString(.., false, false)`) and class-name
    encoding.
  - C6: float precision cut-offs, and a zero numerator.
  - C8: shared iterator, `calendar.getTime()` before clone, static init order.
- Locating the method: 78/78 methods were found in the buggy checkout, and 77 contain part of the patch. The patches
  go fixed → buggy (the `+` side equals the buggy file), so `labels.py` inverts them. 53 diff lines, all in Cli_1,
  do not match the checkout at their stated line numbers (whitespace/blank-line drift in that patch). The in-method
  hunk of Cli_1 is correct. The patch does not touch Lang_30 `indexOfAny(String, String[])`, which is labelled from
  the whole patch.

## 2. LLM judge (`judge.jsonl`)

| docstring set | BUGGY | FIXED | NEITHER |
|---|---|---|---|
| basic (Doc W/ Code, Only Doc) | 29 (37.2%) | 3 (3.8%) | 46 (59.0%) |
| advanced (Advanced Doc) | 32 (41.0%) | 13 (16.7%) | 33 (42.3%) |
| paper (manual, Gemini docstrings) | 15.09% | 62.26% | rest |

- Basic → advanced transitions: BUGGY→FIXED 7, NEITHER→FIXED 5, NEITHER→BUGGY 16, BUGGY→NEITHER 7, unchanged 41.
  Advanced docstrings are longer (3.8k vs 1.0k chars) and commit to more behaviour, in both directions.
- Validation: I gave my own verdicts on 26 cases (every 6th method × both sets) and **agreed on 17/26 = 0.65**.
  - Confusion (mine → judge): BUGGY→BUGGY 5, BUGGY→FIXED 1, FIXED→FIXED 3, FIXED→NEITHER 3, FIXED→BUGGY 2,
    NEITHER→NEITHER 9, NEITHER→BUGGY 3.
  - Binary agreement: 20/26 for BUGGY-vs-not and 20/26 for FIXED-vs-not.
  - The judge leans towards BUGGY. It quoted the patch code instead of the docstring once (Csv_16), and twice read
    "startIndex ≥ size → -1" as buggy behaviour (Lang_60). In the other direction, one verdict contradicts its own
    reason: Gson_15 basic says "always throws IAE for NaN", which is the buggy behaviour, yet the judge answered
    FIXED.
  - 73 of the 77 BUGGY/FIXED quotes occur verbatim in the docstring.
  - Before writing my verdicts I saw the judge's output for 2 of the 26 cases (Gson_15 and Lang_16, basic). I
    disagree with one of them.
- Calls: 156 judge calls for 156 judgements (1 per method × set), 0 parse failures, 0 retries for format. The
  51 retries on 429 errors happened inside the shim and are not counted.

## 3. Outcomes per bug concept (manual labels; methods can appear in more than one row)

Cells: methods with ≥1 E / ≥1 M, then (M/E/FP tests; red-precision).

| concept | n | Doc W/ Code | Only Doc | Advanced Doc | m1 review Only Doc | m1 review Adv Doc |
|---|---|---|---|---|---|---|
| C0 | 8 | E2 M1 (8/2/7; 0.22) | E3 M1 (1/3/16; 0.16) | E3 M1 (7/3/11; 0.21) | E3 M0 (0/3/9; 0.25) | E3 M1 (5/3/15; 0.17) |
| C1 | 12 | E3 M3 (4/7/14; 0.33) | E6 M1 (1/15/19; 0.44) | E6 M0 (0/11/29; 0.28) | E1 M1 (1/1/9; 0.10) | E5 M0 (0/9/18; 0.33) |
| C2 | 3 | E2 M0 (0/6/4; 0.60) | E1 M0 (0/8/9; 0.47) | E2 M0 (0/5/7; 0.42) | E0 M0 (0/0/3; 0.00) | E1 M0 (0/3/3; 0.50) |
| C3 | 19 | E5 M1 (2/19/64; 0.23) | E6 M1 (1/15/121; 0.11) | E6 M0 (0/22/102; 0.18) | E5 M1 (1/9/71; 0.11) | E5 M0 (0/19/77; 0.20) |
| C4 | 19 | E6 M3 (4/35/42; 0.45) | E7 M2 (2/33/79; 0.29) | E9 M1 (1/32/70; 0.31) | E4 M2 (2/15/39; 0.28) | E8 M1 (1/22/42; 0.34) |
| C5 | 10 | E3 M0 (0/6/33; 0.15) | E2 M0 (0/8/50; 0.14) | E6 M1 (1/27/36; 0.43) | E2 M0 (0/8/34; 0.19) | E5 M1 (1/21/27; 0.44) |
| C6 | 4 | E1 M1 (2/1/13; 0.07) | E3 M1 (1/3/21; 0.12) | E3 M0 (0/6/28; 0.18) | E2 M1 (1/2/17; 0.11) | E2 M0 (0/3/28; 0.10) |
| C7 | 11 | E0 M0 (0/0/14; 0.00) | E0 M0 (0/0/36; 0.00) | E1 M1 (1/1/33; 0.03) | E0 M0 (0/0/25; 0.00) | E1 M1 (1/1/25; 0.04) |
| C8 | 6 | E0 M1 (3/0/0; 0.00) | E1 M1 (6/1/13; 0.07) | E0 M1 (1/0/16; 0.00) | E1 M1 (5/1/5; 0.17) | E1 M0 (0/1/7; 0.12) |

- Red-precision is highest for C1, C2 and C4 (0.3-0.6). It is near zero for C7 (0.00-0.04) and C8: tests on
  surrogate/locale/state bugs fail on both versions, or they pass.
- C4's E count is inflated by the six Gson_4 methods, which share one bug (top-level values). These methods get E in
  every config.
- m1's review hurts most in C1: Only Doc goes from 6 to 1 E-method. Those are the tests the reviewer dropped as
  "docstring does not define null behaviour" (see m1 RESULTS).
- The same table with rule labels is in `out/analysis.txt`. It is noisier: its C0 bucket holds 31 methods, with
  E-methods 11/14/14.

## 4. Docstring verdict vs outcome (per method, glitched excluded)

| config | verdict | n | ≥1 E | ≥1 M |
|---|---|---|---|---|
| Doc W/ Code | FIXED / BUGGY / NEITHER | 3 / 29 / 46 | 0 / 8 / 12 | 0 / 4 / 4 |
| Only Doc | FIXED / BUGGY / NEITHER | 3 / 29 / 45 | 1 / 10 / 16 | 0 / 2 / 3 |
| Advanced Doc | FIXED / BUGGY / NEITHER | 12 / 31 / 32 | 6 / 15 / 9 | 0 / 1 / 2 |
| m1 review Only Doc | FIXED / BUGGY / NEITHER | 3 / 29 / 46 | 0 / 7 / 11 | 0 / 2 / 2 |
| m1 review Adv Doc | FIXED / BUGGY / NEITHER | 12 / 32 / 33 | 5 / 12 / 10 | 0 / 1 / 1 |

Fisher exact, two-sided (verdict = v vs the rest):

| config | FIXED → ≥1 E | BUGGY → ≥1 M | BUGGY → ≥1 E |
|---|---|---|---|
| Doc W/ Code | 0/3 vs 20/75, p=0.57 | 4/29 vs 4/49, p=0.46 | 8/29 vs 12/49, p=0.79 |
| Only Doc | 1/3 vs 26/74, p=1.00 | 2/29 vs 3/48, p=1.00 | 10/29 vs 17/48, p=1.00 |
| Advanced Doc | 6/12 vs 24/63, p=0.53 | 1/31 vs 2/44, p=1.00 | 15/31 vs 15/44, p=0.24 |
| m1 review Only Doc | 0/3 vs 18/75, p=1.00 | 2/29 vs 2/49, p=0.63 | 7/29 vs 11/49, p=1.00 |
| m1 review Adv Doc | 5/12 vs 22/65, p=0.74 | 1/32 vs 1/45, p=1.00 | 12/32 vs 15/45, p=0.81 |

- Only 3 basic docstrings are FIXED, so "describes the fixed behaviour" cannot be tested for Doc W/ Code or Only Doc.
- A BUGGY docstring is not a marker of misguidance. The M-methods split BUGGY/NEITHER 4/4 (Doc W/ Code), 2/3
  (Only Doc) and 1/2 (Advanced). Meanwhile 25-30 of the 29-31 BUGGY methods get no M, and 28-48% of them
  get ≥1 E.
- With the judge at 65% agreement, a real but weak association could be hidden. The data do not show a strong one.

## 5. Where the misguided and effective methods fall (manual concept; judge verdict B/F/N)

- ≥1 M. Doc W/ Code (8): Cli_1 hasOption [C0;N], Cli_32 findWrapPos [C3;N], Lang_33 toClass [C1;B],
  Lang_35 add ×2 [C1+C4;B], Lang_49 reduce [C6;N], Lang_57 isAvailableLocale [C8;N], Lang_7 createNumber [C4;B].
  Only Doc (5): Cli_1, Lang_1 [C3+C6;N], Lang_35 ×1, Lang_57, Lang_7. Advanced (3): Cli_1 [C0;B], Lang_57,
  Lang_5 toLocale [C4+C5+C7;N].
- ≥1 E, by concept (Doc W/ Code / Only Doc / Advanced): C4 6/7/9, C3 5/6/6, C1 3/6/6, C5 3/2/6, C6 1/3/3,
  C2 2/1/2, C0 2/3/3, C8 0/1/0, C7 0/0/1.

## 6. Does this explain Only Doc vs Doc W/ Code vs Advanced? (75 methods clean in all three)

| concept | n | Doc W/ Code E/M | Only Doc E/M | Advanced E/M |
|---|---|---|---|---|
| C0 | 7 | 2/1 | 3/1 | 3/1 |
| C1 | 12 | 3/3 | 6/1 | 6/0 |
| C2 | 3 | 2/0 | 1/0 | 2/0 |
| C3 | 17 | 5/1 | 6/1 | 6/0 |
| C4 | 18 | 6/3 | 7/2 | 9/1 |
| C5 | 10 | 3/0 | 2/0 | 6/1 |
| C6 | 4 | 1/1 | 3/1 | 3/0 |
| C7 | 11 | 0/0 | 0/0 | 1/1 |
| C8 | 6 | 0/1 | 1/1 | 0/1 |

- **Doc W/ Code vs Only Doc.** They use the same basic docstring, so the docstring cannot explain the difference.
  The difference sits in C1 (E 3 vs 6, M 3 vs 1) and C4 (M 3 vs 2). This fits the paper's mechanism: with the
  buggy body in the prompt, the model copies the body's null/error behaviour (Lang_33 toClass, Lang_35 add, Lang_7).
- **Advanced vs Only Doc.** The gain is in C5 (6 vs 2 E-methods) and C4 (9 vs 7). Advanced docstrings are FIXED more
  often (13 vs 3). Paired on the same methods, though, the gain does not follow the verdict:
  - methods that moved basic→advanced to FIXED (11): Only Doc 5 E-methods, Advanced 6 (+2/−1);
  - NEITHER→BUGGY (16): +5/−3;
  - BUGGY→BUGGY (14): +2/−2.

  Advanced's extra E-methods come as much from docstrings that describe the *buggy* behaviour in more detail as from
  those that describe the fix. The more likely driver is that longer, more concrete docstrings trigger more tests on
  the edge case, whatever the stated expectation.

## LLM calls
| step | calls | notes |
|---|---|---|
| judge (Gemini 2.5 Flash, thinking off, T=0) | 156 | 78 methods × 2 docstring sets, no re-asks needed; 429 retries inside the shim not counted |
| labels / analysis | 0 | deterministic |

There is no control arm: this method generates no tests and changes no arm, so rule 3 does not apply. The judge was
checked against my verdicts instead.

## Caveats
- n = 78 methods / 60 bugs, and the methods are not independent: Gson_4 contributes 6 methods, Lang_30 5, Lang_35,
  Lang_36, Lang_46, Lang_47, Lang_50 and Lang_60 2 each. There are only 8/5/3 M-methods, so M-side tests have almost
  no power.
- The manual concept labels come from one reader (me). The boundaries are judgement calls: C5 vs C7 for case/locale
  formats, C3 vs C6 for digit-count limits, C4 vs C0 for a read() that returns 0. My notes are in
  `manual_labels.json`. The rule labels are noisy (micro P = R = 0.56), and the conclusions in sections 3-6 use the
  manual labels.
- One judge model, one prompt, and 65% agreement with me on 26 cases. The judge also leans BUGGY. Its numbers are not
  comparable to the paper's 15%/62%: the paper judged "the docstring describes the corrected behaviour" by hand over
  318 methods, probably with a looser reading (for example "describes the intended functionality"). Our question is
  narrower: "is the changed case described?". A docstring that is silent on that case counts as NEITHER here.
- The judge sees the trigger-test names and messages. That helps it find the changed case, but it may also make
  generic statements look like BUGGY.
- Leakage: the patch, fixed version and trigger tests are used only in `labels.py`, `judge.py` and the analysis. No
  generation prompt was produced here.
- Files outside `m2_concept_diag/`: none written. The judge used `run/gemini_shim.py` unchanged.
