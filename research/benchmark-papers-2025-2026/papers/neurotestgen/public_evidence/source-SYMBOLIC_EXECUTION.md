# Symbolic Execution Methodology

## Purpose

Panta uses symbolic execution to improve CFG-guided test generation. Instead of asking the LLM to infer every input value from a raw execution path, Panta first tries to solve the path constraints automatically and appends a concrete input hint to the test-generation prompt.

The implementation is in `src/panta/core/symbolic_executor.py`. It supports two solving modes:

1. **Z3-based symbolic execution**, used for numerical and boolean path constraints that can be represented as SMT formulas.
2. **LLM-based path solving**, used when the path contains non-numerical program behavior that the lightweight Z3 translator cannot model reliably, such as method calls, object fields, arrays, strings, enum constants, or bare boolean predicates.

The output of both modes has the same purpose: add a prompt hint such as:

```text
Please use the input: n=3.
```

or, for LLM solving:

```text
Please use the input: text = "Apple", mode = Mode.STRICT
```

This makes the downstream test-generation LLM more likely to create a test that actually covers the selected CFG path.

## Configuration

Symbolic execution is configured through Panta settings and is passed into `PromptBuilder`.

```ini
enable_symbolic_execution = true
enable_LLM_path_solving = true
enable_LLM_verify = true
llm_verify_max_rejections = 3
```

The behavior is:

- `enable_symbolic_execution = true`: instantiate `SymbolicExecutor`; if this is false, no path solving is attempted.
- `enable_LLM_path_solving = true`: allow paths with non-numerical conditions to be sent to the LLM solver.
- `enable_LLM_verify = true`: ask a second LLM pass to verify the candidate input before accepting it.
- `llm_verify_max_rejections = 3`: retry LLM path solving up to this many verifier rejections.

Z3 is optional at import time. If `z3-solver` is not installed, the executor logs a warning and the Z3 path returns no solution.

```bash
pip install z3-solver
```

## Where Symbolic Execution Fits in Panta

The symbolic executor is used by `PromptBuilder`, after CFG paths have been extracted.

The high-level workflow is:

1. Build a control-flow graph for the source file.
2. Extract methods under test and their candidate execution paths.
3. Select one or two useful paths using missed-line, missed-branch, and path-history heuristics.
4. Split a selected path at return statements when necessary.
5. Run symbolic execution on each selected path segment.
6. If the path is feasible, append the solved input to the path description.
7. If Z3 proves the path unsatisfiable, skip that path and select another candidate.
8. If solving times out, keep the path but add a fallback instruction asking the LLM to reason about an appropriate input.
9. Render the CFG-guided test-generation prompt with the selected path and any solved input.

The key integration method is:

```python
enhance_path_with_symbolic_execution(...)
```

It returns:

```python
(solution_dict_or_none, formatted_prompt_string)
```

For Z3, the solution dictionary maps method parameters to concrete Python values. For LLM solving, the dictionary is a sentinel:

```python
{"llm_result": "<raw LLM answer>"}
```

The sentinel tells `PromptBuilder` that the path has a usable input hint even though the input was not produced by Z3.

## Path Representation

The symbolic executor receives a CFG path as `path_nodes`, a list of tuples:

```python
path_nodes = [
    ([75], "if(n < 0)", False),
    ([78], "if(n == 2)", False),
    ([81], "n = n | 1", None),
    ([82], "if(n == 1)", False),
    ([92], "final int rem = n % 3", None),
    ([93], "if(0 == rem)", True),
]
```

Each tuple contains:

- `line_numbers`: source line numbers associated with the CFG node.
- `statement`: the original statement text from the CFG.
- `conditional`: `True` if the branch condition must be true, `False` if it must be false, and `None` for non-branch statements such as assignments.

Panta also passes `method_params` when available. These are parsed from the method signature and include parameter names and types, for example:

```python
method_params = [
    {"name": "n", "type": "int"}
]
```

