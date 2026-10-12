"""Exact Python prompt adaptations; no implementation reaches test generation."""
from __future__ import annotations

import ast
import re

from trickcatcher_linefacts import preconditions, prompts as harness_prompts

ARMS = ("onlydoc", "advdoc")
SYSTEM = harness_prompts.SYSTEM
TEST_GENERATION_PROMPT = '''You are a professional who writes Python test functions. Please help me write some unit tests in Python language, details are listed below:

```python
# The following is the docstring of the function that you are going to test.

{docstring}

# The full function signature is:
{signature}

# The function name is:
{entry}

# The parameters of the function:
{parameters}

# The parameter types:
{parameter_types}

# The return type of the function:
{return_type}
```
Please write some unit tests in Python with maximizing both branch and line coverage. Please ensure that the output format is Markdown, and no explanations needed.
'''

ADVANCED_DOCSTRING_PROMPT = '''You are professional Python developer, please help me identify the intention and functionality of the function detailed below.

```python
# The following code is the function that you are going to summarize.
{put}

# The parameters of the function:
{parameters}

# The parameter types:
{parameter_types}

# The return type of the function:
{return_type}
```
Please assume the role of an expert software engineer performing a critical code review. Your task is to produce a three-part response: a detailed analysis, a corrected implementation, and a formal docstring that captures the function's intended requirement.

**Part 1: Critical Analysis**
First, provide your analysis by completing the following sections. For each point, state your findings clearly. If no issues are found in a category, you must explicitly state "No issues found."

1.  **Logical Mistakes:** Scrutinize the algorithm's logic. Based on the function's name and context, does its implementation correctly achieve its apparent goal, or are there logical flaws that would produce an incorrect result even on a "happy path"?
2.  **Robustness Omissions:** Check for missing but necessary steps that production-quality code would include. This includes, but is not limited to, input validation (e.g., None checks, boundary conditions), proper error handling, and necessary data sanitization or escaping.
Your analysis should be very detailed and step by step for the given code, make sure you clearly write out your entire analysis.

**Part 2: Corrected Implementation**
Based on your analysis in Part 1, provide a corrected, robust implementation of the function. This code should address all identified logical mistakes and robustness omissions, wrap this code inside a single ```python ``` markdown block.

**Part 3: Final Requirement Docstring**
Based on the **corrected implementation** you provided in Part 2, write a formal docstring that accurately describes its functionality, parameters, and return values. The docstring must be wrapped between Python triple quotes (""" or \'\'\').

Please avoid directly quoting from the original focal function code, as it might be buggy. Output the final docstring separately and make sure the final docstring is the only text inside a <FINAL_DOCSTRING>...</FINAL_DOCSTRING> block. Put the triple-quoted docstring inside that block.
'''


def seed(task, arm, sample, stage=0):
    """run_gen's 1000-sample/8-stage formula, in a reserved disjoint index range."""
    if not 0 <= int(task) < 1000 or not 0 <= sample < 1000 or stage not in (0, 1):
        raise ValueError("seed indices out of range")
    index = 250000 + int(task) * len(ARMS) + ARMS.index(arm)
    return 20261010 + ((index * 1000 + sample) * 8 + stage * 2)


def specification(task, doc=None):
    spec, original, _ = preconditions.specification(task)
    if doc is None:
        return spec
    tree = ast.parse(spec)
    tree.body[0].body = [ast.Expr(ast.Constant(doc))]
    return ast.unparse(ast.fix_missing_locations(tree))


def metadata(task, doc=None):
    # Derive ALL metadata from the stripped specification, never the PUT body.
    spec = specification(task, doc)
    fn = ast.parse(spec).body[0]
    args = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
    args += [a for a in (fn.args.vararg, fn.args.kwarg) if a is not None]
    signature, _, docstring = spec.partition("\n")
    return dict(signature=signature, docstring=docstring, entry=task["entry"],
                parameters=", ".join(a.arg for a in args) or "(none)",
                parameter_types=", ".join(f"{a.arg}: {ast.unparse(a.annotation) if a.annotation else 'unspecified'}"
                                          for a in args) or "(none)",
                return_type=ast.unparse(fn.returns) if fn.returns else "unspecified")


def messages(user):
    return [dict(role="system", content=SYSTEM), dict(role="user", content=user)]


def test_messages(task, doc=None):
    return messages(TEST_GENERATION_PROMPT.format(**metadata(task, doc))
                    + harness_prompts.TAIL.format(entry=task["entry"]))


def advanced_messages(task):
    return messages(ADVANCED_DOCSTRING_PROMPT.format(put=task["put"].rstrip(), **metadata(task)))


def parse_docstring(text, original):
    """Return (docstring, parse_failure); never pick Part 2's implementation docstring."""
    blocks = re.findall(r"<FINAL_DOCSTRING>\s*(.*?)\s*</FINAL_DOCSTRING>", text, re.S | re.I)
    if len(blocks) > 1:
        return original, "ambiguous_final_docstring"
    heading = re.search(r"\bPart\s*3\s*:\s*Final\s+Requirement\s+Docstring\b", text, re.I)
    if blocks:
        region = blocks[0]
    elif heading:
        region = text[heading.end():]
    else:
        return original, "missing_part3"
    quoted = re.findall(r'''(?P<quote>"""|\'\'\')(?P<doc>.*?)(?P=quote)''', region, re.S)
    if len(quoted) == 1:
        quote, raw = quoted[0]
        try:
            doc = ast.literal_eval(quote + raw + quote)
        except (ValueError, SyntaxError):
            return original, "invalid_docstring_literal"
    elif not quoted and blocks and not re.search(r'"""|\'\'\'|```', region):
        # Clearly delimited plain prose is also accepted; unclosed quotes are not.
        doc = region.strip()
    else:
        return original, "missing_or_ambiguous_docstring"
    if not isinstance(doc, str) or not doc.strip() or "\x00" in doc:
        return original, "empty_or_invalid_docstring"
    return doc, None
