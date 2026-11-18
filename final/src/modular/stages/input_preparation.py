"""Prepare input-method context: cohort eligibility, visibility and optional prompt."""
import hashlib

from .base import PipelineStage
from ..input_prompts import structured_input_prompt


class InputPreparationStage(PipelineStage):
    name = "input_context"
    requires = ("frozen_cohort",)

    def __init__(self, methods):
        self.methods = tuple(methods)

    def configuration(self):
        return {"methods": [method.name for method in self.methods]}

    def run(self, context):
        path = context.task_directory + "/packet.json"
        context.packet = context.artifacts.load_or_compute(path, lambda: self.prepare(context))

    def prepare(self, context):
        cohort = context.cohort_task
        generated_program_count = cohort["generated"]
        target_program_count = context.settings.target_programs
        passing_programs = [program for program in cohort["programs"] if program["base"]["status"] == "pass"]
        if generated_program_count != target_program_count or not passing_programs:
            reason = "generation_shortfall" if generated_program_count != target_program_count else "no_base_pass"
            return {"task_id": context.task["task_id"], "skip": reason}
        programs = sorted(passing_programs, key=lambda program: hashlib.sha256(
            f"{context.task_number}:{program['id']}".encode()).hexdigest())
        prompt_methods = [method for method in self.methods if getattr(method, "uses_shared_prompt", False)]
        while programs:
            packet = {"task_id": context.task["task_id"], "visible_put_ids": [program["id"] for program in programs],
                      "common": "", "prompt_tokens": {}}
            if prompt_methods:
                if context.calls is None:
                    raise RuntimeError("Shared-prompt input methods require tokenization")
                packet["common"] = structured_input_prompt(context.task, programs, context.metadata["contract"],
                                                            context.settings.input_budget)
                packet["input_format"] = "named-arguments-v1"
                for method in prompt_methods:
                    packet["prompt_tokens"][method.name] = context.calls.token_count(method.build_messages(packet))
            limit = context.settings.context_tokens - context.settings.input_tokens - 128
            # VALIDATION START: all shared prompts fit the configured context budget.
            if max(packet["prompt_tokens"].values(), default=0) <= limit:
                return packet
            if any(getattr(method, 'preserve_prompt_context', False) for method in prompt_methods):
                return {**packet, 'skip':'prompt_too_large', 'reason':'full_prompt_exceeds_context',
                        'required_prompt_tokens':max(packet['prompt_tokens'].values()),
                        'available_prompt_tokens':limit}
            # VALIDATION END: all shared prompts fit the configured context budget.
            programs.pop()
        return {"task_id": context.task["task_id"], "skip": "prompt_too_large"}
