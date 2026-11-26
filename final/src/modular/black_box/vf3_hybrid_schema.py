"""Shared strict response schema and catalogue predicate validation for VF3."""
from __future__ import annotations

import inspect
from typing import Annotated

from pydantic import Field, JsonValue, create_model

from ..arm_names import VF3_INPUTS_PER_ROUND
from ..call_builder import CallBuilder
from .catalogue import Schema
from ..common.predicates import declared_types
from ..tool_sampling.schema import validate_expression


def _argument_type_map():
    bounded_int = Annotated[int, Field(ge=-(2**32), le=2**32)]
    return {
        "int": bounded_int,
        "float": float,
        "bool": bool,
        "str": Annotated[str, Field(max_length=1000)],
        "list": Annotated[list[JsonValue], Field(max_length=30)],
        "list[int]": Annotated[list[bounded_int], Field(max_length=30)],
        "list[float]": Annotated[list[float], Field(max_length=30)],
        "list[str]": Annotated[list[str], Field(max_length=30)],
    }


def build_response_type(task, build_catalogue_type):
    """Construct the lean strict Pydantic schema enforced during Round 1."""
    builder = CallBuilder.for_source(task["prompt"], task["entry_point"])
    try:
        annotations = declared_types(task["prompt"], task["entry_point"])
    except ValueError:
        annotations = {}
    type_map = _argument_type_map()

    argument_fields = {
        name: (
            type_map.get(annotations.get(name), JsonValue),
            ... if param.default is inspect.Parameter.empty else param.default,
        )
        for name, param in builder.signature.parameters.items()
    }
    arguments_model = create_model("CatalogueArguments", __base__=Schema, **argument_fields)
    input_record = create_model(
        "CatalogueInput",
        __base__=Schema,
        arguments=(arguments_model, ...),
        covers=(list[str], Field(default_factory=list)),
    )

    catalogue_type = build_catalogue_type(arguments_model, annotations, type_map)

    return create_model(
        "Vf3HybridResponse",
        __base__=Schema,
        catalogue=(catalogue_type, ...),
        inputs=(list[input_record], Field(max_length=VF3_INPUTS_PER_ROUND)),
    )


def membership_errors(catalogue, task):
    """Lightweight static check for executable predicates and essential BVA/DT metadata."""
    builder = CallBuilder.for_source(task["prompt"], task["entry_point"])
    parameter_names = set(builder.signature.parameters)
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
        if item.predicate:
            check_predicate(item.id, item.predicate)
        else:
            errors.append(f"{item.id}:missing_predicate")

    for item in catalogue.boundaries:
        if item.numeric_kind != "discrete" and item.lower is None and item.upper is None:
            errors.append(f"{item.id}:missing_numeric_endpoint")
        if item.transform == "count" and item.count_value is None:
            errors.append(f"{item.id}:missing_count_value")
        if item.nominal is None or set(item.nominal) != parameter_names:
            errors.append(f"{item.id}:incomplete_nominal_arguments")

    if catalogue.rules or catalogue.original_rules or catalogue.condition_predicates:
        for name, text in catalogue.condition_predicates.items():
            check_predicate(name, text)
        if catalogue.status == "applicable" and not catalogue.original_rules:
            errors.append("missing_original_rules")

    return errors
