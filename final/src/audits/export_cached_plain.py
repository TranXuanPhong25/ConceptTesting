"""Project the stored naive plain arm unchanged and evaluate it with BVA's frozen scorer."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path

from .continue_bva_evaluation import read, save, digest, checksum, prepare, launch


def export(naive, bva_generation, bva_evaluation, directory):
    if directory.exists():
        raise ValueError("Use a new frozen plain export directory")
    original = read(naive / "modular_manifest.json")
    original_freeze = read(naive / "generation_frozen.json")
    scoring = read(bva_evaluation / "modular_manifest.json")
    if read(naive / "status.json")["state"] != "complete" or read(bva_evaluation / "status.json")["state"] != "complete":
        raise ValueError("Both source runs must be complete")
    for key in ("task_data_sha256", "metadata_sha256", "settings"):
        if original[key] != scoring[key]:
            raise ValueError("Source identity mismatch: " + key)
    if digest(original_freeze["inputs"]) != original_freeze["inputs_sha256"] or set(original_freeze["inputs"]) != set(original["tasks"]):
        raise ValueError("Naive global input ledger changed")
    bva_plan = read(bva_generation / "launch_plan.json")
    target_cohort = read(Path(bva_plan["cohort"]))
    programs = {(row["task_id"], program["id"]): program for row in target_cohort["tasks"] for program in row["programs"]}
    exclusions = read(naive / "resource_exclusions.json")
    for record in exclusions["records"]:
        program = programs[(record["task_id"], record["put_id"])]
        if hashlib.sha256(program["code"].encode()).hexdigest() != record["raw_source_sha256"]:
            raise ValueError("Excluded PUT source differs")
    skip_by_task = {row["task_id"]: row["reason"] for row in bva_plan["skips"]}
    plain_record = next(record for record in original["arms"] if record["name"] == "plain")
    snapshot = read(bva_generation / "source_snapshot.json")
    sources = dict(snapshot["sources"])
    for name in ("modular_manifest.json", "generation_frozen.json", "resource_exclusions.json"):
        path = naive / name
        sources[str(path)] = checksum(path)
    exported, receipts, source_skips = {}, [], []
    directory.mkdir(parents=True)
    (directory / ".worker.lock").touch()
    for task_id in original["tasks"]:
        number = task_id.split("/")[-1]
        source_inputs = naive / "tasks" / number / "inputs.json"
        whole = read(source_inputs)
        if digest(whole) != original_freeze["inputs"][task_id]:
            raise ValueError("Naive source batch changed: " + task_id)
        sources[str(source_inputs)] = checksum(source_inputs)
        if task_id in skip_by_task:
            batch = {"task_id": task_id, "skip": skip_by_task[task_id]}
        elif whole.get("skip"):
            source_skips.append({"task_id": task_id, "reason": whole["skip"]})
            batch = {"task_id": task_id, "arms": {"plain": {"inputs": [], "rejected": [],
                "status": "source_task_skipped", "skip": whole["skip"]}}}
        else:
            batch = {"task_id": task_id, "arms": {"plain": whole["arms"]["plain"]}}
        destination = directory / "tasks" / number / "inputs.json"
        save(destination, batch)
        exported[task_id] = digest(batch)
        packet_path = naive / "tasks" / number / "packet.json"
        sources[str(packet_path)] = checksum(packet_path)
        save(directory / "tasks" / number / "packet.json", read(packet_path))
        receipts.append({"task_id": task_id, "original_whole_batch_sha256": original_freeze["inputs"][task_id],
            "exported_batch_sha256": exported[task_id], "plain_inputs_unchanged": not whole.get("skip"),
            "source_skip": whole.get("skip")})
    usage = collections.Counter()
    responses = list(naive.glob("tasks/*/calls/plain/response.json"))
    attempts = list(naive.glob("tasks/*/calls/plain*/attempt.json"))
    for path in [*responses, *attempts, *naive.glob("tasks/*/calls/plain/request.json")]:
        sources[str(path)] = checksum(path)
    for path in responses:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            usage[key] += read(path).get("usage", {}).get(key, 0)
    save(directory / "modular_manifest.json", {"protocol": "frozen-naive-input-export-1", "arms": [plain_record],
        "tasks": original["tasks"], "cohort_sha256": original["cohort_sha256"], "settings": original["settings"],
        "task_data_sha256": original["task_data_sha256"], "metadata_sha256": original["metadata_sha256"],
        "model": original["model"], "python": scoring["python"], "packages": scoring["packages"],
        "stages": [record for record in scoring["stages"] if record["name"] == "put_evaluation"],
        "scoring_runtime_manifest": str(bva_evaluation / "modular_manifest.json"),
        "generation_provenance": {"source": str(naive), "manifest_sha256": checksum(naive / "modular_manifest.json")}})
    save(directory / "generation_frozen.json", {"cohort_sha256": original["cohort_sha256"], "inputs": exported,
        "inputs_sha256": digest(exported)})
    save(directory / "launch_plan.json", {"cohort": bva_plan["cohort"], "frozen_runtime": str(bva_generation / "runtime")})
    save(directory / "export_receipts.json", {"source": str(naive), "batches": receipts, "source_task_skips_on_new_targets": source_skips,
        "historical_resource_exclusions": exclusions["records"], "original_plain_usage": {"invocations": len(attempts),
            "received": len(responses), "unknown": len(attempts)-len(responses), "known_usage": dict(usage)},
        "policy": "unchanged admitted plain inputs; no response repair or missing-input generation"})
    for path in directory.rglob("*.json"):
        sources[str(path)] = checksum(path)
    save(directory / "source_snapshot.json", {"sources": sources, "archive": snapshot["archive"]})
    save(directory / "status.json", {"state": "frozen_export", "new_model_calls": 0})
    return {"tasks": len(exported), "original_plain_calls": len(responses),
        "inputs": sum(len(read(directory / "tasks" / task.split('/')[-1] / "inputs.json").get("arms", {}).get("plain", {}).get("inputs", [])) for task in exported),
        "resource_exclusions": len(exclusions["records"]), "new_model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--naive", type=Path, default=Path("final/out/v11_concept_inputs"))
    parser.add_argument("--bva-generation", type=Path, default=Path("final/out/boundary_soft_humaneval164_resume_20261107_195417"))
    parser.add_argument("--bva-evaluation", type=Path, default=Path("final/out/boundary_soft_humaneval164_evaluation_20261107_224720"))
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    options = parser.parse_args()
    directory = (options.artifacts or Path("final/out/naive_vs_soft_bva_full164_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))).resolve()
    plain = directory / "plain_inputs"
    result = export(options.naive.resolve(), options.bva_generation.resolve(), options.bva_evaluation.resolve(), plain)
    evaluation = directory / "evaluation"
    prepare(plain, evaluation)
    result.update(artifacts=str(directory), evaluation=str(evaluation))
    if not options.prepare_only:
        result["pid"] = launch(evaluation)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
