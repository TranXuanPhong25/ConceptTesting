"""Admit generated inputs against trusted domain and twice-run reference oracle."""
from __future__ import annotations

from final.src.runtime.execution import execute
from .call_builder import CallBuilder
from .execution_cache import cached_execution
from .input_contract import validate_input_literal
from .references import HumanEvalPlusReferencePrograms


def run_reference_oracle(context, *, execution_cache=None, reference_programs=None) -> dict | None:
    """Validate input types/domain and compute expected outputs using pinned references."""
    if context.inputs is None:
        raise RuntimeError("Reference execution requires generated or saved inputs")
    if context.inputs.get("skip"):
        return None
    reference_programs = reference_programs or HumanEvalPlusReferencePrograms()
    reference = reference_programs.for_task(context.task, context.metadata)
    if reference_programs.record_provenance:
        context.artifacts.write(context.task_directory + "/reference_program.json", reference["provenance"])
    raw_inputs = []
    builder = CallBuilder.for_source(
        context.task["prompt"],
        context.task["entry_point"],
        input_types=context.metadata.get("input_types"),
    )
    type_rejections = {}
    original_arm_indices = {}
    for arm_name, arm_record in context.inputs["arms"].items():
        original_arm_indices[arm_name] = []
        for input_record in arm_record["inputs"]:
            original_arm_indices[arm_name].append(len(raw_inputs))
            try:
                validate_input_literal(input_record)
                builder.validate_call(input_record)
            except (ValueError, TypeError, KeyError, SyntaxError, RecursionError) as error:
                type_rejections[len(raw_inputs)] = str(error)
            raw_inputs.append(input_record)
    admitted_indices = [index for index in range(len(raw_inputs)) if index not in type_rejections]
    job = {
        "mode": "oracle",
        "context": reference["context"],
        "source": reference["source"],
        "entry": reference["entry"],
        "contract": reference["contract"],
        "tests": [raw_inputs[index] for index in admitted_indices],
        "timeout": context.settings.timeout_seconds,
        "seed": context.settings.reference_seed + context.task_number,
    }
    reference_runs = []
    for repeat_index in range(2):
        relative_path = context.task_directory + f"/oracle_{repeat_index}.json"
        outcome = {"tests": []}
        if admitted_indices:
            outcome = cached_execution(context, relative_path, job, repeat_index, execute, execution_cache)
        if len(outcome["tests"]) != len(admitted_indices):
            raise ValueError("Reference result count does not match admitted inputs")
        reference_runs.append(dict(zip(admitted_indices, outcome["tests"])))
    valid_tests = []
    rejected_inputs = []
    raw_to_valid_index = {}
    valid_index_by_input_key = {}
    base_input_keys = set(context.cohort_task["base_input_keys"])
    for raw_index, input_record in enumerate(raw_inputs):
        if raw_index in type_rejections:
            rejected_inputs.append({
                "index": raw_index,
                "reason": "input_type_rejects",
                "detail": type_rejections[raw_index],
            })
            continue
        first_reference_result = reference_runs[0][raw_index]
        second_reference_result = reference_runs[1][raw_index]
        # VALIDATION START: domain/reference acceptance, repeat stability and base duplicates.
        if first_reference_result["status"] != "ok" or second_reference_result["status"] != "ok":
            outcomes = [first_reference_result, second_reference_result]
            reason = "reference_output_limit" if any(
                outcome.get("reason") == "reference_output_limit" for outcome in outcomes
            ) else "domain_or_reference_rejects"
            rejected_inputs.append({
                "index": raw_index,
                "reason": reason,
                "outcomes": outcomes,
            })
            continue
        if (
            first_reference_result["expected"] != second_reference_result["expected"]
            or first_reference_result["input_key"] != second_reference_result["input_key"]
        ):
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
                "args": input_record["args"],
                "kwargs": input_record["kwargs"],
                "expected": first_reference_result["expected"],
                "input_key": input_key,
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
    # Arm-local survivor indices preserve catalogue labels through reference
    # rejection and global deduplication, including differently encoded calls.
    catalogue_survivors = {}
    for arm_name, raw_indices in original_arm_indices.items():
        if "catalogue_status" in context.inputs["arms"][arm_name]:
            catalogue_survivors[arm_name] = [
                index for index, raw_index in enumerate(raw_indices) if raw_index in raw_to_valid_index
            ]
    if catalogue_survivors:
        context.oracle["catalogue_valid_input_indices"] = catalogue_survivors
    context.artifacts.write(context.task_directory + "/oracle_valid.json", context.oracle)
    return context.oracle
