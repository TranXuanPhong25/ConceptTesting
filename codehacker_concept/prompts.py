"""Prompt templates.

* ``APPENDIX_L_*`` reproduce CodeHacker Appendix L (arXiv 2602.20213v2, CC BY 4.0)
  as closely as the HTML rendering allows (text verbatim; list/heading
  markup re-flowed into plain text).
* ``AUTOCODE_*`` implement AutoCode (arXiv 2510.12803) Algorithms 1-3. AutoCode
  publishes no prompt text, so these are written from the algorithm
  descriptions (40 cases = 10 valid + 30 near-valid; 3 candidates; 40
  checker scenarios; three generator strategies).
* ``GLUE_*`` fill protocol gaps the paper leaves unspecified (initial validator
  P_val / checker P_c drafts, refinement feedback, tool-call format).
* ``CONCEPT_*`` are this project's extension (structured weakness concepts).

Placeholders use ``{{name}}`` so literal JSON/C++ braces need no escaping.
"""

from __future__ import annotations

import re

_PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")


def render(template: str, **values: object) -> str:
    missing = set(_PLACEHOLDER.findall(template)) - values.keys()
    if missing:
        raise ValueError(f"missing placeholders: {sorted(missing)}")
    return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), template)


# ============================================================ Appendix L (CodeHacker)

APPENDIX_L_CHECKER_HACK = """Please review the provided checker code and identify logical flaws. Each flaw should target a different logical issue that causes the checker to incorrectly judge the output.

# Inputs
Problem Description: {{problem_description}}
Checker Code: {{checker_code}}

# Reasoning Steps
1. Understand Requirements: Analyze the problem to determine if multiple valid solutions are allowed (Special Judge).
2. Analyze Checker Logic: Look for missing checks (too permissive) or overly rigid comparisons against standard output (too strict).
3. Construct Hack:
   - False Positive: Construct an invalid output that the checker accepts.
   - False Negative: Construct a valid alternative output (different from std) that the checker rejects.
4. Verify: Ensure your constructed output strictly follows the format.

# Target Bug Types
Type 1: False Positive (Too Permissive)
The checker wrongly ACCEPTS an invalid output.
Type 2: False Negative (Too Strict)
The checker wrongly REJECTS a valid output. This often happens when the checker requires the output to be identical to the standard solution, ignoring other valid permutations or solutions.

# Output Format (JSON)
{
  "test_cases": [
    {
      "strategy": "Checker ignores array sorting (False Positive)",
      "bug_type": "false_positive",
      "test_input": "<INPUT>",
      "fake_output": "<WRONG_OUTPUT_ACCEPTED>"
    },
    {
      "strategy": "Checker rejects valid reverse order (False Negative)",
      "bug_type": "false_negative",
      "test_input": "<INPUT>",
      "fake_output": "<VALID_ALT_OUTPUT_REJECTED>"
    }
  ]
}
"""

APPENDIX_L_VALIDATOR_HACK = """Please review the provided validator code and identify logical flaws. Each flaw should target a different logical issue that causes the validator to incorrectly judge the input case.

# Inputs
Constraints Description: {{problem_description}} (Focus on Input Format and Data Ranges)
Validator Code: {{validator_code}}

# Reasoning Steps
1. Extract Constraints: List every constraint from the text (e.g., 1 <= N <= 10^5, graph is connected, no duplicate edges).
2. Audit Code: Check if the Validator enforces each constraint using ensuref() or strict reading methods.
3. Construct Hack:
   - Type 1 (False Positive): Generate an ILLEGAL input that the Validator likely ACCEPTS (e.g., Validator uses int but input is 10^10).
   - Type 2 (False Negative): Generate a LEGAL input that the Validator likely REJECTS (e.g., Validator checks N < 100 but text says N <= 100).

# Bug Types
False Positive (Too Loose)
The Validator accepts an input that violates the constraints. (This is dangerous as it crashes solutions).
False Negative (Too Strict)
The Validator rejects a perfectly valid input.

# Output Format (JSON)
{
  "test_cases": [
    {
      "strategy": "The problem requires a DAG (no cycles), but the validator only checks connectivity. This input contains a cycle.",
      "bug_type": "false_positive",
      "test_input": "3 3\\n1 2\\n2 3\\n3 1",
      "expected_validity": "invalid" // This input SHOULD be invalid
    }
  ]
}
"""

