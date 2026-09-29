from __future__ import annotations

import json
import re
from typing import Any

from .models import ConceptRecord, MechanismRecord, UnitStructure

MECHANISM_SCHEMA = {
    "what": "violated semantic constraint and buggy deviation",
    "where": "applicability conditions and compatible local code shapes",
    "how": "injectable edit direction that reproduces the deviation",
    "expected_buggy_behavior": "externally observable buggy behavior",
    "expected_failure_signal": "assertion-visible difference from the correct version",
}


def mechanism_extraction_prompt(correct: str, buggy: str, dependencies: str = "") -> str:
    return f"""Abstract one transferable real-bug mechanism from this aligned bug unit.
Do not copy project-specific names into general rules. Return one JSON object and no markdown.
Required string keys: {', '.join(MECHANISM_SCHEMA)}.

Correct local code:
{correct}

Buggy local code:
{buggy}

Related dependencies and context:
{dependencies}
"""


def concept_extraction_prompt(mechanism: MechanismRecord, focal_source: str, context: str = "") -> str:
    return f"""Instantiate the mechanism as an explicit test concept for the focal method.
Return one JSON object with exactly these string keys: trigger_input_relation, expected_oracle.
The trigger must describe a concrete relation among input values or state. The oracle must describe
an externally observable assertion on the correct program, not an implementation detail.

Violated constraint: {mechanism.what}
Applicability: {mechanism.where}
Injection intent: {mechanism.how}
Expected difference: {mechanism.expected_failure_signal}

Focal source:
{focal_source}

Repository context:
{context}
"""


def _json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model output is not one JSON object: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("model output must be a JSON object")
    return value


def parse_mechanism(
    text: str, mechanism_id: str, evidence_ids: tuple[str, ...], structures: tuple[UnitStructure, ...], source_project: str
) -> MechanismRecord:
    value = _json_object(text)
    missing = [key for key in MECHANISM_SCHEMA if not isinstance(value.get(key), str) or not value[key].strip()]
    if missing:
        raise ValueError("missing mechanism fields: " + ", ".join(missing))
    return MechanismRecord(mechanism_id, *(value[key].strip() for key in MECHANISM_SCHEMA), evidence_ids, structures, source_project)


def parse_concept(text: str, mechanism: MechanismRecord) -> ConceptRecord:
    value = _json_object(text)
    allowed = {"trigger_input_relation", "expected_oracle"}
    if set(value) != allowed or any(not isinstance(value[key], str) or not value[key].strip() for key in allowed):
        raise ValueError("concept output must contain exactly two non-empty string fields")
    concept = ConceptRecord(mechanism.id, mechanism.what, mechanism.where,
                            value["trigger_input_relation"].strip(), value["expected_oracle"].strip(),
                            mechanism.evidence_ids)
    concept.validate()
    return concept

