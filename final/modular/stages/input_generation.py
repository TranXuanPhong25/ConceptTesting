from .base import PipelineStage


class InputGenerationStage(PipelineStage):
    name = "input_generation"
    requires = ("witness_sampling",)

    def __init__(self, arms):
        self.arms = tuple(arms)

    def configuration(self):
        return {"arms": [arm.name for arm in self.arms]}

    def run(self, context):
        if context.packet.get("skip"):
            result = {"task_id": context.task["task_id"], "skip": context.packet["skip"]}
        else:
            arm_results = {}
            for arm in self.arms:
                arm_results[arm.name] = arm.run(context)
            result = {"task_id": context.task["task_id"], "arms": arm_results}
        context.artifacts.write(context.task_directory + "/inputs.json", result)
        context.inputs = result
