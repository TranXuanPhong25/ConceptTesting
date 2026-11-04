"""Validate model output and boundary targets without executing generated code."""
from __future__ import annotations

import json
import math
import re

from .prompts import selection_messages, generation_messages
from .types import entry_function, input_signature, literal_arguments, literal_value, finite_literal


def number(value):
    return type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def required_text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise ValueError("expected_nonempty_text")
    return value


def parse_response(response):
    if response.finish_reason == "length":
        raise ValueError("truncated_response")
    text = response.text.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    if len(text) > 100000:
        raise ValueError("oversized_response")
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("response_must_be_object")
    return result


def supported_quote(quote, context):
    quote = required_text(quote)
    normalized = " ".join(quote.split())
    for source in (context.specification, context.contract):
        if normalized in " ".join(source.split()):
            return quote
    raise ValueError("quote_not_in_spec_or_contract")


class BoundarySelection:
    name = "selection"

    def run(self, context):
        messages = selection_messages(context)
        response = context.query("select", messages, context.settings.selection_tokens,
                                 context.settings.selection_temperature)
        if response is None:
            return {"status": "prompt_too_large", "boundaries": [], "rejected": []}
        # VALIDATION START: selection response schema and status consistency.
        try:
            record = self.validate_response(response, context.settings.boundary_budget)
        except (ValueError, TypeError, RecursionError):
            return {"status": "invalid_selection", "boundaries": [],
                    "rejected": [{"reason": "invalid_response"}], "finish_reason": response.finish_reason}
        # VALIDATION END: selection response schema and status consistency.
        boundaries = record["boundaries"]
        reason = record["reason"]
        if record["status"] == "no_boundary":
            return {"status": "no_boundary", "reason": reason, "boundaries": [], "rejected": []}
        accepted = []
        rejected = []
        identifiers = set()
        for index, boundary in enumerate(boundaries):
            # VALIDATION START: boundary schema, source quotes and unique ID.
            try:
                validated = self.validate(boundary, context)
                if validated["id"] in identifiers:
                    raise ValueError("duplicate_boundary_id")
                identifiers.add(validated["id"])
                accepted.append(validated)
            except (ValueError, TypeError, KeyError, OverflowError) as error:
                reason = str(error) if type(error) is ValueError else "invalid_boundary_record"
                rejected.append({"index": index, "reason": reason})
            # VALIDATION END: boundary schema, source quotes and unique ID.
        return {"status": "selected" if accepted else "invalid_selection", "reason": reason,
                "boundaries": accepted, "rejected": rejected, "finish_reason": response.finish_reason,
                "semantic_status": "llm_proposed_with_verified_quote_not_entailment_proof"}

    @staticmethod
    def validate_response(response, boundary_budget):
        """Validate the selection envelope before inspecting individual boundaries."""
        record = parse_response(response)
        boundaries = record.get("boundaries")
        if not isinstance(boundaries, list) or len(boundaries) > boundary_budget:
            raise ValueError("invalid_boundary_list")
        required_text(record.get("reason"))
        if record.get("status") == "no_boundary" and not boundaries:
            return record
        if record.get("status") != "selected" or not boundaries:
            raise ValueError("inconsistent_selection_status")
        return record

    @staticmethod
    def validate(boundary, context):
        if not isinstance(boundary, dict):
            raise ValueError("boundary_must_be_object")
        identifier = boundary.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", identifier):
            raise ValueError("invalid_boundary_id")
        templates = {candidate["id"]: candidate for candidate in context.templates["candidates"]}
        template = templates[boundary["template_id"]]
        if boundary["characteristic"] != template["characteristic"]:
            raise ValueError("characteristic_not_in_template")
        threshold = boundary["threshold"]
        if not isinstance(threshold, dict):
            raise ValueError("invalid_threshold")
        if threshold.get("kind") == "constant":
            if set(threshold) != {"kind", "value"} or not number(threshold["value"]):
                raise ValueError("invalid_constant_threshold")
        elif threshold.get("kind") == "expression":
            if set(threshold) != {"kind", "parameter", "operation"}:
                raise ValueError("invalid_threshold_expression")
            expression = {"parameter": threshold["parameter"], "operation": threshold["operation"]}
            if threshold["operation"] == "elements" or not any(
                candidate["characteristic"] == expression for candidate in templates.values()
            ):
                raise ValueError("unsupported_threshold_expression")
            if expression == boundary["characteristic"]:
                raise ValueError("tautological_boundary")
        else:
            raise ValueError("invalid_threshold_kind")
        comparison = boundary["comparison"]
        if comparison not in ("<", "<=", "==", "!=", ">=", ">"):
            raise ValueError("invalid_comparison")
        if boundary["boundary_kind"] not in ("domain_lower", "domain_upper", "behavior"):
            raise ValueError("invalid_boundary_kind")
        neighborhood = boundary["neighborhood"]
        if not isinstance(neighborhood, dict) or neighborhood.get("mode") not in template["neighborhood_modes"]:
            raise ValueError("unsupported_neighborhood")
        if neighborhood["mode"] == "step":
            if set(neighborhood) != {"mode", "step"} or not number(neighborhood["step"]) or neighborhood["step"] <= 0:
                raise ValueError("invalid_step")
            if template["characteristic"]["operation"] == "length" and neighborhood["step"] != 1:
                raise ValueError("length_step_must_be_one")
        elif set(neighborhood) != {"mode"}:
            raise ValueError("invalid_float_neighborhood")
        sides = boundary["target_sides"]
        if (not isinstance(sides, list) or not sides or any(side not in ("below", "at", "above") for side in sides)
                or len(sides) != len(set(sides))):
            raise ValueError("invalid_target_sides")
        # Normal BVA never turns a declared domain precondition violation into a test.
        kind = boundary["boundary_kind"]
        if kind == "domain_lower" and (comparison not in (">", ">=") or "below" in sides
                                       or (comparison == ">" and "at" in sides)):
            raise ValueError("outside_lower_domain")
        if kind == "domain_upper" and (comparison not in ("<", "<=") or "above" in sides
                                       or (comparison == "<" and "at" in sides)):
            raise ValueError("outside_upper_domain")
        constraints = boundary["constraints"]
        if not isinstance(constraints, list) or len(constraints) > 12:
            raise ValueError("invalid_constraints")
        validated_constraints = []
        for constraint in constraints:
            if not isinstance(constraint, dict):
                raise ValueError("invalid_constraint")
            validated_constraints.append({"description": required_text(constraint.get("description")),
                                          "source_quote": supported_quote(constraint.get("source_quote"), context)})
        return {
            "id": identifier, "template_id": template["id"], "characteristic": template["characteristic"],
            "threshold": threshold, "comparison": comparison, "boundary_kind": kind,
            "neighborhood": neighborhood, "target_sides": sides, "constraints": validated_constraints,
            "source_quote": supported_quote(boundary.get("source_quote"), context),
            "explanation": required_text(boundary.get("explanation")),
        }


