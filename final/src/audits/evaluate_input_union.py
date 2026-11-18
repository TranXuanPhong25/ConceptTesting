"""Summarize the union of already evaluated arms; never execute a program or model."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

from final.src.runtime.artifacts import save
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.stages.reporting import ReportingStage
from .detection_kinds import evaluation_observations, observation_kind, strongest_kind

UNION_ARM = "union"


def read(path):
    return json.loads(Path(path).read_text())


def validate_union_pool(oracle, source_arms):
    """Only an exact, deduplicated full pool may reuse these native checkpoints."""
    keys = [test['input_key'] for test in oracle['tests']]
    if len(keys) != len(set(keys)):
        raise ValueError('Source oracle pool has duplicate input keys')
    covered = set()
    for name in source_arms:
        indices = oracle['arm_indices'][name]
        if any(type(index) is not int or not 0 <= index < len(keys) for index in indices):
            raise ValueError('Invalid source arm input index')
        covered.update(indices)
    if covered != set(range(len(keys))):
        raise ValueError('Source arms do not cover the exact native evaluation pool')
    return list(range(len(keys)))


def validate_native_evidence(task_directory, source_result, input_count):
    """Reconfirm every saved failing index from the actual two observations."""
    for put_id, outcome in source_result['outcomes'].items():
        observations = evaluation_observations(task_directory, put_id, outcome)
        if len(observations) != input_count:
            raise ValueError('Native checkpoint length differs from union input count')
        confirmed = [index for index, values in enumerate(observations)
                     if len(values) == 2 and all(value['status'] in ('fail', 'error', 'timeout') for value in values)]
        if confirmed != outcome['failing']:
            raise ValueError('Saved confirmed failures differ from native checkpoint evidence')


def evaluate(source, output, *, replay=False):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.is_relative_to(source):
        raise ValueError("Union needs an output directory outside the source run")
    if replay:
        return read(output / "union_summary.json")
    if output.exists():
        raise ValueError("Union requires a new output directory")
    if (source / "status.json").exists() and read(source / "status.json")["state"] != "complete":
        raise ValueError("Union source must be completed")
    paths = sorted(source.glob("tasks/*/result.json"))
    if not paths:
        raise FileNotFoundError("No saved task evaluation results")
    store = ArtifactStore(output)
    rows, totals, detections = [], {}, []
    kinds = Counter()
    memberships_removed = evaluated_puts = eligible_tasks = 0
    for path in paths:
        original = read(path)
        directory = path.parent.relative_to(source)
        if original.get("skip"):
            store.write(str(directory / "result.json"), original)
            rows.append(original)
            continue
        oracle = read(path.parent / "oracle_valid.json")
        arms = tuple(original["arms"])
        indices = validate_union_pool(oracle, arms)
        validate_native_evidence(path.parent, original, len(oracle["tests"]))
        detected = [put for put, outcome in original["outcomes"].items()
                    if set(indices).intersection(outcome["failing"])]
        result = {**original, "arm_indices": {**original["arm_indices"], UNION_ARM: indices},
                  "arms": {**original["arms"], UNION_ARM: {
                      "valid_inputs": len(indices), "detected": len(detected), "detected_put_ids": detected}}}
        oracle = {**oracle, "arm_indices": result["arm_indices"]}
        store.write(str(directory / "oracle_valid.json"), oracle)
        store.write(str(directory / "result.json"), result)
        # Preserve the evidence needed by input/kind analysis; no source-code snapshot is needed.
        for checkpoint in (path.parent / "evaluation").glob("*.json"):
            destination = store.path(str(directory / "evaluation" / checkpoint.name))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(checkpoint, destination)
        for put in detected:
            outcome = original["outcomes"][put]
            observations = evaluation_observations(path.parent, put, outcome)
            kind = strongest_kind({observation_kind(observations[index])
                                   for index in set(indices).intersection(outcome["failing"])})
            kinds[kind] += 1
            detections.append({"task_id": original["task_id"], "put_id": put, "kind": kind})
        memberships_removed += sum(len(oracle["arm_indices"][arm]) for arm in arms) - len(indices)
        evaluated_puts += original["base_pass"]
        eligible_tasks += 1
        for name, arm in result["arms"].items():
            total = totals.setdefault(name, {"valid_inputs": 0, "detected": 0, "tasks_detected": 0})
            total["valid_inputs"] += arm["valid_inputs"]
            total["detected"] += arm["detected"]
            total["tasks_detected"] += arm["detected"] > 0
        rows.append(result)
    comparisons = [ReportingStage().compare(rows, name, UNION_ARM) for name in totals if name != UNION_ARM]
    summary = {"source_directory": str(source), "task_records": len(rows), "eligible_tasks": eligible_tasks,
               "evaluated_base_pass": evaluated_puts, "arms": totals,
               "union_detection_kinds": dict(kinds), "union_detections": detections,
               "duplicate_valid_memberships_removed": memberships_removed, "comparisons": comparisons,
               "new_model_calls": 0, "new_native_calls": 0, "scope": "saved evaluation outcomes only"}
    store.write_metadata("union_summary.json", summary)
    return summary


def render(summary):
    union = summary["arms"].get(UNION_ARM, {"detected": 0, "valid_inputs": 0, "tasks_detected": 0})
    lines = ["# Union từ kết quả evaluation đã lưu", "",
             f"Union phát hiện {union['detected']}/{summary['evaluated_base_pass']} PUT trên "
             f"{union['tasks_detected']}/{summary['eligible_tasks']} task, bằng {union['valid_inputs']} unique valid inputs.",
             "Đây là tổng hợp outcomes đã lưu; không phản ánh input sửa sau evaluation. "
             "Union dùng budget lớn hơn từng arm, không chứng minh gain ở cùng budget.", "",
             "| Arm | Valid inputs | Detected PUTs | Task có detection |", "|---|---:|---:|---:|"]
    for name, arm in summary['arms'].items():
        lines.append(f"| {name} | {arm['valid_inputs']} | {arm['detected']} | {arm['tasks_detected']} |")
    lines += ["", f"Phân bố kind theo unique PUT: {summary['union_detection_kinds']}.",
              "0 model calls mới, 0 native calls mới. Không kiểm source hash hoặc input freeze.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.source, args.artifacts)
    save(args.artifacts / "result_digest.json", result)
    (args.artifacts / "REPORT.md").write_text(render(result))
    save(args.artifacts / "progress.json", {"state": "complete", "evaluated_tasks": result["task_records"],
                                           "total_tasks": result["task_records"]})
    save(args.artifacts / "status.json", {"state": "complete", "new_model_calls": 0, "new_native_calls": 0})
    print(json.dumps({"arms": result["arms"], "new_model_calls": 0, "new_native_calls": 0}))


if __name__ == "__main__":
    main()
