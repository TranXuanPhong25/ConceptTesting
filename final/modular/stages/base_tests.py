from final.experiments.concept_reference_v1.execution import execute
from .base import PipelineStage


class BaseTestFilterStage(PipelineStage):
    name = "base_tests"
    requires = ("program_generation",)

    def run(self, context):
        if context.cohort_task is not None:
            return
        programs = []
        base_input_keys = set()
        passing_count = 0
        for program in context.generated_programs:
            job = {
                "mode": "base", "context": context.task["prompt"], "source": program["code"],
                "entry": context.task["entry_point"], "base": context.task["test"],
                "timeout": context.settings.timeout_seconds,
                "seed": context.settings.writer_seed + context.task_number, "trace": True,
            }
            relative_path = context.task_directory + f"/base/{program['id']}.json"
            outcome = context.artifacts.load_or_compute(relative_path, lambda: execute(job))
            base_input_keys.update(outcome.get("input_keys", []))
            if outcome["status"] == "pass":
                passing_count += 1
            programs.append(dict(program, base=outcome))
        task_cohort = {
            "task_id": context.task["task_id"], "programs": programs, "generated": len(programs),
            "base_pass": passing_count, "base_input_keys": sorted(base_input_keys),
            "generation_rejections": context.generation_rejections,
            "status": "complete" if len(programs) == context.settings.target_programs else "shortfall",
        }
        context.artifacts.write(context.task_directory + "/cohort_task.json", task_cohort)
        context.cohort_task = task_cohort