APPENDIX_L_CODE_ANALYST = '''You are an expert Code Auditor for Competitive Programming. Your goal is to identify bugs (WA, TLE, RE, MLE) in a C++ submission by interacting with an execution environment.

# Communication Protocol
This is a multi-turn dialogue. In each turn, you must output a **Thought** followed by a **Tool Call** (or a Final Report).
The system will execute your tool and return the [Tool Output] in the next message.

# Available Tools
run_python(script_code)
Executes arbitrary Python code. You can use loops (for/while), define functions, imports (math, itertools), etc.
run_cpp(input_content)
Compiles and runs the target C++ code with the provided input_content (string).
Returns: stdout, stderr, and ExitCode.
finish(code_analysis_report)
Submits the final vulnerability report.

# One-Shot Example
User: Problem: Sum of squares 1^2+...+N^2. N <= 10^6. Code uses int.
Assistant:
Thought: The formula is N(N+1)(2N+1)/6. I need to check if N=10^6 overflows a 32-bit signed int (2x10^9).
Call:
run_python("""
sum = 0
for i in range(1, 10000001):
    sum += i * i
print(sum)
""")
User: [Tool Output] 333333833333500000
Assistant:
Thought: The result is ~3.3x10^17, which far exceeds 2x10^9. This confirms Overflow. Now I'll probe the code with a small case to see if logic is correct otherwise. Expected: 1^2+2^2+3^2=14.
Call: run_cpp("3")
User: [Tool Output] Stdout: "14", ExitCode: 0
Assistant:
Thought: Small case works, but large case will definitely overflow.
Call: finish("The code implements the summation formula correctly but risks overflow for N close to upper bounds. While N=10^6 fits, any intermediate calculation without modulo might exceed limits. The vulnerability is Integer Overflow on large inputs.")

# Your Task
Problem: {{problem_description}}
Code: {{target_code}}'''

APPENDIX_L_STRESS = """You are an expert in Competitive Programming. Your task is to write a **Randomized Test Case Generator** in C++.
This generator will be used for "Stress Testing" (Fuzzing) a target solution.

# Problem Description
{{problem_description}}

# Your Task
Write a complete C++ program that prints a SINGLE valid test case to standard output.

# Requirements for the Generator Code:
1. Randomization: Initialize the random seed using mt19937 rng(chrono::steady_clock::now().time_since_epoch().count()); or srand(time(0)).
2. Validity: The output MUST strictly follow the problem's input format and constraints (e.g., if the graph must be a tree, ensure no cycles and connectivity).
3. Scale: Bias the generation towards large inputs (close to the maximum N) to test for Time Limit Exceeded (TLE) errors, but occasionally generate small edge cases.
4. Robustness: Avoid undefined behavior in your generator (e.g., ensure rand() % 0 never happens).

# Helper Functions Recommendation
You may define helper functions like long long rand(long long a, long long b) to generate numbers in range [a,b].

# Output Format
Provide ONLY the C++ code block. Start with #include <bits/stdc++.h>.
"""

APPENDIX_L_BUG_DISCOVERY = """You are an expert in competitive programming. Your task is to find a bug in the following code and generate a test case that will expose it.

# Problem Description:
{{problem_description}}

# Incorrect Code:
```cpp
{{incorrect_code}}
```
{{hash_section}}{{analyst_section}}
### Your Task
Construct a test case (input) that:
1. Satisfies all the constraints of the original problem
2. Will cause the buggy implementation to produce an incorrect result
3. A correct solution would handle properly

### Types of Errors to Target
The buggy code may fail in one of these ways:
- WA (Wrong Answer): Produces incorrect output due to logical errors, wrong algorithms, or edge case mishandling
- TLE (Time Limit Exceeded): Takes too long to execute, often due to inefficient algorithms or infinite loops
- MLE (Memory Limit Exceeded): Requires too much memory space, often due to increasing space needed in the program.
- RE (Runtime Error): Crashes during execution due to array out of bounds, division by zero, stack overflow, etc.
Your test case should be designed to trigger one of these error types.

# Output Format:
Provide a complete C++ program that generates the test input. The program should:
- Always include bits/stdc++.h first
- Have a main() function that outputs the test case
- Follow the input format specified in the problem

### Example Output Format
Your generator can be as simple or complex as needed. Here are examples:
Simple Example (Direct Output):
```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    // Bug: code assumes n <= 1000, but constraint allows up to 10^5
    // This test case uses n = 100000 to trigger array overflow
    cout << "100000" << endl;
    return 0;
}
```
Complex Example (Algorithmic Generation):
```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    // Bug: O(n^2) algorithm will TLE on large inputs
    // Generate maximum size test case with worst-case pattern
    int n = 200000;
    cout << n << endl;

    // Generate adversarial pattern: descending order
    for (int i = n; i >= 1; i--) {
        cout << i;
        if (i > 1) cout << " ";
    }
    cout << endl;
    return 0;
}
```
Note: Your generator can include loops, conditionals, calculations, or any logic needed to construct the test case.

### Additional Guidelines
1. Analyze the bug: First identify what type of bug exists (Logic errors -> WA, Inefficient loops -> TLE, etc.)
2. Target the weakness: Design your test case to specifically trigger that bug
3. Stay within constraints: Your test case must be valid according to the problem constraints
4. Maximize impact: Choose values that make the error obvious and deterministic

Now, write the C++ generator based on this advice. Think step by step.
"""

