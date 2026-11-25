"""Lean strict JSON Schema contract and canonicalization for VF3 Hybrid Round 1."""
from __future__ import annotations

import ast
import copy
import inspect
from itertools import product
from typing import Annotated, Literal, Union

from pydantic import Field, JsonValue, create_model

from .call_builder import CallBuilder
from .catalogue import Boundary, Number, Schema, boundary_targets
from .input_buckets.predicates import declared_types
from .tool_sampling.schema import validate_expression

PositiveStep = Annotated[int, Field(gt=0)] | Annotated[float, Field(gt=0)]


class EmptyObject(Schema):
    """Strict empty object used when no other parameters exist."""


class HybridMeasuredClass(Schema):
    """Minimal measurable equivalence class without redundant description prose."""

    id: str = Field(min_length=2, max_length=16, pattern=r"^E[0-9]+$")
    predicate: str = Field(
        min_length=1,
        max_length=2048,
        description="Pure executable Python boolean expression over exact parameter names; no English prose.",
    )
    fault_hypothesis: str | None = Field(default=None, min_length=1, max_length=240)


class HybridFeasibleOutcome(Schema):
    """Lean feasible DT row: status first, optional fault_hypothesis."""

    status: Literal["feasible"]
    fault_hypothesis: str | None = Field(default=None, min_length=1, max_length=240)


class HybridInfeasibleOutcome(Schema):
    """Lean infeasible/unresolved DT row: status only."""

    status: Literal["infeasible", "unresolved"]


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


def _annotation_allows_none(annotation):
    if not isinstance(annotation, str) or not annotation.strip():
        return False
    try:
        node = ast.parse(annotation, mode="eval").body
    except SyntaxError:
        return False
    return any(
        (isinstance(child, ast.Constant) and child.value is None)
        or (isinstance(child, ast.Name) and child.id in ("None", "Optional"))
        or (isinstance(child, ast.Attribute) and child.attr == "Optional")
        for child in ast.walk(node)
    )


def _condition_sort_key(name):
    if name.startswith("C") and name[1:].isdigit():
        return (0, int(name[1:]), name)
    return (1, 0, name)


def _build_boundary_type(parameter_names, annotations, type_map):
    """Flat 3-branch boundary schema (numeric, count, discrete) with aligned leading keys."""
    if parameter_names:
        context_fields = {
            name: (type_map.get(annotations.get(name), JsonValue) | None, None)
            for name in parameter_names
        }
        context_model = create_model("HybridBoundaryContext", __base__=Schema, **context_fields)
        param_type = Literal[parameter_names]
    else:
        context_model = EmptyObject
        param_type = str

    numeric_branch = create_model(
        "HybridNumericBoundary",
        __base__=Schema,
        id=(str, Field(min_length=2, max_length=16, pattern=r"^B[0-9]+$")),
        parameter=(param_type, ...),
        transform=(Literal["identity", "length", "parsed_int", "parsed_float"], ...),
        numeric_kind=(Literal["integer", "float"], ...),
        lower=(Number | None, ...),
        upper=(Number | None, ...),
        step=(PositiveStep | None, None),
        context=(context_model, ...),
    )
    count_branch = create_model(
        "HybridCountBoundary",
        __base__=Schema,
        id=(str, Field(min_length=2, max_length=16, pattern=r"^B[0-9]+$")),
        parameter=(param_type, ...),
        transform=(Literal["count"], ...),
        numeric_kind=(Literal["integer"], ...),
        count_value=(Union[type_map["int"], float, Annotated[str, Field(max_length=100)], bool], ...),
        lower=(Annotated[int, Field(ge=0)] | None, ...),
        upper=(Annotated[int, Field(ge=0)] | None, ...),
        context=(context_model, ...),
    )
    discrete_branch = create_model(
        "HybridDiscreteBoundary",
        __base__=Schema,
        id=(str, Field(min_length=2, max_length=16, pattern=r"^B[0-9]+$")),
        parameter=(param_type, ...),
        transform=(Literal["identity", "length"], ...),
        numeric_kind=(Literal["discrete"], ...),
        values=(list[Number | str | bool], Field(min_length=1, max_length=16)),
        context=(context_model, ...),
    )
    return Union[numeric_branch, count_branch, discrete_branch]


def _build_ep_bva_catalogue_type(sections, boundary_type, arguments_model):
    applicable_fields = {"status": (Literal["applicable"], ...)}
    if "boundaries" in sections:
        applicable_fields["nominal"] = (arguments_model, ...)
    if "classes" in sections:
        applicable_fields["classes"] = (list[HybridMeasuredClass], Field(min_length=1))
    if "boundaries" in sections:
        applicable_fields["boundaries"] = (list[boundary_type], Field(min_length=1))

    non_applicable = create_model(
        "NonApplicableHybridCatalogue",
        __base__=Schema,
        status=(Literal["not_applicable", "unresolved"], ...),
        reason=(str, Field(min_length=1, max_length=400)),
    )
    applicable = create_model("ApplicableHybridCatalogue", __base__=Schema, **applicable_fields)
    return Union[applicable, non_applicable]


