"""Operation-role checks: distinguish a mechanism from a merely related API."""

from __future__ import annotations
import ast
import re
from .facts import literal


def nearest_function(a, node):
    p = node
    while p is not None:
        if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return p
        p = a.parent.get(p)
    return None


def bool_name(a, node, name):
    fn = nearest_function(a, node)
    if fn is None:
        return False
    if name in {x.arg for x in [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]}:
        return False
    values = []
    for n in ast.walk(fn):
        if nearest_function(a, n) is not fn:
            continue
        if isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    values.append(n.value)
                elif (
                    isinstance(target, (ast.Tuple, ast.List))
                    and isinstance(n.value, (ast.Tuple, ast.List))
                    and len(target.elts) == len(n.value.elts)
                ):
                    values.extend(
                        v
                        for t, v in zip(target.elts, n.value.elts)
                        if isinstance(t, ast.Name) and t.id == name
                    )
        if (
            isinstance(n, (ast.AugAssign, ast.AnnAssign))
            and isinstance(n.target, ast.Name)
            and n.target.id == name
        ):
            values.append(n.value)
    return bool(values) and all(
        isinstance(v, ast.Constant) and type(v.value) is bool for v in values
    )


def numeric_position(a, node):
    if isinstance(node, ast.Name):
        d = a.stable_definition(node, node.id)
        node = d.value if d else node
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "index"
    ):
        return False
    receiver = node.func.value
    return isinstance(receiver, (ast.List, ast.Tuple)) or (
        isinstance(receiver, ast.Name) and a.sequence_domain(receiver.id, node) is not None
    )


def ordered_iterator(a, loop):
    expr = loop.iter
    reverse = False
    if isinstance(expr, ast.Name):
        d = a.stable_definition(expr, expr.id)
        expr = d.value if d else expr
    if (
        isinstance(expr, ast.Subscript)
        and isinstance(expr.slice, ast.Slice)
        and literal(expr.slice.step) == -1
    ):
        reverse = True
        expr = expr.value
    if (
        isinstance(expr, ast.Call)
        and a.api(expr) == "sorted"
        and not any(kw.arg == "key" for kw in expr.keywords)
    ):
        flag = next((literal(kw.value) for kw in expr.keywords if kw.arg == "reverse"), False)
        return "descending" if bool(flag) ^ reverse else "ascending"
    if isinstance(expr, ast.Call) and a.api(expr) == "range":
        step = literal(expr.args[2]) if len(expr.args) >= 3 else 1
        if type(step) is int and step != 0:
            return "ascending" if step > 0 else "descending"
    return None


