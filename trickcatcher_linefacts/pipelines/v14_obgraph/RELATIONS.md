# v12_rel offline relation coverage

Source: `trickcatcher_linefacts/out/tasks_v7hyb_v4.json`; SHA256 `f0d5d3baa0cbdd07eab667888eceefcc5ec3c77d348b1127514c80282e74f7b0`.
Frozen v7 selections, in their original order; includes 113 dev and 20 pilot tasks. No ranking, fuzz mining, or LLM calls.

| Item | Count |
| --- | ---: |
| tasks | 133 |
| hints | 254 |
| data | 144 |
| control | 67 |
| spec | 142 |
| all_three | 31 |
| any_edge | 206 |
| parameter_anchors | 66 |
| base_failures | 0 |
| base_trace_timeouts | 12 |
| witness_trace_timeouts | 17 |

Counts above are hints with at least one edge of that type. Individual edge counts: {"control": 166, "data": 220, "spec": 142}.

## Method and limits

AST enclosing if/while/for guards; branch outcomes come only from base tracer cells. `always` / `never` describe evaluations of that guard, not every base test. A guard absent from all base executions is labelled `not evaluated`; a truncated base trace makes the outcome unknown.

Def-use edges are observed by the unchanged tracer while replaying base inputs and the selected fuzz witnesses. There is no speculative static reaching-definition fallback. Loop-carried and same-line def-use edges are retained. Comprehensions/lambdas have limited def-use instrumentation; mutation of an object is not a new variable definition. Only syntactically enclosing guards are included, not a full postdominator control-dependence graph; loop else exhaustion without break has no tracer probe and is omitted.

SPEC hints without a line are anchored at the relevant parameter definition, with no invented data/control edge. Docstring prose before the first doctest is split into sentences; maximum identifier/operator word overlap wins, ties choose the first sentence, zero overlap gives no spec edge. This is lexical evidence, not proof of a specification obligation.

Witness values are replayed internally and are absent from chains and this report. The JSON companion contains per-task, per-hint relations and provenance.

## Examples

HumanEval/0, selected hint 1:

spec clause R1 [spec-link, lexical]: Check if in given list of numbers, are any two numbers closer to each other than given threshold. -> condition line 12 [control]: `for i in range(len(numbers))`; T branch always taken by base tests (among evaluations) -> condition line 13 [control]: `for j in range(i + 1, len(numbers))`; T branch sometimes taken by base tests (among evaluations) -> line 14 (line) <- value `i` from line 12 [data, p-use, observed] <- value `j` from line 13 [data, p-use, observed] <- value `numbers` from line 4 [data, p-use, observed] <- value `threshold` from line 4 [data, p-use, observed]

HumanEval/5, selected hint 1:

spec clause R1 [spec-link, lexical]: Insert a number 'delimeter' between every two consecutive elements of input list `numbers' -> condition line 16 [control]: `for i in range(len(numbers) - 1)`; T branch always taken by base tests (among evaluations) -> line 19 (line) <- value `i` from line 16 [data, p-use, observed] <- value `numbers` from line 4 [data, p-use, observed]

HumanEval/5, selected hint 3:

spec clause R1 [spec-link, lexical]: Insert a number 'delimeter' between every two consecutive elements of input list `numbers' -> condition line 16 [control]: `for i in range(len(numbers) - 1)`; T branch always taken by base tests (among evaluations) -> line 17 (line) <- value `i` from line 16 [data, p-use, observed] <- value `numbers` from line 4 [data, p-use, observed]

HumanEval/9, selected hint 2:

condition line 12 [control]: `for (i, n) in enumerate(numbers)`; T branch sometimes taken by base tests (among evaluations) -> line 15 (line) <- value `max_so_far` from line 10 [data, c-use, observed] <- value `max_so_far` from line 14 [data, c-use, observed] <- value `result` from line 11 [data, c-use, observed]

