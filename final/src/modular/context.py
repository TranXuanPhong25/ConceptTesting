"""Explicit data passed from one pipeline stage to the next."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from final.src.models.core_model import ModelResponse
from .artifacts import ArtifactStore

JsonObject = dict[str, Any]


class ModelCalls(Protocol):
    @property
    def model_id(self) -> str: ...

    def token_count(self, messages: list[dict[str, str]]) -> int: ...

    def complete(self, task_number: int, call_name: str, messages: list[dict[str, str]],
                 *, temperature: float, max_tokens: int, seed: int, response_format: dict | None = None) -> ModelResponse: ...

    def complete_structured(self, task_number: int, call_name: str, messages: list[dict[str, str]],
                            *, schema: dict, temperature: float, max_tokens: int, seed: int) -> ModelResponse: ...


@dataclass(frozen=True)
class PipelineSettings:
    input_budget: int = 20
    input_tokens: int = 2048
    input_temperature: float = .7
    input_seed: int = 314159
    reference_seed: int = 271828
    writer_seed: int = 20261030
    context_tokens: int = 8192
    timeout_seconds: float = 8
    target_programs: int = 10
    writer_rounds: int = 10


@dataclass
class TaskContext:
    task: JsonObject
    metadata: JsonObject
    artifacts: ArtifactStore
    settings: PipelineSettings
    calls: ModelCalls | None = None
    cohort_task: JsonObject | None = None
    generated_programs: list[JsonObject] = field(default_factory=list)
    generation_rejections: list[JsonObject] = field(default_factory=list)
    packet: JsonObject | None = None
    inputs: JsonObject | None = None
    oracle: JsonObject | None = None
    result: JsonObject | None = None
    completed_stages: set[str] = field(default_factory=set)
    extensions: JsonObject = field(default_factory=dict)

    @property
    def task_number(self) -> int:
        return int(self.task["task_id"].split("/")[1])

    @property
    def task_directory(self) -> str:
        return f"tasks/{self.task_number}"
