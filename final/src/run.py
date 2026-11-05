"""Run from the repository root: python -m final.src.run --help."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib
import json
import os
import platform
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from .core_model import CoreModel, OpenAICompatibleModel
from .execution import execute
from .pipeline import Pipeline, Settings, digest, save, summarize

HERE = Path(__file__).resolve().parent
DATA_SHA256 = "b2adeeae8b383b6f0c615746a397f25c8abe44da4afb29cd10e6c4bbf0463fd3"


def load_tasks():
    path = HERE.parent / "data" / "humaneval.jsonl"
    if hashlib.sha256(path.read_bytes()).hexdigest() != DATA_SHA256:
        raise ValueError("Bundled HumanEval dataset checksum mismatch")
    tasks = [json.loads(line) for line in path.read_text().splitlines()]
    if len(tasks) != 164 or {t["task_id"] for t in tasks} != {f"HumanEval/{i}" for i in range(164)}:
        raise ValueError("Need exactly the original 164 HumanEval tasks")
    return sorted(tasks, key=lambda t: int(t["task_id"].split("/")[1]))


def check_sandbox():
    result = execute(dict(mode="base", source="def f(x): return x + 1", entry="f",
                          base="def check(candidate): assert candidate(1) == 2", timeout=3))
    if result["status"] != "pass":
        raise RuntimeError("Sandbox preflight failed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE.parent / "out" / "humaneval164")
    parser.add_argument("--model", default=os.environ.get("FINAL_MODEL"))
    parser.add_argument("--base-url-env", default="FINAL_BASE_URL")
    parser.add_argument("--api-key-env", default="FINAL_API_KEY")
    parser.add_argument("--backend-factory", help="module:function; function(args) returns a CoreModel")
    parser.add_argument("--extra-body", default="{}", help="JSON object, e.g. provider-specific sampling options")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--task-ids", nargs="*", type=int, help="Explicit subset for engineering runs; default all 164")
    parser.add_argument("--generation-rounds", type=int, default=5)
    parser.add_argument("--tests", type=int, default=30)
    parser.add_argument("--generation-tokens", type=int, default=16000)
    parser.add_argument("--test-tokens", type=int, default=8000)
    parser.add_argument("--request-timeout", type=float, default=240)
    parser.add_argument("--execution-timeout", type=float, default=3)
    parser.add_argument("--check", action="store_true", help="Validate data/sandbox; no model or API calls")
    args = parser.parse_args(argv)
    if not (1 <= args.workers <= 16 and 1 <= args.generation_rounds <= 10 and 1 <= args.tests <= 100
            and args.generation_tokens > 0 and args.test_tokens > 0
            and args.request_timeout > 0 and args.execution_timeout > 0):
        parser.error("Worker count, generation rounds, tests, token budgets and timeouts must be in range")
    tasks = load_tasks()
    if args.task_ids is not None:
        if not args.task_ids or len(set(args.task_ids)) != len(args.task_ids) or any(i not in range(164) for i in args.task_ids):
            parser.error("task-ids must contain unique integers in 0..163")
        tasks = [task for task in tasks if int(task["task_id"].split("/")[1]) in args.task_ids]
    check_sandbox()
    if args.check:
        print(f"OK: 164 HumanEval tasks, checksum verified; isolated sandbox; Python {platform.python_version()}")
        return 0
    if args.backend_factory:
        module, name = args.backend_factory.rsplit(":", 1)
        model = getattr(importlib.import_module(module), name)(args)
        if not isinstance(model, CoreModel):
            parser.error("Backend factory must return a CoreModel instance")
        backend = args.backend_factory
    else:
        if not args.model:
            parser.error("Set FINAL_MODEL or pass --model (the model/endpoint has not been selected)")
        extra = json.loads(args.extra_body)
        if not isinstance(extra, dict):
            parser.error("extra-body must be a JSON object")
        model = OpenAICompatibleModel(args.model, base_url_env=args.base_url_env,
                                     api_key_env=args.api_key_env, timeout=args.request_timeout, extra_body=extra)
        backend = "final.src.core_model:OpenAICompatibleModel"
    settings = Settings(generation_rounds=args.generation_rounds, tests=args.tests,
                        generation_tokens=args.generation_tokens, test_tokens=args.test_tokens,
                        timeout=args.execution_timeout)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Keep the lock handle alive through every model call, including error cleanup.
    with (out / ".run.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another process already owns this output directory")
        manifest = dict(protocol="final-humaneval-v1", model=model.model_id, backend=backend,
                        settings=asdict(settings), tasks=[t["task_id"] for t in tasks],
                        dataset_sha256=DATA_SHA256, python=platform.python_version(),
                        python_executable=str(Path(sys.executable).resolve()),
                        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(HERE.glob("*.py"))},
                        extra_body_sha256=digest(args.extra_body))
        manifest_path = out / "manifest.json"
        if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
            parser.error("Manifest differs from this run; use a new output directory")
        save(manifest_path, manifest)
        save(out / "status.json", dict(state="running", expected_tasks=len(tasks)))
        pipeline = Pipeline(model, out, settings)
        pool = ThreadPoolExecutor(max_workers=args.workers)
        pending, next_task = {}, iter(tasks)

        def submit():
            task = next(next_task, None)
            if task is not None:
                pending[pool.submit(pipeline.run_task, task)] = task["task_id"]

        for _ in range(args.workers):
            submit()
        try:
            finished = 0
            while pending:
                future = next(as_completed(pending))
                task_id = pending.pop(future)
                result = future.result()
                finished += 1
                print(f"[{finished}/{len(tasks)}] {task_id}: generated={result['generated']} "
                      f"base_pass={result['base_pass']} detected={result['detected_programs']} "
                      f"status={result['status']}", flush=True)
                summarize(out, len(tasks))
                submit()
        except BaseException as exc:
            for future in pending:
                future.cancel()
            # Allow active invocations to persist their responses; never start replacement calls.
            pool.shutdown(wait=True, cancel_futures=True)
            summary = summarize(out, len(tasks))
            save(out / "status.json", dict(state="interrupted", error_type=type(exc).__name__, summary=summary))
            print(f"Run interrupted ({type(exc).__name__}); checkpoints saved. No automatic retries.", file=sys.stderr)
            return 2
        pool.shutdown(wait=True)
        summary = summarize(out, len(tasks))
        complete = summary["complete_generation_tasks"] == len(tasks)
        save(out / "status.json", dict(state="complete" if complete else "generation_shortfall", summary=summary))
        print(json.dumps(summary, indent=2))
        return 0 if complete else 3


if __name__ == "__main__":
    raise SystemExit(main())
