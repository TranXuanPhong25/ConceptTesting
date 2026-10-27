"""Detached, resumable driver with frozen messages and no inference retries."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..retrieval_v2 import corpus
from .client import Client, atomic, digest
from . import prompts

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "retrieval_v2/evaluation"


def tasks():
    return json.loads((OLD / "inputs.json").read_text())


def verify_inputs():
    manifest = json.loads((HERE / "data/INPUTS.json").read_text())
    for name, sha in manifest["input_files"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != sha:
            raise ValueError("Frozen input drift: " + name)
    if corpus.digest() != manifest["corpus_sha256"]:
        raise ValueError("Frozen corpus drift")


def validate_judge(response, mapping):
    parsed = response.get("parsed") or {}
    for group in ("cards", "bindings"):
        rows = parsed.get(group)
        if not isinstance(rows, list) or len(rows) != len(mapping[group]):
            return False
        if {r.get("key") for r in rows if isinstance(r, dict)} != set(mapping[group]):
            return False
        for row in rows:
            if group == "cards":
                if type(row.get("grade")) is not int or not 0 <= row["grade"] <= 3:
                    return False
            elif any(type(row.get(k)) is not int or row[k] not in (0, 1) for k in ("where", "how", "what")):
                return False
    return True


def plan(out):
    verify_inputs()
    jobs = out / "retrieval_jobs"
    for task in tasks():
        stem = task["task_id"].replace("/", "_")
        record = {"task_id": task["task_id"], "split": task["split"], "code_sha256": hashlib.sha256(task["code"].encode()).hexdigest(),
                  "messages": prompts.retrieval(task), "baseline": prompts.baseline(task)}
        atomic(jobs / (stem + ".json"), record)
    freeze = {"files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "client.py", HERE / "prompts.py", HERE / "run.py")},
              "corpus_sha256": corpus.digest(), "jobs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(jobs.glob("*.json"))}}
    atomic(out / "PLAN_FREEZE.json", freeze)
    print("Prepared 113 public-only retrieval requests; no task inference.", flush=True)


def execute(stage, out, *, only=None):
    verify_inputs()
    frozen = json.loads((out / "PLAN_FREEZE.json").read_text())
    for name, sha in frozen["files"].items():
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != sha:
            raise ValueError("Run code changed after plan freeze: " + name)
    for name, sha in frozen["jobs"].items():
        if hashlib.sha256((out / "retrieval_jobs" / name).read_bytes()).hexdigest() != sha:
            raise ValueError("Retrieval message drift after freeze: " + name)
    client = Client(out)
    client.preflight()
    all_tasks = {t["task_id"]: t for t in tasks()}
    if only:
        selected = [all_tasks["HumanEval/" + n] for n in only]
    else:
        selected = list(all_tasks.values())
    jobs = []
    if stage == "retrieve":
        for task in selected:
            stem = task["task_id"].replace("/", "_")
            job = json.loads((out / "retrieval_jobs" / (stem + ".json")).read_text())
            jobs.append((task, "qwen", job["messages"], None))
    elif stage == "judge":
        refs = {r["task_id"]: r["prompt"] + r["canonical_solution"]
                for r in map(json.loads, (Path.home() / ".cache/evalplus/HumanEvalPlus-v0.1.10.jsonl").read_text().splitlines())}
        witness_rows = json.loads((OLD / "witness_grading.json").read_text())["results"]
        for task in selected:
            stem = task["task_id"].replace("/", "_")
            retrieved = json.loads((out / "retrieved" / (stem + ".json")).read_text())
            systems = {"v2": retrieved["baseline"], "v3": retrieved["selected"]}
            candidates = [w for w in witness_rows if w["task_id"] == task["task_id"] and w["validity"].get("value") is True
                          and w["reference"].get("status") == "ok" and not w["value_equal"]]
            candidates.sort(key=lambda w: len(json.dumps(w["args"])))
            witness = None
            if candidates:
                w = candidates[0]
                witness = {"args": w["args"], "expected": w["reference"], "actual": w["put"], "official_contract_passed": True}
            messages, mapping = prompts.judge(task, systems, refs[task["task_id"]], witness)
            atomic(out / "judge_jobs" / (stem + ".json"), {"task_id": task["task_id"], "messages": messages, "mapping": mapping})
            jobs.append((task, "blind", messages, mapping))
    elif stage == "utility":
        cohort = set(json.loads((HERE / "data/utility_cohort.json").read_text())["tasks"])
        for task in selected:
            if task["task_id"] not in cohort:
                continue
            stem = task["task_id"].replace("/", "_")
            row = json.loads((out / "retrieved" / (stem + ".json")).read_text())
            arms = {"plain": [], "v2": row["baseline"], "v3": row["selected"]}
            order = sorted(arms, key=lambda arm: hashlib.sha256((task["task_id"] + ":" + arm).encode()).hexdigest())
            for arm in order:
                jobs.append((task, arm, prompts.utility(task, arms[arm]), None))
    else:
        raise ValueError("unknown stage")

    def one(job):
        task, arm, messages, mapping = job
        n = int(task["task_id"].split("/")[1])
        limit = {"retrieve": 1200, "judge": 1000, "utility": 800}[stage]
        # Utility arms use the same seed; message content is the only treatment.
        seed = {"retrieve": 314100, "judge": 314200, "utility": 314300}[stage] + n
        response = client.complete(messages, stage=stage, max_tokens=limit, seed=seed)
        stem = task["task_id"].replace("/", "_")
        record = {"task_id": task["task_id"], "split": task["split"], "arm": arm, "response": response}
        if stage == "retrieve":
            selected_rows, error = prompts.parse_retrieval(response, task["code"])
            record.update(selected=selected_rows, schema_error=error, baseline=json.loads((out / "retrieval_jobs" / (stem + ".json")).read_text())["baseline"])
            atomic(out / "retrieved" / (stem + ".json"), record)
        elif stage == "judge":
            record.update(valid_schema=validate_judge(response, mapping), mapping=mapping)
            atomic(out / "judged" / (stem + ".json"), record)
        else:
            atomic(out / "utility" / (stem + "__" + arm + ".json"), record)
        return {"task_id": task["task_id"], "arm": arm, "status": response["status"], "finish": response.get("finish_reason"), "seconds": round(response["elapsed_seconds"], 2)}

    complete = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(one, job) for job in jobs]
        for future in as_completed(pending):
            event = future.result()
            complete += 1
            atomic(out / "STATUS.json", {"stage": stage, "completed": complete, "total": len(jobs), "started": started, "updated": time.time(), "last": event})
            print(json.dumps({"stage": stage, "completed": complete, "total": len(jobs), **event}), flush=True)
    atomic(out / (stage + "_COMPLETE.json"), {"stage": stage, "jobs": len(jobs), "finished": time.time()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["plan", "retrieve", "judge", "utility", "all"])
    parser.add_argument("--out", type=Path, default=HERE / "out/run_20261026")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.stage == "plan":
        plan(args.out)
    elif args.stage == "all":
        for name in ("retrieve", "judge", "utility"):
            execute(name, args.out)
    else:
        execute(args.stage, args.out, only=args.only)
