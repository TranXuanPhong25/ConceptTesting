"""Static focal-context and structured-seed extraction."""

from __future__ import annotations

import re
from typing import Any

from .benchmark import Subject


COMPARE_RE = re.compile(r"(?:if|while)\s*\(([^\n{}]+(?:[<>=!]=?|&&|\|\|)[^\n{}]+)\)")
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
LITERAL_RE = re.compile(r"(?<![\w.])-?(?:0x[0-9a-fA-F]+|\d+)(?![\w.])")
CONTROL = frozenset({"if", "while", "for", "switch", "return", "sizeof", "defined"})
KNOWN_SIGNATURES = {
    "tolower": "int tolower(int c)",
    "isdigit": "int isdigit(int c)",
    "towlower": "wint_t towlower(wint_t wc)",
    "iswprint": "int iswprint(wint_t wc)",
    "iswcntrl": "int iswcntrl(wint_t wc)",
    "memcmp": "int memcmp(const void *s1, const void *s2, size_t n)",
    "strlen": "size_t strlen(const char *s)",
    "strnlen": "size_t strnlen(const char *s, size_t maxlen)",
}


def _code_only(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", " ", source, flags=re.S)
    source = re.sub(r"//[^\n]*", " ", source)
    return re.sub(r"^\s*#.*$", " ", source, flags=re.M)


def build_context(source: str, subject: Subject) -> dict[str, Any]:
    code = _code_only(source)
    signature = {
        "return_type": subject.return_type,
        "name": subject.name,
        "parameters": [
            {"Type": typ, "Kind": kind, "ExprInput": name} for typ, kind, name in subject.parameters
        ],
    }
    conditions = [" ".join(m.group(1).split()) for m in COMPARE_RE.finditer(code)]
    calls = []
    for call in CALL_RE.findall(code):
        if (
            call not in CONTROL and call != subject.name and call not in calls
            and not call.isupper() and not call.startswith("__builtin_")
        ):
            calls.append(call)
    return {
        "function": signature,
        "source": source,
        "conditions": conditions,
        "numeric_literals": list(dict.fromkeys(LITERAL_RE.findall(code))),
        "callees": calls,
        "callee_signatures": {name: KNOWN_SIGNATURES[name] for name in calls if name in KNOWN_SIGNATURES},
    }


def _seed_value(kind: str) -> Any:
    if kind in {"string", "bytes", "char_buffer", "wstring"}:
        return ""
    return 0


def build_seed(context: dict[str, Any], extended: bool = False) -> dict[str, Any]:
    params = context["function"]["parameters"]
    seed: dict[str, Any] = {
        "Inputs": [
            {"ExprInput": p["ExprInput"], "Type": p["Type"], "Value": _seed_value(p["Kind"])} for p in params
        ],
        "Outputs": [{"ExprOutput": "return", "Type": context["function"]["return_type"], "Value": 0}],
        "Stubs": [
            {"StubFunctionSig": context.get("callee_signatures", {}).get(callee, callee), "Effects": []}
            for callee in context["callees"]
        ],
    }
    if extended:
        seed["InputConstraints"] = _constraints(params, context)
        seed["FaultHypotheses"] = _hypotheses(context)
        seed["PathEffects"] = _path_effects(context)
    return seed


def _constraints(params: list[dict[str, str]], context: dict[str, Any]) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = []
    for p in params:
        name, kind = p["ExprInput"], p["Kind"]
        if kind in {"string", "wstring", "bytes", "char_buffer"}:
            rules.append({"Rule": f"{name} points to a valid terminated sequence", "Probe": "empty, one-element, repeated, and mismatch-at-end values"})
        elif kind == "integer" and name in {"n", "len", "length", "maxlen", "siz", "hs_len", "ne_len", "haystack_len"}:
            rules.append({"Rule": f"0 <= {name} <= available buffer length/capacity", "Probe": "0, 1, exact length, and one before exact length"})
        else:
            rules.append({"Rule": f"{name} is valid for type {p['Type']}", "Probe": "zero and sign/character-class boundaries"})
    for cond in context["conditions"][:8]:
        rules.append({"Rule": f"execution guard: {cond}", "Probe": "make the guard true, false, and equal at its comparison boundary"})
    return rules


def _hypotheses(context: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    for i, condition in enumerate(context["conditions"][:10], 1):
        result.append({
            "Branch": condition,
            "Hypothesis": "comparison direction, equality handling, or loop termination may be off by one",
            "RequiredTest": f"H{i}: one test on each feasible side and one equality/boundary test",
        })
    if not result:
        result.append({"Branch": "implicit return/data-flow path", "Hypothesis": "empty or zero input may bypass normal processing", "RequiredTest": "H1: contrast empty/zero with a minimal non-empty value"})
    return result


def _path_effects(context: dict[str, Any]) -> list[dict[str, str]]:
    if not context["callees"]:
        return [{"Path": "all paths", "Dependency": "none", "Effect": "no external call requires a mock"}]
    conditions = context["conditions"] or ["entry"]
    return [
        {"Path": conditions[min(i, len(conditions) - 1)], "Dependency": callee, "Effect": "choose arguments/return effects that make this path observable"}
        for i, callee in enumerate(context["callees"][:8])
    ]
