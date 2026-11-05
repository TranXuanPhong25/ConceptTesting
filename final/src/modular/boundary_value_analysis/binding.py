"""Bounded public-guard hints and necessary-domain checks; no PUT execution."""
from __future__ import annotations

import ast
import math
import operator
import re
import textwrap

from .characteristics import characteristic_values, number
from .string_guidance import derive_string_guidance


COMPARISONS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge,
               "==": operator.eq, "!=": operator.ne}
AST_COMPARISONS = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
REVERSE = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!="}


def expression_key(expression):
    return (expression.get("parameter"), expression.get("operation"), expression.get("token"))


class BoundaryGuidance:
    name = "public_guards"

    def run(self, context):
        self.templates = context.templates["candidates"]
        self.by_key = {expression_key(item["characteristic"]): item for item in self.templates}
        self.names = {record.get("spec_name", record["name"]): record["name"]
                      for record in context.input_types["parameters"]}
        self.guards = []
        self.tainted_names = set()
        source = textwrap.dedent(context.contract)
        try:
            syntax = ast.parse(source)
        except SyntaxError:
            syntax = None
        if syntax is not None:
            for node in syntax.body:
                pure_calls = {"all", "len", "min", "max", "sum", "type", "isinstance", "abs", "int", "float", "str"}
                calls = [child for child in ast.walk(node) if isinstance(child, ast.Call)]
                for call in calls:
                    if not isinstance(call.func, ast.Name) or call.func.id not in pure_calls:
                        referenced = {child.id for child in ast.walk(call)
                                      if isinstance(child, ast.Name) and child.id in self.names}
                        self.tainted_names.update(referenced or self.names)
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)) and child.id in self.names:
                        self.tainted_names.add(child.id)
                if isinstance(node, ast.Assert):
                    self.visit_constraint(node.test, {}, source)
        self.spec_hints(context.specification)
        string_guidance = derive_string_guidance(context, self.names)
        self.guards.extend(string_guidance["candidate_guards"])
        return {"domain_guards": [guard for guard in self.guards if guard["origin"] == "contract"
                                   or guard.get("necessary_domain")],
                "candidate_guards": self.guards,
                "projection_evidence": string_guidance["projection_evidence"],
                "domain_status": "recognized-necessary-clauses-only;not-complete-contract"}

    def expression(self, node, aliases):
        if isinstance(node, ast.Name):
            if node.id in self.tainted_names:
                return None
            if node.id in aliases:
                return aliases[node.id]
            if node.id in self.names:
                return {"parameter": self.names[node.id], "operation": "value"}
        if isinstance(node, (ast.Constant, ast.UnaryOp)):
            try:
                value = ast.literal_eval(node)
                if number(value):
                    return {"kind": "constant", "value": value}
            except (ValueError, TypeError):
                pass
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1
                and isinstance(node.args[0], ast.Name) and node.args[0].id in self.names
                and node.args[0].id not in self.tainted_names):
            operation = {"len": "length", "sum": "sum", "min": "minimum", "max": "maximum"}.get(node.func.id)
            if operation:
                return {"parameter": self.names[node.args[0].id], "operation": operation}
        return None

    def emit(self, left, comparison, right, quote, origin, *, necessary_domain=False):
        if left is None or right is None:
            return
        if left.get("kind") == "constant":
            left, right = right, left
            comparison = REVERSE[comparison]
        if (left.get("operation") == "maximum" and right.get("operation") == "minimum"
                and left["parameter"] == right["parameter"]):
            left = {"parameter": left["parameter"], "operation": "range"}
            right = {"kind": "constant", "value": 0}
        template = self.by_key.get(expression_key(left))
        if template is None:
            return
        if right.get("kind") == "constant":
            threshold = right
        elif expression_key(right) in self.by_key and right["operation"] != "elements":
            threshold = {"kind": "expression", **right}
        else:
            return
        guard = {"template_id": template["id"], "characteristic": left,
                 "comparison": comparison, "threshold": threshold, "source_quote": quote,
                 "origin": origin, "necessary_domain": necessary_domain}
        if guard not in self.guards:
            self.guards.append(guard)

    def visit_constraint(self, node, aliases, source):
        # Only conjunctions/universal all() yield necessary clauses. Never flatten OR.
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            for value in node.values:
                self.visit_constraint(value, aliases, source)
        elif isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            for left, comparison, right in zip(operands, node.ops, operands[1:]):
                symbol = AST_COMPARISONS.get(type(comparison))
                if symbol:
                    self.emit(self.expression(left, aliases), symbol, self.expression(right, aliases),
                              ast.get_source_segment(source, node), "contract", necessary_domain=True)
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "all"
              and len(node.args) == 1 and isinstance(node.args[0], (ast.GeneratorExp, ast.ListComp))):
            generator = node.args[0]
            if len(generator.generators) != 1:
                return
            loop = generator.generators[0]
            if (loop.ifs or not isinstance(loop.target, ast.Name) or not isinstance(loop.iter, ast.Name)
                    or loop.iter.id not in self.names or loop.iter.id in self.tainted_names):
                return
            expression = {"parameter": self.names[loop.iter.id], "operation": "elements"}
            if expression_key(expression) in self.by_key:
                self.visit_constraint(generator.elt, {**aliases, loop.target.id: expression}, source)

    def spec_hints(self, specification):
        elements = [item for item in self.templates if item["characteristic"]["operation"] == "elements"]
        lengths = [item for item in self.templates if item["characteristic"]["operation"] == "length"]
        if len(elements) == 1:
            feature = elements[0]["characteristic"]
            match = re.search(r"(?:return|keep|select)\s+only\s+positive\s+numbers", specification, re.I)
            if match:
                self.emit(feature, ">", {"kind": "constant", "value": 0}, match.group(), "spec")
            for match in re.finditer(r"greater\s+than\s+(-?\d+(?:\.\d+)?)", specification, re.I):
                value = float(match.group(1)) if "." in match.group(1) else int(match.group(1))
                self.emit(feature, ">", {"kind": "constant", "value": value}, match.group(), "spec")
            for original_name, name in self.names.items():
                match = re.search(r"below\s+threshold\s+" + re.escape(original_name) + r"\b", specification, re.I)
                maximum = {"parameter": feature["parameter"], "operation": "maximum"}
                if match and expression_key(maximum) in self.by_key:
                    self.emit(maximum, "<", {"parameter": name, "operation": "value"}, match.group(), "spec")
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        if len(lengths) == 1:
            match = re.search(r"at\s+least\s+(\d+|one|two|three|four|five)\s+(?:elements|items|characters)", specification, re.I)
            if match:
                token = match.group(1).lower()
                value = int(token) if token.isdigit() else words[token]
                prefix = specification[max(0, match.start() - 160):match.start()]
                clause = re.split(r"[.\n]", prefix)[-1].lower()
                conditional = re.search(r"\b(if|whether|when)\b|return\s+true", clause)
                declared = re.search(r"\bgiven\b|\binput\b|\bmust\s+have\b|\bhas\s*$", clause)
                necessary = conditional is None and declared is not None
                self.emit(lengths[0]["characteristic"], ">=", {"kind": "constant", "value": value},
                          match.group(), "spec", necessary_domain=necessary)
        match = re.search(r"more\s+than\s+(\d+)\s+consecutive\s+spaces", specification, re.I)
        if match:
            for item in self.templates:
                if item["characteristic"]["operation"] == "run_length":
                    expression = {**item["characteristic"], "token": " "}
                    guard = {"template_id": item["id"], "characteristic": expression, "comparison": ">",
                             "threshold": {"kind": "constant", "value": int(match.group(1))},
                             "source_quote": match.group(), "origin": "spec", "necessary_domain": False}
                    self.guards.append(guard)