def characteristic_values(expression, arguments):
    value = arguments[expression["parameter"]]
    operation = expression["operation"]
    if operation == "value" and number(value):
        return [value]
    if operation == "length" and type(value) in (str, list, tuple, set, dict):
        return [len(value)]
    if operation in ("sum", "elements") and type(value) in (list, tuple) and all(number(item) for item in value):
        return [sum(value)] if operation == "sum" else list(value)
    raise ValueError("input_does_not_support_characteristic")


def boundary_target(boundary, arguments, side):
    threshold = boundary["threshold"]
    if threshold["kind"] == "constant":
        value = threshold["value"]
    else:
        value = characteristic_values(threshold, arguments)[0]
    if not number(value):
        raise ValueError("nonfinite_threshold")
    if side == "at":
        return value
    if boundary["neighborhood"]["mode"] == "float_adjacent":
        target = math.nextafter(value, -math.inf if side == "below" else math.inf)
    else:
        step = boundary["neighborhood"]["step"]
        target = value - step if side == "below" else value + step
    if not number(target) or target == value:
        raise ValueError("unrepresentable_neighbor")
    return target


def frozen_value(value):
    """Type-preserving identity, independent of dict/set iteration order."""
    if type(value) is dict:
        items = [(frozen_value(key), frozen_value(item)) for key, item in value.items()]
        return ("dict", tuple(sorted(items, key=repr)))
    if type(value) in (list, tuple, set):
        items = [frozen_value(item) for item in value]
        if type(value) is set:
            items.sort(key=repr)
        return (type(value).__name__, tuple(items))
    return (type(value).__name__, value)


