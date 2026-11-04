from .plain import PlainArm
from .classical import ClassicalArm
from .contrastive import ContrastiveArm
from .placebo import PlaceboArm
from .toolinput import ToolInputArm
from .witness_only import WitnessOnlyArm
from .v11_concept import V11ConceptArm


def default_arms():
    return (PlainArm(), ClassicalArm(), ContrastiveArm(), PlaceboArm(), ToolInputArm(), WitnessOnlyArm())


def available_arms():
    return default_arms() + (V11ConceptArm(),)


def selected_arms(names, *, v11_cache_directory=None, v11_cache_only=False,
                  v11_resource_exclusions=None):
    available = {}
    for arm in available_arms():
        available[arm.name] = arm
    if "v11_concept" in names:
        configuration = {"cache_only": v11_cache_only}
        if v11_cache_directory is not None:
            configuration["cache_directory"] = v11_cache_directory
        if v11_resource_exclusions is not None:
            configuration["resource_exclusions"] = v11_resource_exclusions
        available["v11_concept"] = V11ConceptArm(**configuration)
    result = []
    for name in names:
        if name not in available:
            raise ValueError(f"Unknown experiment arm: {name}")
        result.append(available[name])
    return tuple(result)
