"""Evidence-based site candidates; public source only, no task execution or labels."""

from __future__ import annotations
import ast
import re
from .facts import literal
from .applicability import public_examples
from .roles import role_check

CONTEXT = {
    "py.branch-boundary-contract",
    "py.empty-singleton-shortcut",
    "py.index-out-of-bounds",
    "py.range-exclusive-stop",
    "py.negative-index-sentinel",
    "py.slice-boundary-normalization",
    "py.aggregation-scope",
    "py.first-occurrence-position",
    "py.empty-reduction-domain",
    "py.tie-break-selection",
}
CONDITIONAL = {
    "py.index-origin-domain",
    "py.quantifier-scope",
    "py.recursive-base-progress",
    "py.literal-classification-domain",
    "py.ascii-unicode-classification",
    "py.text-normalization-contract",
}


def function(a, node):
    p = node
    while p is not None:
        if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return p
        p = a.parent.get(p)
    return None


def parameters(a, node):
    f = function(a, node)
    return (
        set()
        if f is None
        else {x.arg for x in [*f.args.posonlyargs, *f.args.args, *f.args.kwonlyargs]}
    )


def decision(a, node):
    p = node
    while p is not None and not isinstance(
        p, (ast.FunctionDef, ast.AsyncFunctionDef, ast.For, ast.While)
    ):
        if isinstance(p, (ast.If, ast.IfExp)):
            return p
        p = a.parent.get(p)
    return None


def length_test(a, node):
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return None
    left, right = node.left, node.comparators[0]
    if (
        isinstance(left, ast.Call)
        and a.api(left) == "len"
        and len(left.args) == 1
        and isinstance(left.args[0], ast.Name)
        and type(literal(right)) is int
    ):
        return left.args[0].id, type(node.ops[0]).__name__, literal(right)
    return None


def guarded_input(a, node):
    shape = length_test(a, node)
    if shape:
        return shape
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.Not)
        and isinstance(node.operand, ast.Name)
    ):
        return node.operand.id, "Eq", 0
    return None


def direct_return(body):
    return body[0].value if len(body) == 1 and isinstance(body[0], ast.Return) else None


def same(x, y):
    return ast.dump(x, include_attributes=False) == ast.dump(y, include_attributes=False)


def public_nonempty_input(spec):
    return bool(
        re.search(
            r"(?:given|input|takes|supplied|for)\b[^.!?\n]{0,70}?non[- ]empty (?:list|array|string|sequence|collection)",
            spec,
        )
    )


def minimum_length(spec):
    text = re.sub(r"\s+", " ", spec.lower())
    m = re.search(
        r"(?:length(?: is| of)? |of length )(?:at least|greater than or equal to) (\d+|one|two|three)",
        text,
    )
    if not m:
        return None
    v = m.group(1)
    return {"one": 1, "two": 2, "three": 3}.get(v, int(v) if v.isdigit() else None)


def neutral_shape(a, node):
    """Verified identities or explicit public minimum requirements, scoped to guard."""
    d = decision(a, node)
    if not isinstance(d, ast.If):
        return None
    shape = guarded_input(a, d.test)
    if shape is None:
        return None
    name, op, n = shape
    spec = a.spec(node).lower()
    params = parameters(a, node)
    if name not in params:
        return None
    ret = direct_return(d.body)
    value = literal(ret)
    empty = (op == "Eq" and n == 0) or (op == "Lt" and n == 1) or (op == "LtE" and n == 0)
    requirement = minimum_length(spec)
    if empty and public_nonempty_input(spec):
        return "public_nonempty_domain"
    if requirement is not None and (
        op == "Lt" and n <= requirement or op == "LtE" and n < requirement
    ):
        if value is False or isinstance(d.body[0], ast.Raise):
            return "public_minimum_length_requirement"
    if (
        empty
        and value == 0
        and type(value) is not bool
        and re.search(r"\bsum\b|\bcount\b|number of", spec)
    ):
        return "empty_additive_identity"
    if (
        empty
        and isinstance(ret, ast.Constant)
        and ret.value is None
        and re.search(r"return\s+none\s+for\s+empty|empty.*return\s+none", spec)
    ):
        return "explicit_empty_none_policy"
    if empty and value is True and re.search(r"monotonic|palindrom|\bsorted\b", spec):
        return "empty_order_identity"
    if (
        op == "Eq"
        and n == 1
        and isinstance(ret, ast.Subscript)
        and isinstance(ret.value, ast.Name)
        and ret.value.id == name
        and literal(ret.slice) == 0
    ):
        if re.search(r"minimum|maximum|\bsum\b|\bmin\b|\bmax\b", spec) and not re.search(
            r"square|cube|power|magnitude|absolute|digit|sign", spec
        ):
            return "singleton_plain_reduction_identity"
    if empty and isinstance(ret, ast.Name) and ret.id != name and "prefix" in spec:
        f = function(a, node)
        if any(
            isinstance(c, ast.Call)
            and isinstance(c.func, ast.Attribute)
            and c.func.attr == "startswith"
            and c.args
            and isinstance(c.args[0], ast.Name)
            and c.args[0].id == name
            for c in ast.walk(f)
        ):
            return "all_strings_start_with_empty_prefix"
    return None


