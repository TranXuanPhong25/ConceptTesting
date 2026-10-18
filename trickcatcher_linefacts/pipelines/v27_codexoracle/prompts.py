"""Prompts for the five pilot arms (white-box: every arm sees the code, the spec in its docstring and the base tests).

Arms differ only in the section between the existing tests and the instruction:
  plain     no extra section
  concept   top-3 fuzz-confirmed line facts (facts.py)
  placebo   the same number of facts, same templates, about behaviour the base tests already cover
  coverage  one sentence: target behaviour the existing tests do not exercise
  toolinput the fuzz input that reaches each concept fact, without its output; the LLM writes the oracle
"""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

ARMS = ("plain", "concept", "placebo", "coverage", "toolinput")

SYSTEM = "You are an expert software tester."

HEAD = """The Python function below passes the existing tests, but it may still contain a bug that those tests miss. \
Its specification is the docstring.

## Code
```python
{put}
```

## Existing tests
```python
{base}
```
"""

TAIL = """
Write up to 10 new test assertions that could reveal a bug in this implementation. Each assertion must have the form
`assert {entry}(<arguments>) == <expected>`, where <expected> is the value the specification requires, not what the
code returns. Only use inputs the specification allows. Reply with a single ```python code block containing one
assertion per line and nothing else."""

FACTS_HEAD = "\n## Facts about the existing tests (computed by running them)\n" \
    "Facts use standard test-adequacy terms (statement/branch/condition coverage, boundary values, " \
    "equivalence classes, loop coverage, def-use pairs, mutation testing).\n"
FACTS_TAIL = "Use these facts when choosing inputs.\n"
TOOLINPUT_TAIL = "Write an assertion for each of these inputs; you may add others.\n"


def section(arm, task):
    if arm == "plain":
        return ""
    if arm == "coverage":
        return "\n## Hint\nTarget behaviour that the existing tests do not exercise.\n"
    if arm in ("concept", "placebo"):
        facts = task["concept_facts"] if arm == "concept" else task["placebo_facts"]
        return FACTS_HEAD + "".join(f"- {f}\n" for f in facts) + FACTS_TAIL if facts else ""
    if arm == "concept-toolinput":
        facts = task["concept_facts"]
        if not facts:
            return ""
        lines = [f"- {fact}\n" + (f"  An input that reaches this: `{call}`\n" if call else "")
                 for fact, call in zip(facts, task["fact_witnesses"])]
        return FACTS_HEAD + "".join(lines) + FACTS_TAIL + TOOLINPUT_TAIL
    if arm == "toolinput":
        calls = task["tool_inputs"]
        if not calls:
            return ""
        return ("\n## Inputs to test (chosen by a tool)\n" + "".join(f"- `{c}`\n" for c in calls)
                + TOOLINPUT_TAIL)
    raise ValueError(arm)


REQ_HEAD = "\n## Input requirements (mined from the specification)\n"
REQ_TAIL = "Every input you use must satisfy all of these requirements.\n"


def build(arm, task):
    """task: dict with put, base, entry, concept_facts, placebo_facts, tool_inputs (and optional requirements, F5)."""
    req = task.get("requirements")
    req = REQ_HEAD + "".join(f"- {r}\n" for r in req) + REQ_TAIL if req else ""
    return SYSTEM, HEAD.format(put=task["put"].rstrip(), base=task["base"].strip()) + section(arm, task) + req \
        + TAIL.format(entry=task["entry"])
