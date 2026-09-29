from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class UnitStructure:
    anchors: tuple[dict[str, str], ...]
    relations: tuple[str, ...]
    coarse_key: tuple[Any, ...]
    fingerprint: str

    def signatures(self) -> tuple[str, ...]:
        return tuple(f"{a['role']}:{a['signature']}" for a in self.anchors) + self.relations


@dataclass(frozen=True)
class MechanismRecord:
    id: str
    what: str
    where: str
    how: str
    expected_buggy_behavior: str
    expected_failure_signal: str
    evidence_ids: tuple[str, ...] = ()
    structures: tuple[UnitStructure, ...] = ()
    source_project: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConceptRecord:
    """The extension's executable semantic contract for input and oracle synthesis."""

    mechanism_id: str
    violated_constraint: str
    applicability_condition: str
    trigger_input_relation: str
    expected_oracle: str
    provenance: tuple[str, ...] = ()

    def validate(self) -> None:
        for name in (
            "mechanism_id",
            "violated_constraint",
            "applicability_condition",
            "trigger_input_relation",
            "expected_oracle",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"concept field {name} must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class TaskRecord:
    project: str
    bug_id: int
    focal_class: str
    focal_method: str
    fixed_checkout: str
    buggy_checkout: str
    source: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.project}-{self.bug_id}:{self.focal_class}#{self.focal_method}"

