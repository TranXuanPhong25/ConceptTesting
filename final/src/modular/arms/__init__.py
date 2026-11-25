"""Supported input-generation methods for the current pipeline."""
from .plain import PlainArm
from .vf3_hybrid import VF3_HYBRID_ARMS
from .control_flow import ControlFlowArm, ControlFlowFourToolArm


def default_arms():
    return (PlainArm(),)


def available_arms():
    return (
        PlainArm(),
        *(arm() for arm in VF3_HYBRID_ARMS),
        ControlFlowArm(),
        ControlFlowFourToolArm(),
    )


def selected_arms(names):
    available = {arm.name: arm for arm in available_arms()}
    result = []
    for name in names:
        if name not in available:
            raise ValueError(f"Unknown input-generation method: {name}")
        result.append(available[name])
    return tuple(result)
