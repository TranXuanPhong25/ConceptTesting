"""Public input generation abstractions and the method composition adapter."""
from .base import InputGenerator, InputMethod
from .methods import MethodInputGenerator


def default_input_generator():
    from ..arms import default_arms
    return generator_for_arms(default_arms())


def generator_for_arms(arms):
    """Compatibility composition at the boundary; the orchestrator only sees a generator."""
    arms = tuple(arms)
    if any(arm.requires_classical_analysis or arm.requires_witness_pool for arm in arms):
        from .legacy import LegacyArmInputGenerator
        return LegacyArmInputGenerator(arms)
    return MethodInputGenerator(arms)


__all__ = ["InputGenerator", "InputMethod", "MethodInputGenerator"]
