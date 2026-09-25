# Concepts aligned with TestEval's LeetCode tasks

Sources: [TestEval paper](https://aclanthology.org/2025.findings-naacl.197.pdf)
and [official artifact](https://github.com/LLM4SoftwareTesting/TestEval).

## What the benchmark measures

TestEval selected LeetCode Python solutions with cyclomatic complexity at
least 10. The paper reports 210 programs (9 easy, 100 medium, 101 hard). It
defines target branches as `if`/`elif`/`else` branches and target lines as
statements inside those branches. The released `leetcode-py.jsonl` at upstream
commit `6f67dee71de6ccda1767b8c219a93f4ae0a7ce90` contains 1,340 target
lines; the paper text says 1,312, so cite the exact artifact/version used for
an experiment. The first 100 released records have 639 target lines: 3 easy,
55 medium, and 42 hard.

The paper already evaluates a two-step reasoning prompt that first asks for
conditions needed to execute a target line and then asks for a test satisfying
those conditions. A new concept method must therefore do more than restate a
guard. It should connect the guard to a valid, concrete input and account for
state changes before the guard is reached.

## Findings from the first 100 records

AST inspection of their 639 target lines found 495 inside at least one loop,
236 inside nested loops, 163 beneath at least two `if` guards, and 207 beneath
a Boolean guard. These categories overlap. The important unit is the *target's
required execution state*, not the broad algorithm label such as `graph`,
`dynamic programming`, or `hash map`.

Mapping each target line to its narrowest released `blocks` interval gives
335 easy, 136 medium, and 168 hard target lines in the first 100 records.
In the current paper-prompt run, baseline versus concept coverage was
314→318 on easy, 118→119 on medium, and 150→155 on hard lines. This is
exploratory: the hard stratum contributes five of the ten net additional
targets, but the subset is small and no stratum shows a proved effect.

The existing annotator often repeats conditions as both `branch_true` and
`input_relation`, and gives loop presence without the iteration or state at
which the target is reachable. It also misses earlier sibling guards whose
`return`/`continue`/`break` would prevent reaching the target. In `3Sum`, the
duplicate-skip `continue` at line 22 must be avoided before line 33 is
reachable, but that guard is not an ancestor of line 33 in the AST. Its
generic `index_in_bounds` fact can also be misleading for dictionary access or
assignment: a dictionary key need not already exist for `d[key] = value` to
execute.

## Recommended target concept

Represent each target with these fields, only when supported by source facts:

1. `guard_chain`: ordered outer-to-inner predicates with required truth values,
   including earlier guards that must be bypassed because they exit the path.
2. `state_at_guard`: values/relations *after* relevant assignments, updates,
   sorting, queue operations, or previous loop iterations.
3. `input_witness`: a minimal valid input shape and concrete values that make
   the state and guards hold together; verify it by executing the original
   program under line tracing before claiming the witness is valid.
4. `validity_constraints`: input conditions from the LeetCode description,
   such as sortedness, length, uniqueness, and value bounds.
5. `uncertainty`: if static analysis cannot establish a relation, omit or mark
   it unknown rather than inserting a generic or false requirement.

For `3Sum` target line 33 (`l += 1` inside the duplicate-skipping loop), the
concept is: the sorted array has a zero-sum triplet; after that triplet is
recorded, incrementing `l` leaves the new `nums[l]` equal to `nums[l-1]` while
`l < r`. The concrete input `[-2, 0, 0, 0, 2]` was verified to cover line 33;
`[-1, 0, 1, 2, -1, -4]` did not. This distinction captures the missing
cross-step state rather than merely naming `while` or `equality`.

For graph/BFS/union-find and DP tasks, the analogous witness must describe a
reachable intermediate graph state, queue item, component merge, or table
value. Such state usually cannot be derived from a local `if` alone. A safe
first implementation should use trace-verified candidates and keep only facts
that help explain why the target was reached.

## Evaluation rule

Keep the official TestEval prompt, one-test budget, formatter, and evaluator
identical in both arms. Append only the target concept in the concept arm.
Measure official targeted-line coverage plus the number of concepts with a
verified input witness. Compare against the official basic prompt and, if the
claim is about better reasoning, the paper's two-step reasoning baseline.

## Implemented follow-up (2026-09-24)

`concept_annotator_py.v4` now adds guards that bypass earlier guaranteed
`return`/`continue`/`break`/`raise`, tracks simple updates immediately before
a target loop, and detects the prior-iteration map-population pattern when a
map starts empty. It only states index bounds for statically recognizable
sequences. The improved fact set is heuristic; it does not solve arbitrary
path constraints or prove a concrete input witness.

`testeval_py.paper_runner --protocol two-step` reproduces the two official
CoT prompt templates and keeps conditions in the output. The baseline uses
those prompts unchanged. The concept arm appends selected v4 facts to both
steps. These new runs must use fresh predictions and caches; the basic-prompt
results above measure the earlier annotator and cannot establish the v4 effect.

An initial 10-task, 71-target pilot with Gemini 3 Flash and the official
`eval_linecov.py` scored 70/71 for CoT baseline and 69/71 for CoT + v4 concept.
The concept arm missed `3Sum` line 35: its generated conditions correctly
described duplicate values after decrementing the right pointer, but its
generated concrete input did not reach that loop. This pilot is a pipeline
check, not evidence of an improvement; the larger run must be reported
separately once complete.

The subsequent `concept-witness` arm adds an isolated, time-bounded local input
search. It records a candidate only after the original solution returns
normally and tracing confirms the requested line. On `3Sum` line 35 the search
found `[-2, 0, 1, 2, 2]`; a native Vertex two-step call using this witness
generated a test that the official TestEval evaluator marked as covering the
line (1/1). The expanded, description-filtered small-domain search found
witnesses for 395 of 639 targets across 80 of the first 100 tasks. This is
execute-verified reachability, not a guarantee that every generated candidate
obeys all constraints omitted from the benchmark's natural-language record.

On the first 10 tasks, the prompt-only witness arm covered 69/71 targets:
the model changed the verified `3Sum` line-33 input and missed that line.
A separately labelled execution-check/fallback arm replaced that one test
with the verified call and covered 70/71, tying the paper CoT baseline.
The fallback is an algorithmic input substitution, not evidence that the LLM
itself generated a better test, and the substituted test contains no assertion.
