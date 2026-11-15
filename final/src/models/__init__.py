"""Model factory kept separate from the transport implementations."""
from __future__ import annotations


def create_model(*, backend=None, model_name=None, context=12288):
    if backend == 'qwen':
        from .model import QwenModel
        return QwenModel(context=context, timeout=300, expected_model=model_name)
    if backend == 'vertex':
        from .vertex import VertexAIModel
        return VertexAIModel(model=model_name, context=context, timeout=300)
    from .model import TransportError
    raise TransportError('configuration', 'UnknownModelBackend')
