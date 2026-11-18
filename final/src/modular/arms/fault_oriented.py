"""V2 technique guidance: behavioral partitions, fault refinement and soft examples.

V1 prompts and defaults stay separate. Both versions share the same input decoder,
reference oracle, catalogue mechanics and evaluation policy.
"""
from .classical import CatalogueArm
from ..fault_oriented_testing.prompts import (
    EP_BVA_GUIDANCE, DECISION_TABLE_GUIDANCE, FAULT_HYPOTHESIS_OUTPUT_NOTE,
    soft_example_for,
)


class FaultOrientedArm(CatalogueArm):
    example_key = ""

    def source_dependencies(self):
        from pathlib import Path
        return (Path(__file__).parents[1] / 'fault_oriented_testing/soft_examples.json',)

    def configuration(self):
        return {**super().configuration(), "protocol":"testing-catalogue-v2",
                "example_key":self.example_key, "soft_example":soft_example_for(self.example_key),
                "output_note":FAULT_HYPOTHESIS_OUTPUT_NOTE,
                "semantic_fault_hypothesis_validation":"pending"}

    def build_guidance(self, packet):
        guidance = super().build_guidance(packet)
        if self.settings.catalogue:
            guidance += "\n" + FAULT_HYPOTHESIS_OUTPUT_NOTE
        return guidance + "\n\nSOFT EXAMPLE (another domain; adapt only useful ideas):\n" + soft_example_for(self.example_key)

    def extend_summary(self, contexts, summary, reporting):
        accounting = {"classes":0, "rules":0, "annotated_classes":0, "annotated_rules":0,
                      "status":"self_reported", "semantic_validation":"pending"}
        for context in contexts:
            batch = (context.inputs or {}).get('arms', {}).get(self.name, {})
            catalogue = batch.get('catalogue') or {}
            for section in ('classes', 'rules'):
                for obligation in catalogue.get(section, []):
                    accounting[section] += 1
                    accounting['annotated_' + section] += bool(obligation.get('fault_hypothesis'))
        summary.setdefault('fault_hypothesis_annotations', {})[self.name] = accounting


class EpBvaV2Arm(FaultOrientedArm):
    name = "ep_bva_v2"
    sections = ("classes", "boundaries")
    guidance = EP_BVA_GUIDANCE
    example_key = "ep_bva"


class DecisionTableV2Arm(FaultOrientedArm):
    name = "decision_table_v2"
    sections = ("rules",)
    guidance = DECISION_TABLE_GUIDANCE
    example_key = "decision_table"


V2_ARMS = (EpBvaV2Arm, DecisionTableV2Arm)
