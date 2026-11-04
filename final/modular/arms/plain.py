from .base import ExperimentArm


class PlainArm(ExperimentArm):
    name = "plain"
    requires_classical_analysis = False
    requires_witness_pool = False

    def build_guidance(self, packet):
        return "No additional analysis packet. Choose useful new tests from the information above."
