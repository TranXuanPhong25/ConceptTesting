"""Opt-in, bounded source receipts; never execute PUTs or infer NL intent."""
from __future__ import annotations

import ast
import copy
import textwrap

from ...call_builder import entry_function


COMPARISON = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
NEGATE = {"<": ">=", "<=": ">", ">": "<=", ">=": "<", "==": "!=", "!=": "=="}


def checked(context):
    return context.settings.grounding_mode == "checked"


def declared_scalar_types(context):
    """Only pure, conjunctive, top-level assertions; no inferred domain from samples."""
    names = {record.get("spec_name", record["name"]): record["name"]
             for record in context.input_types["parameters"]}
    if (set(names) | set(names.values())) & {"type", "isinstance", "int", "float", "str", "bool"}:
        return {}
    source = textwrap.dedent(context.contract)
    try:
        module = ast.parse(source)
    except SyntaxError:
        return {}
    if any(not isinstance(node, ast.Assert) for node in module.body):
        return {}
    allowed_calls = {"type", "isinstance", "all", "len", "set", "float"}
    if any(not isinstance(call.func, ast.Name) or call.func.id not in allowed_calls
           for call in ast.walk(module) if isinstance(call, ast.Call)):
        return {}
    result = {}

    def types(node):
        items = node.elts if isinstance(node, (ast.List, ast.Tuple)) else [node]
        if not all(isinstance(item, ast.Name) and item.id in ("int", "float", "str", "bool") for item in items):
            return None
        return [item.id for item in items]

    def visit(node):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            for item in node.values:
                visit(item)
        parameter = None
        kinds = None
        if (isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.Eq))
                and isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name)
                and node.left.func.id == "type" and len(node.left.args) == 1
                and isinstance(node.left.args[0], ast.Name)):
            parameter = node.left.args[0].id
            kinds = types(node.comparators[0])
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "isinstance"
                and len(node.args) == 2 and isinstance(node.args[0], ast.Name)):
            parameter = node.args[0].id
            kinds = types(node.args[1])
        if parameter in names and kinds:
            name = names[parameter]
            if name in result:
                kinds = sorted(set(kinds) & set(result[name]["types"]))
            result[name] = {"types": kinds, "source_quote": ast.get_source_segment(source, node),
                            "source": "recognized_contract_assertion"}

    for assertion in module.body:
        visit(assertion.test)
    return result