APPENDIX_L_HASH_SECTION = """
# Hash Collision Data (Optional):
Our anti-hash generator has found two strings which have same hash values.
{{collision}}
"""

APPENDIX_L_ANTI_HASH = """You are a Cryptanalysis and Competitive Programming Expert specializing in **Hash Collisions**.
Your target is to break a solution that uses **Polynomial Rolling Hash** by generating two different strings with the same hash value (Collision).

# Workflow
1. Identify Hashing: Locate the hash calculation logic (usually h = (h * B + c) % M).
2. Extract Parameters:
   - Base (B): The multiplier (e.g., 31, 131, 13331, or a random value).
   - Modulus (M): The modulo (e.g., 10^9+7, 10^9+9).
   - Character Set (C): The valid alphabet (e.g., 'a'-'z').
   - Mapping (C): The character-to-integer conversion logic (e.g., s[i] - 'a' + 1 or raw ASCII values).
   - Note: If the code uses unsigned long long without explicit modulo, M = 2^64.

# Input
Problem: {{problem_description}}
Code: {{target_code}}

# Output Format (JSON)
{
  "vulnerability_type": "Hash Collision",
  "hash_parameters": {
    "base": "List of Integer (e.g., [131, 13331])",
    "modulus": "List of Integer or expression (corresponding one-to-one with base, e.g., [998244353, 2^64])",
    "character set": "a,b,c,...,x,y,z",
    "mapping": "{'a':1,'b':2,...}"
  }
}
"""

# ============================================================ glue (unspecified in the papers)

GLUE_ANALYST_TOOL_FORMAT = """
# Tool-call format (strict)
Write exactly one call per turn after the word `Call:`. The argument must be a single Python string literal
(use triple quotes for multi-line content), e.g.
Call: run_cpp(\"\"\"3
1 2 3
\"\"\")
You have at most {{max_turns}} tool calls; call finish(...) before running out. Keep run_cpp inputs small (<= 20 KB)."""

GLUE_GENERATOR_FEEDBACK = """[Judge Feedback] Your previous generator did not produce a successful hack.
{{feedback}}
Revise your analysis and write a new complete C++ generator (one ```cpp block). Remember the input must satisfy every constraint."""

GLUE_STRESS_FEEDBACK = """[Validator Feedback] Several inputs printed by your generator were rejected by the input validator:
{{feedback}}
Fix the generator so every printed test is valid, and output ONLY the corrected C++ code block."""

# ============================================================ AutoCode (Algorithms 1-3)

AUTOCODE_VALIDATOR_CASES = """You are an experienced competitive-programming problem setter. We are building an input VALIDATOR for the problem below and need an evaluation suite for candidate validators.

# Problem
{{problem_description}}

# Task
Write exactly 40 small test inputs:
- 10 VALID inputs that satisfy every constraint and the exact input format (include boundary values: minimum sizes, maximum values that still fit, equal elements, etc.).
- 30 NEAR-VALID ILLEGAL inputs: each must become valid after a *minor* modification (one value off by one beyond a bound, one token too many/few, a count that does not match, a duplicate where distinctness is required, a violated structural guarantee such as connectivity/acyclicity/sortedness/"answer exists", wrong line structure, value 0 where >= 1 is required, sum constraint exceeded by 1, etc.). Cover as many different constraints as possible.
Keep every input short (at most 30 lines). Use only formats the statement allows.

# Output (JSON only)
{"cases": [{"input": "<raw input text>", "valid": true, "reason": "..."}, ...]}
"""

AUTOCODE_VALIDATOR_PROGRAM = """You are an expert competitive-programming problem setter. Write a strict input VALIDATOR using testlib for the problem below.

# Problem
{{problem_description}}

# Requirements
- `#include "testlib.h"` first, call `registerValidation(argc, argv);`.
- Read the input with strict testlib readers (`inf.readInt(lo, hi, "name")`, `inf.readLong`, `inf.readSpace()`, `inf.readEoln()`, `inf.readEof()`, `inf.readToken/readWord` with regex) so whitespace and line structure are checked exactly.
- Enforce EVERY constraint in the statement, including global ones (sum of n over test cases, distinctness, connectivity/tree/acyclicity, permutation, sortedness, guarantees such as "the answer exists" when they can be checked).
- Exit normally only for valid input; use `ensuref(cond, "message")` for violated properties.
{{variant}}
# Output
Return only the complete C++ program in one ```cpp block."""

