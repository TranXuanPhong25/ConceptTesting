"""Strict JSON Schema contracts and canonicalization for VF3 measured catalogue arms."""
from __future__ import annotations

import ast
import copy
import inspect
from itertools import product
from typing import Annotated, Literal, Union

from pydantic import Field, JsonValue, create_model, field_validator

from .call_builder import CallBuilder, decode_value
from .catalogue import (
    Boundary,
    Number,
    Schema,
    effective_boundary_context,
    matches_context,
    selected_value,
)
from .input_buckets.predicates import declared_types
from .tool_sampling.schema import validate_expression

LIST_ANNOTATIONS = frozenset({"list", "list[int]", "list[float]", "list[str]"})
SCALAR_ANNOTATIONS = frozenset({"int", "float", "bool"})
MAX_PER_PARAMETER_BOUNDARY_VARIANTS = 6

PositiveStep = Annotated[int, Field(gt=0)] | Annotated[float, Field(gt=0)]


class MeasuredClass(Schema):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1, max_length=160)
    predicate: str = Field(min_length=1, max_length=2048)
    fault_hypothesis: str | None = Field(default=None, min_length=1)


class FeasibleOutcome(Schema):
    status: Literal["feasible"]
    actions: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(min_length=1, max_length=4)
    reason: str | None = None
    fault_hypothesis: str | None = Field(default=None, min_length=1)


class InfeasibleOutcome(Schema):
    status: Literal["infeasible", "unresolved"]
    actions: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(default_factory=list, max_length=4)
    reason: str = Field(min_length=1, max_length=400)
    fault_hypothesis: str | None = Field(default=None, min_length=1)


class EmptyObject(Schema):
    """Strict empty object used when no other parameters exist or a DT is not applicable."""


class GenerationBoundary(Boundary):
    # Override step with per-branch gt=0 so Pydantic v2 emits valid JSON Schema
    # "exclusiveMinimum": 0 instead of placing non-standard "gt": 0 on an anyOf node.
    step: PositiveStep | None = None

    @field_validator("context", "nominal")
    @classmethod
    def validate_context_and_nominal_arguments(cls, values):
        # Dynamic argument models check parameter names and JSON types; canonical
        # Catalogue still enforces literal safety after canonicalization.
        return values


def _argument_type_map():
    # Match CallBuilder.matches_annotation: typed int/float never accept bool;
    # untyped parameters still fall back to JsonValue.
    bounded_integer = Annotated[int, Field(ge=-(2**32), le=2**32)]
    return {
        "int": bounded_integer,
        "float": float,
        "bool": bool,
        "str": Annotated[str, Field(max_length=1000)],
        "list": Annotated[list[JsonValue], Field(max_length=30)],
        "list[int]": Annotated[list[bounded_integer], Field(max_length=30)],
        "list[float]": Annotated[list[float], Field(max_length=30)],
        "list[str]": Annotated[list[str], Field(max_length=30)],
    }


def _annotation_allows_none(annotation):
    """Return True only when an explicit type annotation permits None (Optional / | None)."""
    if not isinstance(annotation, str) or not annotation.strip():
        return False
    try:
        node = ast.parse(annotation, mode="eval").body
    except SyntaxError:
        return False
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and child.value is None:
            return True
        if isinstance(child, ast.Name) and child.id in ("None", "Optional"):
            return True
        if isinstance(child, ast.Attribute) and child.attr == "Optional":
            return True
    return False


def _allowed_transforms_for_annotation(annotation):
    if annotation in LIST_ANNOTATIONS:
        return Literal["length", "count"]
    if annotation in SCALAR_ANNOTATIONS:
        return Literal["identity"]
    return Literal["identity", "length", "count", "parsed_int", "parsed_float"]


