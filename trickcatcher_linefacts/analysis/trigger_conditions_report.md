# Trigger inference: turning code-level facts into input-level conditions (offline, CPU)

Date 2026-10-13. Plan rank 3 in CONCEPT_WEAKNESS.md (extended per SAVIOR note to "trigger inference").
No LLM call, no HumanEval+ labels, no edits to existing files. Script: `analysis/trigger_conditions.py`;
outputs: `out/trigger_conditions/`.

## 1. What was done

Input material is only what the method can see: PUT source, base-test inputs (`tracer.run_base`) and the
v3m2 fuzz inputs. The fuzz inputs are not stored in `out/facts_v3m2`, so each task's worker calls
`facts.main` again with the same seed, mined validator (`out/precond_qwen7b_v2`, sha256 matches every
`valid_sha256`) and PUT. **Reproduction check:** on all 93 tasks with shown facts, fact texts, witness
indices and `n_fuzz` are identical to `out/facts_v3m2`. All 198 shown facts re-hit their witness. Fact hits use
`tracer.fact_hit` with the PUT/mutant outputs. Each worker runs as
`unshare -rn python3 -I -B ... worker N` under `timeout`. It took 50 min of CPU in total; tasks 59 and 83 take
about 11 min each.

**Feature library.** It was fixed in code before any outcome was computed (`build_library`). It covers:
- **Per parameter:** type (int/float/str/list/...); numeric = 0, < 0, > 0, = 1, = -1, non-integer,
  whole-number float, odd/even, |x| ≥ 1e6, above the max / below the min seen in base, = / > / < each numeric
  code constant.
- **Length:** 0, 1, 2, ≤ 1, ≤ 2, ≥ 3/5/10, odd/even, above the base max / below the base min, = a code constant.
- **Strings:** has/all uppercase, has/all lowercase, first char uppercase, digit, all digits, no letters,
  whitespace, only whitespace, leading/trailing/double space, non-ASCII, punctuation, repeated char, contains /
  equals / shares a char with a code string literal.
- **List elements:** any/all negative, any zero, all positive, non-integer, float, very large, first/last
  negative, odd/even, above the base max / below the base min, contains a code constant, sorted asc / strictly
  asc / desc / unsorted, duplicates, all equal, mixed types. Lists of strings: empty string, uppercase,
  whitespace, non-ASCII, punctuation, digit, 1-char string. Nested lists: empty inner list, ragged.
  Dicts: non-string key, mixed-case keys.
- **Parameter pairs:** a = b, a > b, a < b; len equal / different / longer / shorter; equal sequences;
  substring both ways; int = len(seq), > len, ≥ len; value is an element of the list.

**Optional source guard (per fact).** This only applies when the expression reads only parameters that the
function never reassigns or mutates:
- OUTCOME: the branch condition with the missing polarity.
- STMT: the innermost enclosing `if`/`while` test.
- MUTANT: "the original and mutated fragments evaluate differently".

Such a guard exists for 42/198 shown facts.

**Search and decision rules.** These were fixed before the outcomes.
- **Candidate condition C:** 1 feature, or a conjunction of 2. C must be true on the witness and false on every
  base input.
- **Predictive test on the ≤ 400 fuzz inputs:** P(hit | C) ≥ 0.5, and either P(hit | not C) = 0 or
  P(hit | C) ≥ 3 · P(hit | not C).
- **Choice:** a passing singleton beats any pair. Within the same size, pick by F1, then precision, then
  library order.
- **Status:** a condition that passes is "derived". If nothing passes, the best separating candidate is kept
  as "weak".
- **Explained miss:** a missed case (fact × sample) is "explained" when none of Qwen's valid round-1 inputs
  for that sample satisfies C.

Manual causes are read from `out/analysis_weak/build_page.py` (`order`, over the 42 sorted groups).
My re-computed hit flags for Qwen's inputs agree with `follow_cases.json` in 194/195 cases. The one mismatch
is task 67, sample 0.

## 2. Results on the 87 missed (good hint × sample) cases

The table uses library + guard. Library-only differs only in cause 2: 2 explained instead of 3.

| Manual cause | n | C derived | derived and Qwen's inputs violate C (explained) | weak only (explained) | nothing separates witness from base |
|---|---|---|---|---|---|
| 1. did not try the simple input form | 38 | **34** | **34** | 4 (3) | 0 |
| 2. right direction but off | 8 | 4 | 3 | 4 (3) | 0 |
| 3. only invalid inputs reach | 6 | 3 | 3 | 3 (3) | 0 |
| 4. needs a computed value / combination | 35 | 16 | 13 | 11 (8) | 8 |
| all | 87 | 57 | **53** | 22 (17) | 8 |