AUTOCODE_VALIDATOR_VARIANTS = [
    "- Style: straightforward direct implementation.",
    "- Style: first write down the list of constraints as comments, then enforce each one explicitly and in order.",
    "- Style: be defensive about 64-bit ranges and global/structural constraints; use DSU/BFS helpers where structure must be checked.",
]

AUTOCODE_CHECKER_SCENARIOS = """You are an expert competitive-programming problem setter building an output CHECKER for the problem below. We need labelled scenarios to select the best candidate checker.

# Problem
{{problem_description}}

# Reference solution (its output is the jury answer)
```cpp
{{reference_code}}
```

# Task
Write 40 scenarios. Each scenario has a SMALL valid input and a contestant output. Mix:
- ~12 contestant outputs that are CORRECT: equal to the reference output, or (if the problem accepts several answers) a different valid answer, with harmless whitespace differences;
- ~28 contestant outputs that LOOK plausible but are WRONG: off-by-one values, wrong counts, violated constraints of the answer, wrong format, truncated output, an answer claimed impossible when possible, etc.
For each input you must compute the correct answer yourself step by step; keep inputs tiny so this is easy.

# Output (JSON only)
{"scenarios": [{"input": "...", "contestant_output": "...", "verdict": "AC" or "WA", "reason": "..."}, ...]}
"""

AUTOCODE_CHECKER_PROGRAM = """You are an expert competitive-programming problem setter. Write an output CHECKER using testlib for the problem below.

# Problem
{{problem_description}}

# Requirements
- `#include "testlib.h"` first, call `registerTestlibCmd(argc, argv);` Streams: `inf` (input), `ouf` (contestant output), `ans` (jury answer produced by a correct reference solution).
- If the answer is unique, compare the contestant output with `ans` token by token (numbers as numbers; use an absolute/relative tolerance only if the statement allows it).
- If several answers are accepted, verify the contestant output directly against the input (all required properties, optimality compared with the jury answer's value, feasibility claims) instead of comparing strings.
- Use `quitf(_ok, ...)` for accepted and `quitf(_wa, ...)` for wrong answers; read contestant values with bounds so malformed output is WA, not a crash. Only `_fail` if the jury answer itself is inconsistent.
{{variant}}
# Output
Return only the complete C++ program in one ```cpp block."""

AUTOCODE_CHECKER_VARIANTS = [
    "- Style: straightforward direct implementation.",
    "- Style: enumerate every property of a correct answer as comments first, then check each explicitly.",
    "- Style: be strict about the output format and robust to extra whitespace; validate every contestant number's range before use.",
]

AUTOCODE_GEN_EXHAUSTIVE = """You are an expert competitive-programming problem setter. Write a C++ test GENERATOR implementing the *small data exhaustion* strategy for the problem below.

# Problem
{{problem_description}}

# Strategy (AutoCode G1: ExhaustiveSmall)
Enumerate small-scale inputs systematically (all small sizes, all value patterns / permutations / combinations of tiny domains) so that fundamental boundary conditions and corner cases are covered completely.
If the format allows several test cases in one input, pack many enumerated cases into one input while respecting every limit (including sums over test cases). Otherwise pick the most informative small instances.

# Interface
The program receives one integer argument `idx` (0 <= idx < 8) and prints ONE complete valid input to stdout; different idx must give different parts of the enumeration.
Return only the C++ code (one ```cpp block, `#include <bits/stdc++.h>` first, deterministic output)."""

AUTOCODE_GEN_RANDOM_EXTREME = """You are an expert competitive-programming problem setter. Write a C++ test GENERATOR implementing the *randomized and extreme data* strategy for the problem below.

# Problem
{{problem_description}}

# Strategy (AutoCode G2: RandomExtreme)
Generate large-scale random inputs and extreme values: push integers to their limits to trigger overflow, test floating-point precision, probe out-of-bounds access, and adversarially design hack cases that make common greedy algorithms fail or induce hash collisions.

# Interface
The program receives one integer argument `idx` (0 <= idx < 8), used as the random seed and to select a sub-strategy; it prints ONE complete valid input to stdout.
Return only the C++ code (one ```cpp block, `#include <bits/stdc++.h>` first)."""