def loop_bound(a, sub):
    if not isinstance(sub, ast.Subscript) or not isinstance(sub.value, ast.Name):
        return None
    idx = sub.slice
    offset = 0
    if (
        isinstance(idx, ast.BinOp)
        and isinstance(idx.op, (ast.Add, ast.Sub))
        and type(literal(idx.right)) is int
    ):
        offset = literal(idx.right) * (1 if isinstance(idx.op, ast.Add) else -1)
        idx = idx.left
    if not isinstance(idx, ast.Name):
        return None
    p = a.parent.get(sub)
    while p is not None and p is not function(a, sub):
        if (
            isinstance(p, ast.For)
            and isinstance(p.target, ast.Name)
            and p.target.id == idx.id
            and isinstance(p.iter, ast.Call)
            and a.api(p.iter) == "range"
        ):
            args = p.iter.args
            if not 1 <= len(args) <= 2:
                return None
            start = 0 if len(args) == 1 else literal(args[0])
            stop = args[-1]
            delta = 0
            if type(start) is not int:
                return None
            if (
                isinstance(stop, ast.BinOp)
                and isinstance(stop.op, (ast.Sub, ast.Add))
                and type(literal(stop.right)) is int
            ):
                delta = literal(stop.right) * (1 if isinstance(stop.op, ast.Add) else -1)
                stop = stop.left
            if not (
                isinstance(stop, ast.Call)
                and a.api(stop) == "len"
                and len(stop.args) == 1
                and same(stop.args[0], sub.value)
            ):
                return None
            if any(
                isinstance(n, ast.Name)
                and n.id in {idx.id, sub.value.id}
                and isinstance(n.ctx, (ast.Store, ast.Del))
                and n is not p.target
                for statement in p.body
                for n in ast.walk(statement)
            ):
                return None
            if any(
                isinstance(n, (ast.Delete, ast.AugAssign))
                for statement in p.body
                for n in ast.walk(statement)
            ):
                return None
            if any(
                isinstance(n, ast.Call) and a.api(n) not in {"len"}
                for statement in p.body
                for n in ast.walk(statement)
            ):
                return None
            if any(
                isinstance(t, ast.Subscript)
                for statement in p.body
                for n in ast.walk(statement)
                if isinstance(n, (ast.Assign, ast.AnnAssign))
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target])
            ):
                return None
            return {
                "start": start,
                "offset": offset,
                "upper_relative_to_length": delta - 1 + offset,
                "loop": p,
            }
        p = a.parent.get(p)
    return None