When method parameters are available, they are the authoritative input variables. When they are not available, the executor uses a fallback heuristic: variables used before assignment are treated as inputs.

## Main Routing Decision

The public entry point is:

```python
enhance_path_with_symbolic_execution(
    path_nodes,
    path_conditions_str="",
    method_name="",
    method_signature="",
    method_params=None,
    source_file_numbered="",
    source_file_name="",
    force_llm=False,
)
```

The routing logic is:

```python
if enable_llm_path_solving and llm_invoker and (force_llm or _path_needs_llm(path_nodes)):
    use LLM path solving
else:
    use Z3 path solving
```

`_path_needs_llm` returns true when any conditional node contains features that the local symbolic translator cannot model meaningfully:

- Method calls, for example `isPrime(n)` or `s.trim().isEmpty()`.
- `instanceof`.
- Null comparisons.
- Dot access, for example `this.value`, `obj.field`, `array.length`, or `Enum.CONSTANT`.
- Array indexing, for example `src[srcPos]`.
- String or character literals.
- Boolean literals.
- Ternary expressions.
- Bare boolean variables, for example `if(flag)` or `if(!enabled)`.
- ALL_CAPS identifiers that look like external constants and are not assigned in the path.

If LLM path solving is disabled, the executor still attempts the Z3 workflow. In that mode, method calls in conditions become unconstrained boolean placeholders, and unsupported expressions may be ignored if they cannot be parsed.

## Z3 Workflow

### 1. Start a Solving Session

`PromptBuilder` calls:

```python
self.symbolic_executor.start_solve_session()
```

This starts a session-level timeout. The default timeout in `SymbolicExecutor` is 300 seconds. Each Z3 solver receives the remaining session time as its timeout. If the budget is exhausted, the executor stops solving additional paths.

### 2. Identify Input Variables

When `method_params` are provided, the executor simply uses their names:

```python
input_vars = {"n"}
```

When `method_params` are missing, it scans the path:

- Variables used in conditions or assignment RHS expressions are recorded as `used_vars`.
- Variables assigned before being used are recorded as `assigned_vars`.
- Loop variables are recorded separately and excluded.
- Input variables are computed as:

```python
input_vars = used_vars - assigned_vars - loop_vars
```

The executor filters out keywords, class names, and method names. This avoids treating words such as `if`, `true`, `Math`, or `isPrime` as method inputs.

### 3. Create Typed Z3 Symbols

For every input variable, the executor creates a typed Z3 symbol using the method parameter type when available.

Java type mapping:

| Java type | Z3 representation |
| --- | --- |
| `byte` | `BitVec(name, 8)` |
| `short` | `BitVec(name, 16)` |
| `int` | `BitVec(name, 32)` |
| `long` | `BitVec(name, 64)` |
| `char` | `BitVec(name, 16)` |
| `float`, `double` | `Real(name)` |
| `boolean` | `Bool(name)` |
| reference or unknown type | `BitVec(name, 32)` |

The executor stores two maps:

```python
env = {}
input_symbols = {}
```

`env` tracks the current symbolic value of each variable as assignments are processed. `input_symbols` preserves the original method-input symbol, so the final model reports the original input value even if the variable is reassigned inside the path.

This distinction is important. If the path contains:

```java
n = n | 1;
```

then `env["n"]` becomes `original_n | 1`, but `input_symbols["n"]` remains `original_n`.

### 4. Process Path Nodes in Order

The executor iterates through `path_nodes`.

For loop statements, it skips the loop body modeling:

```python
if self._is_loop_statement(statement):
    continue
```

For conditional nodes, it extracts and parses the condition:

```python
constraint = _parse_conditional_statement(statement, env, conditional, ...)
solver.add(constraint)
```

For non-conditional nodes, it attempts to process assignments:

```python
_process_assignment(statement, env, var_types)
```

### 5. Parse Conditional Statements

The executor extracts the expression inside `if (...)` or `while (...)` using parenthesis matching, so nested parentheses are handled correctly.

Examples:

