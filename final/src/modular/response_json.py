"""Decode a model's JSON response, falling back to a Python literal reading.

Models often mix Python syntax into JSON: ``True``/``False``/``None``, tuples
``(2, 3)``, a trailing comma or a ``\\x00`` escape. Strict ``json.loads`` then
rejects the whole response and every input in it is lost.

The decoder first tries strict JSON. Only when that fails does it read the same
text as one Python literal with ``ast.literal_eval`` (standard library, no code
execution), treating the JSON words ``true``/``false``/``null`` as the Python
constants. No other rewriting is done; a truncated or otherwise broken response
is still rejected. Downstream validation of each input record is unchanged.
"""
from __future__ import annotations

import ast
import json

JSON_CONSTANTS = {"true": True, "false": False, "null": None}


def strip_code_fence(text: str) -> str:
    return text.strip().removeprefix("```json").removesuffix("```").strip()


class JsonConstantsToPython(ast.NodeTransformer):
    def visit_Name(self, node):
        if node.id in JSON_CONSTANTS:
            return ast.copy_location(ast.Constant(JSON_CONSTANTS[node.id]), node)
        return node


def read_python_literal(text: str):
    try:
        tree = ast.parse(text, mode="eval")
        tree = ast.fix_missing_locations(JsonConstantsToPython().visit(tree))
        return ast.literal_eval(tree)
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError) as error:
        raise ValueError(f"Response is neither JSON nor a Python literal: {type(error).__name__}") from None


def load_response_json(text: str) -> tuple[object, list[str]]:
    """Return the decoded object and the list of repairs applied (empty if strict JSON)."""
    cleaned = strip_code_fence(text)
    try:
        return json.loads(cleaned), []
    except json.JSONDecodeError:
        return read_python_literal(cleaned), ["python_literal_fallback"]
