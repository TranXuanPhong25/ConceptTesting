# v16 behavior foundation — CPU result

CPU foundation gate on fixed 20 design dev tasks; no efficacy result

Representation gate: **17/20**, threshold 16/20: passed. All 20 remain in denominator.
29 tests pass; frozen strategy/common-domain adapter: 10/10 draws accepted. No model calls.
Opaque: task 63 (recursive calls), 76 (recursion and float division), 144 (`eval`).

| Task | Usable | Completed replays | Replay mismatch | FSM states | Mutants | Distinguished |
|---|---|---:|---:|---:|---:|---:|
| 27 | True | 3/3 | 0 | 19 | 4 | 4 |
| 31 | True | 7/8 | 0 | 10 | 6 | 6 |
| 51 | True | 7/7 | 0 | 9 | 1 | 1 |
| 56 | True | 8/8 | 0 | 32 | 12 | 11 |
| 57 | True | 8/8 | 0 | 17 | 12 | 8 |
| 59 | True | 5/5 | 0 | 28 | 12 | 12 |
| 63 | False | 7/7 | 0 | 12 | 9 | 9 |
| 76 | False | 8/8 | 0 | 16 | 9 | 8 |
| 78 | True | 7/7 | 0 | 4 | 0 | 0 |
| 85 | True | 4/4 | 0 | 16 | 4 | 4 |
| 91 | True | 6/6 | 0 | 26 | 3 | 3 |
| 94 | True | 8/8 | 0 | 48 | 5 | 5 |
| 98 | True | 7/7 | 0 | 37 | 2 | 2 |
| 110 | True | 7/7 | 0 | 35 | 9 | 8 |
| 118 | True | 8/8 | 0 | 10 | 5 | 4 |
| 126 | True | 8/8 | 0 | 19 | 12 | 6 |
| 136 | True | 8/8 | 0 | 53 | 12 | 11 |
| 144 | False | 8/8 | 0 | 2 | 1 | 1 |
| 149 | True | 7/7 | 0 | 7 | 1 | 1 |
| 152 | True | 4/4 | 0 | 9 | 0 | 0 |

Totals: {"replays": 136, "completed": 135, "matching": 135, "unresolved": 1, "mismatches": 0, "states": 409, "transitions": 442, "mutants": 119, "distinguished": 104, "nonbase_discriminators": 55, "omitted_events": 93662}.

Task 152: replay return reads result version 7 after six appends. The original input is deep-copied; object identities preserve aliases within each replay. This repairs the old display gap, not the subtraction bug.
Mutation witnesses are original-vs-alternative disagreements, not actual bug detections. Counts include base-distinguished cases and opaque tasks; JSON reports non-base witnesses separately. The first 12 mutants are source-ordered, so later operations can be omitted (notably task 136 MIN blocks). Tasks 78/152 have no eligible mutant under the current operator grammar.

Limits: source IR is structured Python, not SSA or complete symbolic execution. Finite machine is an observed predicate projection; merging does not establish path feasibility. First/last 64 trace events are retained after projection, with omission counts. Version history is change-based; a no-op write may not increment a version. Unknown/timeout is unresolved. Absence of observed mismatch is not a proof of model equivalence or program correctness.

Implemented first-order mutation operators: skip then, unguard then, delete conjunct, flip strict/non-strict/equality comparison, remove list-comprehension filters. MOVE CHECK, full spec-model mutation, solver refinement and MCTS remain extensions. Current alternatives are explicitly implementation-origin; semantic requirements come from the separate proposed spec-only DSL extraction.

Runner supports two-call concept proposal and conditional seven-arm strategy generation/shared-ref scoring. These model stages have not run: the supplied endpoint returned HTTP 404. No concept-gate coverage or D_IO result exists. Do not promote a method from this CPU gate.

Original `v16_behavior` prepare aborted because task 94 output exceeded the inherited 8 MiB IPC cap. Its sources/results are preserved. Compact copy changes retained trace storage after projection, with unchanged execution/selection/gate budgets.

Reproduce: `python3 -B -m trickcatcher_linefacts.pipelines.v16_behavior_ready.behavior_experiment prepare --workers 2`.
Online continuation, with a live user Qwen environment: `python3 -B -m trickcatcher_linefacts.pipelines.v16_behavior_ready.behavior_experiment all --online --workers 2`. Source/config/task hashes must remain unchanged; gates stop generation automatically.

Final ready copy additionally hardens schema-container/ID rejections, before any model outputs. Original compact CPU report remains preserved. Fresh ready totals: {"replays": 136, "completed": 135, "matching": 135, "unresolved": 1, "mismatches": 0, "states": 409, "transitions": 442, "mutants": 119, "distinguished": 104, "nonbase_discriminators": 55, "omitted_events": 93662}.
