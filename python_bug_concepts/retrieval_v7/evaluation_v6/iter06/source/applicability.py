"""Explicit, conservative candidate conditions with public-source evidence."""

from __future__ import annotations
import ast
import re
from collections import Counter
from .facts import Analysis, literal

RULES = {
    "py.extremum-initial-sentinel": {
        "requires": [
            "fixed same-scope initialization",
            "comparison-updated accumulator",
            "contract admits values outside sentinel bound",
        ],
        "excludes": ["initial value is guaranteed extremum under public domain"],
    },
    "py.index-out-of-bounds": {
        "requires": ["index may be outside admissible sequence bounds"],
        "excludes": [
            "stable builtin sequence and dominating nonempty guard for index0/-1",
            "mutation-free aligned builtin range loop",
        ],
    },
    "py.empty-reduction-domain": {
        "requires": ["eligible iterable may be empty and no valid empty-result policy"],
        "excludes": ["stable nonempty builtin-sequence guard"],
    },
    "py.tie-break-selection": {
        "requires": ["selection order disagrees with public tie contract"],
        "excludes": [
            "resolved builtin min/max preserves first maximum/minimum and public contract requests first"
        ],
    },
    "py.set-loses-multiplicity": {
        "requires": ["public contract needs counts", "set-converted value influences output"],
        "excludes": [
            "public positive equal-set/different-count example refutes count-equality requirement"
        ],
    },
    "py.presence-frequency-confusion": {
        "requires": ["occurrence-sensitive public requirement"],
        "excludes": [
            "public positive equal-set/different-count example refutes count-equality requirement"
        ],
    },
    "py.unicode-text-byte-domain": {
        "requires": ["character-domain requirement", "encoded bytes influence measured result"],
        "excludes": ["public requirement explicitly counts encoded bytes"],
    },
    "py.text-normalization-contract": {
        "requires": [
            "normalization influences observable result",
            "public contract preserves original case/content",
        ],
        "excludes": ["public requirement explicitly allows normalization"],
    },
    "py.first-occurrence-position": {
        "requires": ["first value-position lookup replaces required current position"],
        "excludes": ["public contract explicitly asks first matching position"],
    },
}


def public_examples(spec):
    """Read literal calls in public docs; never evaluate a target function."""
    lines = spec.splitlines()
    result = []
    for i, line in enumerate(lines):
        text = line.strip().removeprefix(">>>").strip()
        # Common examples: f(...) == True, f(...) ==> True, f(...) => True.
        text = re.sub(r"==>|=>|➞", "==", text)
        try:
            node = ast.parse(text, mode="eval").body
        except (SyntaxError, ValueError, RecursionError):
            continue
        expected = None
        call = None
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
            and isinstance(node.left, ast.Call)
            and isinstance(node.comparators[0], ast.Constant)
        ):
            call = node.left
            expected = node.comparators[0].value
        elif (
            isinstance(node, ast.Call)
            and i + 1 < len(lines)
            and lines[i + 1].strip() in {"True", "False"}
        ):
            call = node
            expected = lines[i + 1].strip() == "True"
        if call is None:
            continue
        if all(isinstance(arg, ast.Constant) and isinstance(arg.value, str) for arg in call.args):
            result.append(
                {
                    "function": ast.unparse(call.func),
                    "args": [a.value for a in call.args],
                    "expected": expected,
                    "public_clause": line.strip(),
                }
            )
    return result


def safe_loop_index(a, sub):
    if not isinstance(sub.value, ast.Name):
        return None
    name = sub.value.id
    p = a.parent.get(sub)
    while p is not None and p is not a.owner(sub):
        if (
            isinstance(p, ast.For)
            and isinstance(p.target, ast.Name)
            and isinstance(p.iter, ast.Call)
            and a.api(p.iter) == "range"
        ):
            args = p.iter.args
            if len(args) == 1:
                stop = args[0]
                start = 0
            elif len(args) == 2 and type(literal(args[0])) is int:
                start = literal(args[0])
                stop = args[1]
            else:
                return None
            decrement = 0
            if (
                isinstance(stop, ast.BinOp)
                and isinstance(stop.op, ast.Sub)
                and type(literal(stop.right)) is int
            ):
                decrement = literal(stop.right)
                stop = stop.left
            if not (
                isinstance(stop, ast.Call)
                and a.api(stop) == "len"
                and len(stop.args) == 1
                and isinstance(stop.args[0], ast.Name)
                and stop.args[0].id == name
            ):
                return None
            offset = 0
            index = sub.slice
            if (
                isinstance(index, ast.BinOp)
                and isinstance(index.op, ast.Add)
                and type(literal(index.right)) is int
            ):
                offset = literal(index.right)
                index = index.left
            if not (
                isinstance(index, ast.Name)
                and index.id == p.target.id
                and start >= 0
                and 0 <= offset <= decrement
            ):
                return None
            # All calls in the loop other than range/len are potentially mutating;
            # aliases cannot be resolved soundly here, so refuse the exclusion.
            for n in ast.walk(p):
                if a.scope(n) != a.scope(sub):
                    continue
                if isinstance(n, ast.Call) and a.api(n) not in {"range", "len"}:
                    return None
                if (
                    isinstance(n, ast.Name)
                    and n.id == name
                    and isinstance(n.ctx, (ast.Store, ast.Del))
                ):
                    return None
                if (
                    isinstance(n, ast.Name)
                    and n.id == p.target.id
                    and isinstance(n.ctx, (ast.Store, ast.Del))
                    and n is not p.target
                ):
                    return None
                if isinstance(n, ast.Delete):
                    return None
                if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                    targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                    if any(isinstance(t, ast.Subscript) for t in targets):
                        return None
            domain = a.sequence_domain(name, sub)
            if domain:
                return {
                    "loop_span": a.pos(p),
                    "index_offset": offset,
                    "stop_decrement": decrement,
                    "domain": domain,
                }
        p = a.parent.get(p)
    return None