```text
if(n < 0)              -> n < 0
if(0 == (n % p))       -> 0 == (n % p)
if((a > 0 && b < 10))  -> (a > 0 && b < 10)
```

It supports:

- Logical OR: `||`
- Logical AND: `&&`
- Unary negation: `!`
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Null comparisons in the local Z3 path, represented as reference value `0`
- Parentheses-aware splitting, so operators inside nested parentheses are not split too early

If a branch condition is marked `False`, the parsed constraint is negated:

```python
if (n < 0) is False  ->  Not(n < 0)
```

If a condition contains a method call and the Z3 path is being used, the executor creates an unconstrained boolean placeholder:

```python
if (isPrime(n)) is True  ->  method_call_0
if (isPrime(n)) is False ->  Not(method_call_0)
```

This allows the path to remain solvable numerically, but it does not model the actual method body.

### 6. Parse Assignments and Update the Symbolic Environment

Assignments update `env`, not the original input symbol.

Supported assignment forms include:

```java
x = 5
int rem = n % 3
final long k = n + 1
n += 2
n -= 1
n *= 3
n /= 2
n %= 4
n |= 1
n &= mask
n ^= flag
n <<= 1
n >>= 1
n >>>= 1
boolean ok = n > 0
```

Compound assignments are normalized. For example:

```java
n += 2
```

is treated as:

```java
n = n + 2
```

If the RHS contains a method call or object creation, the executor skips precise modeling. If the assigned variable is not already in `env`, it creates a fresh symbolic variable for it.

Boolean assignments are parsed with the condition parser:

```java
isPositive = n > 0
```

Arithmetic and bitwise assignments are parsed with the expression parser.

### 7. Parse Expressions

The expression parser handles:

- Numeric literals, including Java long suffixes such as `10L`.
- Floating-point literals, represented as Z3 real values.
- `null` and `None`, represented as `0`.
- `true` and `false`, represented as `1` and `0` when parsed as expressions.
- Numeric casts, for example `(byte) value` or `(double) x`.
- Unary `~`, unary `+`, and unary `-`.
- Bitwise OR, XOR, and AND: `|`, `^`, `&`.
- Java shifts: `>>>`, `>>`, `<<`.
- Arithmetic: `+`, `-`, `*`, `/`, `%`.

The parser splits operators from low precedence to high precedence and respects parentheses. It also coerces compatible numeric types:

- Bit-vectors of different widths are sign-extended or truncated as needed.
- Bit-vectors can be converted to reals when paired with real expressions.
- Shift operands are coerced to the width of the shifted value.

### 8. Solve and Extract Concrete Inputs

After all path nodes are processed, the executor calls:

```python
solver.check()
```

The result is handled as follows:

- `sat`: extract concrete values from the Z3 model.
- `unsat`: return `None`; `PromptBuilder` treats the selected path as infeasible and tries another candidate.
- `unknown`: usually caused by timeout; return `None`, but `PromptBuilder` can keep the path with a fallback instruction if the session has timed out.

Only original method input symbols are reported. Local variables are not included because they are derived from inputs.

Model values are converted to Python-friendly values:

- Z3 booleans become `True` or `False`.
- Bit-vectors become signed integers.
- Reals become integers, floats, or strings depending on the model value.

The final formatter returns:

```text
Please use the input: param1=value1, param2=value2.
```

## Example 1: Z3 Solving Without LLM

Consider this Java method:

```java
public static int adjust(int n) {
    if (n < 0) {
        return -1;
    }
    if (n == 2) {
        return 2;
    }
    n = n | 1;
    if (n == 1) {
        return 2;
    }
    final int rem = n % 3;
    if (0 == rem) {
        n += 2;
    }
    return n;
}
```

Assume the selected path is:

```python
path_nodes = [
    ([2], "if(n < 0)", False),
    ([5], "if(n == 2)", False),
    ([8], "n = n | 1", None),
    ([9], "if(n == 1)", False),
    ([12], "final int rem = n % 3", None),
    ([13], "if(0 == rem)", True),
    ([16], "return n", None),
]

method_params = [
    {"name": "n", "type": "int"}
]
```