def source_facts(context):
    """Recognize a small side-effect-free subset and expose scope/polarity as data."""
    function = entry_function(context.program_source, context.entry_point)
    parameters = {record["name"] for record in context.input_types["parameters"]}
    strings = set()
    for record in context.input_types["parameters"]:
        if any(description["kind"] == "str" for evidence in record["evidence"] for description in evidence["types"]):
            strings.add(record["name"])
    module = ast.parse(context.program_source)
    nested_scopes = [node for node in ast.walk(function) if node is not function and
                     isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))]
    if nested_scopes or any(isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
                            for node in ast.walk(module)):
        return {"facts": [], "scope": "unknown_nested_scope_or_wildcard_import", "assumptions": []}
    shadowed = set(parameters)
    for node in ast.walk(module):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            shadowed.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            shadowed.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            shadowed.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
    # Mutated input bindings make these summaries unsafe; keep them unknown.
    changed_parameters = {node.id for node in ast.walk(function)
                          if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and node.id in parameters}
    if changed_parameters or any(isinstance(node, (ast.Global, ast.Nonlocal)) for node in ast.walk(function)):
        return {"facts": [], "scope": "unknown_mutated_bindings", "assumptions": []}
    facts = []

    def add(kind, node, **details):
        facts.append({"kind": kind, "code_quote": ast.get_source_segment(context.program_source, node),
                      "line": node.lineno, **details})

    def string_source(node):
        if isinstance(node, ast.Name) and node.id in strings:
            return node.id, "identity"
        if (isinstance(node, ast.Call) and not node.args and not node.keywords
                and isinstance(node.func, ast.Attribute) and node.func.attr in ("lower", "casefold", "upper")
                and isinstance(node.func.value, ast.Name) and node.func.value.id in strings):
            return node.func.value.id, node.func.attr
        return None

    for node in ast.walk(function):
        if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name)
                or node.func.id in shadowed or node.keywords):
            continue
        if node.func.id == "len" and len(node.args) == 1:
            value = node.args[0]
            if isinstance(value, ast.Name) and value.id in strings:
                add("quantity", node, parameter=value.id, measure="string_length", unit="code_points", scope="full")
            elif (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                  and value.func.attr == "encode" and isinstance(value.func.value, ast.Name)
                  and value.func.value.id in strings and len(value.args) <= 1 and not value.keywords
                  and (not value.args or isinstance(value.args[0], ast.Constant) and isinstance(value.args[0].value, str))):
                encoding = value.args[0].value if value.args else "utf-8"
                add("quantity", node, parameter=value.func.value.id, measure="encoded_length", unit="bytes",
                    encoding=encoding, scope="full", note="implementation measure; not intended behavior")
        elif node.func.id == "sum" and len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id in parameters:
            add("quantity", node, parameter=node.args[0].id, measure="sum", scope="full")

    # Direct string-element ord, with transformation retained explicitly.
    for loop in function.body:
        if not isinstance(loop, ast.For) or not isinstance(loop.target, ast.Name):
            continue
        string = string_source(loop.iter)
        if not string or "ord" in shadowed:
            continue
        aliases = {loop.target.id: {"parameter": string[0], "measure": "character", "transform": string[1]}}
        for statement in loop.body:
            assigned = {node.id for node in ast.walk(statement) if isinstance(node, ast.Name)
                        and isinstance(node.ctx, (ast.Store, ast.Del))}
            for name in assigned:
                aliases.pop(name, None)
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name) and isinstance(statement.value, ast.Call)
                    and isinstance(statement.value.func, ast.Name) and statement.value.func.id == "ord"
                    and len(statement.value.args) == 1 and not statement.value.keywords and isinstance(statement.value.args[0], ast.Name)
                    and statement.value.args[0].id == loop.target.id and loop.target.id in aliases):
                aliases[statement.targets[0].id] = {**aliases[loop.target.id], "measure": "code_point"}
                add("quantity", statement, **aliases[statement.targets[0].id], scope="each_transformed_character",
                    note="raw input code_point targets must be checked after this transform")
            for comparison in ast.walk(statement):
                if (isinstance(comparison, ast.Compare) and isinstance(comparison.left, ast.Name)
                        and comparison.left.id in aliases and len(comparison.ops) == 1
                        and aliases[comparison.left.id]["measure"] == "code_point"
                        and type(comparison.ops[0]) in COMPARISON
                        and isinstance(comparison.comparators[0], ast.Constant)
                        and type(comparison.comparators[0].value) is int):
                    add("code_point_transition", comparison, **aliases[comparison.left.id],
                        comparison=COMPARISON.get(type(comparison.ops[0])), threshold=comparison.comparators[0].value)

    # Top-level False returns: expose acceptance as a logical complement, under finite builtin numeric assumptions.
    for statement in function.body:
        if not (isinstance(statement, ast.If) and len(statement.body) == 1
                and isinstance(statement.body[0], ast.Return) and isinstance(statement.body[0].value, ast.Constant)
                and statement.body[0].value.value is False):
            continue
        comparisons = statement.test.values if isinstance(statement.test, ast.BoolOp) and isinstance(statement.test.op, ast.Or) else [statement.test]
        for comparison in comparisons:
            if (isinstance(comparison, ast.Compare) and len(comparison.ops) == 1 and isinstance(comparison.left, ast.Name)
                    and comparison.left.id in parameters and isinstance(comparison.comparators[0], ast.Constant)
                    and type(comparison.comparators[0].value) in (int, float)):
                symbol = COMPARISON.get(type(comparison.ops[0]))
                if symbol:
                    add("reject_predicate", comparison, parameter=comparison.left.id, threshold=comparison.comparators[0].value,
                        rejection_operator=symbol, acceptance_operator=NEGATE[symbol],
                        scope="necessary_condition_to_continue", note="does not prove overall acceptance or a spec match")

    # Simple acc=0; n=len(xs); for i in range(n): acc += xs[i]; if acc > limit:return False.
    initializers = {}
    safe_prelude = True
    for statement in function.body:
        prelude_before_statement = safe_prelude
        if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            safe_prelude = False
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            value = statement.value
            safe_value = (isinstance(value, ast.Constant) and type(value.value) in (int, float)) or (
                isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "len"
                and len(value.args) == 1 and isinstance(value.args[0], ast.Name)
                and value.args[0].id in parameters and not value.keywords)
            safe_prelude = safe_prelude and bool(safe_value) and statement.targets[0].id not in initializers
            initializers[statement.targets[0].id] = statement.value
        elif not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                  and isinstance(statement.value.value, str)) and not isinstance(statement, ast.For):
            safe_prelude = False
        if not (isinstance(statement, ast.For) and isinstance(statement.target, ast.Name)
                and isinstance(statement.iter, ast.Call) and isinstance(statement.iter.func, ast.Name)
                and statement.iter.func.id == "range" and "range" not in shadowed and "len" not in shadowed
                and len(statement.iter.args) == 1 and isinstance(statement.iter.args[0], ast.Name)
                and len(statement.body) >= 2):
            continue
        if not prelude_before_statement:
            continue
        length = initializers.get(statement.iter.args[0].id)
        if not (isinstance(length, ast.Call) and isinstance(length.func, ast.Name) and length.func.id == "len"
                and len(length.args) == 1 and isinstance(length.args[0], ast.Name) and length.args[0].id in parameters):
            continue
        update, guard = statement.body[:2]
        if any(not (isinstance(item, ast.If) and not item.orelse and len(item.body) == 1
                    and isinstance(item.body[0], ast.Return) and isinstance(item.body[0].value, ast.Constant)
                    and item.body[0].value.value is False) for item in statement.body[1:]):
            continue
        if not (isinstance(update, ast.AugAssign) and isinstance(update.target, ast.Name) and isinstance(update.op, ast.Add)
                and isinstance(update.value, ast.Subscript) and isinstance(update.value.value, ast.Name)
                and update.value.value.id == length.args[0].id and isinstance(update.value.slice, ast.Name)
                and update.value.slice.id == statement.target.id):
            continue
        accumulator = update.target.id
        initial = initializers.get(accumulator)
        writes = [node for node in ast.walk(statement) if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del))]
        if not (isinstance(initial, ast.Constant) and initial.value == 0
                and all(node.id in (accumulator, statement.target.id) for node in writes)
                and sum(node.id == accumulator for node in writes) == 1
                and sum(isinstance(node, ast.AugAssign) for node in ast.walk(statement)) == 1):
            continue
        if any(not isinstance(call.func, ast.Name) or call.func.id not in ("len", "range")
               for call in ast.walk(function) if isinstance(call, ast.Call)):
            continue
        # Side effects/nested control can invalidate a recurrence; reject rather than guess.
        if any(isinstance(node, (ast.Call, ast.Assign, ast.AnnAssign, ast.NamedExpr, ast.Delete, ast.For, ast.While,
                                 ast.Try, ast.With, ast.Yield, ast.YieldFrom))
               for body in statement.body for node in ast.walk(body)):
            continue
        if not (isinstance(guard, ast.If) and len(guard.body) == 1 and isinstance(guard.body[0], ast.Return)
                and isinstance(guard.body[0].value, ast.Constant) and guard.body[0].value.value is False
                and isinstance(guard.test, ast.Compare) and len(guard.test.ops) == 1
                and isinstance(guard.test.ops[0], ast.Gt) and isinstance(guard.test.left, ast.Name)
                and guard.test.left.id == accumulator and isinstance(guard.test.comparators[0], ast.Name)
                and guard.test.comparators[0].id in parameters):
            continue
        add("prefix_sum_rejection", guard, parameter=length.args[0].id,
            limit_parameter=guard.test.comparators[0].id, accumulator=accumulator,
            measure="sum", scope="visited_prefix", comparison=">", polarity="reject",
            note="full sum may later decrease; not an operator mismatch with full-sum acceptance <=")
    return {"facts": facts, "scope": "bounded_recognized_syntax_only",
            "assumptions": ["builtin operations on declared/observed builtin types; no custom overloads",
                            "implementation facts locate tests; they do not establish NL intended behavior"]}


