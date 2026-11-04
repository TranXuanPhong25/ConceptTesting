from .base import PipelineStage
from ..input_contract import validate_generated_inputs
from ..generators.base import InputGenerator


class InputGenerationStage(PipelineStage):
    name = "input_generation"
    requires = ("frozen_cohort",)

    def __init__(self, input_generator):
        if not isinstance(input_generator, InputGenerator):
            # Retain direct construction with old arm tuples for archived callers.
            from ..generators import generator_for_arms
            input_generator = generator_for_arms(input_generator)
        self.input_generator = input_generator
        self.requires = ("frozen_cohort", *(stage.name for stage in input_generator.preparation_stages()))

    def source_dependencies(self):
        return self.input_generator.source_dependencies()

    def configuration(self):
        return {"generator_class": type(self.input_generator).__module__ + "." + type(self.input_generator).__qualname__,
                "generator": self.input_generator.configuration()}

    def run(self, context):
        path = context.task_directory + "/inputs.json"
        if context.artifacts.exists(path):
            result = context.artifacts.read(path)
        else:
            if context.artifacts.read_only:
                raise FileNotFoundError(f"Read-only replay requires {path}")
            result = self.input_generator.generate(context)
        # VALIDATION START: every producer uses the same reference-input contract.
        validate_generated_inputs(result, task_id=context.task["task_id"], input_budget=context.settings.input_budget)
        # VALIDATION END: every producer uses the same reference-input contract.
        context.artifacts.write(path, result)
        context.inputs = result
