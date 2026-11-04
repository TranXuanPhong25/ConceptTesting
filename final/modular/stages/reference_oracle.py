from final.experiments.concept_reference_v1.execution import execute
from .base import PipelineStage


class ReferenceOracleStage(PipelineStage):
    name = "reference_oracle"
    requires = ("input_generation",)

    def run(self, context):
        # VALIDATION START: generation must finish and freeze before oracle execution.
        if not context.inputs_frozen:
            raise RuntimeError("All task inputs must be frozen before reference execution")
        # VALIDATION END: generation must finish and freeze before oracle execution.
        if context.inputs.get("skip"):
            return
        raw_inputs = []
        original_arm_indices = {}
        for arm_name, arm_record in context.inputs["arms"].items():
            original_arm_indices[arm_name] = []
            for input_record in arm_record["inputs"]:
                original_arm_indices[arm_name].append(len(raw_inputs))
                raw_inputs.append(input_record)
        job = {
            "mode": "oracle", "context": context.task["prompt"],
            "source": context.task["prompt"] + context.task["canonical_solution"],
            "entry": context.task["entry_point"], "contract": context.metadata["contract"],
            "tests": raw_inputs, "timeout": context.settings.timeout_seconds,
            "seed": context.settings.reference_seed + context.task_number,
        }
        reference_runs = []
        for repeat_index in range(2):
            relative_path = context.task_directory + f"/oracle_{repeat_index}.json"
            outcome = context.artifacts.load_or_compute(relative_path, lambda: execute(job) if raw_inputs else {"tests": []})
            reference_runs.append(outcome["tests"])
        valid_tests = []
        rejected_inputs = []
        raw_to_valid_index = {}
        valid_index_by_input_key = {}
        base_input_keys = set(context.cohort_task["base_input_keys"])
        for raw_index, input_record in enumerate(raw_inputs):
            first_reference_result = reference_runs[0][raw_index]
            second_reference_result = reference_runs[1][raw_index]
            # VALIDATION START: domain/reference acceptance, repeat stability and base duplicates.
            if first_reference_result["status"] != "ok" or second_reference_result["status"] != "ok":
                rejected_inputs.append({"index": raw_index, "reason": "domain_or_reference_rejects",
                                        "outcomes": [first_reference_result, second_reference_result]})
                continue
            if (first_reference_result["expected"] != second_reference_result["expected"]
                    or first_reference_result["input_key"] != second_reference_result["input_key"]):
                rejected_inputs.append({"index": raw_index, "reason": "unstable_reference"})
                continue
            input_key = first_reference_result["input_key"]
            if input_key in base_input_keys:
                rejected_inputs.append({"index": raw_index, "reason": "base_duplicate"})
                continue
            # VALIDATION END: domain/reference acceptance, repeat stability and base duplicates.
            if input_key not in valid_index_by_input_key:
                valid_index_by_input_key[input_key] = len(valid_tests)
                valid_tests.append({
                    "args": input_record["args"], "kwargs": input_record["kwargs"],
                    "expected": first_reference_result["expected"], "input_key": input_key,
                })
            raw_to_valid_index[raw_index] = valid_index_by_input_key[input_key]
        arm_indices = {}
        for arm_name, raw_indices in original_arm_indices.items():
            unique_indices = []
            for raw_index in raw_indices:
                if raw_index in raw_to_valid_index:
                    valid_index = raw_to_valid_index[raw_index]
                    if valid_index not in unique_indices:
                        unique_indices.append(valid_index)
            arm_indices[arm_name] = unique_indices
        context.oracle = {"tests": valid_tests, "rejected": rejected_inputs, "arm_indices": arm_indices}
        context.artifacts.write(context.task_directory + "/oracle_valid.json", context.oracle)