LLM solving is not needed because every condition is numerical and parseable.

The Z3 workflow is:

1. Create the original input symbol:

```python
input_symbols["n"] = BitVec("n", 32)
env["n"] = BitVec("n", 32)
```

In the explanation below, `original_n` means the preserved Z3 symbol stored in `input_symbols["n"]`. It is not a separate variable in the implementation; it is just a readable alias for the method input before any path assignments update `env["n"]`.

2. Process `if(n < 0)` with branch value `False`:

```python
solver.add(Not(n < 0))
```

This means the original input must satisfy `n >= 0`.

3. Process `if(n == 2)` with branch value `False`:

```python
solver.add(Not(n == 2))
```

4. Process the assignment:

```java
n = n | 1
```

The current symbolic environment becomes:

```python
env["n"] = input_symbols["n"] | 1
```

5. Process `if(n == 1)` with branch value `False`:

```python
solver.add(Not((input_symbols["n"] | 1) == 1))
```

6. Process:

```java
final int rem = n % 3
```

The local variable is represented as:

```python
env["rem"] = (input_symbols["n"] | 1) % 3
```

7. Process `if(0 == rem)` with branch value `True`:

```python
solver.add(0 == ((input_symbols["n"] | 1) % 3))
```

The accumulated constraints are equivalent to:

```text
input_symbols["n"] >= 0
input_symbols["n"] != 2
(input_symbols["n"] | 1) != 1
((input_symbols["n"] | 1) % 3) == 0
```

One satisfying model is:

```text
n = 3
```

The executor formats this as:

```text
Please use the input: n=3.
```

The downstream test prompt then includes the path plus this concrete input hint.

## Example 2: LLM Path Solving Enabled

Now consider a path with strings, object-like behavior, and an enum:

```java
enum Mode {
    STRICT,
    LENIENT
}

public static int classify(String text, Mode mode) {
    if (text == null) {
        return -1;
    }
    if (text.trim().isEmpty()) {
        return 0;
    }
    if (mode == Mode.STRICT && text.startsWith("A")) {
        return 1;
    }
    return 2;
}
```

Assume the selected path is:

```python
path_nodes = [
    ([7], "if(text == null)", False),
    ([10], "if(text.trim().isEmpty())", False),
    ([13], "if(mode == Mode.STRICT && text.startsWith(\"A\"))", True),
    ([14], "return 1", None),
]

method_params = [
    {"name": "text", "type": "String"},
    {"name": "mode", "type": "Mode"},
]
```

With `enable_LLM_path_solving = true`, `_path_needs_llm(path_nodes)` returns true because the path contains:

- A null comparison.
- Method calls: `trim()`, `isEmpty()`, and `startsWith(...)`.
- Dot access: `Mode.STRICT`.
- A string literal: `"A"`.

Instead of translating this path to Z3, the executor renders the LLM path-solving prompt with:

- The numbered source file.
- The method name or full method signature.
- The candidate path string.
- Any previous rejected LLM answers.
- Any verifier feedback from previous attempts.

The LLM solver is instructed to output only concrete parameter values, for example:

```text
text = "Apple", mode = Mode.STRICT
```

If `enable_LLM_verify = false`, this answer is accepted immediately and appended to the path:

```text
Please use the input: text = "Apple", mode = Mode.STRICT
```

If `enable_LLM_verify = true`, a second LLM prompt asks the verifier to trace the method and answer `Yes` or `No, <reason>`.

For this example, the verifier should answer `Yes` because:

- `text == null` is false for `"Apple"`.
- `text.trim().isEmpty()` is false.
- `mode == Mode.STRICT` is true.
- `text.startsWith("A")` is true.
- The method reaches `return 1`.

If the verifier answers `No`, the rejected input and verifier explanation are passed back into the next solver prompt. The executor repeats this until the verifier accepts the answer or the number of rejections reaches `llm_verify_max_rejections`.

