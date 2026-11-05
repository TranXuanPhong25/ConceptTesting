"""Supported input-generation methods for the current pipeline."""
from .plain import PlainArm
from .boundary import BoundaryArm


def default_arms():
    return (PlainArm(),)


def available_arms():
    return (PlainArm(), BoundaryArm())


def selected_arms(names):
    available = {arm.name: arm for arm in available_arms()}
    result = []
    for name in names:
        if name not in available:
            raise ValueError(f"Unknown input-generation method: {name}")
        result.append(available[name])
    return tuple(result)
