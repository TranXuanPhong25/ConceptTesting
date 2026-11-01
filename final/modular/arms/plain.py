from .base import ExperimentArm


class PlainArm(ExperimentArm):
    name = "plain"

    def build_guidance(self, packet):
        return "No additional analysis packet. Choose useful new tests from the information above."
