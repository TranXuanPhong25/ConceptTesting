"""P1 source-only capability inventory for v60.

This module reads public requests and ASTs. It never imports, executes, or evaluates
the PUT, contract, reference implementation, or a generated input.
"""
from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path
from typing import Any

from .bindings import resolve


HERE = Path(__file__).resolve().parent

SYMBOLIC_SAFE_CALLS = frozenset({
    "abs", "all", "any", "enumerate", "len", "list", "max", "min", "range",
    "reversed", "set", "sum", "tuple",
})
NATIVE_REQUIRED_NODES = {
    ast.Dict: "dict_literal",
    ast.DictComp: "dict_comprehension",
    ast.GeneratorExp: "generator_expression",
    ast.ListComp: "list_comprehension",
    ast.SetComp: "set_comprehension",
    ast.While: "while_loop",
    ast.Yield: "yield",
    ast.YieldFrom: "yield_from",
    ast.Try: "exception_control_flow",
    ast.With: "context_manager",
}
MUTATING_METHODS = frozenset({"add", "append", "clear", "discard", "extend", "pop", "remove", "sort", "update"})
NONDETERMINISTIC_NAMES = frozenset({"choice", "choices", "randint", "random", "randrange", "shuffle", "time"})


def _span(node: ast.AST) -> list[int]:
    return [getattr(node, "lineno", 0), getattr(node, "col_offset", 0),
            getattr(node, "end_lineno", 0), getattr(node, "end_col_offset", 0)]


def _validate_public_request(request: dict[str, Any]) -> None:
    allowed = {"case_id", "source", "entry", "public_examples", "spec", "proposals"}
    if set(request) - allowed or not {"case_id", "source", "entry", "public_examples"} <= set(request):
        raise ValueError("public_request_schema")
    if not isinstance(request["source"], str) or not isinstance(request["entry"], str):
        raise ValueError("public_request_types")
    if not isinstance(request["public_examples"], list) or not request["public_examples"]:
        raise ValueError("public_examples")
    for row in request["public_examples"]:
        if set(row) != {"arguments", "expected"}:
            raise ValueError("public_example_schema")
        args = ast.literal_eval(row["arguments"])
        ast.literal_eval(row["expected"])
        if type(args) is not tuple:
            raise ValueError("positional_arguments_required")


def _literal_shape(value: Any, depth: int = 0) -> dict[str, Any]:
    if depth > 3:
        return {"kind": "depth_cap"}
    if type(value) in (bool, int, str) or value is None:
        return {"kind": type(value).__name__}
    if type(value) in (list, tuple):
        children = [_literal_shape(v, depth + 1) for v in value]
        return {"kind": type(value).__name__, "length": len(value),
                "elements": sorted({json.dumps(x, sort_keys=True) for x in children})}
    if type(value) is dict:
        return {"kind": "dict", "length": len(value),
                "key_types": sorted({type(k).__name__ for k in value}),
                "value_shapes": sorted({json.dumps(_literal_shape(v, depth + 1), sort_keys=True) for v in value.values()})}
    return {"kind": type(value).__name__}


def _functions(tree: ast.AST) -> dict[str, list[ast.FunctionDef]]:
    result: dict[str, list[ast.FunctionDef]] = collections.defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            result[node.name].append(node)
    return result


def _called_names(fn: ast.FunctionDef) -> set[str]:
    return {node.func.id for node in ast.walk(fn)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}


def _reachable_functions(entry: ast.FunctionDef, all_functions: dict[str, list[ast.FunctionDef]]) -> list[ast.FunctionDef]:
    seen: set[tuple[str, int]] = set()
    out: list[ast.FunctionDef] = []
    queue = [entry]
    while queue:
        fn = queue.pop(0)
        key = (fn.name, fn.lineno)
        if key in seen:
            continue
        seen.add(key); out.append(fn)
        local = {child.name: child for child in fn.body if isinstance(child, ast.FunctionDef)}
        for name in _called_names(fn):
            if name in local:
                queue.append(local[name])
            elif len(all_functions.get(name, [])) == 1:
                queue.append(all_functions[name][0])
    return out


