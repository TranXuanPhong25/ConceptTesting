"""Specification-only prompts for generating candidate programs."""
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
