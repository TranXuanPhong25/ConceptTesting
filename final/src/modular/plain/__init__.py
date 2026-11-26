"""Plain input-generation baseline."""
from ..common import InputGenerationMethod
from ..input_prompts import render_input_prompt


class PlainArm(InputGenerationMethod):
    name = "plain"

    def build_prompt(self, packet):
        return render_input_prompt(packet, "plain")

    def build_guidance(self, packet):
        return ""
