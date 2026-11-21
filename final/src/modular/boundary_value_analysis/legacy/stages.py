"""Validate model output and boundary targets without executing generated code."""
from __future__ import annotations

import json
import math
import re

from ...call_builder import bound_input_identity
from .prompts import selection_messages, generation_messages
from .characteristics import number, characteristic_values, boundary_target
from .binding import validate_binding
from .context_requirements import parse_context_requirements, validate_context_requirements
from .grounding import checked, context_goals, goal_coverage, audit_boundary
from .construction import TargetCompiler, base_identities as compiled_base_identities
from .types import entry_function, input_signature, literal_arguments, literal_value, finite_literal


BOUNDARY_ORIGINS = ("spec", "code", "edge")
BETTER_TECHNIQUES = ("equivalence_partitioning", "decision_table", "none")


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


def supported_code_quote(quote, context):
    quote = required_text(quote)
    if " ".join(quote.split()) not in " ".join(context.program_source.split()):
        raise ValueError("code_quote_not_in_put")
    return quote


def worksheet_fields(boundary, context):
    """Keep the LLM worksheet for the context stage; only the code quote is verifiable."""
    worksheet = {}
    origin = boundary.get("origin")
    if origin is not None:
        if origin not in BOUNDARY_ORIGINS:
            raise ValueError("invalid_boundary_origin")
        worksheet["origin"] = origin
    code_quote = boundary.get("code_quote")
    if code_quote:
        worksheet["code_quote"] = supported_code_quote(code_quote, context)
    elif origin == "code":
        raise ValueError("code_origin_requires_code_quote")
    for name in ("alignment", "reach", "infect"):
        if boundary.get(name) is not None:
            worksheet[name] = required_text(boundary[name])
    side_rules = boundary.get("side_rules")
    if side_rules is not None:
        if not isinstance(side_rules, dict) or any(side not in ("below", "at", "above") for side in side_rules):
            raise ValueError("invalid_side_rules")
        worksheet["side_rules"] = {side: required_text(rule) for side, rule in side_rules.items()}
    return worksheet