def same_domain_boundary(boundary, guard):
    if expression_key(boundary["characteristic"]) != expression_key(guard["characteristic"]):
        return False
    if boundary["threshold"] == guard["threshold"] and boundary["comparison"] == guard["comparison"]:
        return True
    if (boundary.get("numeric_kind") != "int" or boundary["threshold"]["kind"] != "constant"
            or guard["threshold"]["kind"] != "constant"):
        return False
    def discrete_edge(comparison, threshold):
        if comparison == ">": return ("lower", math.floor(threshold) + 1)
        if comparison == ">=": return ("lower", math.ceil(threshold))
        if comparison == "<": return ("upper", math.ceil(threshold) - 1)
        if comparison == "<=": return ("upper", math.floor(threshold))
        return None
    left = discrete_edge(boundary["comparison"], boundary["threshold"]["value"])
    right = discrete_edge(guard["comparison"], guard["threshold"]["value"])
    return left is not None and left == right


def validate_binding(boundary, context):
    # VALIDATION START: executable characteristic and domain role match public evidence.
    operation = boundary["characteristic"]["operation"]
    quote = boundary["source_quote"].lower()
    projections = [boundary["characteristic"]]
    if boundary["threshold"]["kind"] == "expression":
        projections.append(boundary["threshold"])
    projection_evidence = []
    for expression in projections:
        if expression["operation"] == "parsed_float":
            matched = next((evidence for evidence in context.guidance.get("projection_evidence", [])
                            if evidence["parameter"] == expression["parameter"]), None)
            if matched is None:
                raise ValueError("unverified_numeric_string_binding")
            projection_evidence.append(matched)
    if projection_evidence:
        boundary["projection_evidence"] = projection_evidence
    if "consecutive" in quote and "space" in quote and operation != "run_length":
        raise ValueError("consecutive_run_requires_run_length")
    if operation == "run_length":
        if not any(word in quote for word in ("consecutive", "successive", "run of", "repeated")):
            raise ValueError("unverified_run_binding")
        token = boundary["characteristic"]["token"]
        if token == " " and "space" not in quote:
            raise ValueError("run_token_not_supported_by_quote")
        if token != " " and token not in boundary["source_quote"]:
            raise ValueError("run_token_not_supported_by_quote")
    if operation == "elements" and "max(" in quote and "min(" in quote:
        raise ValueError("extrema_difference_requires_range")
    threshold = boundary["threshold"]
    if threshold["kind"] == "expression" and threshold["parameter"] == boundary["characteristic"]["parameter"]:
        raise ValueError("self_dependent_threshold_unsupported")
    if boundary["boundary_kind"] in ("domain_lower", "domain_upper"):
        guards = context.guidance.get("domain_guards", [])
        matched = next((guard for guard in guards if same_domain_boundary(boundary, guard)), None)
        if matched is None:
            raise ValueError("unverified_domain_role")
        boundary["binding_status"] = "recognized_necessary_domain_clause"
        boundary["binding_evidence"] = matched
    else:
        matched = next((guard for guard in context.guidance.get("candidate_guards", [])
                        if same_domain_boundary(boundary, guard)), None)
        boundary["binding_status"] = "matched_public_guard" if matched is not None else "llm_semantic_hypothesis"
        if matched is not None:
            boundary["binding_evidence"] = matched
    # VALIDATION END: executable characteristic and domain role match public evidence.


def validate_known_domain(arguments, guards):
    """Check only recognized necessary constraints; unknown clauses stay unverified."""
    for guard in guards:
        left = characteristic_values(guard["characteristic"], arguments)
        threshold = guard["threshold"]
        right = threshold["value"] if threshold["kind"] == "constant" else characteristic_values(threshold, arguments)[0]
        if not all(COMPARISONS[guard["comparison"]](value, right) for value in left):
            raise ValueError("recognized_domain_constraint_failed")
