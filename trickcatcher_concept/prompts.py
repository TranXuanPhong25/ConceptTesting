"""Paper prompts (verbatim) and the concept-layer extensions.

Baseline prompts are the pinned TrickCatcher templates with only their
placeholders filled. Concept prompts *append* a block to the same templates, so
every concept-arm prompt contains the full paper prompt as a prefix.

Concept provenance (research/fulltext-batches/batch-07.md):
- enumerated atomic input rules: Specification Grounding (#126) -- enumerated
  rules beat prose and "think about edge cases";
- selected validator from candidates + near-valid illegal cases: AutoCode (#125),
  validator calibration against bypass/rejection: CodeHacker (#124);
- PUT-specific fault hypothesis (suspicious code, mechanism, trigger, required
  oracle): CodeHacker's code analyst (#124), AnyPoC's analyzer (#129), KITE's
  semantic bug mechanism (#123);
- independent re-execution of every reported exposure: AnyPoC's checker (#129).
"""

from __future__ import annotations

from typing import Any

from trickcatcher_concept.provenance import fill

LANG_NAME = {"cpp": "C++", "python": "Python 3"}

CARD_PROMPT = """You are an expert competitive programmer and software tester. You will get a problem description and a submitted {lang} solution. The solution passes the problem's existing tests (it is plausible), so if it is wrong the bug only shows on corner-case inputs that those tests miss.

Produce a JSON object with two fields and nothing else.

1. "constraints": the input specification enumerated as ATOMIC rules, one checkable rule per entry, covering: the exact line/token layout, the count of every sequence (e.g. "exactly N integers on line 2"), every numeric range, character sets and string lengths, and every structural or relational guarantee (distinctness, sortedness, graph is a tree/connected, sums bounded, etc.). Use ids C1, C2, ...
   Entry format: {"id": "C1", "rule": "..."}

2. "hypotheses": 3 to 5 fault hypotheses about THIS code, most likely first. Each must be grounded in a specific code excerpt and state the corner-case input condition under which the printed output would be wrong (wrong answer or crash). Consider integer overflow, off-by-one and boundary values, minimum/maximum sizes, equal or repeated values, zero/negative values, degenerate structures, special cases the code handles or forgets, greedy or shortcut logic that is not always correct, precision, and uninitialized or out-of-range access. Do not report pure time-limit issues. Do not claim certainty: these are hypotheses to test.
   Entry format: {"id": "H1", "code": "exact excerpt from the solution", "mechanism": "what the code does versus what the specification requires", "violated_rule": "the property of the specification that breaks", "trigger": "a condition on a VALID input (respecting all constraints) that makes the output wrong", "oracle": "what the correct output must satisfy for such an input"}

**PROBLEM DESCRIPTION**:
{pro_des}

**CODE**:
{code}
"""

VALIDATOR_PROMPT = """You are writing input validators for a competitive programming problem, in the style of a problem setter. A validator is a complete Python 3.8 program that reads the ENTIRE standard input and exits with status 0 if the input is valid and status 1 otherwise. It must not print anything required. It must check every rule: exact token/line structure (the input must contain exactly the tokens the format requires, no missing or extra tokens; trailing whitespace and a final newline are allowed), every sequence length, every numeric range, character sets, and structural guarantees (distinctness, tree/connectivity, sums) listed below. Checks must be efficient for maximum-size inputs (up to a few MB).

Write THREE independent validator programs (they will be compared against known valid and invalid inputs, and the most accurate one will be kept). Use exactly this layout with no other text:
### VALIDATOR 1
```python
...
```
### VALIDATOR 2
```python
...
```
### VALIDATOR 3
```python
...
```

**ENUMERATED INPUT RULES**:
{rules}

**PROBLEM DESCRIPTION**:
{pro_des}
"""

CASES_PROMPT = """You are attacking input validators for the competitive programming problem below. Write 12 SMALL near-valid ILLEGAL inputs, each violating exactly ONE of the enumerated rules while looking otherwise plausible (e.g. a count that does not match the number of values, a value one past its bound, a duplicate where distinctness is required, a wrong character, a missing line). Then write 6 SMALL VALID inputs that sit exactly on rule boundaries (minimum sizes, minimum and maximum values), which a too-strict validator might wrongly reject.

Use exactly this layout with no other text (the content lines are the raw standard input):
INVALID 1 (violates C?):
<input>
...
INVALID 12 (violates C?):
<input>
VALID 1:
<input>
...
VALID 6:
<input>

**ENUMERATED INPUT RULES**:
{rules}

**PROBLEM DESCRIPTION**:
{pro_des}
"""

VARIANT_HYPOTHESIS_BLOCK = """

**FAULT HYPOTHESIS TO CHECK**:
A reviewer suspects the following. Verify it against the problem description before changing anything; if it is a real bug, repair it, and in any case also repair any other bug or logic flaw you find.
- Suspicious code: {code}
- Mechanism: {mechanism}
- Specification property at risk: {violated_rule}
- Suspected trigger: {trigger}
Please reply with ONLY the COMPLETE REPAIRED CODE (rather than code fragments) and DO NOT reply any other content."""

GENERATOR_CONCEPT_BLOCK = """

**ENUMERATED INPUT RULES** (every generated input must satisfy ALL of them; inputs that break any rule are discarded):
{rules}

**TARGETED CORNER CASES**:
A code review of a submitted solution raised the hypotheses below. Make the generator devote a share of the 100 inputs to each trigger condition (while still satisfying every rule), and use the remaining inputs for boundary values (minimum and maximum sizes and values, equal values) and random inputs. Prefer small and medium inputs for the targeted cases so that corner structure is not diluted.
{hypotheses}"""


def rules_text(card: dict[str, Any]) -> str:
    rules = card.get("constraints") or []
    return "\n".join(f"{r.get('id', f'C{i + 1}')}: {r.get('rule', '')}" for i, r in enumerate(rules)) or "(none extracted; use the problem description)"


def hypotheses_text(card: dict[str, Any]) -> str:
    lines = []
    for i, h in enumerate(card.get("hypotheses") or []):
        lines.append(f"{h.get('id', f'H{i + 1}')}: trigger: {h.get('trigger', '')} (mechanism: {h.get('mechanism', '')})")
    return "\n".join(lines) or "(none)"


def card_prompt(lang: str, description: str, code: str) -> str:
    return fill(CARD_PROMPT, lang=LANG_NAME[lang], pro_des=description, code=code)


def validator_prompt(description: str, card: dict[str, Any]) -> str:
    return fill(VALIDATOR_PROMPT, rules=rules_text(card), pro_des=description)


def cases_prompt(description: str, card: dict[str, Any]) -> str:
    return fill(CASES_PROMPT, rules=rules_text(card), pro_des=description)


def variant_prompt(template: str, description: str, code: str, hypothesis: dict[str, Any] | None = None) -> str:
    prompt = fill(template, pro_des=description, code=code)
    if hypothesis:
        prompt = prompt.rstrip("\n") + fill(VARIANT_HYPOTHESIS_BLOCK, **{k: str(hypothesis.get(k, "")) for k in
                                                                        ("code", "mechanism", "violated_rule", "trigger")})
    return prompt


def generator_prompt(template: str, pid: str, description: str, card: dict[str, Any] | None = None) -> str:
    prompt = fill(template, pid=pid, pro_des=description)
    if card is not None:
        prompt = prompt.rstrip("\n") + fill(GENERATOR_CONCEPT_BLOCK, rules=rules_text(card), hypotheses=hypotheses_text(card))
    return prompt
