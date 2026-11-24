"""Public input generation abstractions and the method composition adapter."""
from .base import InputGenerator
from .methods import MethodInputGenerator


def default_input_generator():
    from ..arms import default_arms

    return generator_for_arms(default_arms())


def generator_for_arms(arms):
    return MethodInputGenerator(arms)


__all__ = [
    "InputGenerator",
    "MethodInputGenerator",
    "default_input_generator",
    "generator_for_arms",
]
