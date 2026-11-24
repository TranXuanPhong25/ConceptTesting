"""V2 technique guidance: behavioral partitions, fault refinement and soft examples.

Both arms use the shared input decoder, reference oracle and catalogue evaluation.
"""
from .classical import CatalogueArm
from ..fault_oriented_testing.prompts import EP_BVA_GUIDANCE, DECISION_TABLE_GUIDANCE


class EpBvaV2Arm(CatalogueArm):
    name = "ep_bva_v2"
    sections = ("classes", "boundaries")
    guidance = EP_BVA_GUIDANCE
    example_key = "ep_bva"


class DecisionTableV2Arm(CatalogueArm):
    name = "decision_table_v2"
    sections = ("rules",)
    guidance = DECISION_TABLE_GUIDANCE
    example_key = "decision_table"


V2_ARMS = (EpBvaV2Arm, DecisionTableV2Arm)
