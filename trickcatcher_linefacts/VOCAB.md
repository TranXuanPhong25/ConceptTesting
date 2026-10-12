# Vocabulary v3: course criteria, templates and dev gates

Course sources are the provided slide texts: 03 functional testing, 04 control flow, 05 data flow and 08 mutation testing. Templates describe observations of the existing tests; fuzz witnesses establish reach without establishing specification validity. All gate numbers use DEV only, exclude zero-fail task 66 and use the fixed even/odd folds. PF = fail_hits / total plus hits; matched base weights each task by scored facts. Strong means PF ≥ .5. Both folds must have PF > matched base AND per-task better > worse. Empty evidence fails.

Frozen display slots: OUTCOME, STMT, MUTANT, BOUND, NUM, DU. K=3, G′ on; K=5 reported in the scratch report. Extended mutants retain `extended=true` and a separate MUTANT-X counting slot; a passing aggregate gate merges their display slot into MUTANT.

| Kind | Course chapter / criterion | Tool source | Template | Concrete DEV example | Gate result |
|---|---|---|---|---|---|
| OUTCOME | 04: C2 branch / C3 sub-condition coverage | — | Branch coverage (C2): the False branch of `c` (line L) is never taken. Condition coverage (C3) names a sub-condition instead. | Task 2: Branch coverage (C2): the True branch of `number == 0` (line 13) is never taken by the existing tests. | core retained; overall PF/base 0.476/0.193; E PF/base 0.444/0.113, B/W 9/7; O PF/base 0.500/0.253, B/W 10/6 |
| STMT | 04: C1 statement coverage | — | Statement coverage (C1): lines L–M (`statement`) are never executed by the existing tests. | Task 2: Statement coverage (C1): line 14 (starting with `return 0`) is never executed by the existing tests. | core retained; overall PF/base 0.474/0.173; E PF/base 0.473/0.089, B/W 7/4; O PF/base 0.475/0.228, B/W 9/5 |
| MUTANT | 08: mutation, killed/surviving/equivalent mutants | [MutPy](https://github.com/mutpy/mutpy) / [PIT](https://pitest.org/quickstart/mutators/) operator-family analogues | Mutation (operator family): `before` -> `after` at line L survives: no existing test distinguishes them. | Task 2: Mutation (ROR): the mutant `number >= 0` -> `number > 0` at line 12 survives: no existing test distinguishes them. | core retained; overall PF/base 0.486/0.174; E PF/base 0.551/0.134, B/W 19/5; O PF/base 0.418/0.215, B/W 15/7 |
| BOUND | 03: boundary value analysis | — | Boundary value: at line L, `expression` was never equal to boundary value c (or c±1). | Task 2: Boundary value: at line 13, `number` was never equal to 0 (the constant in `number == 0`). | core retained; overall PF/base 0.367/0.174; E PF/base 0.375/0.105, B/W 11/9; O PF/base 0.359/0.234, B/W 10/6 |
| REL | 03: decision tables / dependent inputs | — | Decision table / dependent inputs: `k` was never greater than `len(xs)` (also equal/order/prefix/length). | Task 5: Decision table / dependent inputs: in the existing tests, the argument `delimeter` was never equal to `len(numbers)`. | FAIL; overall PF/base 0.266/0.155; E PF/base 0.275/0.130, B/W 7/3; O PF/base 0.258/0.174, B/W 4/9 |
| SHAPE | 03: input equivalence classes | — | Equivalence class: parameter `xs` never contained duplicates / was never sorted. | Task 3: Equivalence class: in the existing tests, parameter `operations` of `below_zero` was never sorted in ascending order. | FAIL; overall PF/base 0.207/0.200; E PF/base 0.156/0.172, B/W 19/26; O PF/base 0.298/0.249, B/W 17/16 |
| NUM | 03: input equivalence classes | — | Equivalence class: parameter `n` was never negative/zero/odd/non-integer. | Task 2: Equivalence class: in the existing tests, parameter `number` of `truncate_number` was never negative. | core retained; overall PF/base 0.334/0.166; E PF/base 0.285/0.088, B/W 4/2; O PF/base 0.378/0.236, B/W 8/2 |
| MUTANT-X | 08: extended mutation operators | [MutPy misc](https://github.com/mutpy/mutpy/blob/master/mutpy/operators/misc.py), [MutPy loop](https://github.com/mutpy/mutpy/blob/master/mutpy/operators/loop.py), [PIT](https://pitest.org/quickstart/mutators/) | Same Mutation template, naming SDL/call-result removal/SIR/BCR/ZIL/OIL/RIL. | Task 3: Mutation (ZIL): the mutant `for operation in operations` -> `skip the loop body` at line 21 survives: no existing test distinguishes them. | PASS; overall PF/base 0.418/0.183; E PF/base 0.532/0.162, B/W 10/3; O PF/base 0.296/0.205, B/W 4/3 |
| LOOP | 04: loop coverage (0/1/2; course also lists k/n−1/n/n+1) | — | Loop coverage: the loop at line L never iterates exactly 0/1/2 times in a single execution. | Task 3: Loop coverage: the loop at line 21 never iterates exactly 1 times in a single execution under the existing tests. | FAIL; overall PF/base 0.152/0.250; E PF/base 0.167/0.180, B/W 11/13; O PF/base 0.137/0.315, B/W 7/20 |
| LOOP-MAX | 04: loop coverage beyond observed maximum | — | Loop coverage: the loop at line L never iterates more than N times in a single execution. | Task 3: Loop coverage: the loop at line 21 never iterates more than 5 times in a single execution under the existing tests. | FAIL; overall PF/base 0.239/0.202; E PF/base 0.162/0.152, B/W 12/22; O PF/base 0.322/0.257, B/W 22/12 |
| OUTPUT | 03: OUTPUT-domain equivalence classes | — | Output equivalence class: the function never returns an empty list (or another named output class). | Task 2: Output equivalence class: the function never returns a float value in the class 'zero' in the existing tests. | FAIL; overall PF/base 0.285/0.282; E PF/base 0.279/0.270, B/W 14/12; O PF/base 0.291/0.294, B/W 10/18 |
| DU | 05: def, c-use, p-use, def-use pair, all-defs/all-uses | — | Def-use pair (all-uses, c-use/p-use): the value assigned to `x` at line D never reaches its use at line U. | Task 9: Def-use pair (all-uses, c-use): the value assigned to `max_so_far` at line 10 never reaches its use at line 15 in the existing tests. | PASS; overall PF/base 0.377/0.213; E PF/base 0.458/0.121, B/W 6/2; O PF/base 0.360/0.232, B/W 10/5 |
| DECISION | 03: decision tables; 04: branch outcomes | — | Decision table: no existing test makes `a` True and `b` False in the same call. | Task 2: Decision table: no existing test makes `number == 0` (line 13) False and `number == 1` (line 15) True in the same call. | FAIL; overall PF/base 0.314/0.217; E PF/base 0.386/0.240, B/W 2/5; O PF/base 0.286/0.208, B/W 5/2 |

v3c validity: fuzz evidence counts only after the task's EvalPlus v0.1.10 contract assertions pass in an isolated worker; base tests are taken as given, and the frozen v3f gates/templates/ranking remain unchanged.

## Mutation provenance and precise adaptations

The requested call-result removal is implemented as receiver/argument propagation. PIT’s NonVoidMethodCall operator replaces a call result with a Java default value; PIT’s naked-receiver/argument-propagation operators are the closer analogues for `x.lower() -> x` and `abs(x) -> x`. These Python transformations are type-checked from base-visible evidence.

| Family | Tool source / adaptation | Transformation | DEV example | Gate |
|---|---|---|---|---|
| ROR | MutPy ROR / PIT ROR, conditional boundaries | relational operator replacement | Task 2: Mutation (ROR): the mutant `number >= 0` -> `number > 0` at line 12 survives: no existing test distinguishes them. | core retained; overall PF/base 0.486/0.174; E PF/base 0.551/0.134, B/W 19/5; O PF/base 0.418/0.215, B/W 15/7 |
| AOR | MutPy AOR / PIT math/AOR | arithmetic operator replacement | Task 3: Mutation (AOR): the mutant `balance_sum -= operation` -> `balance_sum += operation` at line 24 survives: no existing test distinguishes them. | core retained; overall PF/base 0.486/0.174; E PF/base 0.551/0.134, B/W 19/5; O PF/base 0.418/0.215, B/W 15/7 |
| COR | MutPy logical-connector replacement; course COR | and ↔ or | Task 36: Mutation (COR): the mutant `n % 11 == 0 or n % 13 == 0` -> `n % 11 == 0 and n % 13 == 0` at line 13 survives: no existing test distinguishes them. | core retained; overall PF/base 0.486/0.174; E PF/base 0.551/0.134, B/W 19/5; O PF/base 0.418/0.215, B/W 15/7 |
| UOI/negation | MutPy logical operator deletion; course negation family | not expression → expression | Task 3 (covered placebo): Mutation (UOI/negation): the mutant `not operations` -> `operations` at line 13 is killed: an existing test distinguishes them. | core retained; overall PF/base 0.486/0.174; E PF/base 0.551/0.134, B/W 19/5; O PF/base 0.418/0.215, B/W 15/7 |
| CRP constant | MutPy CRP / PIT inline constants; ±1 adaptation | integer constant c → c±1 | Task 2: Mutation (CRP constant): the mutant `number >= 0` -> `number >= 1` at line 12 survives: no existing test distinguishes them. | core retained; overall PF/base 0.486/0.174; E PF/base 0.551/0.134, B/W 19/5; O PF/base 0.418/0.215, B/W 15/7 |
| SDL | MutPy SDL Expr; augmented-assignment deletion extends SDL; PIT void-call removal analogue | expression statement or augmented assignment → pass | Task 3: Mutation (SDL): the mutant `balance_sum -= operation` -> `pass` at line 24 survives: no existing test distinguishes them. | PASS; overall PF/base 0.418/0.183; E PF/base 0.532/0.162, B/W 10/3; O PF/base 0.296/0.205, B/W 4/3 |
| call-result removal | PIT naked receiver / argument propagation; NonVoidMethodCall-inspired adaptation | lower/upper/strip/lstrip/rstrip/title/capitalize/swapcase → receiver; sorted/reversed/abs/round/int → argument | Task 12: Mutation (call-result removal): the mutant `s.lower()` -> `s` at line 16 survives: no existing test distinguishes them. | PASS; overall PF/base 0.418/0.183; E PF/base 0.532/0.162, B/W 10/3; O PF/base 0.296/0.205, B/W 4/3 |
| SIR | MutPy SliceIndexRemove | drop lower/upper/step separately | Task 10: Mutation (SIR): the mutant `string[1:-1]` -> `string[:-1]` at line 25 survives: no existing test distinguishes them. | PASS; overall PF/base 0.418/0.183; E PF/base 0.532/0.162, B/W 10/3; O PF/base 0.296/0.205, B/W 4/3 |
| BCR | MutPy BreakContinueReplacement | break ↔ continue | Task 3: Mutation (BCR): the mutant `continue` -> `break` at line 23 survives: no existing test distinguishes them. | PASS; overall PF/base 0.418/0.183; E PF/base 0.532/0.162, B/W 10/3; O PF/base 0.296/0.205, B/W 4/3 |
| ZIL | MutPy ZeroIterationLoop | loop body → break, body work executes zero times | Task 3: Mutation (ZIL): the mutant `for operation in operations` -> `skip the loop body` at line 21 survives: no existing test distinguishes them. | PASS; overall PF/base 0.418/0.183; E PF/base 0.532/0.162, B/W 10/3; O PF/base 0.296/0.205, B/W 4/3 |
| OIL | MutPy OneIterationLoop; bounded-iteration adaptation handles continue | at most the first iteration | Task 3: Mutation (OIL): the mutant `for operation in operations` -> `execute at most its first iteration` at line 21 survives: no existing test distinguishes them. | PASS; overall PF/base 0.418/0.183; E PF/base 0.532/0.162, B/W 10/3; O PF/base 0.296/0.205, B/W 4/3 |
| RIL | MutPy ReverseIterationLoop; runtime restriction to reversible sequence types | reverse list/tuple/str/range iteration | Task 20: Mutation (RIL): the mutant `for i in range(1, len(closest_numbers))` -> `iterate in reverse order` at line 19 survives: no existing test distinguishes them. | PASS; overall PF/base 0.418/0.183; E PF/base 0.532/0.162, B/W 10/3; O PF/base 0.296/0.205, B/W 4/3 |

Operator sources: [PIT mutator documentation](https://pitest.org/quickstart/mutators/), [MutPy operator implementation](https://github.com/mutpy/mutpy/tree/master/mutpy/operators). No external tool is executed; only the requested bounded Python operator adaptations are used.

The legacy sample keeps up to 80 points and the extended sample adds up to 80. Fuzz-equivalent survivors are filtered. OIL can execute zero times when its original condition/iterable is empty; it executes at most once. RIL keeps unsupported iterables unchanged, then the same equivalence filter applies. DU is limited to 64 dynamic missing local pairs, including entry parameters; comprehension-local variables are omitted. DECISION tests at most 32 non-nested pairs per task; co-occurrence is within one call, including different loop iterations. Loop counts recorded on interrupted executions support LOOP-MAX resource facts.

Placebo facts use the same criteria for covered behaviour (taken branches, executed statements, observed classes/counts/pairs and killed mutants). The shared FACTS header lists course terms for both concept and placebo. The human kit contains 30 seeded, kind-stratified K=3 shown facts from DEV only. Pilot `doc_fail` tasks 108, 116 and 131 will be reported separately in the future pilot analysis. No pilot confirmation or prompt regeneration occurred.

## v4 tool provenance (frozen old vocabulary above remains historical)

Hypothesis 6.169.0 supplies the LLM-written input-domain draws, shared across facts,
toolinput and hybrids, mechanically filtered by B5 mined preconditions. coverage.py 7.16.2
supplies C1 function-body statement lines and C2 line arcs (including loop exits); it can
report a loop exit that the old if/while tracer did not. The tracer supplies only criteria
without a standard replacement here: C3 atomic subconditions, boundaries, input/output
equivalence classes, relations, DU pairs, loop counts/maxima and decision pairs. Ranking,
gates, templates and seeded placebo construction remain v3. No home-made mutant enters v4.

mutmut 3.8.0 + libcst 1.9.0 uses create_mutations(filename, source) from
mutmut.mutation.file_mutation; module.deep_replace(original_node, mutated_node).code
materializes each single-point mutant, preserving all other source. Function-contained
mutations are used; module-only mutations are excluded. The existing 80 core/80 extended
sampling caps and fuzz-equivalence filtering remain.

| mutmut operator | Course family / displayed name |
|---|---|
| operator_swap_op (comparison, including conditional boundaries) | ROR |
| operator_swap_op (binary/augmented arithmetic and bitwise) | AOR |
| operator_swap_op (and/or) | COR |
| operator_swap_op (unary +/-), operator_remove_unary_ops (not/~ deletion) | UOI/negation |
| operator_keywords (is/is not/in/not in) | ROR |
| operator_keywords (continue -> break; break -> return) | BCR (partial analogue; no break -> continue) |
| operator_number (constant +1), operator_string (XX/case), operator_name (True/False) | CRP constant |
| operator_name (deepcopy -> copy) | name replacement (extended) |
| operator_augmented_assignment (+= -> =) | AOR |
| operator_assignment (RHS -> None or empty string) | assignment replacement (extended) |
| operator_lambda (body -> None/0) | lambda-result replacement (extended) |
| operator_dict_arguments (keyword rename) | dictionary-key replacement (extended) |
| operator_arg_removal (argument -> None / delete one of multiple arguments) | argument replacement/removal (extended) |
| operator_symmetric_string_methods_swap, operator_unsymmetrical_string_methods_swap | string-method replacement (extended) |
| operator_match (delete a case) | case deletion (extended) |
| operator_if_exp (force ternary condition) | COR |

Lost old families: SDL statement deletion, call-result receiver/argument propagation,
SIR slice-index removal, ZIL/OIL/RIL loop transformations have no corresponding mutmut
operator here. Full BCR break/continue swapping is lost; only continue->break survives,
and break->return is an additional partial control-flow mutation. Assignment/argument
replacement is not relabelled SDL or call-result removal. Numeric CRP is +1 rather than
both +/-1. mutmut generates c ** 2 -> c * 2 as operator_swap_op/AOR; this is checked on 157.
