"""Data-only tool constructors, candidate evidence and post-freeze diagnostics."""

__all__ = ["ToolInputGenerator"]


def __getattr__(name):
    if name == "ToolInputGenerator":
        from .generator import ToolInputGenerator

        return ToolInputGenerator
    raise AttributeError(name)