def _constructs(functions: list[ast.FunctionDef]) -> tuple[dict[str, int], list[dict[str, Any]], list[str], bool]:
    counts: collections.Counter[str] = collections.Counter()
    details: list[dict[str, Any]] = []
    native_reasons: set[str] = set()
    nondeterministic = False
    for fn in functions:
        if any(isinstance(child, ast.FunctionDef) for child in fn.body):
            counts["nested_function"] += 1
            native_reasons.add("nested_function")
        for node in ast.walk(fn):
            for kind, reason in NATIVE_REQUIRED_NODES.items():
                if isinstance(node, kind):
                    counts[reason] += 1
                    native_reasons.add(reason)
                    details.append({"kind": reason, "span": _span(node), "function": fn.name})
            if isinstance(node, ast.AugAssign) and isinstance(node.target, (ast.Subscript, ast.Attribute)):
                counts["heap_update"] += 1
                native_reasons.add("heap_update")
                details.append({"kind": "heap_update", "span": _span(node), "function": fn.name})
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attribute = node.func.attr
                    if attribute in NONDETERMINISTIC_NAMES:
                        nondeterministic = True
                        native_reasons.add("possible_nondeterminism")
                    if attribute in MUTATING_METHODS:
                        counts["mutating_method"] += 1
                        native_reasons.add("mutating_method")
                        details.append({"kind": "mutating_method:" + attribute, "span": _span(node), "function": fn.name})
                    elif attribute not in {"bit_length", "items"}:
                        counts["library_method"] += 1
                        native_reasons.add("library_method")
                        details.append({"kind": "library_method:" + attribute, "span": _span(node), "function": fn.name})
                elif isinstance(node.func, ast.Name):
                    name = node.func.id
                    if name in NONDETERMINISTIC_NAMES:
                        nondeterministic = True
                        native_reasons.add("possible_nondeterminism")
                    if name not in SYMBOLIC_SAFE_CALLS and name not in {f.name for f in functions}:
                        counts["external_or_unsupported_call"] += 1
                        native_reasons.add("external_or_unsupported_call")
                        details.append({"kind": "external_call:" + name, "span": _span(node), "function": fn.name})
    return dict(counts), details, sorted(native_reasons), nondeterministic


def _requires_native_shape(shape: dict[str, Any], depth: int = 0) -> bool:
    if shape.get("kind") in {"dict", "depth_cap"}:
        return True
    if shape.get("kind") in {"list", "tuple"}:
        if depth >= 1:
            return True
        return any(_requires_native_shape(json.loads(child), depth + 1) for child in shape.get("elements", []))
    return False


def inventory(request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    _validate_public_request(request)
    tree = ast.parse(request["source"])
    entry, method_wrapper = resolve(tree, request["entry"])
    funcs = _reachable_functions(entry, _functions(tree))
    counts, details, native_reasons, nondeterministic = _constructs(funcs)
    examples = [ast.literal_eval(row["arguments"]) for row in request["public_examples"]]
    shapes = [[_literal_shape(arg) for arg in args] for args in examples]
    shape_requires_native = any(_requires_native_shape(shape) for args in shapes for shape in args)
    if shape_requires_native:
        native_reasons.append("nested_or_mapping_input")
        native_reasons = sorted(set(native_reasons))
    symbolic_route = not native_reasons
    route = "symbolic_then_native" if symbolic_route else "native_first"
    return {
        "case_id": request["case_id"],
        "source_sha256": hashlib.sha256(request["source"].encode()).hexdigest(),
        "entry": request["entry"],
        "entry_method_wrapper": method_wrapper,
        "reachable_functions": [{"name": fn.name, "line": fn.lineno, "span": _span(fn)} for fn in funcs],
        "public_input_topologies": shapes,
        "construct_counts": counts,
        "construct_details": details,
        "route": route,
        "native_reasons": native_reasons,
        "repeatability_required": nondeterministic,
        "capability_status": "source_inventory_only",
        "budgets": {
            "max_recipes": config["max_recipes_per_case"],
            "max_candidates": config["max_candidates_per_case"],
            "max_native_executions": config["max_native_executions_per_case"],
            "max_case_seconds": config["max_case_seconds"],
            "worker_seconds": config["worker_seconds"],
            "repeat_seeds": config["repeat_seeds"],
            "repeats_per_program_seed": config["repeats_per_program_seed"],
            "max_symbolic_summaries": config["max_symbolic_summaries"],
        },
        "private_data_used": False,
    }


def _atomic_new(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    requests = json.loads(args.requests.read_text())
    if not isinstance(requests, list):
        raise ValueError("requests_must_be_list")
    config = json.loads((HERE / "config.json").read_text())["pathfault_complete"]
    rows = [inventory(request, config) for request in requests]
    result = {
        "phase": config["phase"],
        "requests_sha256": hashlib.sha256(args.requests.read_bytes()).hexdigest(),
        "config": config,
        "rows": rows,
        "private_data_used": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _atomic_new(args.out, result)
    print(json.dumps({"cases": len(rows), "routes": dict(collections.Counter(row["route"] for row in rows))}))


if __name__ == "__main__":
    main()
