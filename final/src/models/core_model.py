"""Model response/interface shared by transports, including models.vertex.VertexAIModel."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelResponse:
    text: str
    usage: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None


class ModelError(RuntimeError):
    """Sanitized transport error; never includes credentials or endpoint URLs."""


class CoreModel(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str:
        """Stable identifier recorded in run manifests."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], *, temperature: float,
                 max_tokens: int, seed: int) -> ModelResponse:
        """One model invocation, without automatic retries."""
