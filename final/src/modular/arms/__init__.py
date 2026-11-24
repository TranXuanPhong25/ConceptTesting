"""Supported input-generation methods for the current pipeline."""
from .plain import PlainArm
from .fault_oriented import V2_ARMS
from .vf3_measured import VF3_MEASURED_ARMS
from .control_flow import ControlFlowArm


def default_arms():
    return (PlainArm(),)


def available_arms():
    return (
        PlainArm(),
        *(arm() for arm in V2_ARMS),
        *(arm() for arm in VF3_MEASURED_ARMS),
        ControlFlowArm(),
    )


def selected_arms(names):
    available = {arm.name: arm for arm in available_arms()}
    result = []
    for name in names:
        if name not in available:
            raise ValueError(f"Unknown input-generation method: {name}")
        result.append(available[name])
    return tuple(result)