If the LLM solver returns:

```text
Could not find possible input, this path is unsatisfiable.
```

or if all verifier retries are rejected, the executor returns no solution and the selected path is skipped.

## What Happens When LLM Solving Is Disabled

If `enable_LLM_path_solving = false`, every path goes through the Z3 route when symbolic execution is enabled.

For simple numerical paths, this is ideal because Z3 can produce deterministic concrete inputs.

For paths with method calls or object behavior, the fallback is less precise:

- Method-call conditions are represented by unconstrained boolean placeholders.
- Assignments containing method calls or `new` object creation are skipped or represented by fresh symbols.
- Expressions involving strings, arrays, fields, enum constants, or unsupported syntax may fail to parse.

For example:

```java
if (isPrime(n)) {
    return n;
}
```

can become:

```python
solver.add(method_call_0)
```

This preserves the path shape but does not prove that the chosen `n` actually makes `isPrime(n)` true. Therefore, LLM path solving is preferred for non-numerical or semantic conditions.

## Supported Z3 Features

The Z3 translator is intentionally lightweight. It is designed for path guidance, not full Java symbolic execution.

Supported features include:

- Java and Python style `if` and `while` condition extraction.
- Parenthesis-aware condition parsing.
- `&&`, `||`, and unary `!`.
- `==`, `!=`, `<`, `>`, `<=`, and `>=`.
- Integer, long, float, and double literals.
- Boolean and null literals in limited contexts.
- Signed bit-vector modeling for Java integer-like values.
- Z3 real modeling for `float` and `double`.
- Typed method parameters when signatures are available.
- Arithmetic: `+`, `-`, `*`, `/`, `%`.
- Bitwise operators: `|`, `&`, `^`, `~`.
- Java shifts: `<<`, `>>`, `>>>`.
- Numeric casts.
- Simple and compound assignments.
- Boolean assignments such as `flag = n > 0`.
- Signed extraction of bit-vector model values.

## Limitations

The implementation does not perform full symbolic interpretation of Java.

Important limitations:

- Loops are skipped rather than unrolled.
- Method bodies are not inlined.
- Method calls are either routed to the LLM solver or represented as unconstrained placeholders in the Z3 route.
- Object state and field values are not modeled by Z3.
- Arrays and array elements are not modeled by Z3.
- Strings and characters are not modeled by Z3.
- Enum constants and static constants are not evaluated by Z3.
- Object creation is skipped.
- Unsupported expressions may be ignored instead of blocking the entire path.
- LLM solving is heuristic and depends on the quality of the source context, path text, and verifier.

These limitations are acceptable for Panta's use case because the goal is not to verify the program completely. The goal is to generate useful concrete input hints for tests that can improve path and coverage exploration.

## Infeasible Paths and Timeouts

The executor distinguishes three important outcomes:

| Outcome | Meaning | PromptBuilder behavior |
| --- | --- | --- |
| `sat` | A concrete input was found. | Append `Please use the input: ...` |
| `unsat` | Z3 proved the constraints inconsistent. | Skip the selected path and try another candidate. |
| `unknown` or timeout | Z3 could not decide within the time budget. | Keep the path only if the session timed out, and ask the LLM to think of an appropriate input. |

This prevents infeasible paths from wasting test-generation attempts while still allowing progress when the solver budget is exhausted.

## Methodology Summary

Panta's symbolic execution is a hybrid path-solving layer placed between CFG path selection and LLM test generation.

For numerical paths, it converts branch decisions and assignments into Z3 constraints, tracks variable updates through an SSA-style environment, solves for original method inputs, and appends deterministic input hints to the prompt.

For non-numerical paths, it delegates path solving to an LLM using the full source file and candidate path. Optionally, a second LLM verifies the proposed input by tracing the method. Rejected answers are fed back into the next attempt until a verified input is found or the path is abandoned.

In both cases, the symbolic executor serves the same methodological role: it narrows the test-generation problem from "infer how to cover this path" to "write a test using this concrete input to cover this path."
