"""V11 concept extraction, followed by the modern one-call inputs-only generator."""
from pathlib import Path

from .base import ConceptArm
from ..stages.v11_concept import V11ConceptStage, select_concept_cards
from ..stages.v11_concept_reporting import V11ConceptReportingStage


class V11ConceptArm(ConceptArm):
    name = "v11_concept"

    def __init__(self, *, cache_directory=Path("final/out/v11_clean_runtimefix"),
                 cache_only=False, card_limit=4, resource_exclusions=None):
        if card_limit < 1:
            raise ValueError("At least one V11 concept card is required")
        self.cache_directory = Path(cache_directory).resolve() if cache_directory is not None else None
        self.cache_only = cache_only
        self.card_limit = card_limit
        self.resource_exclusions = Path(resource_exclusions).resolve() if resource_exclusions is not None else None

    def configuration(self):
        configuration = {
            "cache_directory": str(self.cache_directory) if self.cache_directory is not None else None,
            "cache_only": self.cache_only,
            "card_limit": self.card_limit,
            "selection": "rank-round-robin-over-visible-PUTs",
            "generator": "shared-inputs-only-one-call-per-task",
        }
        if self.resource_exclusions is not None:
            from ..stages.resource_exclusions import ResourceExclusionPlan
            configuration["resource_exclusions"] = ResourceExclusionPlan(self.resource_exclusions).configuration()
        return configuration

    def preparation_stages(self):
        return (V11ConceptStage(self.cache_directory, cache_only=self.cache_only,
                                resource_exclusions=self.resource_exclusions),)

    def reporting_stage(self):
        return V11ConceptReportingStage()

    def extend_analysis(self, context, visible_programs, analysis):
        analysis[self.name] = select_concept_cards(
            context.extensions["v11_concepts"], visible_programs, self.card_limit
        )