def _build_dt_catalogue_type():
    variants = []
    for condition_count in range(1, 5):
        predicates = create_model(
            f"HybridConditions{condition_count}",
            __base__=Schema,
            **{f"C{i + 1}": (str, Field(min_length=1, max_length=2048)) for i in range(condition_count)},
        )
        table = create_model(
            f"HybridOriginalTable{condition_count}",
            __base__=Schema,
            **{
                "R" + "".join(bits): (HybridFeasibleOutcome | HybridInfeasibleOutcome, ...)
                for bits in product("01", repeat=condition_count)
            },
        )
        variants.append(
            create_model(
                f"ApplicableHybridDecisionCatalogue{condition_count}",
                __base__=Schema,
                status=(Literal["applicable"], ...),
                condition_predicates=(predicates, ...),
                rules=(table, ...),
            )
        )
    variants.append(
        create_model(
            "NonApplicableHybridDecisionCatalogue",
            __base__=Schema,
            status=(Literal["not_applicable", "unresolved"], ...),
            reason=(str, Field(min_length=1, max_length=400)),
        )
    )
    return Union[tuple(variants)]


def response_type(task, sections, input_budget):
    """Construct the lean strict Pydantic schema enforced during Round 1."""
    builder = CallBuilder.for_source(task["prompt"], task["entry_point"])
    parameter_names = tuple(builder.signature.parameters)
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

    if "rules" in sections:
        catalogue_type = _build_dt_catalogue_type()
    else:
        boundary_type = _build_boundary_type(parameter_names, annotations, type_map) if "boundaries" in sections else None
        catalogue_type = _build_ep_bva_catalogue_type(sections, boundary_type, arguments_model)

    return create_model(
        "Vf3HybridResponse",
        __base__=Schema,
        catalogue=(catalogue_type, ...),
        inputs=(list[input_record], Field(max_length=input_budget)),
    )


def _derive_numeric_boundary_values(boundary_dict):
    probe_payload = {
        "id": boundary_dict.get("id", "B"),
        "dimension": "probe",
        "values": [0],
        **{
            key: boundary_dict.get(key)
            for key in ("parameter", "transform", "count_value", "numeric_kind", "lower", "upper", "step")
        },
    }
    probe_payload["transform"] = probe_payload["transform"] or "identity"
    try:
        targets = boundary_targets(Boundary.model_validate(probe_payload))
    except Exception:
        targets = []
    if targets:
        return targets
    return [v for v in (boundary_dict.get("lower"), boundary_dict.get("upper")) if v is not None] or [0]


def canonical_response(value, sections, *, task=None):
    """Normalize lean Round 1 output into canonical Catalogue views."""
    result = copy.deepcopy(value)
    catalogue = result.get("catalogue")
    if not isinstance(catalogue, dict):
        return result

    raw_annotations = {}
    if task is not None:
        builder = CallBuilder.for_source(task["prompt"], task["entry_point"])
        raw_annotations = {
            name: param.annotation
            for name, param in builder.signature.parameters.items()
            if param.annotation is not inspect.Parameter.empty
        }

    shared_nominal = catalogue.pop("nominal", None)

    if "classes" in sections:
        catalogue.setdefault("classes", [])
        for item in catalogue["classes"]:
            if isinstance(item, dict) and not item.get("description"):
                derived = item.get("fault_hypothesis") or item.get("predicate") or item.get("id") or "class"
                item["description"] = str(derived)[:160]

    if "boundaries" in sections:
        catalogue.setdefault("boundaries", [])
        for boundary in catalogue["boundaries"]:
            if not isinstance(boundary, dict):
                continue
            tested = boundary.get("parameter")
            context = boundary.get("context") or {}
            cleaned_context = {
                name: field_value
                for name, field_value in context.items()
                if name != tested and (field_value is not None or _annotation_allows_none(raw_annotations.get(name)))
            }
            boundary["context"] = cleaned_context
            if not boundary.get("dimension"):
                transform = boundary.get("transform", "identity")
                boundary["dimension"] = (
                    f"{tested}:count({boundary.get('count_value')!r})"
                    if transform == "count"
                    else f"{tested}:{transform}"
                )
            if not boundary.get("values"):
                boundary["values"] = _derive_numeric_boundary_values(boundary)
            if boundary.get("nominal") is None and isinstance(shared_nominal, dict):
                boundary["nominal"] = {**shared_nominal, **cleaned_context}

    if "rules" in sections:
        catalogue.pop("conditions", None)
        catalogue.pop("mutually_exclusive", None)
        catalogue.setdefault("condition_predicates", {})
        table = catalogue.get("rules")
        if not isinstance(table, dict):
            catalogue["original_rules"] = []
            catalogue["rules"] = []
        else:
            condition_names = sorted(catalogue["condition_predicates"], key=_condition_sort_key)
            original_rows = []
            for identifier, outcome in table.items():
                assignments = {name: bit == "1" for name, bit in zip(condition_names, identifier[1:])}
                row = {"id": identifier, "conditions": assignments, **outcome}
                row_status = row.get("status")
                if row_status == "feasible":
                    row.setdefault("actions", [f"rule:{identifier}"])
                elif row_status in ("infeasible", "unresolved"):
                    row.setdefault("actions", [])
                    row.setdefault("reason", f"{row_status}_declared")
                original_rows.append(row)
            catalogue["original_rules"] = original_rows
            catalogue["rules"] = [
                {key: row[key] for key in ("id", "conditions", "actions", "fault_hypothesis") if key in row}
                for row in original_rows
                if row.get("status") == "feasible"
            ]
    return result


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


__all__ = ["canonical_response", "membership_errors", "response_type"]
