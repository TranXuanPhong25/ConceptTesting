from abc import ABC, abstractmethod

from ..context import TaskContext


class PipelineStage(ABC):
    """Implement run(context); declare dependencies so invalid order fails early."""
    name: str
    requires: tuple[str, ...] = ()

    @abstractmethod
    def run(self, context: TaskContext) -> None:
        """Read explicit context fields, then fill the fields needed by later stages."""

    def configuration(self) -> dict:
        """Override when a custom stage introduces configurable behavior."""
        if vars(self):
            raise NotImplementedError("Configured stages must expose their configuration for cache invalidation")
        return {}
