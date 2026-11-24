"""Dependency-inversion contract: orchestration depends on this abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..context import JsonObject, TaskContext


class InputGenerator(ABC):
    """Generate named input batches consumed by reference oracle and PUT evaluation."""

    cache_input_execution: bool = True

    def prepare_context(self, context: TaskContext) -> None:
        """Optional per-task preparation before input generation."""

    @abstractmethod
    def generate(self, context: TaskContext) -> JsonObject:
        """Return {task_id, arms: {method_name: {inputs: [...]}}} or task skip."""

    def validate_generation(self, contexts: list[TaskContext]) -> None:
        """Optional producer-specific admission check before oracle/PUT execution."""

    def post_reference(self, context: TaskContext) -> None:
        """Optional hook run after reference oracle admission, before PUT evaluation."""

    def post_evaluation(self, context: TaskContext, execution_cache, reference_programs) -> None:
        """Optional hook run after PUT evaluation."""

    def reporter(self):
        return None

    def extend_summary(self, contexts, summary, reporter) -> None:
        pass

    def configuration(self) -> dict:
        return {}

    def runtime_dependencies(self) -> tuple[str, ...]:
        return ()