def classify(a, cid, node):
    tier = 0 if cid in CONTEXT else 1 if cid in CONDITIONAL else 2
    notes = []
    benign = None
    spec = a.spec(node).lower()
    d = decision(a, node)
    if cid in {"py.empty-singleton-shortcut", "py.branch-boundary-contract"}:
        benign = neutral_shape(a, node)
        if isinstance(a.parent.get(node), ast.Assert):
            tier = 0
            notes.append("assertion is an input precondition, not evidence of a faulty decision")
        shape = guarded_input(a, node)
        if cid == "py.empty-singleton-shortcut" and shape:
            if shape[0] not in parameters(a, node):
                tier = 0
                notes.append("shape check is on internal state, not the public input")
            else:
                tier = max(tier, 1)
        if isinstance(d, ast.If) and direct_return(d.body) is not None:
            ret = direct_return(d.body)
            rv = literal(ret)
            if shape and shape[0] in parameters(a, node):
                if shape[2] == 0 and rv is False and re.search(r"bracket|parenthes|balanced", spec):
                    tier = 3
                    notes.append(
                        "empty balanced sequence is rejected despite no public nonempty requirement"
                    )
                elif not benign:
                    tier = max(tier, 1)
            # Explicit output bound, not a guessed expected value.
            if type(rv) in (int, float):
                bounds = re.findall(
                    r"(?:result|output|return value|(?:decimal|fractional|leftover) part)[^.!?\n]{0,100}?(?:smaller|less) than\s+(\d+)\b",
                    spec,
                )
                if any(rv >= int(b) for b in bounds):
                    tier = 3
                    notes.append("constant shortcut conflicts with explicit public upper bound")
            if (
                isinstance(d.test, ast.Compare)
                and len(d.test.ops) == 1
                and isinstance(d.test.left, ast.Name)
                and d.test.left.id in parameters(a, node)
                and literal(d.test.comparators[0]) in (0, 1)
            ):
                if (
                    isinstance(d.test.ops[0], (ast.Lt, ast.LtE))
                    and (
                        rv is False
                        or isinstance(rv, str)
                        and "invalid" in rv.lower()
                        or rv is None
                        and isinstance(ret, ast.Constant)
                    )
                    and re.search(r"total|count|number of", spec)
                    and not re.search(r"positive integer|positive number|greater than zero", spec)
                ):
                    tier = max(tier, 2)
                    notes.append(
                        "input count rejected below a positive threshold without public positivity requirement"
                    )
        if isinstance(d, ast.IfExp) and re.search(r"monotonic|increasing or decreasing", spec):
            tier = 3
            notes.append(
                "prefix comparison chooses a global ordering direction, including the equality branch"
            )
        if isinstance(node, ast.Compare) and any(
            type(literal(x)) is int and abs(literal(x)) >= 1000
            for x in [node.left, *node.comparators]
        ):
            if isinstance(d, ast.If) and (
                literal(direct_return(d.body)) is False
                or any(isinstance(x, ast.Raise) for x in d.body)
            ):
                constants = [
                    literal(x) for x in [node.left, *node.comparators] if type(literal(x)) is int
                ]
                # Requirement section only; dates in examples are not range requirements.
                requirements = re.split(r"\bexamples?\b|for example", spec)[0]
                if constants and not any(
                    re.search(r"(?<!\d)" + str(c) + r"(?!\d)", requirements) for c in constants
                ):
                    tier = 3
                    notes.append(
                        "large input-rejection bound has no corresponding stated requirement"
                    )
        if re.search(r"product of all signs|product.*sign", spec) and isinstance(d, ast.If):
            if any(
                isinstance(x, ast.Compare)
                and any(isinstance(op, ast.Lt) for op in x.ops)
                and literal(x.comparators[0]) == 0
                for x in ast.walk(d.test)
            ):
                ret = direct_return(d.body)
                parity = ret is not None and any(
                    isinstance(x, ast.Call)
                    and (a.api(x) == "len" or (a.api(x) or "").endswith("prod"))
                    or isinstance(x, ast.BinOp)
                    and isinstance(x.op, ast.Mod)
                    and literal(x.right) == 2
                    for x in ast.walk(ret)
                )
                fixed_sign_sum = (
                    isinstance(ret, ast.UnaryOp)
                    and isinstance(ret.operand, ast.Call)
                    and a.api(ret.operand) == "sum"
                )
                if fixed_sign_sum and not parity:
                    tier = 3
                    notes.append(
                        "all-negative fixed-sign sum ignores the parity of the sign product"
                    )
    if cid == "py.index-out-of-bounds" and isinstance(node, ast.Subscript):
        bound = loop_bound(a, node)
        if bound and bound["upper_relative_to_length"] >= 0:
            tier = 3
            notes.append(
                "loop index plus offset can reach or exceed sequence length at its last iteration"
            )
        elif (
            isinstance(node.slice, ast.Call)
            and a.api(node.slice) == "len"
            and node.slice.args
            and same(node.value, node.slice.args[0])
        ):
            tier = 3
            notes.append("index equals receiver length")
    if cid == "py.negative-index-sentinel" and isinstance(node, ast.Subscript):
        bound = loop_bound(a, node)
        if bound and bound["start"] + bound["offset"] >= 0:
            benign = "loop_lower_bound_prevents_negative_offset"
        if (
            isinstance(node.slice, ast.BinOp)
            and isinstance(node.slice.op, ast.Sub)
            and literal(node.slice.right) == 1
            and isinstance(node.slice.left, ast.Name)
        ):
            name = node.slice.left.id
            initials = [
                s
                for s in a.assignments.get((a.scope(node), name), [])
                if isinstance(s, (ast.Assign, ast.AnnAssign)) and literal(s.value) == 0
            ]
            if initials and any(isinstance(p, ast.Return) for p in ancestors(a, node)):
                tier = 3
                notes.append(
                    "zero-initialized state is consumed as index minus one after conditional updates"
                )
    if (
        cid == "py.first-occurrence-position"
        and isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    ):
        if re.search(r"(?:smallest|first|lowest) index|index.*first occurrence", spec):
            if node.args and isinstance(node.args[0], ast.Name):
                definition = a.stable_definition(node.args[0], node.args[0].id)
                value = definition.value if definition else None
                if (
                    isinstance(value, ast.Call)
                    and a.api(value) in {"min", "max"}
                    and len(value.args) == 1
                    and same(node.func.value, value.args[0])
                    and isinstance(node.func.value, ast.Name)
                    and a.value_unchanged(
                        node.func.value.id,
                        (definition.end_lineno, definition.end_col_offset),
                        (node.lineno, node.col_offset),
                        a.scope(node),
                    )
                ):
                    benign = "first_position_of_selected_extremum_matches_tie_contract"
        if any(
            isinstance(p, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.For))
            for p in ancestors(a, node)
        ):
            tier = max(tier, 2)
            notes.append(
                "first-index lookup inside value iteration can confuse repeated occurrences"
            )
    if (
        cid == "py.index-origin-domain"
        and isinstance(node, ast.Call)
        and a.api(node) == "enumerate"
    ):
        tier = 0
        notes.append("standard enumerate origin alone does not establish an index-domain mismatch")
    if cid == "py.first-match-vs-optimum":
        loop = next((p for p in ancestors(a, node) if isinstance(p, ast.For)), None)
        targets = (
            {x.id for x in ast.walk(loop.target) if isinstance(x, ast.Name)} if loop else set()
        )
        ret = node.value if isinstance(node, ast.Return) else node
        uses_target = bool(targets & {x.id for x in ast.walk(ret) if isinstance(x, ast.Name)})
        tier = 3 if uses_target else 1
        notes.append(
            "early qualifying loop item must match the global optimum"
            if uses_target
            else "return is not a direct qualifying item; early-return mismatch is unproven"
        )
        if isinstance(ret, ast.Call) and a.api(ret) in {"min", "max"}:
            benign = "global_extremum_computed_at_return"
        if loop and isinstance(loop.iter, ast.Call) and a.api(loop.iter) == "sorted":
            reverse = next(
                (literal(kw.value) for kw in loop.iter.keywords if kw.arg == "reverse"), False
            )
            keyed = any(kw.arg == "key" for kw in loop.iter.keywords)
            matching = (not reverse and bool(re.search(r"smallest|minimum|closest", spec))) or (
                reverse is True and bool(re.search(r"largest|maximum|biggest", spec))
            )
            if not keyed and matching:
                benign = "ordered_iteration_already_supports_first_optimum"
            else:
                tier = 1
                notes.append("sorted iteration requires key/direction review")
    if cid == "py.text-normalization-contract":
        if re.search(
            r"flip.*case|case[- ]insensitive|ignore.*case|convert.*lowercase|convert.*uppercase",
            spec,
        ):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"lower", "upper", "casefold"}
            ):
                tier = 0
                notes.append(
                    "case transformation is requested; operation presence alone is not a preservation fault"
                )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"lower", "upper", "casefold", "strip", "lstrip", "rstrip"}
        ):
            tier = 2
            notes.append(
                "input normalization changes text before an output or decision; contract preservation must be checked"
            )
    if cid == "py.unicode-text-byte-domain":
        if re.search(r"\bbytes?\b|encoded length", spec):
            tier = 1
        elif re.search(r"character|distinct|\bstring\b", spec):
            tier = 3
            notes.append("encoded bytes feed a requirement stated in the character domain")
    if cid == "py.presence-frequency-confusion" and isinstance(node, ast.Compare):
        if isinstance(d, ast.If) and any(isinstance(x, ast.Delete) for x in ast.walk(d)):
            tier = 3
            notes.append(
                "membership-only state is destructively consumed during an occurrence-sensitive calculation"
            )
        elif isinstance(d, ast.If) and any(
            isinstance(x, ast.Assign) and isinstance(t, ast.Subscript)
            for x in ast.walk(d)
            for t in (x.targets if isinstance(x, ast.Assign) else [])
        ):
            tier = 0
            notes.append("membership only guards construction of a first-occurrence table")
    if cid == "py.range-exclusive-stop" and "prime" in spec:
        tier = 0
        notes.append("not testing a number as its own divisor is correct")
    if cid == "py.empty-reduction-domain" and public_nonempty_input(spec):
        if (
            isinstance(node, ast.Call)
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in parameters(a, node)
        ):
            benign = "public_nonempty_reduction_domain"
    if (
        cid in {"py.quantifier-scope", "py.aggregation-scope"}
        and isinstance(node, ast.Call)
        and a.api(node) == "sum"
    ):
        if (
            re.search(r"at any point|at that point|prefix|running balance", spec)
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in parameters(a, node)
        ):
            tier = 3
            notes.append(
                "whole-input sum is observed where the public requirement concerns an intermediate prefix"
            )
    if cid == "py.branch-boundary-contract" and isinstance(node, ast.Compare):
        # A sequence placeholder must not be used as a value-based input filter.
        for operand in [node.left, *node.comparators]:
            if not isinstance(operand, ast.Subscript) or not isinstance(operand.value, ast.Name):
                continue
            seq = operand.value.id
            constants = [
                literal(x) for x in [node.left, *node.comparators] if isinstance(x, ast.Constant)
            ]
            for c in constants:
                if type(c) not in (int, float, str):
                    continue
                if c == 0 and re.search(r"positive (?:integer|number)", spec):
                    continue
                f = function(a, node)
                inserted = any(
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == seq
                    and call.func.attr in {"insert", "append"}
                    and call.args
                    and literal(call.args[-1]) == c
                    and call.lineno < node.lineno
                    for call in ast.walk(f)
                )
                if inserted and "between" in spec and not re.search(r"ignore|discard|remove", spec):
                    tier = 3
                    notes.append("inserted placeholder is also treated as a forbidden input value")
        if isinstance(d, ast.If) and re.search(
            r"odd digits|hasn.t any even digit|no even digit", spec
        ):
            if any(
                type(literal(x)) is int and literal(x) == 10 for x in [node.left, *node.comparators]
            ) and any(
                isinstance(x, ast.Call)
                and isinstance(x.func, ast.Attribute)
                and x.func.attr == "append"
                for x in d.body
                if isinstance(x, ast.Expr)
                for x in [x.value]
            ):
                tier = 3
                notes.append(
                    "single-digit shortcut appends without checking the required digit parity"
                )
    if cid == "py.signed-modulo-domain":
        tier = 1
        if re.search(r"positive (?:integer|number)", spec):
            tier = 0
            notes.append("public positive domain does not establish a signed-remainder mismatch")
        if re.search(r"(?<!non-)(?<!non )\bnegative\b|last digit|unit digit", spec):
            tier = 2
        p = a.parent.get(node)
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Mod)
            and isinstance(p, ast.Compare)
            and len(p.ops) == 1
            and isinstance(p.ops[0], (ast.Eq, ast.NotEq))
            and any(literal(x) == 0 for x in [p.left, *p.comparators] if x is not node)
        ):
            benign = "zero_remainder_divisibility_is_sign_invariant"
    if (
        cid == "py.text-normalization-contract"
        and isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    ):
        if node.func.attr == "replace":
            tier = 2
            notes.append(
                "literal replacement changes source content before required output construction"
            )
        if (
            node.func.attr in {"lower", "upper", "casefold"}
            and isinstance(a.parent.get(node), ast.Compare)
            and re.search(r"vowel|consonant", spec)
            and "case sensitive" not in spec
        ):
            if not re.search(
                r"upper[- ]?case.*vowel|vowel.*upper[- ]?case|lower[- ]?case.*vowel|vowel.*lower[- ]?case",
                spec,
            ):
                tier = 0
                notes.append(
                    "normalization is used for character classification; a case-sensitive contract mismatch is not established"
                )
    if cid == "py.first-occurrence-position" and isinstance(node, ast.Compare):
        loop = next((p for p in ancestors(a, node) if isinstance(p, ast.For)), None)
        if loop and isinstance(loop.target, ast.Name) and isinstance(loop.iter, ast.Name):
            values = [node.left, *node.comparators]
            current = any(isinstance(x, ast.Name) and x.id == loop.target.id for x in values)
            last = any(
                isinstance(x, ast.Subscript)
                and isinstance(x.value, ast.Name)
                and x.value.id == loop.iter.id
                and literal(x.slice) == -1
                for x in values
            )
            if (
                current
                and last
                and re.search(r"end|last|position", spec)
                and not re.search(r"\bunique\b|\bdistinct\b", spec)
            ):
                tier = 3
                notes.append(
                    "equality to the last element value does not identify the current iteration position"
                )
    if (
        cid == "py.aggregation-scope"
        and isinstance(node, ast.Call)
        and a.api(node) == "len"
        and node.args
    ):
        value = node.args[0]
        if isinstance(value, ast.Call) and a.api(value) == "set" and value.args:
            value = value.args[0]
        if (
            isinstance(value, ast.Name)
            and value.id in parameters(a, node)
            and re.search(r"list.*strings", spec, re.S)
            and re.search(r"total.*(?:char|character)", spec, re.S)
        ):
            tier = 3
            notes.append("list/set cardinality is measured where total character count is required")
    if cid == "py.first-match-vs-optimum":
        loop = next((p for p in ancestors(a, node) if isinstance(p, ast.For)), None)
        if loop and isinstance(loop.iter, ast.Call):
            right = bool(re.search(r"from the right|right side|rightmost", spec))
            left = bool(re.search(r"from the left|left side|leftmost", spec))
            backwards = (
                a.api(loop.iter) == "reversed"
                or a.api(loop.iter) == "range"
                and len(loop.iter.args) == 3
                and type(literal(loop.iter.args[2])) is int
                and literal(loop.iter.args[2]) < 0
            )
            forwards = a.api(loop.iter) == "range" and (
                len(loop.iter.args) < 3 or literal(loop.iter.args[2]) == 1
            )
            if right and backwards or left and forwards:
                benign = "scan_direction_matches_positional_optimum"
    if cid == "py.literal-classification-domain" and re.search(r"vowel", spec):
        table, folded = classification_table(a, node)
        if table and len(table) >= 3 and table <= set("aeiouAEIOUyY"):
            expected = (
                set("AEIOU") if re.search(r"upper[- ]?case", spec) and not folded else set("aeiou")
            )
            f = function(a, node)
            upper_example = any(
                e["function"] == getattr(f, "name", None)
                and isinstance(e["expected"], str)
                and any(c in "AEIOU" for c in e["expected"])
                for e in public_examples(a.spec(node))
            )
            if upper_example and not folded:
                expected |= set("AEIOU")
            if expected - table:
                tier = 3
                notes.append(
                    "literal vowel class omits characters required by the public definition/example"
                )
            elif (
                set("aeiouAEIOU") == table
                and not re.search(r"upper[- ]?case.*vowel|vowel.*upper[- ]?case", spec)
            ) or (
                folded
                and set("aeiou") <= table
                and not re.search(r"upper[- ]?case.*vowel|vowel.*upper[- ]?case", spec)
            ):
                benign = "complete_case_appropriate_vowel_table"
    if (
        cid == "py.empty-reduction-domain"
        and isinstance(node, ast.Call)
        and node.args
        and isinstance(node.args[0], ast.Name)
    ):
        arg = node.args[0]
        if arg.id not in parameters(a, node):
            definition = a.stable_definition(arg, arg.id)
            value = definition.value if definition else None
            empty_possible = (
                isinstance(value, ast.List)
                and not value.elts
                or isinstance(value, ast.ListComp)
                and any(g.ifs for g in value.generators)
            )
            if empty_possible and not a.guarded_nonempty(arg.id, node):
                tier = 3
                notes.append(
                    "internal eligible collection is reduced without proving that it contains any element"
                )
    if (
        cid == "py.numeric-cast-loss"
        and isinstance(node, ast.Call)
        and a.api(node) == "int"
        and node.args
    ):
        if (
            isinstance(node.args[0], ast.BinOp)
            and isinstance(node.args[0].op, ast.Pow)
            and literal(node.args[0].right) == 0.5
            and "prime" in spec
        ):
            if any(isinstance(p, ast.Call) and a.api(p) == "range" for p in ancestors(a, node)):
                benign = "floor_square_root_is_a_primality_loop_bound"
    if (
        cid == "py.index-origin-domain"
        and isinstance(node, ast.Call)
        and a.api(node) == "range"
        and len(node.args) == 3
        and literal(node.args[2]) == 2
    ):
        if isinstance(node.args[0], ast.Name) and re.search(r"\beven\b|\bodd\b", spec):
            tier = 3
            notes.append(
                "stride-two iteration inherits starting-value parity rather than ensuring the public parity requirement"
            )
    shape = guarded_input(a, node)
    if cid == "py.empty-singleton-shortcut" and shape and isinstance(d, ast.If):
        name, op, n = shape
        ret = direct_return(d.body)
        if (
            n == 2
            and re.search(r"minimum.*sum.*sub[- ]?array", spec, re.S)
            and not re.search(r"positive|non[- ]negative", spec)
            and isinstance(ret, ast.Call)
            and a.api(ret) == "min"
        ):
            if not any(
                isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add) for x in ast.walk(ret)
            ):
                tier = 3
                notes.append("two-element subarray shortcut omits the eligible full-pair sum")
        if (
            n == 1
            and isinstance(ret, ast.Subscript)
            and isinstance(ret.value, ast.Name)
            and ret.value.id == name
            and literal(ret.slice) == 0
            and "square" in spec
        ):
            tier = 3
            notes.append(
                "singleton raw element bypasses the required square transformation at index zero"
            )
        if (
            re.search(r"mean absolute deviation", spec)
            and op == "Lt"
            and n == 2
            and any(isinstance(x, ast.Raise) for x in d.body)
        ):
            tier = 3
            notes.append(
                "singleton mean absolute deviation is zero, so rejecting length one needs a public restriction"
            )
        if (
            n == 1
            and literal(ret) is True
            and re.search(r"weight", spec)
            and re.search(r"\bsum\b", spec)
        ):
            tier = 3
            notes.append("singleton truth shortcut omits the independent public weight constraint")
    if cid == "py.quantifier-scope" and re.search(r"palindrom", spec):
        f = function(a, node)
        recursive = any(
            isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == f.name
            for x in ast.walk(f)
        )
        if not recursive and not any(
            isinstance(x, (ast.For, ast.While, ast.ListComp, ast.GeneratorExp)) for x in ast.walk(f)
        ):
            if any(
                isinstance(x, ast.Compare)
                and len(x.ops) == 1
                and isinstance(x.ops[0], ast.Eq)
                and isinstance(x.left, ast.Subscript)
                and any(
                    isinstance(y, ast.Subscript)
                    and same(y.value, x.left.value)
                    and {literal(y.slice), literal(x.left.slice)} == {0, -1}
                    for y in x.comparators
                )
                for x in ast.walk(f)
            ):
                tier = 3
                notes.append("endpoint equality alone does not establish all mirrored pairs")
    role = role_check(a, cid, node, spec)
    if role["benign_binding"]:
        benign = role["benign_binding"]
    if role.get("promote_tier") is not None:
        tier = max(tier, role["promote_tier"])
        notes.append("builtin tie-to-even rounding conflicts with explicit away-from-zero policy")
    if role["cap_tier"] is not None:
        tier = min(tier, role["cap_tier"])
        notes.append("operation role does not establish the required semantic mismatch")
    return {
        "tier": tier,
        "reasons": notes
        or [
            "mechanism-specific structural risk"
            if tier >= 2
            else "operation present; actual contract mismatch remains unverified"
        ],
        "benign_binding": benign,
    }