def enrich_guidance(context, guidance):
    result = copy.deepcopy(guidance)
    result["implementation_receipts"] = source_facts(context)
    result["type_receipts"] = declared_scalar_types(context)
    return result


def context_goals(context):
    goals = []
    facts = context.guidance.get("implementation_receipts", {}).get("facts", [])
    for boundary in context.selection["boundaries"]:
        characteristic = boundary["characteristic"]
        for fact in facts:
            if fact.get("parameter") != characteristic["parameter"]:
                continue
            if (fact["kind"] == "quantity" and fact.get("measure") == "encoded_length"
                    and fact.get("encoding", "").lower().replace("_", "-") in ("utf-8", "utf8")
                    and characteristic["operation"] in ("length", "code_point")):
                goals.append({"boundary_id": boundary["id"], "property": "non_ascii",
                              "parameter": characteristic["parameter"],
                              "reason": "distinguish code-point length from encoded byte length; empty/ASCII cannot distinguish them"})
            if fact["kind"] == "prefix_sum_rejection" and characteristic["operation"] == "sum":
                goals.append({"boundary_id": boundary["id"], "property": "prefix_exceeds_limit",
                              "parameter": fact["parameter"], "limit_parameter": fact["limit_parameter"],
                              "reason": "request a proper prefix > limit while total <= limit, if domain permits; preserve other reach conditions"})
    return goals


