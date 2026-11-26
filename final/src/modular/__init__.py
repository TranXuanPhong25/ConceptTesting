"""Registry for modular input generation."""


def default_arms():
    return selected_arms(('plain',))


def arm_factories():
    from .plain import PlainArm
    from .black_box import VF3_HYBRID_ARMS
    from .control_flow import ControlFlowArm, ControlFlowFourToolArm
    from .spec_obligation import RepairedControlFlowObligationArm

    return {
        PlainArm.name: PlainArm,
        **{arm.name: arm for arm in VF3_HYBRID_ARMS},
        ControlFlowArm.name: ControlFlowArm,
        ControlFlowFourToolArm.name: ControlFlowFourToolArm,
        RepairedControlFlowObligationArm.name: RepairedControlFlowObligationArm,
    }


def available_arms():
    return tuple(factory() for factory in arm_factories().values())


def selected_arms(names, *, tool_runs_dir=None):
    factories = arm_factories()
    result = []
    for name in names:
        if name not in factories:
            raise ValueError(f"Unknown input-generation method: {name}")
        if name == 'control_flow_4tool':
            result.append(factories[name](tool_runs_dir=tool_runs_dir))
        else:
            result.append(factories[name]())
    return tuple(result)