AUTOCODE_GEN_TLE = """You are an expert competitive-programming problem setter. Write a C++ test GENERATOR implementing the *TLE-inducing data* strategy for the problem below.

# Problem
{{problem_description}}

# Strategy (AutoCode G3: TLEInducing)
Construct maximum-size inputs with specific structures that maximize the running time of plausible but too-slow algorithms (quadratic scans, naive recursion, bad pivot choices, long chains / stars / deep trees, many queries on worst-case ranges, etc.) so only solutions with the intended complexity pass.

# Interface
The program receives one integer argument `idx` (0 <= idx < 8) selecting the structure; it prints ONE complete valid input to stdout.
Return only the C++ code (one ```cpp block, `#include <bits/stdc++.h>` first)."""

GLUE_CHECKER_JUDGE = """You are an independent judge auditing a claimed ground-truth output for a competitive-programming problem (LLM-as-a-Judge, anti-hallucination step).

# Problem
{{problem_description}}

# Input (small)
{{input}}

# Claimed output
{{output}}

# Claimed reasoning
{{reasoning}}

Re-derive the answer yourself, step by step, strictly from the statement. Then answer with JSON only:
{"output_is_valid": true or false, "explanation": "..."}"""

GLUE_REFINE_VALIDATOR = """The validator below mis-classifies some inputs for this problem. Fix it.

# Problem
{{problem_description}}

# Current validator
```cpp
{{code}}
```

# Failure cases (ground-truth validity was checked)
{{failures}}

Return the complete corrected validator (testlib, strict) in one ```cpp block."""

GLUE_REFINE_CHECKER = """The checker below gives wrong verdicts on some outputs for this problem. Fix it.

# Problem
{{problem_description}}

# Current checker
```cpp
{{code}}
```

# Failure cases (verified: input, contestant output, jury answer from the reference solution, correct verdict)
{{failures}}

Return the complete corrected checker (testlib; streams inf/ouf/ans) in one ```cpp block."""

# ============================================================ concept extension

CONCEPT_ANALYST_SUFFIX = """
# Structured weakness concepts (required for the final report)
Your finish(...) argument must be a JSON object (as a Python string literal) with up to 3 ranked concepts:
{"concepts": [{
  "fault_class": "WA" | "RE" | "TLE" | "MLE",
  "mechanism": "<name from the mechanism list below, or a short new name>",
  "code_region": "<the exact line(s)/expression of the target code that is wrong>",
  "violated_invariant": "<the invariant or algorithmic assumption the code relies on that the problem does not guarantee>",
  "trigger_relation": "<a precise condition over the input variables/constraints that makes the region misbehave, e.g. 'n - 30 in {6,10,14}', 'sum a_i > 2^31-1', 'graph has >= 2 components'>",
  "trigger_check": "<Python source defining `def trigger(inp: str) -> bool` that returns True iff a raw input satisfies trigger_relation>",
  "expected_behaviour": "<what a correct solution outputs/does on such inputs>",
  "witness": "<a SMALL valid raw input satisfying the trigger on which you believe the target fails, or empty if only large inputs can trigger it>",
  "evidence": "<tool observations supporting the hypothesis>"
}]}
One concept = one atomic, testable rule. Prefer concepts you confirmed with run_cpp/run_python.
Verify `trigger_check` with run_python on your witness before finishing.

# Candidate bug mechanisms retrieved from a knowledge base of other problems (hints, not facts about this code)
{{mechanisms}}"""

CONCEPT_GENERATOR_SECTION = """
# Target weakness concept (from the Code Analyst; verified fields)
- Fault class: {{fault_class}}
- Mechanism: {{mechanism}}
- Suspicious code region: {{code_region}}
- Violated invariant / assumption: {{violated_invariant}}
- Trigger relation over the input: {{trigger_relation}}
- Expected correct behaviour: {{expected_behaviour}}
Your generated input MUST satisfy the trigger relation. It is checked automatically by:
```python
{{trigger_check}}
```
"""

CONCEPT_FEEDBACK_TRIGGER_MISS = """The generated input does NOT satisfy the concept's trigger relation (trigger(input) returned {{value}}). Keep the same concept and fix the generator so the trigger holds while every constraint stays valid."""

CONCEPT_FEEDBACK_HYPOTHESIS_REJECTED = """The generated input satisfies the trigger relation, is valid, and the target was still accepted. Either the trigger relation is too weak (refine it: which additional condition makes the region actually produce a wrong result?) or the concept is wrong. Explain which, then output a new generator (and, if you refine the relation, restate it as a comment on the first line of the generator: `// TRIGGER: ...`)."""
