from final.experiments.concept_reference_v1.execution import execute
from final.experiments.concept_reference_v1.pools import candidate_pool, select_witnesses
from .base import PipelineStage


class WitnessSamplingStage(PipelineStage):
    name = "witness_sampling"
    requires = ("concept_analysis",)

    def __init__(self, tool_input_arm):
        self.tool_input_arm = tool_input_arm

    def configuration(self):
        return {"tool_input_arm": self.tool_input_arm.name}

    def run(self, context):
        packet = context.packet
        if not packet.get("skip") and "witnesses" not in packet:
            if context.artifacts.read_only:
                raise FileNotFoundError("Read-only replay requires saved witnesses; sampling/execution disabled")
            visible_identifiers = set(packet["visible_put_ids"])
            visible_programs = []
            for program in context.cohort_task["programs"]:
                if program["id"] in visible_identifiers:
                    visible_programs.append(program)
            # Use the same hash ordering as prompt visibility; sampler order matters.
            ordered_programs = []
            by_identifier = {}
            for program in visible_programs:
                by_identifier[program["id"]] = program
            for program_identifier in packet["visible_put_ids"]:
                ordered_programs.append(by_identifier[program_identifier])
            pool = candidate_pool(ordered_programs, context.task_number)
            checks = execute({
                "mode": "validate", "context": context.task["prompt"], "source": "",
                "entry": context.task["entry_point"], "contract": context.metadata["contract"],
                "tests": pool, "timeout": context.settings.timeout_seconds,
            })["tests"]
            witnesses = select_witnesses(pool, checks, set(context.cohort_task["base_input_keys"]), context.task_number)
            packet["witnesses"] = witnesses
            prompt_limit = context.settings.context_tokens - context.settings.input_tokens - 128
            while (witnesses and context.calls is not None
                   and context.calls.token_count(self.tool_input_arm.build_messages(packet)) > prompt_limit):
                witnesses.pop()
            packet.update(pool=pool, pool_validation=checks)
        context.artifacts.write(context.task_directory + "/packet.json", packet)