def _build_boundary_type(parameter_names, annotations, type_map, arguments_model):
    """Build per-parameter boundary schemas that exclude the tested parameter from context."""
    if not parameter_names or len(parameter_names) > MAX_PER_PARAMETER_BOUNDARY_VARIANTS:
        context_fields = {
            name: (type_map.get(annotations.get(name), JsonValue) | None, None)
            for name in parameter_names
        }
        fallback_context = create_model("BoundaryContext", __base__=Schema, **context_fields)
        return create_model(
            "MeasuredBoundary",
            __base__=GenerationBoundary,
            parameter=(Literal[parameter_names] if parameter_names else str, ...),
            numeric_kind=(Literal["integer", "float", "discrete"], ...),
            transform=(Literal["identity", "length", "count", "parsed_int", "parsed_float"], ...),
            lower=(Number | None, ...),
            upper=(Number | None, ...),
            context=(fallback_context, ...),
            nominal=(arguments_model, ...),
        )

    variants = []
    for index, tested_parameter in enumerate(parameter_names):
        other_parameters = [name for name in parameter_names if name != tested_parameter]
        if other_parameters:
            context_fields = {
                other: (type_map.get(annotations.get(other), JsonValue) | None, None)
                for other in other_parameters
            }
            context_model = create_model(
                f"BoundaryContext_{index}",
                __base__=Schema,
                **context_fields,
            )
        else:
            context_model = EmptyObject
        transform_type = _allowed_transforms_for_annotation(annotations.get(tested_parameter))
        variant = create_model(
            f"MeasuredBoundary_{index}",
            __base__=GenerationBoundary,
            parameter=(Literal[tested_parameter], ...),
            numeric_kind=(Literal["integer", "float", "discrete"], ...),
            transform=(transform_type, ...),
            lower=(Number | None, ...),
            upper=(Number | None, ...),
            context=(context_model, ...),
            nominal=(arguments_model, ...),
        )
        variants.append(variant)
    return variants[0] if len(variants) == 1 else Union[tuple(variants)]


def _build_ep_bva_catalogue_type(sections, boundary_type):
    """Separate applicable catalogues from non-applicable/unresolved via disjoint fields.

    Every anyOf branch MUST place 'status' FIRST in property order so xgrammar /
    strict JSON Schema guided decoding never locks out 'applicable' when the model
    emits '{"catalogue": {"status":' first, while keeping classes/boundaries exclusively
    on ApplicableCatalogue and reason exclusively on NonApplicableCatalogue.
    """
    applicable_fields = {
        "status": (Literal["applicable"], ...),
    }
    if "classes" in sections:
        applicable_fields["classes"] = (list[MeasuredClass], Field(min_length=1))
    if "boundaries" in sections:
        applicable_fields["boundaries"] = (list[boundary_type], Field(min_length=1))

    non_applicable_fields = {
        "status": (Literal["not_applicable", "unresolved"], ...),
        "reason": (
            str,
            Field(
                min_length=1,
                max_length=400,
                description="ONLY explain why EP+BVA genuinely cannot apply; NEVER summarize generated tests here.",
            ),
        ),
    }

    applicable_model = create_model("ApplicableCatalogue", __base__=Schema, **applicable_fields)
    non_applicable_model = create_model("NonApplicableCatalogue", __base__=Schema, **non_applicable_fields)
    # Plain Union emits standard JSON Schema anyOf (consistent with DT variants).
    return Union[applicable_model, non_applicable_model]


def _build_decision_table_catalogue_type():
    """Fixed 1..4 Boolean table variants for applicable status, plus a disjoint non-applicable branch."""
    variants = []
    for condition_count in range(1, 5):
        predicate_fields = {
            f"C{index + 1}": (str, Field(min_length=1, max_length=2048))
            for index in range(condition_count)
        }
        predicates_model = create_model(f"Conditions{condition_count}", __base__=Schema, **predicate_fields)
        table_fields = {
            "R" + "".join(bits): (FeasibleOutcome | InfeasibleOutcome, ...)
            for bits in product("01", repeat=condition_count)
        }
        table_model = create_model(f"OriginalTable{condition_count}", __base__=Schema, **table_fields)
        variants.append(
            create_model(
                f"ApplicableDecisionCatalogue{condition_count}",
                __base__=Schema,
                status=(Literal["applicable"], ...),
                condition_predicates=(predicates_model, ...),
                rules=(table_model, ...),
            )
        )
    non_applicable_dt = create_model(
        "NonApplicableDecisionCatalogue",
        __base__=Schema,
        status=(Literal["not_applicable", "unresolved"], ...),
        reason=(
            str,
            Field(
                min_length=1,
                max_length=400,
                description="ONLY explain why no Boolean decision table can apply; NEVER summarize generated tests here.",
            ),
        ),
    )
    variants.append(non_applicable_dt)
    return Union[tuple(variants)]