class BoundaryInputGeneration:
    name = "generation"

    def run(self, context):
        response = context.query("inputs", generation_messages(context), context.settings.input_tokens,
                                 context.settings.input_temperature)
        if response is None:
            return {"status": "prompt_too_large", "inputs": [], "rejected": []}
        # VALIDATION START: generation response schema.
        try:
            record = self.validate_response(response)
        except (ValueError, TypeError, RecursionError):
            return {"status": "invalid_generation", "inputs": [], "rejected": [{"reason": "invalid_response"}],
                    "finish_reason": response.finish_reason}
        # VALIDATION END: generation response schema.
        signature = input_signature(entry_function(context.program_source, context.entry_point))
        boundaries = {boundary["id"]: boundary for boundary in context.selection["boundaries"]}
        seen = self.base_identities(context.base_inputs, signature)
        accepted = []
        rejected = []
        for index, input_record in enumerate(record["inputs"][:context.settings.input_budget]):
            # VALIDATION START: literals, signature, boundary target and duplicates.
            try:
                validated_input, identity = self.validate_input(input_record, signature, boundaries, seen)
                seen.add(identity)
                accepted.append(validated_input)
            except (ValueError, SyntaxError, TypeError, KeyError, OverflowError, RecursionError) as error:
                reason = str(error) if type(error) is ValueError else "invalid_input_record"
                if not re.fullmatch(r"[a-z_]{1,80}", reason):
                    reason = "invalid_input_record"
                rejected.append({"index": index, "reason": reason})
            # VALIDATION END: literals, signature, boundary target and duplicates.
        # VALIDATION START: generated input budget.
        if len(record["inputs"]) > context.settings.input_budget:
            rejected.append({"reason": "input_budget_exceeded",
                             "count": len(record["inputs"]) - context.settings.input_budget})
        # VALIDATION END: generated input budget.
        return {"status": "generated" if accepted else "no_inputs", "inputs": accepted, "rejected": rejected,
                "reason": record.get("reason", ""), "finish_reason": response.finish_reason}

    @staticmethod
    def validate_response(response):
        """Validate the input-generation envelope; preserve the model's reason."""
        record = parse_response(response)
        if not isinstance(record.get("inputs"), list):
            raise ValueError("invalid_input_list")
        if "reason" in record and not isinstance(record["reason"], str):
            raise ValueError("invalid_reason")
        return record

    @staticmethod
    def validate_input(input_record, signature, boundaries, seen):
        """Return a checked input and identity; prose constraints remain unverified."""
        arguments, keywords = literal_arguments(input_record)
        if not finite_literal(arguments) or not finite_literal(keywords):
            raise ValueError("unsupported_or_nonfinite_literal")
        bound = signature.bind(*arguments, **keywords)
        bound.apply_defaults()
        if not finite_literal(dict(bound.arguments)):
            raise ValueError("unsupported_or_nonfinite_default")
        boundary = boundaries[input_record["boundary_id"]]
        side = input_record["side"]
        if side not in boundary["target_sides"]:
            raise ValueError("undeclared_side")
        values = characteristic_values(boundary["characteristic"], bound.arguments)
        target = boundary_target(boundary, bound.arguments, side)
        if target not in values:
            raise ValueError("boundary_not_hit")
        identity = frozen_value(dict(bound.arguments))
        if identity in seen:
            raise ValueError("duplicate_input")
        validated_input = {
            "args": input_record["args"], "kwargs": input_record["kwargs"],
            "concept_id": boundary["id"], "boundary_id": boundary["id"], "side": side,
            "validation": {"signature": "passed", "boundary_target": "passed",
                           "domain_constraints": "unverified", "oracle": "not_run"},
        }
        return validated_input, identity

    @staticmethod
    def base_identities(records, signature):
        identities = set()
        for record in records:
            try:
                if "args" in record and "kwargs" in record:
                    positional, keywords = literal_arguments(record)
                    bound = signature.bind(*positional, **keywords)
                    bound.apply_defaults()
                    arguments = dict(bound.arguments)
                elif "bound" in record:
                    arguments = {name: literal_value(text) for name, text in record["bound"].items()}
                    if set(arguments) != set(signature.parameters):
                        continue
                else:
                    continue
                if finite_literal(arguments):
                    identities.add(frozen_value(arguments))
            except (ValueError, SyntaxError, TypeError, KeyError, RecursionError):
                continue
        return identities
