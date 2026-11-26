"""Shared entry point for generating or reading input batches."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..context import JsonObject, TaskContext


class InputGenerator(ABC):
    """Generate named input batches consumed by reference oracle and PUT evaluation."""

    methods = ()

    def prepare_context(self, context: TaskContext) -> None:
        """Optional per-task preparation before input generation."""

    @abstractmethod
    def generate(self, context: TaskContext) -> JsonObject:
        """Return {task_id, arms: {method_name: {inputs: [...]}}} or task skip."""

    def extend_summary(self, contexts, summary, reporter) -> None:
        pass

    def configuration(self) -> dict:
        return {}

    def runtime_dependencies(self) -> tuple[str, ...]:
        return ()
