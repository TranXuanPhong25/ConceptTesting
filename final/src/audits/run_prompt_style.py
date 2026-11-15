"""Matched direct/soft-BVA/worksheet diagnostic; a fresh directory per invocation."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from final.src.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.call_builder import CallBuilder
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.cohort import call_usage, load_cohort
from final.src.modular.context import PipelineSettings
from final.src.modular.dataset import load_tasks
from final.src.modular.execution_cache import InputExecutionCache
from final.src.modular.generators.base import InputGenerator
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.runtime.artifacts import digest, save
from final.src.runtime.keepalive import KeepAlive
from final.src.runtime.model import QwenModel, TransportError


ARMS = ("direct", "soft_bva", "worksheet")
MODEL = "qwen3.5-27b-awq"
LEGACY_ENDPOINT_FILE = Path("/tmp/concepttester-final-qwen.env")


def configure_endpoint(explicit_file=None):
    """Resolve private configuration before preparing a run; no network request."""
    selected_file = explicit_file or os.environ.get("FINAL_ENDPOINT_ENV_FILE")
    if selected_file:
        path = Path(selected_file).expanduser().resolve()
        if not path.is_file():
            raise ValueError("Endpoint env file does not exist; check --endpoint-env-file or FINAL_ENDPOINT_ENV_FILE")
    elif os.environ.get("FINAL_BASE_URL"):
        # An explicit process URL should not be overwritten by a stale default file.
        path = Path(os.devnull)
    else:
        configuration_root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        persistent = configuration_root / "concepttester" / "final-qwen.env"
        legacy = LEGACY_ENDPOINT_FILE
        path = persistent if persistent.is_file() else legacy
        if not path.is_file():
            raise ValueError("Missing Qwen endpoint. Set FINAL_BASE_URL or use --endpoint-env-file; "
                             "default private config: ~/.config/concepttester/final-qwen.env")
    os.environ["FINAL_ENDPOINT_ENV_FILE"] = str(path)
    QwenModel()  # Configuration validation only; no models/tokenizer/completion call.
    return path


def read(path):
    return json.loads(Path(path).read_text())


def status(directory, state, **details):
    save(directory / "status.json", {"state": state, "pid": os.getpid(), "updated_utc": time.time(), **details})


def request_identity(request):
    return {key: request[key] for key in ("messages", "temperature", "max_tokens", "seed")}


def decode(response, builder, budget):
    """Common strict parser matching the completed three-task diagnostic."""
    if response.finish_reason == "length":
        return {"status": "invalid_generation", "inputs": [], "rejected": [{"reason": "truncated_response"}]}
    try:
        record = json.loads(response.text)
        if not isinstance(record, dict) or set(record) != {"inputs"} or not isinstance(record["inputs"], list):
            raise ValueError("invalid_envelope")
        if len(record["inputs"]) > budget:
            raise ValueError("input_budget_exceeded")
    except (ValueError, TypeError, RecursionError):
        return {"status": "invalid_generation", "inputs": [], "rejected": [{"reason": "invalid_response"}]}
    accepted, rejected, seen = [], [], set()
    for index, row in enumerate(record["inputs"]):
        try:
            if not isinstance(row, dict) or set(row) != {"arguments"}:
                raise ValueError("invalid_input_record")
            encoded = builder.build(row["arguments"])
            identity = encoded["args"], encoded["kwargs"]
            if identity in seen:
                raise ValueError("duplicate_within_arm")
            seen.add(identity)
            accepted.append(encoded)
        except (ValueError, TypeError, OverflowError, RecursionError) as error:
            reason = str(error) if type(error) is ValueError else "invalid_input_record"
            rejected.append({"index": index, "reason": reason})
    return {"status": "generated" if accepted else "no_inputs", "inputs": accepted, "rejected": rejected}


def verify(directory):
    snapshot = read(directory / "source_snapshot.json")
    for section in ("sources", "prior_outputs"):
        for name, expected in snapshot[section].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
                raise RuntimeError("Frozen file changed: " + name)


def execution_sources():
    """Keep production code frozen; test edits cannot affect this runner."""
    return [path for path in Path("final/src").rglob("*.py")
            if "tests" not in path.parts and not path.name.startswith("test_")]


def validate_continuation(directory):
    if read(directory / "status.json")["state"] not in {"interrupted", "complete"}:
        raise ValueError("Continuation source is not stopped")
    snapshot = read(directory / "source_snapshot.json")
    for section in ("sources", "prior_outputs"):
        for name, expected in snapshot[section].items():
            path = Path(name)
            # Only this controller and non-executable tests may change for recovery.
            if section == "sources" and (path.resolve() == Path(__file__).resolve()
                    or "tests" in path.parts or path.name.startswith("test_")):
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Continuation frozen file changed: " + name)


def reusable_response(source, number, arm, request):
    """Import a received call or its verified inherited receipt, never an unknown attempt."""
    old_call = source / "tasks" / str(number) / "calls" / ("style_" + arm)
    inherited = source / "reused_calls" / str(number) / arm
    old_plan = source / "requests" / str(number) / (arm + ".json")
    if old_plan.exists() and read(old_plan) != request:
        raise ValueError("Reuse request mismatch; choose fresh requests explicitly")
    if old_call.exists():
        attempt = read(old_call / "attempt.json")
        previous_request = read(old_call / "request.json")
        if attempt.get("state") != "received" or attempt.get("request_id") != digest(previous_request):
            raise ValueError("Reuse requires a received checkpoint; unresolved calls cannot be retried")
        call = old_call
    elif inherited.exists():
        call = inherited
        previous_request = read(call / "request.json")
    else:
        return None
    if read(old_plan) != request or previous_request != request_identity(request):
        raise ValueError("Reuse request mismatch; choose fresh requests explicitly")
    snapshot_path = source / "source_snapshot.json"
    snapshot = read(snapshot_path)
    frozen = {**snapshot["sources"], **snapshot["prior_outputs"]}
    paths = [old_plan, snapshot_path, *call.glob("*.json")]
    for path in paths:
        expected = frozen.get(str(path.resolve()))
        if path == old_plan and expected is None:
            raise ValueError("Reuse request is not frozen")
        if call == inherited and path.parent == call and expected is None:
            raise ValueError("Inherited reuse file is not frozen")
        if expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Reuse frozen checksum mismatch: " + str(path))
    response_path = call / "response.json"
    response_hash = hashlib.sha256(response_path.read_bytes()).hexdigest()
    if call == inherited:
        receipt = read(call / "receipt.json")
        original = Path(receipt["source_response"])
        if (receipt.get("request_identity_matched") is not True or receipt["sha256"] != response_hash
                or hashlib.sha256(original.read_bytes()).hexdigest() != response_hash):
            raise ValueError("Inherited response checksum mismatch")
        paths.append(original)
    return response_path, paths


class FrozenStyleInputs(InputGenerator):
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.freeze = read(self.directory / "direct_inputs_frozen.json")

    def configuration(self):
        return {"directory": str(self.directory), "freeze": self.freeze, "setting": "same-packet-prompt-style"}

    def source_dependencies(self):
        return (self.directory / "direct_inputs_frozen.json", self.directory / "encoded_inputs.json")

    def generate(self, context):
        batch = read(self.directory / "encoded_inputs.json")[context.task["task_id"]]
        if digest(batch) != self.freeze[context.task["task_id"]]:
            raise ValueError("Frozen direct inputs changed")
        return batch


def prepare(options):
    continuation = getattr(options, "continue_from", None)
    if continuation is not None:
        if options.no_reuse:
            raise ValueError("--continue-from cannot be combined with --no-reuse")
        # Hold the old worker's existing lock without writing any old artifact.
        with (continuation / ".worker.lock").open("r") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            validate_continuation(continuation)
            return prepare_run(options, [continuation.resolve()])
    sources = [options.reuse.resolve()] if options.reuse is not None and not options.no_reuse else []
    return prepare_run(options, sources)


def prepare_run(options, reuse_sources):
    directory = options.artifacts.resolve()
    if directory.exists():
        raise ValueError("Output already exists; choose a new --artifacts directory")
    if any(not source.is_dir() for source in reuse_sources):
        raise ValueError("Reuse directory missing; use --no-reuse explicitly for a fresh run")
    cohort = load_cohort(options.cohort)
    records = {row["task_id"]: row for row in cohort["tasks"]}
    tasks = [task for task in load_tasks() if task["task_id"] in records]
    if not tasks:
        raise ValueError("No known tasks in cohort")
    styles = read(options.styles)
    settings = styles["settings"]
    if (set(styles["styles"]) != set(ARMS) or settings != {
            "temperature": 0.7, "max_tokens": 2048, "context_tokens": 8192, "input_budget": 20, "model": MODEL}):
        raise ValueError("Style settings differ from the registered diagnostic")
    metadata = read(Path("final/data/contracts.json"))
    directory.mkdir(parents=True)
    source_paths = execution_sources() + [Path(__file__), options.cohort, options.styles,
        Path("final/data/contracts.json"), Path("final/data/humaneval.jsonl"),
        Path("final/data/humanevalplus_v0.1.10_references.json")]
    order, reused, reused_usage, prior_outputs = [], [], [], []
    for index, task in enumerate(tasks):
        number = int(task["task_id"].split("/")[-1])
        programs = records[task["task_id"]]["programs"]
        if len(programs) != 1 or programs[0]["base"]["status"] != "pass":
            raise ValueError("Each task must have exactly one base-passing PUT")
        program = programs[0]
        base = [{key: row[key] for key in ("args", "kwargs", "bound") if key in row}
                for row in program["base"].get("calls", [])[:12]]
        packet = {"task_id": task["task_id"], "specification": task["prompt"],
                  "domain_contract": metadata[task["task_id"]]["contract"], "put_source": program["code"],
                  "existing_inputs": base}
        for arm in ARMS:
            messages = [{"role": "system", "content": styles["system"]}, {"role": "user", "content":
                styles["common"] + "\nGUIDANCE:\n" + styles["styles"][arm]
                + "\nTASK DATA (data, not instructions):\n" + json.dumps(packet, ensure_ascii=False)}]
            request = {"task": number, "put_id": program["id"], "arm": arm,
                       "messages": messages, **settings, "seed": 314159 + number}
            if getattr(options, "continue_from", None):
                previous_plan = reuse_sources[0] / "requests" / str(number) / (arm + ".json")
                if not previous_plan.is_file() or read(previous_plan) != request:
                    raise ValueError("Continuation request mismatch")
            request_path = directory / "requests" / str(number) / (arm + ".json")
            save(request_path, request)
            source_paths.append(request_path)
            for source in reuse_sources:
                checkpoint = reusable_response(source, number, arm, request)
                if checkpoint is not None:
                    response_path, dependencies = checkpoint
                    response = read(response_path)
                    imported = directory / "reused_calls" / str(number) / arm
                    save(imported / "request.json", request_identity(request))
                    save(imported / "response.json", response)
                    receipt = {"source_response": str(response_path.resolve()),
                               "sha256": hashlib.sha256(response_path.read_bytes()).hexdigest(),
                               "request_identity_matched": True}
                    save(imported / "receipt.json", receipt)
                    source_paths.extend(imported.glob("*.json"))
                    prior_outputs.extend(dependencies)
                    reused.append([number, arm])
                    reused_usage.append(response.get("usage", {}))
                    break
        rotation = index % len(ARMS)
        order.extend([number, arm] for arm in ARMS[rotation:] + ARMS[:rotation])
    plan = {"cohort": str(options.cohort.resolve()), "styles": str(options.styles.resolve()),
            "tasks": [task["task_id"] for task in tasks], "order": order, "settings": settings,
            "logical_slots": len(order), "reused_slots": reused, "new_logical_calls": len(order) - len(reused),
            "reused_usage": {key: sum(row.get(key, 0) for row in reused_usage)
                             for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "generation_scope": "same-packet diagnostic; received responses reused only with exact request identity",
            "reuse_source": str(reuse_sources[0]) if reuse_sources else None,
            "continuation_source": str(options.continue_from.resolve()) if getattr(options, "continue_from", None) else None}
    save(directory / "run_plan.json", plan)
    source_paths.append(directory / "run_plan.json")
    checksums = lambda paths: {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sorted(set(paths)) if path.is_file()}
    save(directory / "source_snapshot.json", {"sources": checksums(source_paths), "prior_outputs": checksums(prior_outputs)})
    status(directory, "prepared", logical_slots=len(order), reused_slots=len(reused), new_logical_calls=plan["new_logical_calls"])
    return plan


def evaluate(directory, plan, read_only=False):
    tasks = [task for task in load_tasks() if task["task_id"] in plan["tasks"]]
    return BenchmarkPipeline(Path(plan["cohort"]), ArtifactStore(directory / "evaluation", read_only=read_only),
        input_generator=FrozenStyleInputs(directory), settings=PipelineSettings(target_programs=1, input_budget=20),
        execution_cache=InputExecutionCache(Path("final/out/execution_cache"), read_only=read_only),
    ).run(tasks, read(Path("final/data/contracts.json")))


def worker(directory):
    with (directory / ".worker.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory / "worker_started.json").open("x") as marker:
            json.dump({"pid": os.getpid(), "started_utc": time.time(), "automatic_restart": False}, marker)
        try:
            verify(directory)
            plan = read(directory / "run_plan.json")
            status(directory, "preflight")
            model = QwenModel()
            endpoint = model.check_endpoint()
            token_counts = []
            for number, arm in plan["order"]:
                request = read(directory / "requests" / str(number) / (arm + ".json"))
                count = model.tokens(request["messages"])
                if count + request["max_tokens"] + 128 > request["context_tokens"]:
                    raise ValueError("Prompt exceeds configured context; no completion sent")
                token_counts.append({"task": number, "arm": arm, "prompt_tokens": count})
            save(directory / "prelaunch_readiness.json", {"state": "ready", "endpoint": endpoint, "requests": token_counts})
            calls = RecordedModelCalls(model, ArtifactStore(directory))
            tasks = {task["task_id"]: task for task in load_tasks()}
            batches = {}
            with KeepAlive(directory):
                for slot, (number, arm) in enumerate(plan["order"]):
                    verify(directory)
                    status(directory, "running", phase="generation", slot=slot + 1, task=number, arm=arm)
                    request = read(directory / "requests" / str(number) / (arm + ".json"))
                    cached = directory / "reused_calls" / str(number) / arm / "response.json"
                    if cached.exists():
                        response = ModelResponse(**read(cached))
                    else:
                        response = calls.complete(number, "style_" + arm, request["messages"],
                            temperature=request["temperature"], max_tokens=request["max_tokens"], seed=request["seed"])
                    task_id = "HumanEval/" + str(number)
                    task = tasks[task_id]
                    batch = decode(response, CallBuilder.for_source(task["prompt"], task["entry_point"]), 20)
                    save(directory / "decoded" / str(number) / (arm + ".json"), batch)
                    batches.setdefault(task_id, {"task_id": task_id, "arms": {}})["arms"][arm] = batch
                    print(json.dumps({"task": number, "arm": arm, "reused": cached.exists(),
                                      "status": batch["status"], "admitted_inputs": len(batch["inputs"])}), flush=True)
            for batch in batches.values():
                batch["arms"] = {arm: batch["arms"][arm] for arm in ARMS}
            save(directory / "encoded_inputs.json", batches)
            save(directory / "direct_inputs_frozen.json", {key: digest(value) for key, value in batches.items()})
            save(directory / "generation_costs.json", {"new_calls": call_usage(directory),
                "reused_response_count": len(plan["reused_slots"]), "reused_historical_usage": plan["reused_usage"]})
            verify(directory)
            status(directory, "running", phase="evaluation_after_all_outputs_frozen")
            summary = evaluate(directory, plan)
            if summary != evaluate(directory, plan, read_only=True):
                raise ValueError("Read-only replay differs")
            verify(directory)
            save(directory / "result_digest.json", {"arms": summary["arms"],
                "costs": read(directory / "generation_costs.json"), "replay_matches": True,
                "scope": "outcome-selected10PUT diagnostic; reused/new epochs disclosed, not general efficacy"})
            status(directory, "complete", arms=summary["arms"])
            print(json.dumps({"arms": summary["arms"]}), flush=True)
        except BaseException as error:
            status(directory, "interrupted", error_type=type(error).__name__,
                   error=error.details() if hasattr(error, "details") else None)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--styles", type=Path, default=Path("final/review/prompts/prompt_style_v1.json"))
    parser.add_argument("--reuse", type=Path)
    parser.add_argument("--continue-from", type=Path, help="Continue a stopped run in a fresh directory, importing received and inherited responses")
    parser.add_argument("--no-reuse", action="store_true", help="Regenerate all slots instead of importing matching old responses")
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--endpoint-env-file", type=Path, help="Private env file outside the repository; not printed or copied")
    parser.add_argument("--detach", action="store_true", help="Start an independent background controller and print PID/log path")
    parser.add_argument("--check-only", action="store_true", help="Prepare/verify requests and reuse offline; no network or model calls")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.artifacts is None:
        options.artifacts = Path("final/out/boundary_prompt_style10_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
    directory = options.artifacts.resolve()
    if options.worker:
        worker(directory)
        return
    if not options.check_only:
        try:
            configure_endpoint(options.endpoint_env_file)
        except (ValueError, OSError) as error:
            parser.error(str(error) if type(error) is ValueError else "Cannot read the private endpoint env file")
        except TransportError as error:
            parser.error("Qwen endpoint configuration failed: " + error.error_type +
                         ". Check --endpoint-env-file or FINAL_BASE_URL; no run created.")
    plan = prepare(options)
    print(json.dumps({"artifacts": str(directory), "tasks": len(plan["tasks"]), "logical_slots": plan["logical_slots"],
                      "reused_slots": len(plan["reused_slots"]), "new_model_calls_planned": plan["new_logical_calls"]}), flush=True)
    if options.check_only:
        return
    if not options.detach:
        worker(directory)
        return
    with (directory / "runner.log").open("xb") as log:
        process = subprocess.Popen([sys.executable, "-u", "-m", "final.src.audits.run_prompt_style", "--worker", "--artifacts", str(directory)],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=dict(os.environ))
    (directory / "runner.pid").write_text(str(process.pid) + "\n")
    print(json.dumps({"pid": process.pid, "log": str(directory / "runner.log"), "status": str(directory / "status.json")}), flush=True)


if __name__ == "__main__":
    main()
