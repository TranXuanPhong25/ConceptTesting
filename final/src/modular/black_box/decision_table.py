"""VF3 decision table testing."""
from __future__ import annotations

import copy
from itertools import product
from typing import Literal, Union

from pydantic import Field, create_model

from .catalogue import Schema
from .vf3_hybrid import StructuredCatalogueArm


DECISION_TABLE_GUIDANCE = (
    "Use Decision Table Testing for behaviors determined by interacting conditions.\n"
    "Derive conditions and ordered actions from the specification; a condition may be "
    "an input predicate or relation, even when the function has only one parameter. "
    "Form combinations; distinguish feasible, infeasible and unresolved cases.\n"
    "Use plausible fault hypotheses to notice missing conditions, combinations or priorities.\n"
    "Vary interacting conditions across multiple feasible inputs per rule to expose subtle "
    "implementation bugs; use existing base calls as context and add NEW distinct contrasts.\n"
    "Check gaps, overlaps and representative membership; keep tests for distinct faults. "
    "Other useful tests are welcome. List the rules in the catalogue."
)


DECISION_TABLE_EXAMPLE = (
    "For example, HTTP response preconditions (Werkzeug Response.apply_conditions) combine method, validators and time. "
    "If-Match uses strong ETag comparison and, when present, takes precedence over If-Unmodified-Since. If-None-Match uses weak comparison; "
    "a match gives 304 for GET/HEAD but 412 for other methods. Its presence suppresses If-Modified-Since even when it does not match. "
    "Possible discriminating pairs use a matching strong If-Match with an otherwise failing date, a weakly matching If-None-Match under GET "
    "versus PUT, or a nonmatching If-None-Match with a date that alone would give 304. These can expose wrong precedence or merging rules "
    "across method-dependent actions. This is one source of test ideas, not a required table shape; only group conditions supported by the "
    "actual specification.\n\nTest a workshop receipt toggle when both settings have identical ordered actions under the spec. Hold the rest of the booking fixed."
)


DT_R1_INSTRUCTION = """Model 2 to 4 independent specification conditions C1..Cn (1 only for truly single-predicate specs) as pure executable Python boolean syntax ONLY over exact parameter names (NO English prose, NO undefined vars — use any/all generators and guard empty sequences/indices).
Mark each truth-table row R.. (e.g. R01: C1=false, C2=true) feasible (at least one, optional short fault_hypothesis), infeasible, or unresolved.
Do not stop at one input per rule: generate diverse fault-revealing contrasts and tricky edge cases across feasible rules up to the requested input budget."""


DT_CONDITION_CAP = 4


class HybridFeasibleOutcome(Schema):
    """Lean feasible DT row: status first, optional fault_hypothesis."""

    status: Literal["feasible"]
    fault_hypothesis: str | None = Field(default=None, min_length=1, max_length=240)


class HybridInfeasibleOutcome(Schema):
    """Lean infeasible/unresolved DT row: status only."""

    status: Literal["infeasible", "unresolved"]


class DecisionTableArm(StructuredCatalogueArm):
    name = "decision_table_vf3_hybrid"
    sections = ("rules",)
    guidance = DECISION_TABLE_GUIDANCE
    soft_example = DECISION_TABLE_EXAMPLE
    round1_instruction = DT_R1_INSTRUCTION

    def build_catalogue_type(self, arguments_model, annotations, type_map):
        variants = []
        for condition_count in range(1, DT_CONDITION_CAP + 1):
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

    def normalize_catalogue(self, value, *, task):
        catalogue = copy.deepcopy(value)
        condition_names = sorted(catalogue.setdefault("condition_predicates", {}))
        original_rows = []
        for identifier, outcome in catalogue.get("rules", {}).items():
            assignments = {name: bit == "1" for name, bit in zip(condition_names, identifier[1:])}
            row = {"id": identifier, "conditions": assignments, **outcome}
            if row["status"] == "feasible":
                row["actions"] = [f"rule:{identifier}"]
            else:
                row["actions"] = []
                row["reason"] = f"{row['status']}_declared"
            original_rows.append(row)
        catalogue["original_rules"] = original_rows
        catalogue["rules"] = [
            {key: row[key] for key in ("id", "conditions", "actions", "fault_hypothesis") if key in row}
            for row in original_rows
            if row["status"] == "feasible"
        ]
        return catalogue

    def summarize_catalogue(self, catalogue):
        if not isinstance(catalogue, dict):
            return {}
        return {
            "existing_conditions": dict(catalogue.get("condition_predicates") or {}),
            "feasible_rule_ids": [
                row["id"] for row in catalogue.get("original_rules", [])
                if isinstance(row, dict) and row.get("status") == "feasible"
            ],
        }
