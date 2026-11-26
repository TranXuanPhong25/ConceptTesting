"""VF3 equivalence partitioning and boundary value analysis."""
from __future__ import annotations

import ast
import copy
from typing import Annotated, Literal, Union

from pydantic import Field, JsonValue, create_model

from ..call_builder import CallBuilder
from .catalogue import Boundary, Number, Schema, boundary_targets
from .vf3_hybrid import StructuredCatalogueArm


EP_BVA_GUIDANCE = (
    "Use Equivalence Partitioning (EP) with normal Boundary Value Analysis (BVA). "
    "Start from specification behaviors and input dependencies.\n"
    "Partition by meaningful rules, result categories and jointly valid combinations, "
    "rather than numeric ranges alone. Use plausible specification-supported fault "
    "hypotheses to refine classes; split or merge when a different fault could be hidden.\n"
    "Choose typical representatives that satisfy their class, keeping unrelated values ordinary; "
    "then add useful class-edge min/min+, max-/max tests, varying one quantity at a time.\n"
    "Check membership and remove redundancy unless tests distinguish different plausible faults. "
    "Other useful tests are welcome. List classes and boundaries in the catalogue."
)


EP_BVA_EXAMPLE = (
    "One possible example is package-version filtering (packaging SpecifierSet.filter). With a final-only specifier such as >=2.0, "
    "prereleases=None keeps matching prereleases only when no matching final survives; prereleases=True or False changes that policy. "
    "A final outside the specifier must not suppress an otherwise matching prerelease. Useful ideas might compare candidate lists "
    "[2.1a1], [1.9,2.1a1] and [2.1a1,2.1], in either order, then consider explicit policy overrides. These classes depend on policy "
    "and the filtered candidate set, not separate numeric intervals alone. A plausible fault is checking for any final before applying "
    "the specifier. A prerelease/final transition can suggest extra boundary tests. This illustrates possible reasoning, not required "
    "class names or a complete suite; use other ideas when better."
)


EP_BVA_R1_INSTRUCTION = """Set status="applicable" with one shared catalogue.nominal, unique class IDs E1, E2.. and boundary IDs B1, B2.. (never reuse IDs across sections), and spec-derived boundaries.
Every class predicate MUST be pure executable Python boolean syntax ONLY over exact parameter names (NO English prose, NO undefined loop vars like i — use any/all generators and guard empty sequences/indices).
For boundaries: use transform="length" (upper=null when unbounded, never invent upper=30), numeric_kind="discrete" with explicit values for unbounded discrete points (never both lower=null and upper=null), and positive step for floats.
Include nominal and single-fault boundary inputs alongside broader fault-revealing edge cases."""


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


class EpBvaArm(StructuredCatalogueArm):
    name = "ep_bva_vf3_hybrid"
    sections = ("classes", "boundaries")
    guidance = EP_BVA_GUIDANCE
    soft_example = EP_BVA_EXAMPLE
    round1_instruction = EP_BVA_R1_INSTRUCTION

    def build_catalogue_type(self, arguments_model, annotations, type_map):
        parameter_names = tuple(arguments_model.model_fields)
        boundary_type = _build_boundary_type(parameter_names, annotations, type_map)
        applicable_fields = {
            "status": (Literal["applicable"], ...),
            "nominal": (arguments_model, ...),
            "classes": (list[HybridMeasuredClass], Field(min_length=1)),
            "boundaries": (list[boundary_type], Field(min_length=1)),
        }
        non_applicable = create_model(
            "NonApplicableHybridCatalogue",
            __base__=Schema,
            status=(Literal["not_applicable", "unresolved"], ...),
            reason=(str, Field(min_length=1, max_length=400)),
        )
        applicable = create_model("ApplicableHybridCatalogue", __base__=Schema, **applicable_fields)
        return Union[applicable, non_applicable]

    def normalize_catalogue(self, value, *, task):
        catalogue = copy.deepcopy(value)
        for item in catalogue.setdefault("classes", []):
            item["description"] = (item.get("fault_hypothesis") or item["predicate"])[:160]

        parameters = CallBuilder.for_source(task["prompt"], task["entry_point"]).signature.parameters
        shared_nominal = catalogue.pop("nominal", None)
        for boundary in catalogue.setdefault("boundaries", []):
            tested = boundary["parameter"]
            cleaned_context = {
                name: field_value
                for name, field_value in boundary["context"].items()
                if name != tested and (field_value is not None or _annotation_allows_none(parameters[name].annotation))
            }
            boundary["context"] = cleaned_context
            transform = boundary["transform"]
            boundary["dimension"] = (
                f"{tested}:count({boundary['count_value']!r})" if transform == "count" else f"{tested}:{transform}"
            )
            if "values" not in boundary:
                boundary["values"] = _derive_numeric_boundary_values(boundary)
            boundary["nominal"] = {**shared_nominal, **cleaned_context}
        return catalogue

    def summarize_catalogue(self, catalogue):
        if not isinstance(catalogue, dict):
            return {}
        return {
            "existing_classes": [
                {"id": row["id"], "predicate": row.get("predicate")}
                for row in catalogue.get("classes", []) if isinstance(row, dict) and "id" in row
            ],
            "existing_boundaries": [
                {k: row[k] for k in ("id", "parameter", "transform", "count_value", "numeric_kind", "lower", "upper", "values") if row.get(k) is not None}
                for row in catalogue.get("boundaries", []) if isinstance(row, dict) and "id" in row
            ],
        }