def response_type(task, sections, input_budget):
    """Construct the strict Pydantic schema enforced during structured generation."""
    builder = CallBuilder.for_source(task["prompt"], task["entry_point"])
    parameter_names = tuple(builder.signature.parameters)
    try:
        annotations = declared_types(task["prompt"], task["entry_point"])
    except ValueError:
        annotations = {}
    type_map = _argument_type_map()

    argument_fields = {}
    for name, parameter in builder.signature.parameters.items():
        field_type = type_map.get(annotations.get(name), JsonValue)
        default_value = ... if parameter.default is inspect.Parameter.empty else parameter.default
        argument_fields[name] = (field_type, default_value)
    arguments_model = create_model("CatalogueArguments", __base__=Schema, **argument_fields)

    input_record = create_model(
        "CatalogueInput",
        __base__=Schema,
        arguments=(arguments_model, ...),
        covers=(list[str], Field(default_factory=list)),
    )

    if "rules" in sections:
        catalogue_type = _build_decision_table_catalogue_type()
    else:
        boundary_type = (
            _build_boundary_type(parameter_names, annotations, type_map, arguments_model)
            if "boundaries" in sections
            else None
        )
        catalogue_type = _build_ep_bva_catalogue_type(sections, boundary_type)

    return create_model(
        "Vf3MeasuredResponse",
        __base__=Schema,
        catalogue=(catalogue_type, ...),
        inputs=(list[input_record], Field(max_length=input_budget)),
    )


def _condition_sort_key(name):
    if name.startswith("C") and name[1:].isdigit():
        return (0, int(name[1:]), name)
    return (1, 0, name)


def canonical_response(value, sections, *, task=None):
    """Normalize structured responses into canonical Catalogue views without inventing metadata."""
    result = copy.deepcopy(value)
    catalogue = result.get("catalogue")
    if not isinstance(catalogue, dict):
        return result

    raw_annotations = {}
    if task is not None:
        builder = CallBuilder.for_source(task["prompt"], task["entry_point"])
        for name, parameter in builder.signature.parameters.items():
            if parameter.annotation is not inspect.Parameter.empty:
                raw_annotations[name] = parameter.annotation

    if "classes" in sections:
        catalogue.setdefault("classes", [])
    if "boundaries" in sections:
        catalogue.setdefault("boundaries", [])
        if isinstance(catalogue.get("boundaries"), list):
            for boundary in catalogue["boundaries"]:
                if not isinstance(boundary, dict):
                    continue
                context = boundary.get("context")
                if isinstance(context, dict):
                    tested = boundary.get("parameter")
                    cleaned_context = {}
                    for name, field_value in context.items():
                        if name == tested:
                            continue
                        # None is the schema sentinel for an unconstrained context parameter
                        # unless the function signature explicitly annotates Optional / | None.
                        if field_value is None and not _annotation_allows_none(raw_annotations.get(name)):
                            continue
                        cleaned_context[name] = field_value
                    boundary["context"] = cleaned_context

    if "rules" in sections:
        catalogue.pop("conditions", None)
        catalogue.pop("mutually_exclusive", None)
        catalogue.setdefault("condition_predicates", {})
        table = catalogue.get("rules")
        if table is None:
            catalogue["original_rules"] = []
            catalogue["rules"] = []
        elif isinstance(table, dict):
            condition_names = sorted(catalogue.get("condition_predicates", {}), key=_condition_sort_key)
            original_rows = []
            for identifier, outcome in table.items():
                assignments = {
                    name: bit == "1"
                    for name, bit in zip(condition_names, identifier[1:])
                }
                original_rows.append({"id": identifier, "conditions": assignments, **outcome})
            catalogue["original_rules"] = original_rows
            catalogue["rules"] = [
                {
                    key: row[key]
                    for key in ("id", "conditions", "actions", "fault_hypothesis")
                    if key in row
                }
                for row in original_rows
                if row.get("status") == "feasible"
            ]
    return result