class BoundarySelection:
    name = "selection"

    def run(self, context):
        messages = selection_messages(context)
        response = context.query("select", messages, context.settings.selection_tokens,
                                 context.settings.selection_temperature)
        if response is None:
            return {"status": "prompt_too_large", "boundaries": [], "rejected": []}
        if response.finish_reason == "length":
            return {"status": "selection_truncated", "boundaries": [],
                    "rejected": [{"reason": "truncated_response"}], "finish_reason": response.finish_reason,
                    "reason": "Selection output reached its token budget; applicability is unknown."}
        # VALIDATION START: selection response schema and status consistency.
        try:
            record = self.validate_response(response, context.settings.boundary_budget)
        except (ValueError, TypeError, RecursionError):
            return {"status": "invalid_selection", "boundaries": [],
                    "rejected": [{"reason": "invalid_response"}], "finish_reason": response.finish_reason}
        # VALIDATION END: selection response schema and status consistency.
        boundaries = record["boundaries"]
        reason = record["reason"]
        if record["status"] != "selected":
            status = record["status"]
            if status == "no_applicable_boundary" and any(
                guard["origin"] == "spec" and not guard.get("necessary_domain")
                for guard in context.guidance.get("candidate_guards", [])
            ):
                status = "uncertain_binding"
            result = {"status": status, "reason": reason, "boundaries": [], "rejected": []}
            if record.get("better_technique") in BETTER_TECHNIQUES:
                result["better_technique"] = record["better_technique"]
            return result
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
                rejection_reason = str(error) if type(error) is ValueError else "invalid_boundary_record"
                rejected.append({"index": index, "reason": rejection_reason})
            # VALIDATION END: boundary schema, source quotes and unique ID.
        status = "selected" if accepted else "invalid_selection"
        binding_failures = {"consecutive_run_requires_run_length", "unverified_run_binding", "unverified_domain_role",
                            "run_token_not_supported_by_quote", "extrema_difference_requires_range", "self_dependent_threshold_unsupported",
                            "unverified_numeric_string_binding"}
        if not accepted and rejected and all(item["reason"] in binding_failures for item in rejected):
            status = "uncertain_binding"
        return {"status": status, "reason": reason,
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
        if record.get("status") in ("no_boundary", "no_applicable_boundary", "unsupported_characteristic", "uncertain_binding") and not boundaries:
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
        characteristic = boundary["characteristic"]
        if not isinstance(characteristic, dict):
            raise ValueError("invalid_characteristic")
        expected = template["characteristic"]
        if {key: characteristic.get(key) for key in ("parameter", "operation")} != expected:
            raise ValueError("characteristic_not_in_template")
        if expected["operation"] == "run_length":
            if set(characteristic) != {"parameter", "operation", "token"} or not isinstance(characteristic["token"], str) or len(characteristic["token"]) != 1:
                raise ValueError("invalid_run_token")
        elif characteristic != expected:
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
            if threshold["operation"] in ("elements", "run_length", "code_point") or not any(
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
        result = {
            "id": identifier, "template_id": template["id"], "characteristic": characteristic,
            "threshold": threshold, "comparison": comparison, "boundary_kind": kind,
            "neighborhood": neighborhood, "target_sides": sides, "constraints": validated_constraints,
            "source_quote": supported_quote(boundary.get("source_quote"), context),
            "explanation": required_text(boundary.get("explanation")),
        }
        result.update(worksheet_fields(boundary, context))
        if context.settings.construction_mode == "compiled":
            result["numeric_kind"] = template["numeric_kind"]
            validate_binding(result, context)
        if checked(context):
            result["grounding_findings"] = audit_boundary(result, context.guidance)
        return result


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
        compiled_seen = compiled_base_identities(context, signature)
        obligations = {item["id"]: item for item in context.construction.get("obligations", [])}
        obligation_counts = {}
        accepted = []
        rejected = []
        for index, input_record in enumerate(record["inputs"][:context.settings.input_budget]):
            # VALIDATION START: literals, signature, boundary target and duplicates.
            try:
                obligation_id = None
                if context.settings.construction_mode == "compiled":
                    if not isinstance(input_record, dict):
                        raise ValueError("input_must_be_object")
                    obligation_id = input_record.get("obligation_id")
                    if "arguments" not in input_record:
                        obligation_id = str(input_record.get("boundary_id")) + ":" + str(input_record.get("side"))
                    if not isinstance(obligation_id, str) or obligation_id not in obligations:
                        raise ValueError("unknown_obligation_id")
                    if obligation_counts.get(obligation_id, 0) >= obligations[obligation_id]["context_budget"]:
                        raise ValueError("obligation_budget_exceeded")
                if isinstance(input_record, dict) and "arguments" in input_record and context.settings.construction_mode == "compiled":
                    obligation = obligations[obligation_id]
                    requirements = input_record.get("context_requirements", [])
                    # null is invalid, just like other malformed requirement lists.
                    parse_context_requirements(requirements, signature)
                    validated_input = TargetCompiler.build_input(context, obligation, input_record["arguments"],
                                                                 compiled_seen, requirements)
                else:
                    validated_input, identity, arguments = self.validate_input(input_record, signature, boundaries, seen)
                    requirements = parse_context_requirements(input_record.get("context_requirements", []), signature)
                    validate_context_requirements(requirements, arguments)
                    validated_input["context_requirements"] = requirements
                    validated_input["validation"]["context_requirements"] = "passed" if requirements else "none_declared"
                    validated_input["validation"]["reach_propagation"] = "unverified"
                    seen.add(identity)
                    if context.settings.construction_mode == "compiled":
                        shared_identity = bound_input_identity(arguments)
                        if shared_identity in compiled_seen:
                            raise ValueError("duplicate_input")
                        compiled_seen.add(shared_identity)
                        validated_input["construction"] = "literal-target-check"
                if obligation_id is not None:
                    obligation_counts[obligation_id] = obligation_counts.get(obligation_id, 0) + 1
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
        result = {"status": "generated" if accepted else "no_inputs", "inputs": accepted, "rejected": rejected,
                  "reason": record.get("reason", ""), "finish_reason": response.finish_reason, "model_call_used": True}
        if checked(context):
            result["context_goal_coverage"] = goal_coverage(context_goals(context), accepted, signature)
        return result

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
        """Return a checked input, identity, and bound arguments."""
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
            "guidance_id": boundary["id"], "boundary_id": boundary["id"], "side": side,
            "validation": {"signature": "passed", "boundary_target": "passed",
                           "domain_constraints": "unverified", "oracle": "not_run"},
        }
        return validated_input, identity, bound.arguments

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
