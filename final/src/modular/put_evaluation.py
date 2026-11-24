"""Execute base-passing PUTs on admitted oracle tests under the configured repeat policy."""
from __future__ import annotations

from final.src.runtime.execution import execute
from .execution_cache import cached_execution

FAILURE_STATUSES = ("fail", "error", "timeout")


def _confirm_first_failures(context, program, job, execution_cache) -> dict:
    evaluation_path = context.task_directory + f"/evaluation/{program['id']}"
    first_result = cached_execution(context, evaluation_path + "_0.json", job, 0, execute, execution_cache)
    if len(first_result["tests"]) != len(job["tests"]):
        raise ValueError("First PUT evaluation result count does not match input count")
    # A first-run pass cannot fail both runs, so only retry fail/error/timeout.
    # Keep the same seed and confirm failure to reduce transient detections.
    retested_indices = []
    retested_inputs = []
    for test_index, outcome in enumerate(first_result["tests"]):
        if outcome["status"] in FAILURE_STATUSES:
            retested_indices.append(test_index)
            retested_inputs.append(context.oracle["tests"][test_index])
    failing_indices = []
    unstable_indices = []
    if retested_indices:
        retry_job = dict(job)
        retry_job["tests"] = retested_inputs
        # A separate path avoids reusing an old full-suite second-run checkpoint.
        second_result = cached_execution(
            context,
            evaluation_path + "_retry_1.json",
            retry_job,
            1,
            execute,
            execution_cache,
        )
        if len(second_result["tests"]) != len(retested_indices):
            raise ValueError("PUT confirmation result count does not match retested input count")
        for retry_index, test_index in enumerate(retested_indices):
            first_status = first_result["tests"][test_index]["status"]
            second_status = second_result["tests"][retry_index]["status"]
            if second_status in FAILURE_STATUSES:
                failing_indices.append(test_index)
            # Only retested inputs have two observations to compare.
            if first_status != second_status:
                unstable_indices.append(test_index)
    return {"failing": failing_indices, "unstable": unstable_indices, "retested": retested_indices}


def _full_two_repeats(context, program, job, execution_cache) -> dict:
    repeated_results = []
    for repeat_index in range(2):
        relative_path = context.task_directory + f"/evaluation/{program['id']}_{repeat_index}.json"
        result = cached_execution(context, relative_path, job, repeat_index, execute, execution_cache)
        if len(result["tests"]) != len(job["tests"]):
            raise ValueError("PUT evaluation result count does not match input count")
        repeated_results.append(result["tests"])
    failing_indices = []
    unstable_indices = []
    for test_index in range(len(context.oracle["tests"])):
        first_status = repeated_results[0][test_index]["status"]
        second_status = repeated_results[1][test_index]["status"]
        if first_status in FAILURE_STATUSES and second_status in FAILURE_STATUSES:
            failing_indices.append(test_index)
        if first_status != second_status:
            unstable_indices.append(test_index)
    return {"failing": failing_indices, "unstable": unstable_indices}


def evaluate_programs(context, *, execution_cache=None) -> dict:
    """Evaluate all base-passing PUTs for a task and aggregate arm detections."""
    scorer = context.settings.scorer
    if scorer not in ("confirm_first_failures", "full_two_repeats"):
        raise ValueError(f"Unknown scorer: {scorer}")
    passing_programs = [
        program for program in context.cohort_task["programs"] if program["base"]["status"] == "pass"
    ]
    program_outcomes = {}
    for program in passing_programs:
        job = {
            "mode": "evaluate",
            "context": context.task["prompt"],
            "source": program["code"],
            "entry": context.task["entry_point"],
            "tests": context.oracle["tests"],
            "atol": context.metadata["atol"],
            "timeout": context.settings.timeout_seconds,
            "seed": context.settings.reference_seed + context.task_number,
        }
        if scorer == "full_two_repeats":
            program_outcomes[str(program["id"])] = _full_two_repeats(context, program, job, execution_cache)
        else:
            program_outcomes[str(program["id"])] = _confirm_first_failures(context, program, job, execution_cache)
    arm_results = {}
    for arm_name, selected_indices in context.oracle["arm_indices"].items():
        selected_set = set(selected_indices)
        detected_programs = [
            program_identifier
            for program_identifier, outcomes in program_outcomes.items()
            if selected_set.intersection(outcomes["failing"])
        ]
        arm_results[arm_name] = {
            "valid_inputs": len(selected_indices),
            "detected_put_ids": detected_programs,
            "detected": len(detected_programs),
        }
        generation_record = context.inputs["arms"][arm_name]
        if "status" in generation_record:
            arm_results[arm_name]["generation_status"] = generation_record["status"]
            arm_results[arm_name]["generation_skip"] = generation_record.get("skip")
    return {
        "task_id": context.task["task_id"],
        "base_pass": len(passing_programs),
        "arms": arm_results,
        "arm_indices": context.oracle["arm_indices"],
        "outcomes": program_outcomes,
        "oracle_rejected": len(context.oracle["rejected"]),
        "valid_union": len(context.oracle["tests"]),
    }


def evaluate_puts(context, *, execution_cache=None) -> dict:
    """Evaluate a task unless skipped, persist result.json, and store on context."""
    if context.inputs.get("skip"):
        result = {"task_id": context.task["task_id"], "skip": context.inputs["skip"]}
    else:
        result = evaluate_programs(context, execution_cache=execution_cache)
    context.artifacts.write(context.task_directory + "/result.json", result)
    context.result = result
    return result
