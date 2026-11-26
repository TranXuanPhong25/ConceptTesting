"""VF3 Hybrid generation and catalogue measurement."""
from .catalogue import measure_task_catalogues
from .vf3_hybrid import StructuredCatalogueArm
from .decision_table import DecisionTableArm
from .ep_bva import EpBvaArm

VF3_HYBRID_ARMS = (EpBvaArm, DecisionTableArm)

__all__ = [
    "DecisionTableArm",
    "EpBvaArm",
    "StructuredCatalogueArm",
    "VF3_HYBRID_ARMS",
    "measure_task_catalogues",
]