- **Cause 1 (target):** the derived input-level condition covers and explains 34/38 cases (89%). Caveat: one
  of these (task 56) had no valid Qwen input at all, so it is explained trivially.
  - The 4 that are not covered are task 80 (`s.lower()` mutant, 3 cases) and task 163 (1 case).
  - For task 80, "has uppercase" separates the witness from the base inputs but has precision 0.07: an
    uppercase letter rarely changes `is_happy`.
  - For task 163, the needed "a > b" already occurs in a base test, so no single feature or pair separates.
- **Does C capture the trigger in Qwen's own input space?** On every unique valid Qwen input for the good
  facts that have a derived C, P(hit | C) = 105/110 (95%) and P(hit | not C) = 13/852 (1.5%). Recall is
  105/118. In the 108 hit cases, a hitting Qwen input satisfies C in 75 of the 78 cases that have a C. So when
  Qwen does satisfy the condition it almost always hits the fact, and when it misses, it almost always
  violated the condition. This is the main evidence that "say C to Qwen" could fix these misses. It is
  evidence, not a run: no LLM was called.
- **Post-hoc robustness.** This rule was added after seeing the numbers: keep only derived conditions with
  recall ≥ 0.5 on fuzz.
  - The point is to remove surface correlates, such as "string with ≥ 10 characters" for the palindrome
    branches of tasks 10 and 14, or a 1-input pair for task 3.
  - Explained cases under this rule: cause 1 is unchanged at 34/38, cause 2 is 3, cause 3 is 3, cause 4 is
    10, and the total is 50/87.

**Coverage over shown facts.** Library + guard, derived / total; every shown fact has a witness.

| Set | derived | weak only | post hoc recall ≥ .5 |
|---|---|---|---|
| good shown facts (65 in follow_cases) | 45 (69%) | 12 | 42 |
| all shown facts, dev (165) | 114 (69%) | 36 | 99 |
| all shown facts, dev+pilot (198) | 139 (70%) | 42 | 119 |

- **By kind (dev+pilot):** NUM 24/26, BOUND 22/29, STMT 12/13, OUTCOME 29/38, MUTANT 42/75, DU 10/17.
  MUTANT and DU are the hard kinds: their trigger usually depends on intermediate values.
- **Shape of the conditions:** 117 of the 139 derived conditions are a single feature. The most frequent are
  len = 1, len = 2, = 0, negative, empty, list contains '', all negative.
- **Guard:** the source guard adds only 1 derived fact. It is the deciding feature in 6 conditions; e.g. task
  67 `n < 1`, where the library alone falls back to `n = 0`.

## 3. Ten examples: code-level fact vs. input-level hint

The "e.g." part is the witness. Without it the hint is the pure condition; with it, the hint is close to
toolinput (see §5).

| # | Task | Code-level fact (current) | Input-level hint (derived) | Qwen's round-1 inputs (missed) |
|---|---|---|---|---|
| 1 | 4 | True branch of `len(numbers) < 2` (line 13) never taken | No existing test calls `mean_absolute_deviation` with `numbers` with exactly 1 element (e.g. `[1.0]`). P = R = 1.0 | all lists with ≥ 2 elements |
| 2 | 9 | mutant `0` -> `1` at line 10 survives (also DU of `max_so_far`) | ... with `numbers` whose first element is negative (e.g. `[-1, 3, 2, 1]`). P 1.0, R .83 | no negative numbers |
| 3 | 12 | mutant `s.lower()` -> `s` at line 16 survives | ... with `strings` containing a string with an uppercase letter. P .73, R 1.0 | all lowercase / empty strings |
| 4 | 31 | parameter `n` of `is_prime` never negative | ... with `n` negative (e.g. `-5007`). P = R = 1.0 | 2, 9, 29, 97, ... |
| 5 | 61 | True branch of `len(brackets) == 0` (line 22) never taken | ... with `brackets` empty (e.g. `''`). P = R = 1.0 | non-empty bracket strings |
| 6 | 110 | True branch of `len(lst1) != len(lst2)` never taken | ... with `lst1` and `lst2` of different lengths. P = R = 1.0 | always equal lengths |
| 7 | 128 | True branch of `all(x < 0 for x in arr)` never taken; mutant `x > 0` -> `x < 0` | ... with `arr` with only negative numbers. P = R = 1.0 | always mixed with 0 / positive |
| 8 | 158 | DU `max_word` line 12 -> 20; mutant `0` -> `-1` line 13 | ... with `words` containing an empty string (e.g. `['']`). P .67, R 1.0 | no empty word |
| 9 | 160 (cause 4) | mutant `i == 0` -> `i == -1` at line 33 | ... with `operator` with exactly 1 element. P .93, R .96 | always ≥ 2 operators |
| 10 | 67 (cause 2, guard) | True branch of `n < 1` (line 18) never taken | ... with arguments for which `n < 1` is true (e.g. `(…, 0)`). P .95, R 1.0 | tried n = 0 once and still missed (2/3 explained) |

