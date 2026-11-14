"""Supported input-generation methods for the current pipeline."""
from .plain import PlainArm
from .boundary import BoundaryArm
from .classical import CATALOGUE_ARMS
from .fault_oriented import V2_ARMS
from .control_flow import ControlFlowArm
from .spec_obligation import SpecObligationArm, ControlFlowObligationArm


def default_arms():
    return (PlainArm(),)


def available_arms():
    return (PlainArm(), BoundaryArm(), *(arm() for arm in (*CATALOGUE_ARMS, *V2_ARMS)), ControlFlowArm(), SpecObligationArm(), ControlFlowObligationArm())


def selected_arms(names):
    available = {arm.name: arm for arm in available_arms()}
    result = []
    for name in names:
        if name not in available:
            raise ValueError(f"Unknown input-generation method: {name}")
        result.append(available[name])
    return tuple(result)
