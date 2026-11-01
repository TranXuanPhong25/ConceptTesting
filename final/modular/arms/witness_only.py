from .base import ExperimentArm


class WitnessOnlyArm(ExperimentArm):
    name = "witness_only"
    uses_model = False

    def build_guidance(self, packet):
        raise RuntimeError("Witness-only arm never creates a model prompt")

    def run(self, context):
        if context.packet is None:
            raise RuntimeError("Witness-only arm requires a prepared packet")
        return {"inputs": context.packet["witnesses"], "rejected": []}
