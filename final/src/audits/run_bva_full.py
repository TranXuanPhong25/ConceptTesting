"""Launch the existing soft BVA pipeline on full HumanEval with frozen run guards."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from final.src.modular.arms.boundary import BoundaryArm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.boundary_value_analysis.prompts import generation_messages
from final.src.modular.call_builder import CallBuilder
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.cohort import load_cohort, call_usage
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.dataset import load_tasks, load_metadata
from final.src.modular.execution_cache import InputExecutionCache
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.stages.input_preparation import InputPreparationStage
from final.src.runtime.artifacts import digest, save
from final.src.models.keepalive import KeepAlive
from final.src.models.model import QwenModel
from .run_prompt_style import configure_endpoint, read


ROOT = Path(__file__).resolve().parents[3]


def prepare(cohort_path, directory, input_budget=20):
    if directory.exists():
        raise ValueError("Use a new output directory")
    cohort = load_cohort(cohort_path)
    tasks = load_tasks()
    if {row["task_id"] for row in cohort["tasks"]} != {task["task_id"] for task in tasks}:
        raise ValueError("Full run requires all164tasks in the frozen cohort")
    records = {row["task_id"]: row for row in cohort["tasks"]}
    metadata = load_metadata()
    settings = PipelineSettings(target_programs=10, input_budget=input_budget)
    arm = BoundaryArm()
    requests, eligible, skips = {}, [], []
    for task in tasks:
        CallBuilder.for_source(task["prompt"], task["entry_point"])
        context = TaskContext(task, metadata[task["task_id"]], ArtifactStore(directory), settings)
        context.cohort_task = records[task["task_id"]]
        packet = InputPreparationStage([arm]).prepare(context)
        if packet.get("skip"):
            skips.append({"task_id": task["task_id"], "reason": packet["skip"]})
            continue
        eligible.append(task["task_id"])
        identifiers = packet["visible_put_ids"][:input_budget]
        quotient, remainder = divmod(input_budget, len(identifiers))
        programs = {program["id"]: program for program in context.cohort_task["programs"]}
        for index, identifier in enumerate(identifiers):
            program = programs[identifier]
            allocation = quotient + (index < remainder)
            messages = generation_messages(task_id=task["task_id"], specification=task["prompt"],
                contract=context.metadata["contract"], program_source=program["code"],
                base_inputs=program["base"].get("calls", []), input_budget=allocation, base_example_limit=12)
            request = {"messages": messages, "temperature": settings.input_temperature,
                       "max_tokens": settings.input_tokens, "seed": settings.input_seed + context.task_number}
            key = f"{context.task_number}/bva_{identifier}_soft_inputs"
            requests[key] = {"request_sha256": digest(request), "messages_sha256": digest(messages),
                             "input_budget": allocation}
    directory.mkdir(parents=True)
    save(directory / "launch_plan.json", {
        "cohort": str(cohort_path.resolve()), "cohort_sha256": cohort["cohort_sha256"], "tasks": len(tasks),
        "eligible_task_ids": eligible, "skips": skips, "logical_call_cap": len(requests),
        "target_programs": 10, "input_budget": input_budget, "method": arm.configuration(),
        "requests": requests, "precision_tools": False, "new_plain_calls": 0,
        "readiness_policy": "exact model/context plus tokenizer; per-PUT context overflow is an explicit skip",
    })
    sources = [path.resolve() for path in Path("final/src/modular").rglob("*.py") if "tests" not in path.parts]
    sources += [path.resolve() for path in Path("final/src/runtime").glob("*.py")]
    sources += [path.resolve() for path in Path("final/src/models").glob("*.py")]
    sources += [Path(__file__).resolve(),
                Path("final/src/audits/run_prompt_style.py").resolve(), Path("final/__init__.py").resolve(),
                Path("final/src/__init__.py").resolve(), Path("final/src/audits/__init__.py").resolve()]
    sources += [cohort_path.resolve(), Path("final/data/humaneval.jsonl").resolve(),
        Path("final/data/contracts.json").resolve(), Path("final/data/humanevalplus_v0.1.10_references.json").resolve(),
        directory / "launch_plan.json"]
    hashes, archives = {}, {}
    notes = Path("final/src/modular/PREREG.md").resolve()
    for path in sorted(set(sources + [notes])):
        if not path.is_relative_to(ROOT):
            raise ValueError("Source archive requires repository-local files")
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        archived = directory / "source_archive" / path.relative_to(ROOT)
        archived.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, archived)
        if path != notes:
            hashes[str(path)] = checksum
        archives[str(archived)] = checksum
    save(directory / "source_snapshot.json", {"sources": hashes, "archive": archives})
    save(directory / "status.json", {"state": "prepared", "tasks": len(tasks), "logical_call_cap": len(requests)})
    return read(directory / "launch_plan.json")


class SourceGuard:
    def __init__(self, directory):
        self.snapshot = read(directory / "source_snapshot.json")

    def verify(self, *, archive=False):
        sections = ("sources", "archive") if archive else ("sources",)
        for section in sections:
            for name, checksum in self.snapshot[section].items():
                if hashlib.sha256(Path(name).read_bytes()).hexdigest() != checksum:
                    raise RuntimeError("Frozen file changed: " + name)


class GuardedCalls(RecordedModelCalls):
    def __init__(self, model, artifacts, guard, plan):
        super().__init__(model, artifacts)
        self.guard, self.plan = guard, plan
        self.allowed_messages = {request["messages_sha256"] for request in plan["requests"].values()}

    def token_count(self, messages):
        self.guard.verify()
        if digest(messages) not in self.allowed_messages:
            raise ValueError("Unregistered tokenization request")
        return super().token_count(messages)

    def complete(self, task_number, call_name, messages, *, temperature, max_tokens, seed):
        self.guard.verify()
        key = f"{task_number}/{call_name}"
        request = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens, "seed": seed}
        expected = self.plan["requests"].get(key)
        if expected is None or digest(request) != expected["request_sha256"]:
            raise ValueError("Unregistered completion request")
        return super().complete(task_number, call_name, messages, temperature=temperature, max_tokens=max_tokens, seed=seed)


class ProgressPipeline(BenchmarkPipeline):
    def __init__(self, *args, guard, **kwargs):
        self.guard = guard
        self.generated_tasks = self.evaluated_tasks = 0
        self.keepalive = None
        self.total_tasks = 164
        super().__init__(*args, **kwargs)

    def execute_stages(self, stages, context):
        self.guard.verify()
        return super().execute_stages(stages, context)

    def record_stage_event(self, context, stage, state, **details):
        super().record_stage_event(context, stage, state, **details)
        if state == "complete" and stage.name in ("input_generation", "put_evaluation"):
            self.generated_tasks += stage.name == "input_generation"
            self.evaluated_tasks += stage.name == "put_evaluation"
            # Stop observer writes before ReportingStage reads final accounting.
            if self.evaluated_tasks == self.total_tasks and self.keepalive is not None:
                self.keepalive.stop_event.set()
                self.keepalive.thread.join()
            record = {"task_id": context.task["task_id"], "stage": stage.name,
                      "generated_tasks": self.generated_tasks, "evaluated_tasks": self.evaluated_tasks,
                      "updated_utc": time.time()}
            if not self.artifacts.read_only:
                save(self.artifacts.path("progress.json"), record)
                print(json.dumps(record), flush=True)


def worker(directory):
    with (directory / ".worker.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory / "worker_started.json").open("x") as marker:
            json.dump({"pid": os.getpid(), "started_utc": time.time(), "automatic_restart": False}, marker)
        guard = SourceGuard(directory)
        try:
            guard.verify(archive=True)
            plan = read(directory / "launch_plan.json")
            model = QwenModel()
            save(directory / "status.json", {"state": "preflight", "pid": os.getpid()})
            endpoint = model.check_endpoint()
            probe_tokens = model.tokens([{"role": "user", "content": "ping"}])
            save(directory / "readiness.json", {"endpoint": endpoint, "tokenizer_probe_tokens": probe_tokens})
            guard.verify()
            artifacts = ArtifactStore(directory)
            settings = PipelineSettings(target_programs=plan["target_programs"], input_budget=plan["input_budget"])
            calls = GuardedCalls(model, artifacts, guard, plan)
            pipeline = ProgressPipeline(Path(plan["cohort"]), artifacts, calls=calls, arms=(BoundaryArm(),), settings=settings,
                execution_cache=InputExecutionCache(Path("final/out/execution_cache")), guard=guard)
            save(directory / "status.json", {"state": "running", "pid": os.getpid(), "tasks": plan["tasks"],
                 "logical_call_cap": plan["logical_call_cap"], "started_utc": time.time()})
            with KeepAlive(directory) as keepalive:
                pipeline.keepalive = keepalive
                summary = pipeline.run(load_tasks(), load_metadata())
                guard.verify(archive=True)
                replay = BenchmarkPipeline(Path(plan["cohort"]), ArtifactStore(directory, read_only=True),
                    arms=(BoundaryArm(),), settings=settings,
                    execution_cache=InputExecutionCache(Path("final/out/execution_cache"), read_only=True))
                if summary != replay.run(load_tasks(), load_metadata()):
                    raise ValueError("Read-only replay differs")
            guard.verify(archive=True)
            if call_usage(directory)["received"] > plan["logical_call_cap"]:
                raise ValueError("Generation call cap exceeded")
            digest_record = {"requested_tasks": plan["tasks"], "eligible_tasks": len(plan["eligible_task_ids"]),
                "evaluated_base_pass": summary["evaluated_base_pass"],
                "arms": summary["arms"], "skips": summary["skips"], "boundary_analysis": summary["boundary_analysis"],
                "tester_calls": summary["tester_calls"], "keepalive_calls": summary["keepalive_calls"],
                "replay_matches": True, "source_and_archive_hashes_verified": True,
                "scope": "full164softBVA;existing eligibility and20inputs/task;no matched plain control"}
            save(directory / "result_digest.json", digest_record)
            save(directory / "status.json", {"state": "complete", "pid": os.getpid(), "finished_utc": time.time(), **digest_record})
            print(json.dumps(digest_record), flush=True)
        except BaseException as error:
            save(directory / "status.json", {"state": "interrupted", "pid": os.getpid(), "updated_utc": time.time(),
                 "error_type": type(error).__name__, "error": error.details() if hasattr(error, "details") else str(error)})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"))
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--input-budget", type=int, default=20)
    parser.add_argument("--prepare-only", action="store_true", help="No network or model calls; freeze exact request identities")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.input_budget < 1:
        parser.error("input budget must be positive")
    directory = (options.artifacts or Path("final/out/boundary_soft_humaneval164_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))).resolve()
    if options.worker:
        worker(directory)
        return
    if not options.prepare_only:
        configure_endpoint()
    plan = prepare(options.cohort.resolve(), directory, options.input_budget)
    print(json.dumps({"artifacts": str(directory), "tasks": plan["tasks"], "eligible_tasks": len(plan["eligible_task_ids"]),
                      "logical_call_cap": plan["logical_call_cap"], "input_budget_per_task": plan["input_budget"]}), flush=True)
    if options.prepare_only:
        return
    with (directory / "launch_reserved.json").open("x") as marker:
        json.dump({"automatic_restart": False}, marker)
    with (directory / "runner.log").open("xb") as log:
        process = subprocess.Popen([sys.executable, "-u", "-m", "final.src.audits.run_bva_full", "--worker", "--artifacts", str(directory)],
            cwd=ROOT, env=dict(os.environ), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (directory / "runner.pid").write_text(str(process.pid) + "\n")
    print(json.dumps({"pid": process.pid, "log": str(directory / "runner.log"), "status": str(directory / "status.json")}), flush=True)


if __name__ == "__main__":
    main()
