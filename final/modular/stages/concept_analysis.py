import hashlib

from final.experiments.concept_reference_v1.analysis import analyze_task
from final.experiments.concept_reference_v1.prompts import common_prompt
from .base import PipelineStage


class ConceptAnalysisStage(PipelineStage):
    name = "concept_analysis"
    requires = ("frozen_cohort",)

    def __init__(self, arms):
        self.arms = tuple(arms)

    def configuration(self):
        return {"arms": [arm.name for arm in self.arms]}

    def run(self, context):
        packet_path = context.task_directory + "/packet.json"
        if context.artifacts.exists(packet_path):
            context.packet = context.artifacts.read(packet_path)
            return
        if context.artifacts.read_only:
            raise FileNotFoundError(f"Read-only replay requires {packet_path}")
        cohort_task = context.cohort_task
        passing_programs = []
        for program in cohort_task["programs"]:
            if program["base"]["status"] == "pass":
                passing_programs.append(program)
        if cohort_task["generated"] != context.settings.target_programs or not passing_programs:
            reason = "generation_shortfall" if cohort_task["generated"] != context.settings.target_programs else "no_base_pass"
            context.packet = {"task_id": context.task["task_id"], "skip": reason}
            return
        requires_model = any(arm.uses_model for arm in self.arms)
        if context.calls is None and requires_model:
            raise RuntimeError("Preparing new prompts requires tokenization")
        visible_programs = sorted(passing_programs, key=lambda program: hashlib.sha256(
            f"{context.task_number}:{program['id']}".encode()).hexdigest())
        while visible_programs:
            common_text = common_prompt(context.task, visible_programs, context.metadata["contract"], context.settings.input_budget)
            analysis = analyze_task(dict(cohort_task, programs=visible_programs))
            for arm_name in ("classical", "contrastive", "placebo"):
                for card in analysis[arm_name]:
                    card["text"] = card["text"][:800]
            partial_packet = {"common": common_text, "analysis": analysis, "witnesses": []}
            token_counts = {}
            for arm in self.arms:
                if arm.uses_model and arm.name != "toolinput":
                    token_counts[arm.name] = context.calls.token_count(arm.build_messages(partial_packet))
            # With only toolinput selected, budget its common prompt even before
            # witness examples are added. The standard six-arm packet stays identical.
            if not token_counts:
                for arm in self.arms:
                    if arm.uses_model:
                        token_counts[arm.name] = context.calls.token_count(arm.build_messages(partial_packet))
            prompt_limit = context.settings.context_tokens - context.settings.input_tokens - 128
            if max(token_counts.values(), default=0) <= prompt_limit:
                break
            visible_programs.pop()
        if not visible_programs:
            context.packet = {"task_id": context.task["task_id"], "skip": "prompt_too_large"}
            return
        visible_identifiers = []
        for program in visible_programs:
            visible_identifiers.append(program["id"])
        context.packet = {
            "task_id": context.task["task_id"], "visible_put_ids": visible_identifiers,
            "common": common_text, "analysis": analysis, "prompt_tokens": token_counts,
        }
