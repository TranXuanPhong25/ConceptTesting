"""Only visible fields enter prompts; canonical solutions never go to the model."""
import json


def programs(task, retained, count):
    prompt = f"""Implement this HumanEval specification in Python. Return exactly {count} new
solutions as one JSON object: {{"programs":[{{"approach":"algorithm description",
"code":"complete standalone Python source"}}]}}.
Every solution must aim to satisfy the ENTIRE specification, including edge cases.
Do not deliberately introduce bugs or just target examples. Preserve the public
function name/signature. Include any required standard-library imports.
Use different algorithms, data structures, decompositions, or control flow wherever
possible: iteration vs recursion, direct computation vs search, different traversal
orders, auxiliary representations, streaming vs materialization. Do not pad code
with unreachable branches, dummy statements, no-op wrappers or unused imports to
manufacture differences. Renaming variables, formatting and comments do not count.
These solutions must differ structurally from each other and from the retained ones.
Return JSON only, without markdown fences.

SPECIFICATION:
{task['prompt']}

ALREADY RETAINED (do not duplicate):
{json.dumps(retained, ensure_ascii=False)}"""
    return [{"role": "system", "content": "You write correct, diverse Python implementations."},
            {"role": "user", "content": prompt}]


def tests(task, passing, count):
    prompt = f"""Write up to {count} NEW tests to expose specification violations in the
following Python solutions, which all passed the existing HumanEval base tests.
One shared test suite will be applied to every solution. Reason from the spec,
inspect differences and likely edge cases, and compute expected behavior yourself.
Use only inputs within the documented domain. Do not reuse ANY input exercised by
the base tests. Do not assume the majority of these implementations is correct.

Return JSON only: {{"tests":[{{"args":"([...], 3)", "kwargs":"{{}}",
"assertion":"result == expected_literal"}}]}}.
args and kwargs are strings containing Python literals (not executable code).
args must be a list/tuple of positional arguments; kwargs is a dict.
assertion is a Python boolean EXPRESSION with result (the actual returned value),
args, kwargs, math, and these builtins: abs, all, any, bool, dict, enumerate, float,
int, len, list, max, min, range, reversed, round, set, sorted, str, sum, tuple, zip.
Use concrete expected literals, not an undefined expected_literal name. You may use
comprehensions and public math attributes, but no other attribute access, lambda,
assignment, imports or calls to the candidate. For floating point use the tolerance
required by the specification (e.g. math.isclose). For non-unique correct outputs,
assert the required PROPERTY rather than equality to one arbitrary valid output
(e.g. polynomial residual for find_zero, valid ordering/permutation when relevant).
An assertion must return bool. Keep each test small enough to run in 3 seconds.

SPECIFICATION:
{task['prompt']}

EXISTING BASE TESTS:
{task['test']}

SOLUTIONS THAT PASS BASE TESTS:
{json.dumps(passing, ensure_ascii=False)}"""
    return [{"role": "system", "content": "You write independent, specification-grounded Python tests."},
            {"role": "user", "content": prompt}]
