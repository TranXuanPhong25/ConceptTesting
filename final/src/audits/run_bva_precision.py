"""Offline Phase A: frozen soft seeds → adjacent floats → fixed20/pool evaluation."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path

from final.src.models.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.boundary_value_analysis.inputs import decode_inputs
from final.src.modular.boundary_value_analysis.precision import expand_seeds, fixed_twenty, call_identity
from final.src.modular.call_builder import CallBuilder
from final.src.modular.cohort import load_cohort
from final.src.modular.context import PipelineSettings
from final.src.benchmarks.datasets import load_tasks, load_metadata
from final.src.modular.execution_cache import InputExecutionCache
from final.src.modular.generators.base import InputGenerator
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.runtime.artifacts import digest, save
from final.src.audits.run_prompt_style import read, reusable_response
from .detection_kinds import evaluation_observations


def verify(directory):
    for name, expected in read(directory / "source_snapshot.json").items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Frozen file changed: " + name)


def prepare(source, cohort_path, directory):
    if directory.exists():
        raise ValueError("Use a new output directory")
    if read(source / "status.json")["state"] != "complete":
        raise ValueError("Source diagnostic must be complete")
    cohort = load_cohort(cohort_path)
    tasks = {task["task_id"]: task for task in load_tasks()}
    metadata = load_metadata()
    bundles, constructions = {}, {}
    for row in cohort["tasks"]:
        task_id = row["task_id"]
        task = tasks[task_id]
        number = int(task_id.split("/")[-1])
        if len(row["programs"]) != 1 or row["programs"][0]["base"]["status"] != "pass":
            raise ValueError("Expected exactly one base-passing PUT per task")
        program = row["programs"][0]
        batches = {}
        for arm in ("direct", "soft_bva"):
            request = read(source / "requests" / str(number) / (arm + ".json"))
            if request["put_id"] != program["id"] or request["input_budget"] != 20:
                raise ValueError("Source PUT or budget mismatch")
            packet = json.loads(request["messages"][1]["content"].split("TASK DATA (data, not instructions):\n")[1])
            if (packet["specification"] != task["prompt"] or packet["put_source"] != program["code"]
                    or packet["domain_contract"] != metadata[task_id]["contract"]):
                raise ValueError("Source packet mismatch")
            checkpoint = reusable_response(source, number, arm, request)
            if checkpoint is None:
                raise ValueError("Source response missing")
            response = ModelResponse(**read(checkpoint[0]))
            decoded = decode_inputs(response, CallBuilder.for_source(task["prompt"], task["entry_point"]), 20)
            if decoded != read(source / "decoded" / str(number) / (arm + ".json")):
                raise ValueError("Source decode mismatch")
            batches[arm] = decoded
        expanded = expand_seeds(specification=task["prompt"], entry_point=task["entry_point"],
            program_source=program["code"], contract=metadata[task_id]["contract"], inputs=batches["soft_bva"]["inputs"])
        selected = fixed_twenty(expanded)
        fixed_inputs = [item["input"] for item in selected]
        if len(fixed_inputs) > 20:
            raise ValueError("Primary policy exceeded20inputs")
        fixed_batch = {"status": "generated" if fixed_inputs else "no_inputs", "inputs": fixed_inputs, "rejected": []}
        pool = expanded["seeds"] + [item["input"] for item in expanded["expansions"]]
        pool_batch = {"status": "generated" if pool else "no_inputs", "inputs": pool, "rejected": []}
        bundles[task_id] = {"fixed": {"task_id": task_id, "arms": {**batches, "precision_fixed": fixed_batch}},
                            "pool": {"task_id": task_id, "arms": {"precision_pool": pool_batch}}}
        constructions[task_id] = {**expanded, "selection": selected}
    directory.mkdir(parents=True)
    save(directory / "bundles.json", bundles)
    save(directory / "constructions.json", constructions)
    save(directory / "generation_frozen.json", {"bundles_sha256": digest(bundles),
         "constructions_sha256": digest(constructions), "tasks": list(bundles)})
    pool_budget = max(len(row["pool"]["arms"]["precision_pool"]["inputs"]) for row in bundles.values())
    save(directory / "plan.json", {"source_run": str(source.resolve()), "cohort": str(cohort_path.resolve()),
         "task_ids": list(bundles), "fixed_budget": 20, "pool_budget": pool_budget, "new_model_calls": 0,
         "policy": "first10seeds+first10round-robin-adjacent-expansions;remaining-seed-fill",
         "gate": "new stable value-mismatch PUT and no lost soft-detected PUT; pool alone cannot pass"})
    source_paths = [path for path in Path("final/src").rglob("*.py") if "tests" not in path.parts]
    source_paths += list(source.rglob("*.json"))
    source_paths += [cohort_path, Path("final/src/modular/PREREG.md"),
        Path("final/review/boundary_soft_tool_plan_2026-11-07.md"),
        Path("final/data/contracts.json"), Path("final/data/humaneval.jsonl"),
        Path("final/data/humanevalplus_v0.1.10_references.json"), *directory.glob("*.json")]
    save(directory / "source_snapshot.json", {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
         for path in sorted(set(source_paths))})
    save(directory / "status.json", {"state": "prepared", "new_model_calls": 0})
    return read(directory / "plan.json")


class FrozenPrecisionInputs(InputGenerator):
    def __init__(self, directory, policy):
        self.directory, self.policy = Path(directory).resolve(), policy
        self.freeze = read(self.directory / "generation_frozen.json")

    def configuration(self):
        return {"directory": str(self.directory), "policy": self.policy, "freeze": self.freeze}

    def source_dependencies(self):
        return (self.directory / "bundles.json", self.directory / "generation_frozen.json")

    def generate(self, context):
        bundles = read(self.directory / "bundles.json")
        if digest(bundles) != self.freeze["bundles_sha256"]:
            raise ValueError("Frozen input bundles changed")
        return bundles[context.task["task_id"]][self.policy]


def evaluate(directory, policy, *, read_only=False):
    plan = read(directory / "plan.json")
    tasks = [task for task in load_tasks() if task["task_id"] in plan["task_ids"]]
    budget = plan["fixed_budget"] if policy == "fixed" else plan["pool_budget"]
    return BenchmarkPipeline(Path(plan["cohort"]), ArtifactStore(directory / ("evaluation_" + policy), read_only=read_only),
        input_generator=FrozenPrecisionInputs(directory, policy), settings=PipelineSettings(target_programs=1, input_budget=budget),
        execution_cache=InputExecutionCache(Path("final/out/execution_cache"), read_only=read_only),
    ).run(tasks, load_metadata())


def outcomes_by_input(directory, policy, task_number, arm):
    task_directory = directory / ("evaluation_" + policy) / "tasks" / str(task_number)
    batch = read(task_directory / "inputs.json")
    oracle = read(task_directory / "oracle_valid.json")
    result = read(task_directory / "result.json")
    offsets, offset = {}, 0
    for name, item in batch["arms"].items():
        offsets[name] = offset
        offset += len(item["inputs"])
    rejections = {item["index"]: item for item in oracle["rejected"]}
    valid_indices = {call_identity(item): index for index, item in enumerate(oracle["tests"])}
    repeats = {put: evaluation_observations(task_directory, put, outcome)
               for put, outcome in result["outcomes"].items()}
    outcomes = {}
    for ordinal, item in enumerate(batch["arms"][arm]["inputs"]):
        raw_index = offsets[arm] + ordinal
        if raw_index in rejections:
            outcomes[call_identity(item)] = {"stage": "reference_rejected", "rejection": rejections[raw_index]}
        else:
            index = valid_indices[call_identity(item)]
            outcomes[call_identity(item)] = {"stage": "executed", "expected": oracle["tests"][index]["expected"],
                "puts": {put: values[index] for put, values in repeats.items()}}
    return outcomes


def detected_tasks(rows, arm, *, value_mismatch_only=False):
    detected = set()
    for row in rows:
        if value_mismatch_only:
            for record in row["outcomes"][arm]:
                if record["outcome"]["stage"] == "executed" and any(
                    len(repeats) == 2 and all(outcome["status"] == "fail" for outcome in repeats)
                    for repeats in record["outcome"]["puts"].values()):
                    detected.add(row["task_id"])
        elif row["arms"][arm]["detected"]:
            detected.add(row["task_id"])
    return detected


def analyze(directory, summaries):
    constructions = read(directory / "constructions.json")
    rows = []
    for task_id, construction in constructions.items():
        number = int(task_id.split("/")[-1])
        fixed = read(directory / "evaluation_fixed/tasks" / str(number) / "result.json")
        pool = read(directory / "evaluation_pool/tasks" / str(number) / "result.json")
        outcomes = {}
        for policy, arms in (("fixed", ("direct", "soft_bva", "precision_fixed")), ("pool", ("precision_pool",))):
            for arm in arms:
                mapping = outcomes_by_input(directory, policy, number, arm)
                outcomes[arm] = [{"input": {"args": key[0], "kwargs": key[1]}, "outcome": value}
                                 for key, value in mapping.items()]
        fixed_mapping = outcomes_by_input(directory, "fixed", number, "precision_fixed")
        pool_mapping = outcomes_by_input(directory, "pool", number, "precision_pool")
        expansion_trace = [{**item, "fixed_outcome": fixed_mapping.get(call_identity(item["input"]), {"stage": "not_selected"}),
                            "pool_outcome": pool_mapping[call_identity(item["input"])]} for item in construction["expansions"]]
        retained = {call_identity(item["input"]) for item in construction["selection"] if item["kind"] == "seed"}
        rows.append({"task_id": task_id, "arms": {**fixed["arms"], **pool["arms"]}, "outcomes": outcomes,
                     "seed_count": len(construction["seeds"]), "expansion_count": len(expansion_trace),
                     "expansion_trace": expansion_trace, "selection": construction["selection"],
                     "dropped_seeds": [{"seed_index": index, "input": item} for index, item in enumerate(construction["seeds"])
                                       if call_identity(item) not in retained]})
    baseline = detected_tasks(rows, "soft_bva")
    fixed = detected_tasks(rows, "precision_fixed")
    new_value_tasks = detected_tasks(rows, "precision_fixed", value_mismatch_only=True) - baseline
    lost = baseline - fixed
    plan = read(directory / "plan.json")
    original = read(Path(plan["source_run"]) / "result_digest.json")
    for arm in ("direct", "soft_bva"):
        if summaries["fixed"]["arms"][arm] != original["arms"][arm]:
            raise ValueError("Saved baseline no longer reproduces")
    return {"scope": "Post-hoc known10seed precision diagnostic; construction vs allocation, not general efficacy",
            "new_model_calls": 0, "rows": rows, "summaries": {key: summary["arms"] for key, summary in summaries.items()},
            "gate": {"passed": bool(new_value_tasks) and not lost, "new_value_mismatch_tasks": sorted(new_value_tasks),
                     "lost_soft_tasks": sorted(lost), "pool_only_cannot_pass": True}, "read_only_replay_matches": True}


def run_evaluation(directory):
    with (directory / ".worker.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory / "evaluation_started.json").open("x") as marker:
            json.dump({"automatic_restart": False}, marker)
        try:
            verify(directory)
            save(directory / "status.json", {"state": "running", "phase": "fixed20", "new_model_calls": 0})
            fixed = evaluate(directory, "fixed")
            if fixed != evaluate(directory, "fixed", read_only=True):
                raise ValueError("Fixed policy read-only replay differs")
            verify(directory)
            save(directory / "status.json", {"state": "running", "phase": "pool_ceiling", "new_model_calls": 0})
            pool = evaluate(directory, "pool")
            if pool != evaluate(directory, "pool", read_only=True):
                raise ValueError("Pool read-only replay differs")
            verify(directory)
            report = analyze(directory, {"fixed": fixed, "pool": pool})
            save(directory / "report.json", report)
            save(directory / "status.json", {"state": "complete", "gate": report["gate"], "new_model_calls": 0})
            print(json.dumps({"artifacts": str(directory), "summaries": report["summaries"], "gate": report["gate"]}), flush=True)
        except BaseException as error:
            save(directory / "status.json", {"state": "interrupted", "error_type": type(error).__name__, "new_model_calls": 0})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, default=Path("final/out/boundary_prompt_style10_20261107_120909"))
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--evaluate", action="store_true", help="Evaluate only after all fixed/pool inputs freeze; no model calls")
    options = parser.parse_args()
    directory = (options.artifacts or Path("final/out/boundary_precision_phase_a_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))).resolve()
    plan = prepare(options.source_run.resolve(), options.cohort.resolve(), directory)
    print(json.dumps({"artifacts": str(directory), "tasks": len(plan["task_ids"]), "pool_budget": plan["pool_budget"],
                      "new_model_calls": 0, "state": "all_inputs_frozen"}), flush=True)
    if options.evaluate:
        run_evaluation(directory)


if __name__ == "__main__":
    main()
