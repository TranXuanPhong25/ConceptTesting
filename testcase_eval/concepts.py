"""Static, non-oracle fault concepts for TestCase-Eval buggy programs."""

from __future__ import annotations

import re
from typing import Any


def static_fault_concepts(source: str, language: str) -> dict[str, Any]:
    tags: list[str] = []
    risks: list[str] = []

    def add(tag: str) -> None:
        if tag not in tags:
            tags.append(tag)

    if re.search(r"\b(?:cnt|count|freq|frequency|f|mp|map)\s*\[[^]]+\]\s*(?:\+\+|\+=)", source, re.I):
        add("frequency_counting")
    if re.search(r"^[^\n]*(?:\[[0-9]+\]|\b(?:dict|list|map|set)\b)[^\n;]*;", source, re.M):
        add("global_mutable_state")
    if re.search(r"\b(?:sort|sorted)\s*\(", source):
        add("sorting")
    if re.search(r"(?:%|\bmod\b)", source, re.I):
        add("modular_arithmetic")
    if re.search(r"\[[^]]+\]", source):
        add("indexing")
    if re.search(r"(?:<=|>=|<|>)", source):
        add("boundary_comparison")
    if re.search(r"\b(?:int|long long)\b", source) and re.search(r"(?:\*|\+)", source):
        add("integer_arithmetic")

    reset = re.search(
        r"for\s*\([^;]+;\s*[^;]+<\s*([A-Za-z_]\w*)[^;]*;[^)]*\)\s*(?:\{[^}]*\}|[^;]*;)",
        source,
        re.S,
    )
    if "global_mutable_state" in tags and reset:
        risks.append(
            "State is reset with a loop bounded by an input-sized variable; probe the maximum valid key/index and multiple test cases for stale state."
        )
    if "frequency_counting" in tags:
        risks.append("Exercise repeated values, all-distinct values, and a value at the declared domain boundary.")
    if "boundary_comparison" in tags:
        risks.append("Probe equality and the nearest values on both sides of strict/non-strict comparisons.")
    if "integer_arithmetic" in tags:
        risks.append("Probe the largest legal operands and zero/one-sized cases for arithmetic edge behavior.")
    if not risks:
        risks.append("Vary the smallest valid case, a boundary-sized case, and structurally different valid inputs.")

    return {"language": language, "tags": tags, "risk_hypotheses": risks}


def render_fault_concepts(concepts: dict[str, Any]) -> str:
    lines = ["Static fault-oriented concepts (not an answer or sample input):"]
    lines.append("- code concepts: " + (", ".join(concepts.get("tags", [])) or "general control/data flow"))
    for risk in concepts.get("risk_hypotheses", []):
        lines.append("- risk hypothesis: " + risk)
    lines.append("Use these hypotheses to choose one small valid input that distinguishes the buggy implementation.")
    return "\n".join(lines)

