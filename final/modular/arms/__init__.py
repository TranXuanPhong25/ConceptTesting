from .plain import PlainArm
from .classical import ClassicalArm
from .contrastive import ContrastiveArm
from .placebo import PlaceboArm
from .toolinput import ToolInputArm
from .witness_only import WitnessOnlyArm


def default_arms():
    return (PlainArm(), ClassicalArm(), ContrastiveArm(), PlaceboArm(), ToolInputArm(), WitnessOnlyArm())


def selected_arms(names):
    available = {}
    for arm in default_arms():
        available[arm.name] = arm
    result = []
    for name in names:
        if name not in available:
            raise ValueError(f"Unknown experiment arm: {name}")
        result.append(available[name])
    return tuple(result)