def condition(a: Analysis, cid, node):
    rule = RULES.get(
        cid,
        {
            "requires": ["task contract and operation establish the stated mechanism"],
            "excludes": [],
        },
    )
    result = {
        "requires": rule["requires"],
        "excludes": rule["excludes"],
        "status": "unknown",
        "support": [],
        "contradictions": [],
    }
    spec = a.spec(node)
    if isinstance(node, ast.Subscript) and cid == "py.index-out-of-bounds":
        if isinstance(node.value, ast.Name) and literal(node.slice) in (0, -1):
            guard = a.guarded_nonempty(node.value.id, node)
            if guard:
                result["contradictions"].append({"kind": "guarded_index", "evidence": guard})
        loop = safe_loop_index(a, node)
        if loop:
            result["contradictions"].append({"kind": "bounded_loop_index", "evidence": loop})
    if isinstance(node, ast.Call):
        api = a.api(node)
        if (
            cid == "py.empty-reduction-domain"
            and api in {"min", "max"}
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
        ):
            guard = a.guarded_nonempty(node.args[0].id, node)
            if guard:
                result["contradictions"].append({"kind": "guarded_reduction", "evidence": guard})
        if (
            cid == "py.tie-break-selection"
            and api in {"min", "max"}
            and re.search(r"\bfirst\b", spec, re.I)
            and re.search(r"\btie\b|same|equal|multiple|several|more than one", spec, re.I)
        ):
            # Only a simple selection key whose tie evaluation has no side effect.
            keys = [kw.value for kw in node.keywords if kw.arg == "key"]
            plain_argument = len(node.args) == 1 and isinstance(node.args[0], ast.Name)
            owner = a.owner(node)
            if plain_argument and isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.args[0].id
                parameters = {
                    arg.arg
                    for arg in [*owner.args.posonlyargs, *owner.args.args, *owner.args.kwonlyargs]
                }
                rewritten = any(
                    (n.lineno, n.col_offset) < (node.lineno, node.col_offset)
                    for n in a.assignments.get((a.scope(node), name), [])
                )
                stable = (
                    name in parameters
                    and not rewritten
                    and a.value_unchanged(
                        name,
                        (owner.lineno, owner.col_offset),
                        (node.lineno, node.col_offset),
                        a.scope(node),
                    )
                )
            else:
                stable = False
            if stable and (
                not keys
                or all(isinstance(k, ast.Name) and a.qname(k) == "builtins.len" for k in keys)
            ):
                result["contradictions"].append(
                    {
                        "kind": "builtin_first_tie",
                        "api": api,
                        "public_clause": spec[:600],
                        "semantics": "Resolved builtin min/max preserves first encountered extremum; argument is an unchanged input parameter, key absent or builtin len",
                    }
                )
        if cid in {"py.set-loses-multiplicity", "py.presence-frequency-confusion"} and api == "set":
            owner = a.owner(node)
            fn = getattr(owner, "name", None)
            for example in public_examples(spec):
                args = example["args"]
                if (
                    example["function"] == fn
                    and example["expected"] is True
                    and len(args) == 2
                    and set(args[0]) == set(args[1])
                    and Counter(args[0]) != Counter(args[1])
                ):
                    result["contradictions"].append(
                        {"kind": "public_count_equality_counterexample", "evidence": example}
                    )
        if api in {"int", "float", "set", "len", "min", "max"}:
            result["support"].append(
                {"kind": "resolved_builtin", "fact_id": a.id(node), "api": api}
            )
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "encode",
            "lower",
            "upper",
            "casefold",
            "index",
        }:
            result["support"].append(
                {
                    "kind": "conditional_receiver_effect",
                    "fact_id": a.id(node),
                    "attribute": node.func.attr,
                    "receiver_domain_proven": False,
                }
            )
    if result["contradictions"]:
        result["status"] = "excluded_binding_under_recorded_assumptions"
    elif result["support"]:
        result["status"] = "operation_supported_contract_unverified"
    return result
