import json

from .base import ExperimentArm


class ToolInputArm(ExperimentArm):
    name = "toolinput"

    def build_guidance(self, packet):
        examples = []
        for witness in packet["witnesses"]:
            examples.append({"args": witness["args"], "kwargs": witness["kwargs"]})
        return ("Optional new input examples from a deterministic library sampler (not known bugs):\n"
                + json.dumps(examples, separators=(",", ":")))
