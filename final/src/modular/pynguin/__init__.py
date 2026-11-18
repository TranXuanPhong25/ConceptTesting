"""Opt-in upstream Pynguin adapter; the tool lives in a separate interpreter."""
from .config import PynguinSettings

__all__ = ['PynguinSettings', 'PynguinInputGenerator']

def __getattr__(name):
    if name == 'PynguinInputGenerator':
        from .adapter import PynguinInputGenerator
        return PynguinInputGenerator
    raise AttributeError(name)
