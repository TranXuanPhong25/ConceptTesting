from .base import InputGenerationMethod
from ..input_prompts import INPUT_SIZE_GUIDANCE


class PlainArm(InputGenerationMethod):
    name = "plain"

    def build_messages(self, packet):
        instructions, separator, context = packet["common"].partition("\n\nSPECIFICATION:\n")
        instructions = instructions.replace(" small, distinct new calls", " distinct new calls", 1)
        instructions = instructions.replace(INPUT_SIZE_GUIDANCE, "", 1)
        return super().build_messages({**packet, "common": instructions + separator + context})

    def build_guidance(self, packet):
        return ""
