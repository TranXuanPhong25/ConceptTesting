"""Registry for modular input generation."""


def default_arms():
    from .plain import PlainArm

    return (PlainArm(),)


def available_arms():
    from .black_box import VF3_HYBRID_ARMS
    from .control_flow import ControlFlowArm, ControlFlowFourToolArm
    from .spec_obligation import RepairedControlFlowObligationArm

    return (
        *default_arms(),
        *(arm() for arm in VF3_HYBRID_ARMS),
        ControlFlowArm(),
        ControlFlowFourToolArm(),
        RepairedControlFlowObligationArm(),
    )


def selected_arms(names):
    available = {arm.name: arm for arm in available_arms()}
    result = []
    for name in names:
        if name not in available:
            raise ValueError(f"Unknown input-generation method: {name}")
        result.append(available[name])
    return tuple(result)
