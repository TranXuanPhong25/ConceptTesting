"""Dependency-inversion contract: orchestration depends on this abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from ..context import TaskContext, JsonObject


class InputMethod(Protocol):
    """An arm or a stage can produce a batch without inheriting an arm class."""
    name: str

    def run(self, context: TaskContext) -> JsonObject: ...

    def configuration(self) -> dict: ...


class InputGenerator(ABC):
    """Generate named input batches consumed by the existing reference stage."""
    cache_input_execution = True

    def preparation_stages(self):
        return ()

    def post_reference_stages(self):
        return ()

    def post_evaluation_stages(self, execution_cache, reference_programs):
        return ()

    def runtime_dependencies(self):
        return ()

    def validate_generation(self, contexts):
        """Optional producer-specific admission check before oracle/PUT execution."""

    @abstractmethod
    def generate(self, context: TaskContext) -> JsonObject:
        """Return {task_id, arms: {method_name: {inputs: [...]}}} or task skip."""

    def configuration(self):
        if vars(self):
            raise NotImplementedError("Configured input generators must expose their configuration")
        return {}

    def source_dependencies(self):
        """Declare helper modules outside final/src/modular that affect generation."""
        return ()

    def dependency_objects(self):
        """Objects whose defining source files must enter the run manifest."""
        return ()

    def reporting_stage(self):
        return None

    def extend_summary(self, contexts, summary, reporting):
        pass

    def render_summary(self, summary):
        return ""