def ancestors(a, node):
    p = a.parent.get(node)
    while p is not None and not isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
        yield p
        p = a.parent.get(p)


def classification_table(a, node):
    if not isinstance(node, ast.Compare):
        return None, False
    folded = (
        isinstance(node.left, ast.Call)
        and isinstance(node.left.func, ast.Attribute)
        and node.left.func.attr in {"lower", "casefold"}
    )
    for op, value in zip(node.ops, node.comparators):
        if not isinstance(op, (ast.In, ast.NotIn)):
            continue
        if isinstance(value, ast.Name):
            definition = a.stable_definition(value, value.id)
            value = definition.value if definition else None
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return set(value.value), folded
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)) and all(
            isinstance(x, ast.Constant) and isinstance(x.value, str) and len(x.value) == 1
            for x in value.elts
        ):
            return {x.value for x in value.elts}, folded
    return None, folded


def unique_domain(a, expr):
    if not isinstance(expr, ast.Call):
        return False
    if a.api(expr) in {"set", "range"}:
        return True
    if isinstance(expr.func, ast.Attribute) and expr.func.attr == "keys":
        value = expr.func.value
        if isinstance(value, ast.Name):
            definition = a.stable_definition(value, value.id)
            value = definition.value if definition else None
        return (
            isinstance(value, (ast.Dict, ast.DictComp))
            or isinstance(value, ast.Call)
            and a.api(value) == "dict"
        )
    return False