def membership_errors(catalogue, task):
    """Check static predicate support and BVA/DT metadata completeness before execution."""
    builder = CallBuilder.for_source(task["prompt"], task["entry_point"])
    parameter_names = builder.signature.parameters
    try:
        annotations = declared_types(task["prompt"], task["entry_point"])
    except ValueError:
        annotations = {}
    expression_types = {name: annotations.get(name, "any") for name in parameter_names}
    errors = []

    def check_predicate(identifier, text):
        try:
            validate_expression(text, expression_types)
        except (ValueError, TypeError, SyntaxError, RecursionError) as error:
            errors.append(f"{identifier}:{str(error)[:200]}")

    for item in catalogue.classes:
        if item.predicate is None:
            errors.append(f"{item.id}:missing_predicate")
        else:
            check_predicate(item.id, item.predicate)

    for item in catalogue.boundaries:
        if item.numeric_kind != "discrete" and item.lower is None and item.upper is None:
            errors.append(f"{item.id}:missing_numeric_endpoint")
        if item.numeric_kind == "float" and item.step is None and (item.lower is not None or item.upper is not None):
            errors.append(f"{item.id}:missing_float_step")
        if item.transform == "count" and item.count_value is None:
            errors.append(f"{item.id}:missing_count_value")
        if item.parameter in annotations and annotations[item.parameter] == "str":
            if item.transform == "count" and item.count_value is not None and type(item.count_value) is not str:
                errors.append(f"{item.id}:str_count_requires_str_count_value")
            if item.transform == "identity" and item.numeric_kind != "discrete":
                errors.append(f"{item.id}:str_identity_requires_discrete_numeric_kind")
        if item.parameter in annotations and annotations[item.parameter] in LIST_ANNOTATIONS and item.transform == "identity":
            errors.append(f"{item.id}:list_identity_transform_unsupported")
        if item.parameter is not None and item.parameter in item.context:
            errors.append(f"{item.id}:context_contains_tested_parameter")
        if not set(item.context) <= set(parameter_names):
            errors.append(f"{item.id}:unknown_context_parameter")
        if item.nominal is None:
            errors.append(f"{item.id}:missing_nominal_arguments")
        elif set(item.nominal) != set(parameter_names):
            errors.append(f"{item.id}:incomplete_nominal_arguments")
        else:
            try:
                builder.build(item.nominal)
            except (ValueError, TypeError, RecursionError) as error:
                errors.append(f"{item.id}:invalid_nominal:{str(error)[:100]}")
            else:
                decoded_nominal = {key: decode_value(val) for key, val in item.nominal.items()}
                if not matches_context(decoded_nominal, effective_boundary_context(item)):
                    errors.append(f"{item.id}:nominal_violates_context")
                if not selected_value(item, decoded_nominal)[1]:
                    errors.append(f"{item.id}:nominal_selector_unavailable")

    if catalogue.rules or catalogue.original_rules or catalogue.condition_predicates:
        for name, text in catalogue.condition_predicates.items():
            check_predicate(name, text)
        for rule in catalogue.rules + catalogue.original_rules:
            for name, value in rule.conditions.items():
                if value != "-" and name not in catalogue.condition_predicates:
                    errors.append(f"{rule.id}:missing_condition_predicate:{name}")
        if catalogue.status == "applicable" and not catalogue.original_rules:
            errors.append("missing_original_rules")

    return errors
