"""Direct batch baseline."""
from .base import InputGenerationMethod


class DirectBatchArm(InputGenerationMethod):
    name = 'direct'

    def build_guidance(self, packet):
        return ''