def supplemental(a):
    """Recognize syntax/relations missing from the copied v2 eligibility gate."""
    rows = []

    def add(cid, node, reason, priority=160, tier=3):
        f = a.fact(node)
        rows.append(
            {
                "concept_id": cid,
                "line": f["span"]["line"],
                "end_line": f["span"]["end_line"],
                "expression": f["expression"][:500],
                "fact_id": f["id"],
                "scope_id": f["scope_id"],
                "span": f["span"],
                "priority": priority,
                "reason": reason,
                "semantic_support": {"tier": tier, "reasons": [reason], "benign_binding": None},
            }
        )

    for node in a.nodes:
        spec = a.spec(node).lower()
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            chars = [
                literal(x)
                for x in operands
                if isinstance(x, ast.Constant) and isinstance(x.value, str)
            ]
            if (
                len(node.ops) >= 2
                and any(c in {"A", "Z", "a", "z"} for c in chars)
                and len(chars) >= 2
                and re.search(r"upper|lower|case|alphabet|letter", spec)
            ):
                english = bool(re.search(r"english|ascii", spec))
                add(
                    "py.ascii-unicode-classification",
                    node,
                    "Literal ASCII range chooses a narrower character class than Unicode case semantics.",
                    180,
                    1 if english else 3,
                )
            if isinstance(a.parent.get(node), ast.IfExp):
                add(
                    "py.branch-boundary-contract",
                    node,
                    "A conditional expression partitions inputs and sets derived state.",
                    120,
                    3 if "monotonic" in spec else 1,
                )
            if (
                any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops)
                and "sort" in spec
                and not re.search(r"unique|distinct|deduplic", spec)
            ):
                owner = next(
                    (
                        p
                        for p in ancestors(a, node)
                        if isinstance(p, (ast.ListComp, ast.GeneratorExp, ast.SetComp))
                    ),
                    None,
                )
                if owner is not None and any(unique_domain(a, g.iter) for g in owner.generators):
                    add(
                        "py.presence-frequency-confusion",
                        node,
                        "Iterating a unique domain and testing membership cannot preserve repeated elements required by sorting.",
                        200,
                    )
        if (
            isinstance(node, ast.BoolOp)
            and isinstance(node.op, ast.And)
            and "frequency" in spec
            and not re.search(r"neighbor|adjacent|local maximum", spec)
        ):
            compared = [x for x in ast.walk(node) if isinstance(x, ast.Compare)]
            if any(
                isinstance(x.left, ast.Subscript)
                and any(
                    isinstance(c, ast.Subscript) and same(c.value, x.left.value)
                    for c in x.comparators
                )
                for x in compared
            ):
                add(
                    "py.branch-boundary-contract",
                    node,
                    "Neighboring frequency buckets add a restriction beyond the stated self-frequency selection rule.",
                    190,
                )
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.BinOp)
            and isinstance(node.value.op, ast.Mult)
            and re.search(r"derivative|coefficients", spec)
        ):
            lhs, rhs = node.value.left, node.value.right
            if (
                isinstance(lhs, ast.Subscript)
                and isinstance(rhs, ast.Call)
                and a.api(rhs) == "len"
                and len(rhs.args) == 1
                and same(lhs.value, rhs.args[0])
            ):
                add(
                    "py.index-origin-domain",
                    node,
                    "Coefficient value is multiplied by sequence length; polynomial degree is indexed from zero.",
                    205,
                )
    return rows
