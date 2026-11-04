from .plain import PlainArm
from .boundary import BoundaryArm

LEGACY_METHOD_NAMES = ("classical", "contrastive", "placebo", "toolinput", "witness_only", "v11_concept")


def default_arms():
    return (PlainArm(),)


def legacy_arms():
    """Archived six-arm comparison; only selected explicitly for compatibility."""
    from .classical import ClassicalArm
    from .contrastive import ContrastiveArm
    from .placebo import PlaceboArm
    from .toolinput import ToolInputArm
    from .witness_only import WitnessOnlyArm
    return (PlainArm(), ClassicalArm(), ContrastiveArm(), PlaceboArm(), ToolInputArm(), WitnessOnlyArm())


def available_arms():
    return (PlainArm(), BoundaryArm())


def legacy_available_arms():
    from .v11_concept import V11ConceptArm
    return legacy_arms() + (V11ConceptArm(), BoundaryArm())


def selected_arms(names, *, v11_cache_directory=None, v11_cache_only=False,
                  v11_resource_exclusions=None):
    available = {}
    candidates = available_arms()
    if set(names) - {arm.name for arm in candidates}:
        candidates = legacy_available_arms()
    for arm in candidates:
        available[arm.name] = arm
    if "v11_concept" in names:
        from .v11_concept import V11ConceptArm
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
