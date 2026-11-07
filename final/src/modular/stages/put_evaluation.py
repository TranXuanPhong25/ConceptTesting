from final.src.runtime.execution import execute
from .base import PipelineStage
from ..execution_cache import cached_execution


class PutEvaluationStage(PipelineStage):
    name = "put_evaluation"
    requires = ("reference_oracle",)
    failure_statuses = ("fail", "error", "timeout")

    def __init__(self, execution_cache=None):
        self.execution_cache = execution_cache

    def configuration(self):
        configuration = {"repeat_policy": "confirm-first-failures-v1", "unstable_scope": "retested-inputs"}
        if self.execution_cache is not None:
            configuration["execution_cache"] = self.execution_cache.configuration()
        return configuration

    def run(self, context):
        if context.inputs.get("skip"):
            result = {"task_id": context.task["task_id"], "skip": context.inputs["skip"]}
        else:
            result = self.evaluate_programs(context)
        context.artifacts.write(context.task_directory + "/result.json", result)
        context.result = result

    def evaluate_programs(self, context):
        passing_programs = []
        for program in context.cohort_task["programs"]:
            if program["base"]["status"] == "pass":
                passing_programs.append(program)
        program_outcomes = {}
        for program in passing_programs:
            evaluation_path = context.task_directory + f"/evaluation/{program['id']}"
            job = {
                "mode": "evaluate", "context": context.task["prompt"], "source": program["code"],
                "entry": context.task["entry_point"], "tests": context.oracle["tests"],
                "atol": context.metadata["atol"], "timeout": context.settings.timeout_seconds,
                "seed": context.settings.reference_seed + context.task_number,
            }
            first_result = cached_execution(context, evaluation_path + "_0.json", job, 0,
                                            execute, self.execution_cache)
            if len(first_result["tests"]) != len(job["tests"]):
                raise ValueError("First PUT evaluation result count does not match input count")
            # A first-run pass cannot fail both runs, so only retry fail/error/timeout.
            # Keep the same seed and confirm failure to reduce transient detections.
            retested_indices = []
            retested_inputs = []
            for test_index, outcome in enumerate(first_result["tests"]):
                if outcome["status"] in self.failure_statuses:
                    retested_indices.append(test_index)
                    retested_inputs.append(context.oracle["tests"][test_index])
            failing_indices = []
            unstable_indices = []
            if retested_indices:
                retry_job = dict(job)
                retry_job["tests"] = retested_inputs
                # A separate path avoids reusing an old full-suite second-run checkpoint.
                second_result = cached_execution(context, evaluation_path + "_retry_1.json", retry_job, 1,
                                                 execute, self.execution_cache)
                if len(second_result["tests"]) != len(retested_indices):
                    raise ValueError("PUT confirmation result count does not match retested input count")
                for retry_index, test_index in enumerate(retested_indices):
                    first_status = first_result["tests"][test_index]["status"]
                    second_status = second_result["tests"][retry_index]["status"]
                    if second_status in self.failure_statuses:
                        failing_indices.append(test_index)
                    # Only retested inputs have two observations to compare.
                    if first_status != second_status:
                        unstable_indices.append(test_index)
            program_outcomes[str(program["id"])] = {
                "failing": failing_indices, "unstable": unstable_indices, "retested": retested_indices,
            }
        arm_results = {}
        for arm_name, selected_indices in context.oracle["arm_indices"].items():
            detected_programs = []
            selected_set = set(selected_indices)
            for program_identifier, outcomes in program_outcomes.items():
                if selected_set.intersection(outcomes["failing"]):
                    detected_programs.append(program_identifier)
            arm_results[arm_name] = {
                "valid_inputs": len(selected_indices), "detected_put_ids": detected_programs,
                "detected": len(detected_programs),
            }
            generation_record = context.inputs["arms"][arm_name]
            if "status" in generation_record:
                arm_results[arm_name]["generation_status"] = generation_record["status"]
                arm_results[arm_name]["generation_skip"] = generation_record.get("skip")
        return {
            "task_id": context.task["task_id"], "base_pass": len(passing_programs), "arms": arm_results,
            "arm_indices": context.oracle["arm_indices"], "outcomes": program_outcomes,
            "oracle_rejected": len(context.oracle["rejected"]), "valid_union": len(context.oracle["tests"]),
        }
