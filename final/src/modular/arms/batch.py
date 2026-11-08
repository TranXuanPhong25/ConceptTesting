"""Paired batch arms: shared mechanics, only soft BVA guidance differs."""
from .base import InputGenerationMethod
from ..boundary_value_analysis.prompts import GUIDANCE


class DirectBatchArm(InputGenerationMethod):
    name = 'direct'

    def build_guidance(self, packet):
        return ''


class SoftBvaBatchArm(InputGenerationMethod):
    name = 'soft_bva'

    def build_guidance(self, packet):
        return GUIDANCE