Example 9, and the two task-62 mutants ("`xs` with exactly 2 elements", P .89, R 1.0), are labelled cause 4
by hand, but they turn out to have a simple input-level trigger. The manual label and the derived condition
disagree there.

## 4. Where conditions cannot be derived (honest list)

- **No candidate at all: 8 cases, all cause 4.**
  - Task 153 (DU `strongest_extension`, mutants `-1` -> `-2` and `0` -> `1`), 6 cases: two extensions must have
    equal strength (uppercase count minus lowercase count). This is a computed value, and no per-argument
    feature separates the witness from the base inputs.
  - Task 69: the sub-condition `freq[i] > freq[i-1]` needs a frequency drop between adjacent values.
  - Task 102: the mutant `y % 2` -> `y // 2` needs a specific parity/size combination.
- **Weak only (separating but not predictive): 22 cases.** These are mostly cause 4:
  - task 20: nearest-pair position;
  - task 73: palindromic pairs `[3, 3, 1, 1]`, best feature "sorted descending", P .07;
  - task 3: running sum exactly 1;
  - task 81: `grade > 3.7` (best: a pair of code constants, P .13);
  - tasks 48 and 80: `.lower()` mutants, where uppercase is needed **and** it must change the result;
  - task 50: the needed non-letter is spec-forbidden (cause 3).
- **Cause 4 in general:** 16/35 get a derived condition, but by the post-hoc filter only 10 are robust, and
  those are the ones whose manual label is arguably cause 1 (tasks 62, 160, 85). Triggers that are relations
  between intermediate values are out of reach for a per-argument library; that would need path conditions
  over locals, i.e. symbolic or concolic execution.
- **Cause 3:** a condition exists (task 94: "≥ 5 elements and a negative number", P .50), but it describes
  inputs the mined spec forbids. Telling Qwen this would mostly add invalid inputs.

## 5. Caveats

- **Where the predictiveness comes from.** It is measured on the fuzz inputs, which are mutations of the base
  inputs. A condition can look predictive only because the fuzz space is narrow. The Qwen-input check in §2
  (95% vs 1.5%) is the independent validation, but it covers only the 65 good facts.
- **Selection is in-sample.** The condition is chosen per fact on the same fuzz set it is scored on. There is
  no held-out split for the selection rule; MIN_PREC = .5 and MIN_LIFT = 3 were fixed before running.
- **"Explained" is necessary, not sufficient.** It shows that Qwen's inputs did not satisfy C. Whether Qwen
  would follow a C-based hint is untested. Section B4 of CONCEPT_WEAKNESS.md already shows that v7's
  input-level spec hints were followed only partly.
- **The "e.g." example.** Including the witness makes the hint close to the toolinput arm. A fair test needs
  the pure condition text, or the condition as round-2 tool feedback ("your inputs all have len ≥ 2; the
  branch needs len < 2"), which is how plan rank 1 would use it.
- **One base hit.** For the RIL mutant of task 31, a base input already gives a different output; the
  assertion does not check it.

## 6. Rerun

```
cd trickcatcher_linefacts
python3 analysis/trigger_conditions.py run --jobs 10     # sandboxed workers (≈ 15–20 min wall at 10 jobs; 50 CPU-min), then analysis
python3 analysis/trigger_conditions.py analyze           # analysis only, from out/trigger_conditions/worker/*.json
```

Files:
- `out/trigger_conditions/summary.txt` / `summary.json`: all numbers above, plus a per-group table with both
  hint texts.
- `conditions.json`: per shown fact, the derived/weak condition, precision/recall/F1, and the hint text.
- `cases.json`: the 195 cases with the explained flag.
- `worker/<task>.json`: features, hits and guards per input.
- `regen/<task>.json`: the regenerated facts.
- `logs/`.
