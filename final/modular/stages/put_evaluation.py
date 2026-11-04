from final.experiments.concept_reference_v1.execution import execute
from .base import PipelineStage


class PutEvaluationStage(PipelineStage):
    name = "put_evaluation"
    requires = ("reference_oracle",)
    failure_statuses = ("fail", "error", "timeout")

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
            repeated_results = []
            for repeat_index in range(2):
                relative_path = context.task_directory + f"/evaluation/{program['id']}_{repeat_index}.json"
                job = {
                    "mode": "evaluate", "context": context.task["prompt"], "source": program["code"],
                    "entry": context.task["entry_point"], "tests": context.oracle["tests"],
                    "atol": context.metadata["atol"], "timeout": context.settings.timeout_seconds,
                    "seed": context.settings.reference_seed + context.task_number,
                }
                result = context.artifacts.load_or_compute(
                    relative_path, lambda: execute(job) if context.oracle["tests"] else {"tests": []})
                repeated_results.append(result["tests"])
            failing_indices = []
            unstable_indices = []
            for test_index in range(len(context.oracle["tests"])):
                first_status = repeated_results[0][test_index]["status"]
                second_status = repeated_results[1][test_index]["status"]
                if first_status in self.failure_statuses and second_status in self.failure_statuses:
                    failing_indices.append(test_index)
                if first_status != second_status:
                    unstable_indices.append(test_index)
            program_outcomes[str(program["id"])] = {"failing": failing_indices, "unstable": unstable_indices}
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
