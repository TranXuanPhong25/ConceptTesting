"""Explicit compatibility adapter for archived concept/witness experiments."""
from .methods import MethodInputGenerator


class LegacyArmInputGenerator(MethodInputGenerator):
    """Old preparation is opt-in and absent from the modern orchestration module."""
    cache_input_execution = False

    def __init__(self, arms):
        from ..stages.concept_analysis import ConceptAnalysisStage
        from ..stages.witness_sampling import WitnessSamplingStage
        from ..arms.toolinput import ToolInputArm

        arms = tuple(arms)
        preparation = {}
        for arm in arms:
            for stage in arm.preparation_stages():
                previous = preparation.get(stage.name)
                if previous is not None and previous.configuration() != stage.configuration():
                    raise ValueError(f"Conflicting preparation stage configuration: {stage.name}")
                preparation[stage.name] = stage
        stages = (*preparation.values(), ConceptAnalysisStage(arms), WitnessSamplingStage(ToolInputArm()))
        super().__init__(arms, preparation_stages=stages)
