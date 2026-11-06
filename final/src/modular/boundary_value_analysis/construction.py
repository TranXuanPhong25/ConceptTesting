"""Compile targets and instantiate named contexts with bounded, pure constructors."""
from __future__ import annotations

import ast
import copy
import re

from ..call_builder import CallBuilder, MAX_CONTAINER_ITEMS
from .characteristics import number, characteristic_values, boundary_target, parsed_float
from .binding import validate_known_domain
from .context_requirements import parse_context_requirements, validate_context_requirements


def input_identity(signature, record):
    arguments = ast.literal_eval(record["args"])
    keywords = ast.literal_eval(record["kwargs"])
    bound = signature.bind(*arguments, **keywords)
    bound.apply_defaults()
    # Strict identity preserves literal types and container ordering.
    return repr([(name, type(value).__name__, repr(value)) for name, value in bound.arguments.items()])


def base_identities(context, signature):
    identities = set()
    for record in context.base_inputs:
        try:
            if "args" in record and "kwargs" in record:
                identities.add(input_identity(signature, record))
            elif isinstance(record.get("bound"), dict) and set(record["bound"]) == set(signature.parameters):
                values = {name: ast.literal_eval(value) for name, value in record["bound"].items()}
                encoded = CallBuilder(signature).build_values(values)
                identities.add(input_identity(signature, encoded))
        except (ValueError, SyntaxError, TypeError, RecursionError):
            continue
    return identities


def parameter_seed(context, name):
    """Type/shape seed from observed inputs, never outputs or PUT execution."""
    builder = CallBuilder.for_source(context.program_source, context.entry_point)
    for record in context.base_inputs:
        try:
            if "args" in record and "kwargs" in record:
                bound = builder.signature.bind(*ast.literal_eval(record["args"]), **ast.literal_eval(record["kwargs"]))
                bound.apply_defaults()
                if name in bound.arguments:
                    return copy.deepcopy(bound.arguments[name])
            elif name in record.get("bound", {}):
                return ast.literal_eval(record["bound"][name])
        except (ValueError, SyntaxError, TypeError, RecursionError):
            continue
    for parameter in context.input_types["parameters"]:
        if parameter["name"] != name:
            continue
        for evidence in parameter["evidence"]:
            for description in evidence["types"]:
                kind = description["kind"]
                if kind == "str": return ""
                if kind == "tuple": return (0,)
                if kind == "list":
                    items = description.get("items", [])
                    return [[0]] if any(item["kind"] == "list" for item in items) else [0]
                if kind == "float": return 0.0
                if kind == "int": return 0
    raise ValueError("missing_parameter_shape")


def validated_size(target):
    if not number(target) or int(target) != target:
        raise ValueError("non_integral_length_target")
    if target < 0:
        raise ValueError("characteristic_has_no_negative_values")
    if target > MAX_CONTAINER_ITEMS:
        raise ValueError("construction_resource_limit")
    return int(target)


