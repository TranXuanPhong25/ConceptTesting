from abc import ABC, abstractmethod

from ..context import TaskContext, JsonObject


class PipelineStage(ABC):
    """Implement run(context); declare dependencies so invalid order fails early."""
    name: str
    requires: tuple[str, ...] = ()

    def source_dependencies(self):
        """Extra source files imported by this stage, included in the run manifest."""
        return ()

    @abstractmethod
    def run(self, context: TaskContext) -> JsonObject | None:
        """Update context; input-producing stages may return a batch for MethodInputGenerator."""

    def configuration(self) -> dict:
        """Override when a custom stage introduces configurable behavior."""
        if vars(self):
            raise NotImplementedError("Configured stages must expose their configuration for cache invalidation")
        return {}
