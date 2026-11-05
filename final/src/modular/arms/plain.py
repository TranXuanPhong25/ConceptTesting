from .base import InputGenerationMethod


class PlainArm(InputGenerationMethod):
    name = "plain"

    def build_guidance(self, packet):
        return "No additional analysis packet. Choose useful new tests from the information above."
