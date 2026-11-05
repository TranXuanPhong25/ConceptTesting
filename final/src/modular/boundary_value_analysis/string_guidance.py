"""Narrow, inspectable spec derivations for numeric strings and fixed formats.

Only public specification text is used. Derived guards describe behavior, never
input preconditions. These rules are hints to the selector, not a fallback arm.
"""
from __future__ import annotations

import ast
import re


NUMERIC_STRING = re.compile(
    r"\b(?:numeric|decimal|floating[- ]point)\s+string\b"
    r"|\b(?:string|str)\b\s*[)\]`'\"]*\s*(?:(?:that|which)\s+)?"
    r"(?:represent(?:s|ing)?|contain(?:s|ing)?|encod(?:es|ing))\s+(?:a\s+)?"
    r"(?:finite\s+)?(?:floating[- ]point\s+)?(?:number|numeric\s+value)\b"
    r"|\b(?:number|numeric\s+value)\s+(?:as|in|encoded\s+as)\s+(?:a\s+)?string\b",
    re.I,
)
NEAREST_INTEGER = re.compile(r"\b(?:closest|nearest)\s+integer\b", re.I)
FORMAT_DECLARATION = re.compile(
    r"\b(?:(?:must|should)\s+(?:be\s+)?(?:in\s+)?(?:the\s+)?format"
    r"|(?:is\s+)?in\s+the\s+format)\s*:?\s*[`'\"]?"
    r"(?P<mask>(?:yyyy|yy|mm|dd|hh|ss)(?:[-/:. T]+(?:yyyy|yy|mm|dd|hh|ss)){1,5})"
    r"(?![\w])", re.I,
)


def specification_text(specification, entry_point):
    """Read a public docstring as source text; do not execute annotations/code."""
    try:
        tree = ast.parse(specification)
    except SyntaxError:
        return specification
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == entry_point and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                return ast.get_source_segment(specification, first) or ""
    return ""


def clause_context(text, match):
    start = max(text.rfind("\n", 0, match.start()), text.rfind(". ", 0, match.start()))
    return text[max(0, start + 1):match.end()]


def unambiguous_templates(templates, names, text):
    if len(templates) == 1:
        return templates
    selected = []
    for template in templates:
        parameter = template["characteristic"]["parameter"]
        if any(actual == parameter and re.search(r"\b" + re.escape(original) + r"\b", text)
               for original, actual in names.items()):
            selected.append(template)
    return selected


def derive_string_guidance(context, names):
    text = specification_text(context.specification, context.entry_point)
    templates = context.templates["candidates"]
    parsed_templates = [item for item in templates if item["characteristic"]["operation"] == "parsed_float"]
    string_names = {item["characteristic"]["parameter"] for item in parsed_templates}
    lengths = [item for item in templates if item["characteristic"]["operation"] == "length"
               and item["characteristic"]["parameter"] in string_names]
    projections = []
    guards = []
    for match in NUMERIC_STRING.finditer(text):
        clause = clause_context(text, match)
        prefix = clause[:-len(match.group())]
        if re.search(r"\b(?:not|non|example|optional)\b", prefix, re.I):
            continue
        for template in unambiguous_templates(parsed_templates, names, clause):
            evidence = {**template["characteristic"], "source_quote": match.group(),
                        "rule": "numeric_string_declaration"}
            if evidence not in projections:
                projections.append(evidence)
    nearest = NEAREST_INTEGER.search(text)
    nearest_prefix = clause_context(text, nearest)[:-len(nearest.group())] if nearest else ""
    if nearest and not re.search(r"\b(?:not|example|optional)\b", nearest_prefix, re.I):
        for template in parsed_templates:
            parameter = template["characteristic"]["parameter"]
            if not any(item["parameter"] == parameter for item in projections):
                continue
            # Representatives of n+0.5 on either side of zero, not global bounds.
            for midpoint, pair in [(0.5, [0, 1]), (-0.5, [-1, 0])]:
                guards.append({"template_id": template["id"], "characteristic": template["characteristic"],
                    "comparison": "==", "threshold": {"kind": "constant", "value": midpoint},
                    "source_quote": nearest.group(), "origin": "spec", "necessary_domain": False,
                    "derivation": {"rule": "nearest_integer_midpoint", "adjacent_integers": pair,
                                   "scope": "representatives-of-half-integer-behavior-boundaries"}})
    for match in FORMAT_DECLARATION.finditer(text):
        clause = clause_context(text, match)
        before_mask = clause[:clause.rfind(match.group("mask"))]
        tail = text[match.end():match.end() + 80]
        if (re.search(r"\b(?:not|optional|example|variable)\b", before_mask, re.I)
                or re.match(r"\s*(?:\[|\.\.\.|or\b)", tail, re.I)):
            continue
        mask = match.group("mask")
        for template in unambiguous_templates(lengths, names, clause):
            guards.append({"template_id": template["id"], "characteristic": template["characteristic"],
                "comparison": "==", "threshold": {"kind": "constant", "value": len(mask)},
                "source_quote": match.group(), "origin": "spec", "necessary_domain": False,
                "derivation": {"rule": "fixed_width_format_length", "format_mask": mask,
                               "field_widths": [len(field.group()) for field in re.finditer(r"yyyy|yy|mm|dd|hh|ss", mask, re.I)],
                               "scope": "format-acceptance-behavior-not-input-domain"}})
    return {"projection_evidence": projections, "candidate_guards": guards}