def instantiate_value(expression, target, seed, *, preserve_palindrome=False):
    operation = expression["operation"]
    if operation == "value":
        return target
    if operation == "parsed_float":
        encoded = repr(float(target))
        if parsed_float(encoded) != target:
            raise ValueError("unrepresentable_float_target")
        return encoded
    if operation in ("length", "run_length"):
        target = validated_size(target)
        if operation == "run_length":
            if not isinstance(seed, str):
                raise ValueError("run_context_must_be_string")
            token = expression["token"]
            matches = list(re.finditer(re.escape(token) + "+", seed))
            if not matches:
                return seed + token * target
            longest = max(matches, key=lambda match: len(match.group()))
            pieces = []
            offset = 0
            for match in matches:
                pieces.append(seed[offset:match.start()])
                size = target if match is longest else min(target, len(match.group()))
                pieces.append(token * size)
                offset = match.end()
            pieces.append(seed[offset:])
            return "".join(pieces)
        if isinstance(seed, str):
            fill = seed or "a"
            return (fill * (target // len(fill) + 1))[:target]
        if type(seed) in (list, tuple):
            fill = list(seed) or [0]
            result = [copy.deepcopy(fill[index % len(fill)]) for index in range(target)]
            return tuple(result) if isinstance(seed, tuple) else result
        raise ValueError("length_constructor_unsupported_for_type")
    if type(seed) not in (list, tuple) or not all(number(item) for item in seed):
        raise ValueError("numeric_sequence_context_required")
    values = list(seed) or [target]
    if operation == "elements":
        values[0] = target
    elif operation == "maximum":
        values = [min(value, target) for value in values]
        values[0] = target
    elif operation == "minimum":
        values = [max(value, target) for value in values]
        values[0] = target
    elif operation == "sum":
        if preserve_palindrome:
            if values != values[::-1]:
                raise ValueError("context_seed_is_not_palindrome")
            middle = len(values) // 2
            if len(values) % 2:
                values[middle] = target - sum(values[:middle] + values[middle + 1:])
            else:
                remainder = target - sum(values[:middle - 1] + values[middle + 1:])
                integer_target = type(target) is int and all(type(value) is int for value in values)
                if integer_target and remainder % 2:
                    raise ValueError("context_shape_cannot_realize_target")
                center = remainder // 2 if integer_target else remainder / 2
                values[middle - 1] = center
                values[middle] = center
        else:
            values[-1] = target - sum(values[:-1])
    elif operation == "range":
        if target < 0:
            raise ValueError("range_cannot_be_negative")
        values = [0.0 if type(target) is float else 0, target]
    else:
        raise ValueError("characteristic_constructor_unsupported")
    return tuple(values) if isinstance(seed, tuple) else values


class TargetCompiler:
    name = "compiled_targets"

    def run(self, context):
        obligations = []
        blocked = []
        builder = CallBuilder.for_source(context.program_source, context.entry_point)
        seen = base_identities(context, builder.signature)
        closed_by_id = {}
        scalar_only = len(builder.signature.parameters) == 1 and all(
            boundary["characteristic"]["operation"] in ("value", "parsed_float")
            and boundary["threshold"]["kind"] == "constant"
            for boundary in context.selection["boundaries"])
        for boundary in context.selection["boundaries"]:
            for side in boundary["target_sides"]:
                obligation = {"id": boundary["id"] + ":" + side, "boundary_id": boundary["id"], "side": side,
                              "characteristic": boundary["characteristic"], "target": None}
                if boundary["threshold"]["kind"] == "constant":
                    try:
                        obligation["target"] = boundary_target(boundary, {}, side)
                        target = obligation["target"]
                        if boundary["characteristic"]["operation"] in ("length", "run_length"):
                            validated_size(target)
                        if boundary["characteristic"]["operation"] == "range" and target < 0:
                            raise ValueError("range_cannot_be_negative")
                    except (ValueError, OverflowError) as error:
                        reason = str(error) if type(error) is ValueError else "arithmetic_overflow"
                        blocked.append({"obligation_id": obligation["id"], "reason": reason})
                        continue
                obligations.append(obligation)
        queues = {}
        for obligation in obligations:
            queues.setdefault(obligation["boundary_id"], []).append(obligation)
        ordered = []
        while any(queues.values()):
            for queue in queues.values():
                if queue:
                    ordered.append(queue.pop(0))
        if scalar_only:
            available = []
            for obligation in ordered:
                try:
                    call = self.build_input(context, obligation, {}, seen)
                    closed_by_id[obligation["id"]] = call
                    available.append(obligation)
                except (ValueError, TypeError, KeyError, OverflowError) as error:
                    blocked.append({"obligation_id": obligation["id"], "reason": str(error)})
            ordered = available
        active = ordered[:context.settings.input_budget]
        for obligation in ordered[context.settings.input_budget:]:
            blocked.append({"obligation_id": obligation["id"], "reason": "obligation_budget_exhausted"})
        for index, obligation in enumerate(active):
            quota = 1
            if not scalar_only:
                quotient, remainder = divmod(context.settings.input_budget, len(active))
                quota = quotient + (index < remainder)
            obligation["context_budget"] = quota
        closed = [closed_by_id[item["id"]] for item in active] if scalar_only else []
        return {"status": "compiled", "obligations": active, "blocked": blocked,
                "closed_scalar": scalar_only, "closed_inputs": closed,
                "unused_input_budget": context.settings.input_budget - sum(item["context_budget"] for item in active)}

    @staticmethod
    def build_input(context, obligation, named_arguments, seen, context_requirements=None):
        builder = CallBuilder.for_source(context.program_source, context.entry_point)
        requirements = parse_context_requirements(
            [] if context_requirements is None else context_requirements, builder.signature)
        values = builder.decode_arguments(named_arguments)
        boundary = next(item for item in context.selection["boundaries"] if item["id"] == obligation["boundary_id"])
        parameter = boundary["characteristic"]["parameter"]
        target = boundary_target(boundary, values, obligation["side"])
        template = next(item for item in context.templates["candidates"] if item["id"] == boundary["template_id"])
        if template.get("numeric_kind") == "float" and type(target) is int:
            target = float(target)
        seed = values.get(parameter)
        if seed is None:
            seed = parameter_seed(context, parameter)
        preserve_palindrome = any(requirement["parameter"] == parameter and requirement["property"] == "palindrome"
                                  for requirement in requirements)
        values[parameter] = instantiate_value(boundary["characteristic"], target, seed,
                                              preserve_palindrome=preserve_palindrome)
        encoded = builder.build_values(values, guidance_id=boundary["id"])
        bound = builder.signature.bind(*ast.literal_eval(encoded["args"]), **ast.literal_eval(encoded["kwargs"]))
        bound.apply_defaults()
        # VALIDATION START: actual target, recognized domain clauses and exact base duplicates.
        actual_values = characteristic_values(boundary["characteristic"], bound.arguments)
        if target not in actual_values:
            raise ValueError("constructor_did_not_realize_target")
        validate_known_domain(bound.arguments, context.guidance.get("domain_guards", []))
        validate_context_requirements(requirements, bound.arguments)
        identity = input_identity(builder.signature, encoded)
        if identity in seen:
            raise ValueError("duplicate_input")
        # VALIDATION END: actual target, recognized domain clauses and exact base duplicates.
        seen.add(identity)
        return {**encoded, "boundary_id": boundary["id"], "side": obligation["side"],
                "obligation_id": obligation["id"], "construction": "compiled-target",
                "context_requirements": requirements,
                "validation": {"signature": "passed", "boundary_target": "passed",
                               "domain_constraints": "recognized-clauses-passed;remaining-unverified",
                               "context_requirements": "passed" if requirements else "none_declared",
                               "reach_propagation": "unverified", "oracle": "not_run"}}
