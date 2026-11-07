"""Post-hoc envelope-only audit of frozen Phase B responses; never calls a model."""
import argparse
import datetime as dt
import hashlib
from pathlib import Path

from final.src.core_model import ModelResponse
from final.src.modular.boundary_value_analysis.precision import expand_seeds, matched_twenty, fixed_twenty
from final.src.modular.call_builder import CallBuilder
from final.src.modular.cohort import load_cohort
from final.src.modular.dataset import load_tasks, load_metadata
from final.src.runtime.artifacts import digest, save
from .run_prompt_style import read
from .run_bva_precision import evaluate, verify, outcomes_by_input
from .run_bva_precision_direction import decode_writer


def unwrap_json_fence(text):
    stripped = text.strip()
    if stripped.startswith("```json\n") and stripped.endswith("\n```") and stripped.count("```") == 2:
        return stripped[8:-4].strip(), True
    return text, False


def run(source, directory):
    if directory.exists():
        raise ValueError("Use a new output directory")
    primary = read(source / "report.json")
    for name, checksum in read(source / "generation_frozen.json")["writer_files"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != checksum:
            raise ValueError("Original writer checkpoint changed")
    plan = read(source / "plan.json")
    cohort = load_cohort(Path(plan["cohort"]))
    tasks = {task["task_id"]: task for task in load_tasks()}
    metadata = load_metadata()
    bundles, constructions = {}, {}
    for row in cohort["tasks"]:
        task_id = row["task_id"]
        number = task_id.split("/")[-1]
        task = tasks[task_id]
        response = read(source / "tasks" / number / "calls/precision_writer/response.json")
        text, unwrapped = unwrap_json_fence(response["text"])
        decoded, requests, remapping = decode_writer(ModelResponse(**{**response, "text": text}),
                                                     CallBuilder.for_source(task["prompt"], task["entry_point"]))
        expanded = expand_seeds(specification=task["prompt"], entry_point=task["entry_point"],
            program_source=row["programs"][0]["code"], contract=metadata[task_id]["contract"], inputs=decoded["inputs"])
        matched = matched_twenty(expanded, requests)
        def batch(items):
            if len(items) > 20:
                raise ValueError("Audit policy exceeded20inputs")
            return {"status": "generated" if items else "no_inputs", "inputs": items, "rejected": []}
        original = read(Path(plan["source_run"]) / "decoded" / number / "soft_bva.json")
        bundles[task_id] = {"fixed": {"task_id": task_id, "arms": {
            "soft_original": original, "recovered_seeds": decoded,
            "concept_matched": batch(matched["concept"]), "generic_matched": batch(matched["generic"]),
            "autonomous_precision": batch([item["input"] for item in fixed_twenty(expanded)]),
        }}}
        constructions[task_id] = {"outer_fence_removed": unwrapped, "expanded": expanded, "matched": matched,
                                 "normalized_requests": requests, "raw_index_remapping": remapping}
    directory.mkdir(parents=True)
    save(directory / "bundles.json", bundles)
    save(directory / "constructions.json", constructions)
    save(directory / "generation_frozen.json", {"bundles_sha256": digest(bundles),
        "constructions_sha256": digest(constructions), "tasks": list(bundles)})
    save(directory / "plan.json", {"cohort": plan["cohort"], "task_ids": list(bundles), "fixed_budget": 20,
        "scope": "Post-hoc outer JSON fence removal only; all directive/value checks unchanged",
        "source": str(source), "new_model_calls": 0, "primary_gate_unchanged": primary["gate"]})
    paths = [path for path in Path("final/src").rglob("*.py") if "tests" not in path.parts]
    paths += list(source.rglob("*.json")) + [Path("final/src/modular/PREREG.md"), Path(plan["cohort"]),
        Path("final/data/contracts.json"), Path("final/data/humaneval.jsonl"),
        Path("final/data/humanevalplus_v0.1.10_references.json"), *directory.glob("*.json")]
    save(directory / "source_snapshot.json", {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(paths))})
    save(directory / "status.json", {"state": "all_audit_inputs_frozen", "new_model_calls": 0})
    print({"artifacts": str(directory), "state": "all_audit_inputs_frozen", "new_model_calls": 0}, flush=True)
    verify(directory)
    summary = evaluate(directory, "fixed")
    if summary != evaluate(directory, "fixed", read_only=True):
        raise ValueError("Audit read-only replay differs")
    verify(directory)
    rows = []
    for task_id in plan["task_ids"]:
        number = int(task_id.split("/")[-1])
        result = read(directory / "evaluation_fixed/tasks" / str(number) / "result.json")
        outcomes = {}
        for arm in bundles[task_id]["fixed"]["arms"]:
            mapping = outcomes_by_input(directory, "fixed", number, arm)
            outcomes[arm] = [{"input": {"args": key[0], "kwargs": key[1]}, "outcome": value}
                             for key, value in mapping.items()]
        rows.append({"task_id": task_id, "arms": result["arms"], "construction": constructions[task_id], "outcomes": outcomes})
    report = {"scope": "Post-hoc envelope audit, not a changed primary Phase B result", "new_model_calls": 0,
              "arms": summary["arms"], "rows": rows, "primary_gate_unchanged": primary["gate"],
              "read_only_replay_matches": True}
    save(directory / "report.json", report)
    save(directory / "status.json", {"state": "complete", "new_model_calls": 0})
    print({"artifacts": str(directory), "arms": summary["arms"], "primary_gate_unchanged": primary["gate"]}, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("final/out/boundary_precision_direction_20261107_153836"))
    parser.add_argument("--artifacts", type=Path)
    options = parser.parse_args()
    directory = (options.artifacts or Path("final/out/boundary_precision_interface_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))).resolve()
    run(options.source.resolve(), directory)


if __name__ == "__main__":
    main()
