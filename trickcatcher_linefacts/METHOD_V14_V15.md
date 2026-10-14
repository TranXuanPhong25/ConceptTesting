# What v14/v15 actually extract

Implementation audit, 2026-10-14. Documentation only; frozen experiment code is unchanged.
References below point to the repaired copies, whose extraction logic is identical to their parents.

## Docstring segments, then candidate obligations

`relations.clauses(fn)` obtains the target function's docstring through Python AST, keeps only
the text before the first `>>>`, collapses whitespace, and splits at `.`, `!`, or `?` followed
by whitespace. `experiment_schema.graph` assigns consecutive IDs R1, R2, etc.
The output is an ID-to-text dictionary. There is no LLM or semantic parser in segmentation.
It neither separates multiple requirements in a sentence nor filters narrative sentences.
Examples without `>>>` remain. Sentence IDs anchor candidate model interpretations; the
segmentation does not itself identify preconditions, postconditions or atomic obligations.

Real task 152 (`compare`) has seven segments. R1/R2 are narrative, R4 describes equal-length
inputs, R5 describes output length, R6 describes zero/absolute-difference values, and R7
contains examples. These are exactly the prepared artifacts, not a hand-cleaned spec.

## Observed data edges

The tool executes original base tests to capture calls and replays those calls plus the
selected frozen fact witnesses on instrumented PUT code. Instrumentation records local
parameter/assignment definitions and reads, keyed by function scope and execution frame.
Each read records its last definition line, use line, variable name and c-use/p-use kind.
Evidence is unioned across recorded runs. Missing edges mean no retained evidence.

For task 152, original source lines are:

```text
L2:  def compare(game,guess):
L17:     result = []
L18:     for i in range(len(game)):
L19:         result.append(game[i] - guess[i])
L20:     return result
```

Actual edges include DATA L2→L19 for game/guess, L18→L19 for i, L17→L19 for
result, and L17→L20 for result. The implementation tracks variable bindings; it does
not update result's definition after `append`, track list elements/aliases, or provide
a complete interprocedural dependence analysis. There is no L19→L20 edge in this graph.
Consequently it cannot represent the full arithmetic-to-return propagation for this
example under the connected-path-to-return validator. This is an extraction limitation.

## Enclosing-guard control edges

For each candidate statement, the tool walks AST ancestors up to the enclosing function.
If/while/for/async-for ancestors provide guard-line→statement edges and required branch
outcomes: T for body, F for if-else. Loop-else is omitted because exhaustion without break
is not represented by the available probes. Base traces annotate branch observation in
candidate metadata. This is lexical/structural approximation, not CFG/postdominator
control dependence. Early returns and exception-mediated control are not fully modelled.

Task 152 has CONTROL L18→L19 with condition `for i in range(len(game))`, outcome T.
Task 31 has CONTROL L23→L24 with condition `n % i == 0`, outcome T, leading to
`return False`. These are actual prepared edges.

## Concepts and model links

Graph nodes contain source line, code and base-coverage flag. Concepts attach deterministic
AST labels and applicable frozen LineFacts kinds to a node. Task 152 includes INDEX and
ARITHMETIC at L19 and RETURN at L20. These labels identify syntax/evidence anchors; they
do not establish that subtraction should have been absolute difference.

The model chooses an exact clause ID, concept IDs, a typed path, a trigger T, obligation O,
and an alternative hypothesis. The parser validates ID existence, concept attachment and
path connectivity (1–6 distinct edges, ending at RETURN), plus Python predicate restrictions.
The spec→concept interpretation and R→O entailment remain model hypotheses. Exact clause
IDs and executable anchors do not prove that interpretation semantically correct.

For MR proposals, the same sentence IDs anchor D/tau/rho candidates; graph paths are not
required. Base consistency rejects finite contradictions only. Canonical/contract checks
enter a separate scoring stage after generation is frozen.

## Execution evidence limits

For a selected input, T must hold; the tool retraces the PUT and checks every selected edge.
DATA requires its exact def-use record; CONTROL requires the selected guard outcome and
execution of the destination line. All checks concern the same trace, but aggregated cells
do not prove a temporally ordered causal chain or one particular loop iteration's propagation.
An observed path or a false obligation on buggy PUT alone does not establish a true bug.

Source pointers: [clause splitting](pipelines/v14_obgraph_py/relations.py),
[graph/schema validation](pipelines/v14_obgraph_py/experiment_schema.py),
[candidate evidence](pipelines/v14_obgraph_py/hyp_worker.py),
[def-use instrumentation](pipelines/v14_obgraph_py/tracer.py),
[execution/property checks](pipelines/v14_obgraph_py/experiment_worker.py).
