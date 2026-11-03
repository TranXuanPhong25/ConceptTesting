"""Canonical-reference evaluation of each PUT's OWN V11-generated input suite."""

import json

from final.pipeline import save
from final.experiments.concept_reference_v1.execution import execute


class V11ReferenceEvaluationStage:
    name = "v11_reference_evaluation"

    def run(self, context, metadata):
        result_path = context.directory / "evaluation.json"
        if result_path.exists():
            return json.loads(result_path.read_text())
        raw_inputs = []
        origins = {}
        for arm_name, record in context.arm_results.items():
            origins[arm_name] = []
            for input_record in record["inputs"]:
                if not input_record.get("valid", True):
                    continue
                origins[arm_name].append(len(raw_inputs))
                raw_inputs.append(dict(args=input_record["input_repr"], kwargs="{}"))
        reference_runs = []
        for repeat_index in range(2):
            path = context.directory / f"gold_{repeat_index}.json"
            if path.exists():
                outcome = json.loads(path.read_text())
            else:
                outcome = execute(
                    dict(
                        mode="oracle",
                        source=context.human_eval["prompt"]
                        + context.human_eval["canonical_solution"],
                        context=context.human_eval["prompt"],
                        contract=metadata["contract"],
                        entry=context.human_eval["entry_point"],
                        tests=raw_inputs,
                        timeout=3,
                        seed=271828 + context.task["task"],
                    )
                )
                save(path, outcome)
            reference_runs.append(outcome["tests"])
        valid = []
        by_key = {}
        raw_to_valid = {}
        rejections = []
        base_keys = set(context.original_program["base"].get("input_keys", []))
        for index, record in enumerate(raw_inputs):
            first = reference_runs[0][index]
            second = reference_runs[1][index]
            if first["status"] != "ok" or second["status"] != "ok":
                rejections.append(
                    dict(index=index, reason="domain_or_reference_rejects")
                )
                continue
            if (
                first["expected"] != second["expected"]
                or first["input_key"] != second["input_key"]
            ):
                rejections.append(dict(index=index, reason="unstable_reference"))
                continue
            key = first["input_key"]
            if key in base_keys:
                rejections.append(dict(index=index, reason="base_duplicate"))
                continue
            if key not in by_key:
                by_key[key] = len(valid)
                valid.append(dict(record, expected=first["expected"], input_key=key))
            raw_to_valid[index] = by_key[key]
        repeated = []
        for repeat_index in range(2):
            path = context.directory / f"put_{repeat_index}.json"
            if path.exists():
                outcome = json.loads(path.read_text())
            else:
                outcome = execute(
                    dict(
                        mode="evaluate",
                        context=context.human_eval["prompt"],
                        source=context.original_program["code"],
                        entry=context.human_eval["entry_point"],
                        atol=metadata["atol"],
                        tests=valid,
                        timeout=3,
                        seed=271828 + context.task["task"],
                    )
                )
                save(path, outcome)
            repeated.append(outcome["tests"])
        failing = []
        unstable = []
        for index in range(len(valid)):
            if all(
                run[index]["status"] in ("fail", "error", "timeout") for run in repeated
            ):
                failing.append(index)
            if repeated[0][index]["status"] != repeated[1][index]["status"]:
                unstable.append(index)
        arm_results = {}
        for arm_name, indices in origins.items():
            selected = list(
                dict.fromkeys(
                    raw_to_valid[index] for index in indices if index in raw_to_valid
                )
            )
            arm_results[arm_name] = dict(
                valid_inputs=len(selected),
                selected_indices=selected,
                detected=bool(set(selected).intersection(failing)),
                llm_calls=context.arm_results[arm_name].get("llm_calls", 0),
            )
        result = dict(
            task_id=context.human_eval["task_id"],
            program_id=context.original_program["id"],
            case_id=context.task["task"],
            arms=arm_results,
            failing_indices=failing,
            unstable_indices=unstable,
            tests=valid,
            rejections=rejections,
        )
        save(result_path, result)
        return result
