"""Prompt construction for direct, STRUT, and extended STRUT arms."""

from __future__ import annotations

import json
from typing import Any


SYSTEM = "You generate deterministic C unit tests. Follow the requested output format exactly; do not explain."


def direct_prompt(context: dict[str, Any]) -> str:
    f = context["function"]
    signature = f["return_type"] + " " + f["name"] + "(" + ", ".join(
        p["Type"] + " " + p["ExprInput"] for p in f["parameters"]
    ) + ");"
    return f"""Generate a complete C test harness for `{f['name']}` from the source below.
Return C code only, no markdown. Include a main function and at least six diverse tests.
Declare the focal function exactly as `{signature}` (do not define it).
Use only valid inputs. Check exact return values or pointer offsets and observable buffer effects.
Do not redefine the focal function. Use checks of the form `failures += !(condition)` and return
0 only when all checks pass; do not abort, fuzz, print, or use undefined behavior.

FOCAL SOURCE:
{context['source']}
"""


def structured_prompt(context: dict[str, Any], seed: dict[str, Any], extended: bool) -> str:
    label = "fault-relevant extended structured seed" if extended else "STRUT structured seed"
    extra = """
Each InputConstraints rule is atomic: include a test for its boundary when feasible.
Target every FaultHypotheses RequiredTest and honor PathEffects. Never violate a buffer capacity.
""" if extended else ""
    return f"""Expand the {label} into 6-10 structured unit test cases for the focal C function.
Return a JSON array only. Every object MUST have exactly Inputs, Outputs, and Stubs; copy every
input expression and Type from the seed. Values are JSON strings/numbers, never C expressions.
For numeric returns use ExprOutput `return`. For pointer returns use `return_offset:<input-name>`
with an integer byte/element offset or null when NULL is expected. For changed char buffers add an
output whose ExprOutput is the input name and whose Value is the expected string. Stubs must be an
array. Preserve each full StubFunctionSig and give its case-specific return Effect; bare-name stubs
have unknown interfaces and must remain effect-free for normal linking. Use valid inputs and exact
oracles. Do not include duplicate cases.{extra}

FOCAL SOURCE:
{context['source']}

ONE-SHOT SEED:
{json.dumps(seed, ensure_ascii=False, indent=2)}
"""


def prompt_for(arm: str, context: dict[str, Any], seed: dict[str, Any]) -> str:
    if arm == "direct":
        return direct_prompt(context)
    if arm == "strut":
        return structured_prompt(context, seed, False)
    if arm == "extended":
        return structured_prompt(context, seed, True)
    raise ValueError(f"unknown arm: {arm}")
