"""Deterministic, source-only concept cards for the TrickCatcher ablation.

Rules are generic AST patterns. They do not consult benchmark solutions,
contracts, task IDs, model output, or evaluation results.
"""

from __future__ import annotations

import ast
import json
import re


def _doc_property(function: ast.FunctionDef) -> str:
    doc = ast.get_docstring(function) or ""
    cleaned = re.sub(r"\s+", " ", doc).strip()
    # Keep the documented behavior, but omit worked examples and long notes.
    cleaned = re.split(r"\b(?:Examples?|For example|Note:|>>>|Returns?:)\b", cleaned, maxsplit=1, flags=re.I)[0]
    return cleaned[:420].strip(" :;,.\n") or "Behavior should satisfy the function docstring."


def _signals(function: ast.FunctionDef) -> list[tuple[int, int, str, str, str]]:
    found: list[tuple[int, int, str, str, str]] = []
    for node in ast.walk(function):
        line = getattr(node, "lineno", 10**9)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op, right = node.ops[0], node.comparators[0]
            if isinstance(op, (ast.In, ast.NotIn)) and isinstance(right, ast.Constant) and isinstance(right.value, str):
                found.append((0, line, "literal_membership", ast.unparse(node),
                              "Try valid characters or tokens in the documented category that differ from the literal membership set; include a near miss."))
            elif any(isinstance(item, ast.Constant) for item in (node.left, right)):
                found.append((2, line, "constant_comparison", ast.unparse(node),
                              "Exercise the condition at equality and on either valid side of its boundary; combine it with other independent conditions."))
        elif isinstance(node, ast.Subscript):
            found.append((3, line, "index_or_slice", ast.unparse(node),
                          "Vary valid sequence lengths and positions around the index or slice boundary; include repeated elements if the input permits them."))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            found.append((4, line, "modulo", ast.unparse(node),
                          "Try valid numbers with different remainders, including zero and negative values only if the docstring permits them."))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"replace", "split", "strip", "lower", "upper", "sort", "reverse"}:
            found.append((5, line, "transformation", ast.unparse(node),
                          "Try valid inputs where this transformation changes information, order, case, or delimiters; include duplicates where meaningful."))
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Constant):
            found.append((6, line, "constant_return", ast.unparse(node),
                          "Find valid inputs close to the branch boundary where a constant return may differ from the documented rule."))
    return sorted(found, key=lambda item: (item[0], item[1]))


def static_concept(source: str) -> tuple[str, list[str]]:
    """Return the same JSON card schema as Gemini and the triggered rule IDs."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    if not functions:
        raise ValueError("PUT has no top-level function")
    function = functions[-1]
    signals = _signals(function)
    chosen = signals[:2]
    card = {
        "expected_property": _doc_property(function),
        "suspected_shortcut": (
            "; ".join(f"{tag}: {code}" for _, _, tag, code, _ in chosen)
            if chosen else "No specific shortcut identified by static AST rules."
        ),
        "separating_input_relation": (
            " ".join(relation for _, _, _, _, relation in chosen)
            if chosen else "Try valid small, boundary, and mixed inputs under the documented domain."
        ),
    }
    return json.dumps(card, ensure_ascii=False), [tag for _, _, tag, _, _ in chosen]