def goal_coverage(goals, inputs, signature):
    from .context_requirements import validate_context_requirements
    rows = []
    for goal in goals:
        requirement = {key: goal[key] for key in ("parameter", "property", "limit_parameter") if key in goal}
        covered = []
        for index, record in enumerate(inputs):
            if record.get("boundary_id") != goal["boundary_id"]:
                continue
            bound = signature.bind(*ast.literal_eval(record["args"]), **ast.literal_eval(record["kwargs"]))
            bound.apply_defaults()
            try:
                validate_context_requirements([requirement], bound.arguments)
                covered.append(index)
            except ValueError:
                continue
        rows.append({**goal, "input_indices": covered, "status": "covered" if covered else "unmet",
                     "meaning": "context property only; no NL entailment or bug verdict"})
    return rows


def audit_boundary(boundary, guidance):
    """Diagnose supported inconsistencies without rewriting/rejecting a model claim."""
    findings = []
    expression = boundary["characteristic"]
    threshold = boundary["threshold"]
    facts = guidance.get("implementation_receipts", {}).get("facts", [])
    quote = " ".join(boundary.get("code_quote", "").split())
    for fact in facts:
        if fact.get("parameter") != expression["parameter"]:
            continue
        if (fact["kind"] == "reject_predicate" and threshold.get("kind") == "constant"
                and threshold["value"] == fact["threshold"] and expression["operation"] == "value"
                and boundary["comparison"] == fact["acceptance_operator"] and quote
                and " ".join(fact["code_quote"].split()) in quote and boundary.get("alignment") == "operator"):
            findings.append({"kind": "complementary_reject_not_operator_mismatch", "receipt": fact,
                             "scope": "this comparison only, not whole-program correctness"})
        if fact["kind"] == "prefix_sum_rejection" and expression["operation"] == "sum":
            findings.append({"kind": "full_vs_prefix_quantity", "receipt": fact,
                             "scope": "alignment requires a scope check; a sign comparison alone is insufficient"})
        if (fact["kind"] == "code_point_transition" and expression["operation"] == "length"
                and threshold.get("value") == fact["threshold"]):
            findings.append({"kind": "codepoint_threshold_bound_to_length", "receipt": fact,
                             "scope": "same constant is not binding evidence; intent unknown"})
    return findings
