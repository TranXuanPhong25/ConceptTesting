"""Deterministic approximation of KITE's Java AST unit-structure representation.

The paper does not publish its parser or anchor rules.  This module deliberately
uses a conservative lexical Java scanner while preserving the published grammar,
normalization, relation names, coarse key, and SHA-1/16 fingerprint definition.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter

from .models import UnitStructure

_CONTROL = re.compile(r"\b(if|for|while|switch|catch)\s*\((.*?)\)")
_RETURN = re.compile(r"\b(return|throw|break|continue)\b(?:\s+([^;]+))?")
_ASSIGN = re.compile(r"(?<![=!<>])\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*=\s*([^=].*?);")
_CALL = re.compile(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\((.*?)\)")
_COMPARE = re.compile(r"([^&|;]+?)\s*(==|!=|<=|>=|<|>)\s*([^&|;]+)")
_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"|\b\d+(?:\.\d+)?\b|\b(?:true|false|null)\b')
_IDENT = re.compile(r"\b[A-Za-z_$][\w$]*\b")
_KEYWORDS = frozenset("if else for while switch case return throw break continue new true false null".split())


def _normalize(expr: str) -> str:
    expr = _LITERAL.sub("Literal", expr)
    mapping: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in _KEYWORDS or token[:1].isupper() or token == "Literal":
            return token
        mapping.setdefault(token, f"V{len(mapping)}")
        return mapping[token]

    return re.sub(r"\s+", "", _IDENT.sub(repl, expr))


def extract_unit_structures(source: str) -> list[UnitStructure]:
    lines = source.splitlines()
    raw: list[tuple[int, str, str, str]] = []
    for number, line in enumerate(lines, 1):
        stripped = re.sub(r"//.*$", "", line).strip()
        if not stripped:
            continue
        match = _CONTROL.search(stripped)
        if match:
            raw.append((number, "control_header", f"{match.group(1).title()}Statement({_normalize(match.group(2))})", stripped))
        match = _RETURN.search(stripped)
        if match:
            raw.append((number, "statement_center", f"{match.group(1).title()}Statement({_normalize(match.group(2) or '')})", stripped))
        match = _ASSIGN.search(stripped)
        if match:
            raw.append((number, "statement_center", f"Assignment({_normalize(match.group(2))})", stripped))
        for match in _COMPARE.finditer(stripped):
            raw.append((number, "expression_center", f"Comparison({_normalize(match.group(0))})", stripped))
        if not any(item[0] == number for item in raw):
            match = _CALL.search(stripped)
            if match and match.group(1) not in _KEYWORDS:
                raw.append((number, "expression_center", f"MethodInvocation({_normalize(match.group(1))})", stripped))

    units: list[UnitStructure] = []
    for center, item in enumerate(raw):
        selected = raw[max(0, center - 1) : center + 2]
        anchors = tuple(
            {"index": str(i), "role": role, "signature": signature, "line": str(line)}
            for i, (line, role, signature, _text) in enumerate(selected)
        )
        relations: list[str] = []
        for i in range(len(selected) - 1):
            a, b = selected[i], selected[i + 1]
            if a[0] == b[0]:
                rel = "expr_in_stmt"
            elif a[1] == "control_header" and b[0] == a[0] + 1:
                rel = "guard_to_body"
            elif abs(a[0] - b[0]) == 1:
                rel = "adjacent_stmt"
            else:
                rel = "same_block"
            relations.append(f"{i}-{i + 1}:{rel}")
        roles = tuple(sorted(a["role"] for a in anchors))
        roots = tuple(sorted(a["signature"].split("(", 1)[0] for a in anchors))
        rel_types = tuple(sorted(r.split(":", 1)[1] for r in relations))
        coarse = (len(anchors), len(relations), roles, roots, rel_types)
        canonical = "|".join(f"{a['role']}[{a['signature']}]" for a in anchors) + "||" + "|".join(relations)
        units.append(UnitStructure(anchors, tuple(relations), coarse, hashlib.sha1(canonical.encode()).hexdigest()[:16]))
    return units


def multiset_jaccard(left: UnitStructure, right: UnitStructure) -> float:
    a, b = Counter(left.signatures()), Counter(right.signatures())
    union = sum((a | b).values())
    return sum((a & b).values()) / union if union else 1.0

