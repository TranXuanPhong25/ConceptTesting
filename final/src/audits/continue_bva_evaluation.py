"""Evaluate a complete frozen BVA generation with its original runtime, without a model."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(Path(path).read_text())


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def sandbox_binary():
    binary = shutil.which("bwrap", path=os.defpath)
    if binary is None:
        raise RuntimeError("bubblewrap missing from the sanitized executable path")
    return {"path": binary, "sha256": checksum(binary), "path_policy": os.defpath}


def prepare(source, directory, *, native_lock=None):
    if directory.exists():
        raise ValueError("Use a new evaluation directory")
    with (source / ".worker.lock").open("r") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if read(source / "status.json")["state"] not in ("interrupted", "frozen_export"):
            raise ValueError("Evaluation requires a stopped source or a frozen input export")
        manifest, freeze = read(source / "modular_manifest.json"), read(source / "generation_frozen.json")
        if (digest(freeze["inputs"]) != freeze["inputs_sha256"] or set(freeze["inputs"]) != set(manifest["tasks"])):
            raise ValueError("Source input freeze mismatch")
        for task_id in manifest["tasks"]:
            number = task_id.split("/")[-1]
            if digest(read(source / "tasks" / number / "inputs.json")) != freeze["inputs"][task_id]:
                raise ValueError("Frozen source inputs changed: " + task_id)
        if manifest["python"] != platform.python_version():
            raise ValueError("Python version differs from generation")
        for package, version in manifest["packages"].items():
            if importlib.metadata.version(package) != version:
                raise ValueError("Dependency version differs: " + package)
        snapshot = read(source / "source_snapshot.json")
        for section in ("sources", "archive"):
            for path, expected in snapshot[section].items():
                if checksum(path) != expected:
                    raise ValueError("Frozen parent dependency changed: " + path)
        runtime = Path(read(source / "launch_plan.json").get("frozen_runtime", str(source / "runtime"))).resolve()
        if not runtime.is_dir():
            raise ValueError("Missing isolated source runtime")
        descriptor = sandbox_binary()
        directory.mkdir(parents=True)
        control = directory / "control.py"
        shutil.copyfile(Path(__file__), control)
        control.chmod(0o444)
        sources = dict(snapshot["sources"])
        sources[str(control)] = checksum(control)
        for name in ("modular_manifest.json", "generation_frozen.json"):
            path = source / name
            sources[str(path)] = checksum(path)
        imported = []
        for task_id in manifest["tasks"]:
            task_directory = source / "tasks" / task_id.split("/")[-1]
            for name in ("inputs.json", "packet.json"):
                path = task_directory / name
                sources[str(path)] = checksum(path)
            paths = list(task_directory.glob("oracle*.json")) + list(task_directory.glob("reference_program.json"))
            paths += list(task_directory.glob("result.json")) + list((task_directory / "evaluation").glob("*.json"))
            for path in paths:
                destination = directory / path.relative_to(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
                expected = checksum(path)
                sources[str(path)] = expected
                sources[str(destination)] = expected
                imported.append({"source": str(path), "destination": str(destination), "sha256": expected})
        save(directory / "plan.json", {"source": str(source), "runtime": str(runtime),
            "cohort": read(source / "launch_plan.json")["cohort"], "settings": manifest["settings"],
            "execution_cache": next(stage["configuration"]["execution_cache"]["directory"]
                for stage in manifest["stages"] if stage["name"] == "put_evaluation"),
            "tasks": manifest["tasks"], "sandbox": descriptor, "new_model_calls": 0,
            "imported_task_results": len(list(source.glob("tasks/*/result.json"))),
            "scope": "evaluation only; original frozen runtime/scoring and exact source input ledger",
            "native_evaluation_lock": str(native_lock) if native_lock is not None else None})
        save(directory / "import_receipts.json", {"checkpoints": imported, "source_input_freeze": freeze})
        for path in (directory / "plan.json", directory / "import_receipts.json"):
            sources[str(path)] = checksum(path)
        save(directory / "source_snapshot.json", {"sources": sources, "archive": snapshot["archive"]})
        save(directory / "status.json", {"state": "prepared", "new_model_calls": 0})
        return read(directory / "plan.json")


def worker(directory):
    # Imports resolve only through the parent's read-only runtime, set by launch().
    from final.src.modular.arms.boundary import BoundaryArm
    from final.src.modular.arms.plain import PlainArm
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings
    from final.src.modular.cohort import call_usage
    from final.src.benchmarks.datasets import load_tasks, load_metadata
    from final.src.modular.execution_cache import InputExecutionCache
    from final.src.modular.generators.frozen import FrozenInputsGenerator
    from final.src.modular.stages.base import PipelineStage
    from final.src.runtime.execution import execute
    from final.src.audits.run_bva_full import ProgressPipeline

    class SavedPacket(PipelineStage):
        name = "saved_input_context"
        requires = ("cohort_loader",)

        def __init__(self, source):
            self.source = source

        def configuration(self):
            return {"source": str(self.source.directory)}

        def run(self, context):
            context.packet = self.source.read(context.task_directory + "/packet.json")
            context.artifacts.write(context.task_directory + "/packet.json", context.packet)

    class FrozenPackets(FrozenInputsGenerator):
        def __init__(self, source):
            names = [record["name"] for record in read(Path(source) / "modular_manifest.json")["arms"]]
            if names == ["boundary"]:
                methods = (BoundaryArm(),)
            elif names == ["plain"]:
                methods = (PlainArm(),)
            else:
                raise ValueError("Frozen evaluation supports only a plain or boundary batch")
            super().__init__(source, methods=methods)
            self.packet_stage = SavedPacket(self.source)

        def preparation_stages(self):
            return (self.packet_stage,)

        def source_dependencies(self):
            return (*super().source_dependencies(), *(self.source.path(f"tasks/{task.split('/')[-1]}/packet.json")
                for task in self.manifest["tasks"]))

    def smoke():
        descriptor = sandbox_binary()
        job = {"mode": "evaluate", "context": "def f(x):\n    pass\n", "source": "def f(x):\n    return x\n",
               "entry": "f", "tests": [{"args": "(1,)", "kwargs": "{}", "expected": "1"}],
               "atol": 0, "timeout": 3, "seed": 1}
        result = execute(job)
        if result["tests"][0]["status"] != "pass":
            raise RuntimeError("Cold sandbox smoke failed")
        return descriptor

    with (directory / ".worker.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory / "evaluation_started.json").open("x") as marker:
            json.dump({"pid": os.getpid(), "automatic_restart": False}, marker)
        try:


            plan = read(directory / "plan.json")
            readiness = smoke()
            if readiness["sha256"] != plan["sandbox"]["sha256"]:
                raise ValueError("Sandbox executable changed after preparation")
            save(directory / "sandbox_readiness.json", readiness)
            source = Path(plan["source"])
            methods = FrozenPackets(source)
            tasks = [task for task in load_tasks() if task["task_id"] in plan["tasks"]]
            metadata = load_metadata()
            settings = PipelineSettings(**plan["settings"])
            for attempt in range(2):
                pipeline = ProgressPipeline(Path(plan["cohort"]), ArtifactStore(directory), input_generator=methods,
                    settings=settings, execution_cache=InputExecutionCache(Path(plan["execution_cache"])))
                save(directory / "status.json", {"state": "running", "pid": os.getpid(), "phase": "evaluation_only",
                     "new_model_calls": 0, "infrastructure_attempt": attempt + 1})
                try:
                    summary = pipeline.run(tasks, metadata)
                    break
                except FileNotFoundError as error:
                    if error.filename != "bwrap" or attempt:
                        raise
                    save(directory / "sandbox_spawn_retry.json", {"error_type": type(error).__name__,
                         "filename": error.filename, "attempt": 1, "checkpoints_preserved": True})
                    smoke()

            replay = ProgressPipeline(Path(plan["cohort"]), ArtifactStore(directory, read_only=True), input_generator=FrozenPackets(source),
                settings=settings, execution_cache=InputExecutionCache(pipeline.execution_cache.directory, read_only=True))
            if replay.run(tasks, metadata) != summary:
                raise ValueError("Read-only replay differs")

            if call_usage(directory)["invocations"]:
                raise ValueError("Evaluation-only job unexpectedly recorded model calls")
            generation_usage = read(source / "export_receipts.json")["original_plain_usage"] if (source / "export_receipts.json").exists() else call_usage(source)
            report = {"arms": summary["arms"], "requested_tasks": len(tasks), "skips": summary["skips"],
                "evaluated_base_pass": summary["evaluated_base_pass"],
                "source_run": str(source), "new_model_calls": 0, "source_generation_usage": generation_usage,
                "reused_generation": summary["reused_generation"], "read_only_replay_matches": True,
                "source_and_input_hashes_verified": None, "imported_task_results": plan["imported_task_results"]}
            if "boundary_analysis" in summary:
                report["boundary_analysis"] = summary["boundary_analysis"]
            save(directory / "result_digest.json", report)
            save(directory / "status.json", {"state": "complete", "pid": os.getpid(), "finished_utc": time.time(), **report})
            print(json.dumps(report), flush=True)
        except BaseException as error:
            save(directory / "status.json", {"state": "interrupted", "pid": os.getpid(), "error_type": type(error).__name__, "error": str(error)})
            raise


def launch(directory):
    plan = read(directory / "plan.json")
    environment = {name: os.environ[name] for name in ("HOME", "LANG", "LC_ALL", "TZ", "TMPDIR") if name in os.environ}
    environment.update(PATH=os.defpath, PYTHONPATH=plan["runtime"], PYTHONDONTWRITEBYTECODE="1")
    with (directory / "launch_reserved.json").open("x") as marker:
        json.dump({"automatic_restart": False}, marker)
    with (directory / "runner.log").open("xb") as log:
        command = [sys.executable, "-P", "-B", "-u", str(directory / "control.py"), "--worker", "--artifacts", str(directory)]
        if plan.get("native_evaluation_lock"):
            command = ["/usr/bin/flock", "--no-fork", plan["native_evaluation_lock"], *command]
        process = subprocess.Popen(command,
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (directory / "runner.pid").write_text(str(process.pid) + "\n")
    return process.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, default=Path("final/out/boundary_soft_humaneval164_resume_20261107_195417"))
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    directory = (options.artifacts or Path("final/out/boundary_soft_humaneval164_evaluation_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))).resolve()
    if options.worker:
        worker(directory)
        return
    plan = prepare(options.source_run.resolve(), directory)
    result = {"artifacts": str(directory), "tasks": len(plan["tasks"]), "imported_task_results": plan["imported_task_results"], "new_model_calls": 0}
    if not options.prepare_only:
        result["pid"] = launch(directory)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