def role_check(a, cid, node, spec):
    """Return exclusion/cap; never establish safety of the whole function."""
    reason = None
    cap = None
    fn = nearest_function(a, node)
    if cid == "py.late-bound-closure":
        loops = (
            [node]
            if isinstance(node, (ast.For, ast.comprehension))
            else list(node.generators)
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
            else []
        )
        targets = [x for loop in loops for x in ast.walk(loop.target) if isinstance(x, ast.Name)]
        closures = [
            x
            for x in ast.walk(node)
            if isinstance(x, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        captures = []
        for closure in closures:
            for ref in ast.walk(closure):
                if isinstance(ref, ast.Name) and isinstance(ref.ctx, ast.Load):
                    captures.extend(
                        (closure, ref)
                        for target in targets
                        if ref.id == target.id
                        and (
                            a.qname(ref) == a.qname(target)
                            if a.qname(ref) and a.qname(target)
                            else True
                        )
                    )
        if not captures:
            reason = "no_direct_capture_of_iteration_symbol"
        elif all(
            isinstance(a.parent.get(c), ast.Call) and a.parent[c].func is c for c, _ in captures
        ):
            reason = "capturing_lambda_is_invoked_before_loop_advances"
    if cid == "py.shortcircuit-boolean-result" and isinstance(node, ast.BoolOp):
        safe = all(
            isinstance(x, ast.Constant)
            and type(x.value) is bool
            or isinstance(x, ast.Name)
            and bool_name(a, x, x.id)
            or isinstance(x, ast.UnaryOp)
            and isinstance(x.op, ast.Not)
            for x in node.values
        )
        if safe:
            reason = "all_shortcircuit_operands_are_boolean_values"
    if cid == "py.set-order-loss" and isinstance(node, (ast.Call, ast.SetComp, ast.Set)):
        p = a.parent.get(node)
        if isinstance(p, ast.Call) and a.api(p) == "len":
            reason = "set_order_is_not_observed_by_length"
    if cid == "py.lexicographic-numeric-order" and isinstance(node, ast.Compare):
        if all(numeric_position(a, x) for x in [node.left, *node.comparators]):
            reason = "comparison_operands_are_numeric_positions"
    if (
        cid == "py.numeric-text-width"
        and isinstance(node, ast.Call)
        and a.api(node) == "int"
        and node.args
    ):
        arg = node.args[0]
        if (
            isinstance(arg, ast.Subscript)
            and not isinstance(arg.slice, ast.Slice)
            and isinstance(arg.value, ast.Name)
            and (a.sequence_domain(arg.value.id, node) or {}).get("domain") == "str"
        ):
            reason = "single_digit_parsing_does_not_discard_sequence_width"
        elif fn is not None and any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "zfill"
            for c in ast.walk(fn)
        ):
            cap = 1
            reason = None
    if cid == "py.unicode-text-byte-domain":
        if not re.search(r"count|distinct|length|number of", spec):
            cap = 0
    if cid == "py.numeric-cast-loss" and isinstance(node, ast.Call):
        api = a.api(node)
        if (
            api == "float"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.lower() in {"inf", "-inf", "infinity", "-infinity"}
        ):
            reason = "infinity_constant_is_an_extremum_identity"
        elif api == "int":
            child = node
            p = a.parent.get(node)
            while p is not None and p is not fn:
                if isinstance(p, ast.Call) and a.api(p) == "range":
                    reason = "integer_conversion_is_used_as_an_iteration_bound"
                    break
                if isinstance(p, ast.While) and child is p.test:
                    reason = "integer_conversion_is_used_as_an_iteration_bound"
                    break
                child = p
                p = a.parent.get(p)
            if re.search(
                r"closest integer|nearest integer|sum.*digits|digits.*sum", spec
            ) and not re.search(r"fraction|precision", spec):
                cap = 0
    if cid == "py.rounding-policy":
        cap = 1
        if re.search(r"round.*(?:decimal|places|zero)|closest integer|nearest integer", spec):
            cap = 0
        elif fn and any(isinstance(x, ast.Compare) for x in ast.walk(fn)):
            cap = 2
    if cid == "py.split-join-separator-loss":
        cap = 1
        if re.search(
            r"preserve.*(?:space|separator|delimiter)|keep.*(?:space|separator|delimiter)|consecutive spaces",
            spec,
        ):
            cap = 2
    if (
        cid == "py.text-normalization-contract"
        and isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    ):
        p = a.parent.get(node)
        if (
            isinstance(p, ast.Call)
            and a.api(p) in {"int", "float"}
            and re.search(r"number|decimal|comma", spec)
        ):
            cap = 0
        if (
            node.func.attr in {"strip", "lstrip", "rstrip"}
            and re.search(r"sentence|word", spec)
            and re.search(r"delimit|split", spec)
        ):
            cap = 0
        if node.func.attr == "replace" and re.search(r"separated.*(?:comma|space)|replac", spec):
            cap = 1
    if cid == "py.first-match-vs-optimum":
        p = a.parent.get(node)
        loop = None
        while p is not None and p is not fn:
            if isinstance(p, ast.For):
                loop = p
                break
            p = a.parent.get(p)
        if loop:
            order = ordered_iterator(a, loop)
            if (
                order == "descending"
                and re.search(r"largest|maximum|biggest", spec)
                or order == "ascending"
                and re.search(r"smallest|minimum", spec)
            ):
                reason = "known_iteration_order_already_selects_the_optimum"
            ret = node.value if isinstance(node, ast.Return) else node
            value = ret.elts[0] if isinstance(ret, (ast.Tuple, ast.List)) and ret.elts else ret
            if isinstance(value, ast.Name):
                d = a.stable_definition(value, value.id)
                if d and isinstance(d.value, ast.Call) and a.api(d.value) in {"min", "max"}:
                    reason = "selected_extremum_was_computed_before_index_scan"
    if cid == "py.extremum-initial-sentinel" and isinstance(node, ast.Compare):
        p = a.parent.get(node)
        if isinstance(p, ast.If):
            assignments = [x for x in p.body if isinstance(x, ast.Assign)]
            if assignments and all(
                isinstance(x.value, ast.Constant) and x.value.value == 0 for x in assignments
            ):
                reason = "reset_to_additive_identity_is_not_an_extremum_seed"
    promote = None
    if (
        cid == "py.rounding-policy"
        and isinstance(node, ast.Call)
        and a.api(node) == "round"
        and "away from zero" in spec
    ):
        child = node
        p = a.parent.get(child)
        non_tie = False
        while p is not None and p is not fn:
            if (
                isinstance(p, ast.If)
                and isinstance(p.test, ast.Compare)
                and len(p.test.ops) == 1
                and any(literal(x) == 0.5 for x in [p.test.left, *p.test.comparators])
            ):
                if (
                    isinstance(p.test.ops[0], ast.NotEq)
                    and child in p.body
                    or isinstance(p.test.ops[0], ast.Eq)
                    and child in p.orelse
                ):
                    non_tie = True
            child = p
            p = a.parent.get(p)
        if non_tie:
            reason = "bankers_round_only_runs_on_non_half_cases"
        else:
            cap = None
            promote = 3
    return {"benign_binding": reason, "cap_tier": cap, "promote_tier": promote}
