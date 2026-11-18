"""Split saved PUT detections into wrong-value, crash and resource kinds.

Read-only over existing evaluation directories: no model call, no PUT/reference
execution. A detected PUT is confirmed by inputs that failed on both runs. Each
confirming input gets one kind from its two observations:

- wrong_value: both runs returned a value that differs from the reference;
- resource: any run hit the timeout or a RecursionError/MemoryError, whose outcome
  depends on harness limits rather than on the specification;
- crash: any other exception (TypeError, IndexError, ...).

A PUT takes the strongest kind among its confirming inputs, in the order
wrong_value > crash > resource. Detection counts stay unchanged; the kinds only
split them, so resource detections can be reported separately.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path



def read(path):
    return json.loads(Path(path).read_text())


def evaluation_observations(task_directory, program_id, outcome):
    """Read full historical repeats or indexed failure confirmations without inventing passes."""
    evaluation = task_directory / "evaluation"
    first = read(evaluation / f"{program_id}_0.json")["tests"]
    observations = [[item] for item in first]
    if "retested" in outcome:
        indices = outcome["retested"]
        second = read(evaluation / f"{program_id}_retry_1.json")["tests"] if indices else []
        if len(second) != len(indices) or len(set(indices)) != len(indices):
            raise ValueError("Confirmation checkpoint/index count mismatch")
        for index, item in zip(indices, second):
            if type(index) is not int or not 0 <= index < len(first):
                raise ValueError("Invalid confirmation input index")
            if first[index]["status"] not in ("fail", "error", "timeout"):
                raise ValueError("Confirmation index does not identify a first failure")
            observations[index].append(item)
        if any(item["status"] in ("fail", "error", "timeout") and index not in indices
               for index, item in enumerate(first)):
            raise ValueError("Missing first-failure confirmation")
    else:
        second = read(evaluation / f"{program_id}_1.json")["tests"]
        if len(second) != len(first):
            raise ValueError("Historical repeat result count mismatch")
        for index, item in enumerate(second):
            observations[index].append(item)
    return observations



RESOURCE_EXCEPTIONS = ("RecursionError", "MemoryError")
KIND_ORDER = ("wrong_value", "crash", "resource")


def observation_kind(observations):
    """Return the kind of one confirmed failing input from its two observations."""
    statuses = [item["status"] for item in observations]
    if len(statuses) != 2 or any(status not in ("fail", "error", "timeout") for status in statuses):
        raise ValueError(f"Not a confirmed failure: {statuses}")
    if all(status == "fail" for status in statuses):
        return "wrong_value"
    for item in observations:
        if item["status"] == "timeout":
            return "resource"
        if item["status"] == "error" and item.get("exception") in RESOURCE_EXCEPTIONS:
            return "resource"
    return "crash"


def strongest_kind(kinds):
    for kind in KIND_ORDER:
        if kind in kinds:
            return kind
    raise ValueError("No confirming input")


def classify_arm(evaluation_directory, arm):
    """Map (task_id, put_id) -> {kind, inputs} for every PUT the arm detected."""
    detections = {}
    for result_path in sorted(Path(evaluation_directory).glob("tasks/*/result.json")):
        result = read(result_path)
        if result.get("skip") or arm not in result.get("arms", {}):
            continue
        arm_indices = set(result["arm_indices"][arm])
        tests = read(result_path.parent / "oracle_valid.json")["tests"]
        for put_id in result["arms"][arm]["detected_put_ids"]:
            outcome = result["outcomes"][put_id]
            observations = evaluation_observations(result_path.parent, put_id, outcome)
            confirming = sorted(arm_indices & set(outcome["failing"]))
            input_rows = []
            for index in confirming:
                input_rows.append({
                    "index": index,
                    "args": tests[index]["args"],
                    "kwargs": tests[index]["kwargs"],
                    "kind": observation_kind(observations[index]),
                    "statuses": [item["status"] for item in observations[index]],
                    "exceptions": [item.get("exception") for item in observations[index]],
                })
            kind = strongest_kind({row["kind"] for row in input_rows})
            detections[(result["task_id"], put_id)] = {"kind": kind, "inputs": input_rows}
    return detections


def kind_counts(detections):
    counts = {kind: 0 for kind in KIND_ORDER}
    for row in detections.values():
        counts[row["kind"]] += 1
    counts["total"] = len(detections)
    counts["non_resource"] = counts["total"] - counts["resource"]
    return counts


def compare(left, right):
    left_keys, right_keys = set(left), set(right)
    def split(keys, source):
        counts = {kind: 0 for kind in KIND_ORDER}
        for key in keys:
            counts[source[key]["kind"]] += 1
        counts["total"] = len(keys)
        return counts
    return {"shared": len(left_keys & right_keys),
            "left_only": split(left_keys - right_keys, left),
            "right_only": split(right_keys - left_keys, right)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", action="append", required=True,
                        help="label=evaluation_directory:arm, repeatable")
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    sources = {}
    for text in arguments.source:
        label, rest = text.split("=", 1)
        directory, arm = rest.rsplit(":", 1)
        sources[label] = classify_arm(directory, arm)
    labels = list(sources)
    report = {
        "kind_definitions": {
            "wrong_value": "both runs returned a value different from the reference",
            "crash": "an exception other than RecursionError/MemoryError on a confirmed input",
            "resource": "timeout, RecursionError or MemoryError on a confirmed input",
            "put_kind": "strongest kind among confirming inputs: wrong_value > crash > resource",
        },
        "counts": {label: kind_counts(rows) for label, rows in sources.items()},
        "pairs": {f"{labels[i]}_vs_{labels[j]}": compare(sources[labels[i]], sources[labels[j]])
                  for i in range(len(labels)) for j in range(i + 1, len(labels))},
        "detections": {label: [{"task_id": key[0], "put_id": key[1], **row}
                               for key, row in sorted(rows.items())]
                       for label, rows in sources.items()},
        "new_model_calls": 0,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"counts": report["counts"], "pairs": report["pairs"]}, indent=2))


if __name__ == "__main__":
    main()
