"""Frozen V11-family run over existing programs; every stage/checkpoint is per PUT."""

import fcntl
import hashlib
import importlib.metadata
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from final.pipeline import digest, save
from final.run import load_tasks
from final.experiments.concept_reference_v1.cohort import load_cohort
from final.experiments.concept_reference_v1_recovery.model import TransportError
from final.experiments.concept_reference_v1_recovery.checkpoint import (
    CompletionRetryLimit,
)
from .cohort import V11ProgramView
from .context import V11Context
from .model_calls import V11ModelCalls
from .sandbox import V11Sandbox
from .stages import V11MiningStage, V11FactsStage
from .arm import V11Arm
from .evaluation import V11ReferenceEvaluationStage
from final.experiments.concept_reference_v1_recovery.keepalive import KeepAlive

OUTPUT = Path("final/out/v11_clean_runtimefix")
ARM_NAMES = ("v11_concept", "v11_plain", "v11_placebo", "v11_witness", "v11_toolinput")


def source_hashes():
    result = {}
    for directory in [
        Path(__file__).parent,
        Path("trickcatcher_linefacts/pipelines/v11_fair"),
    ]:
        for path in directory.glob("*"):
            if path.is_file() and path.suffix in (".py", ".json"):
                result[str(path.resolve())] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    for path in [
        Path("final/experiments/concept_reference_v1_recovery/model.py"),
        Path("final/experiments/concept_reference_v1_recovery/checkpoint.py"),
        Path("final/experiments/concept_reference_v1/worker.py"),
        Path("final/experiments/concept_reference_v1/execution.py"),
        Path("final/pipeline.py"),
        Path("final/core_model.py"),
        Path("final/experiments/concept_reference_v1_recovery/keepalive.py"),
    ]:
        result[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in [
        "final/modular/stages/reporting.py",
        "final/experiments/concept_reference_v1/worker.py",
        "final/experiments/concept_reference_v1/contracts.py",
        "final/experiments/concept_reference_v1/data/contracts.json",
    ]:
        path = Path(name)
        result[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class V11BenchmarkRunner:
    def __init__(self, directory=OUTPUT, stage_factories=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.cohort = load_cohort(
            Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json")
        )
        self.tasks = {task["task_id"]: task for task in load_tasks()}
        self.metadata = json.loads(
            Path(
                "final/experiments/concept_reference_v1/data/contracts.json"
            ).read_text()
        )
        self.calls = V11ModelCalls(self.directory)
        self.sandbox = V11Sandbox()
        self.stage_factories = tuple(
            stage_factories or (V11MiningStage, V11FactsStage, V11Arm)
        )

    def cases(self):
        cases = []
        for task in self.cohort["tasks"]:
            for program in task["programs"]:
                case_id = int(task["task_id"].split("/")[1]) * 10 + program["id"]
                cases.append((case_id, self.tasks[task["task_id"]], program))
        return cases

    def one_case(self, case):
        case_id, human_eval, program = case
        directory = self.directory / "cases" / str(case_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "result.json"
        if path.exists():
            return json.loads(path.read_text())
        if program["base"]["status"] != "pass":
            result = dict(
                case_id=case_id,
                task_id=human_eval["task_id"],
                program_id=program["id"],
                state="base_rejected",
            )
            save(path, result)
            return result
        try:
            view = V11ProgramView().build(human_eval, program)
            task = dict(
                task=case_id,
                entry=human_eval["entry_point"],
                put=view,
                base=human_eval["test"],
                split="fixed_cohort",
            )
            context = V11Context(
                task, human_eval, program, directory, self.calls, self.sandbox
            )
            save(
                directory / "program_view.json",
                dict(
                    raw_source_sha256=hashlib.sha256(
                        program["code"].encode()
                    ).hexdigest(),
                    method_source=view,
                    seed_alias=case_id,
                    original_task_id=human_eval["task_id"],
                ),
            )
            for factory in self.stage_factories:
                stage = factory()
                save(
                    directory / "progress.json",
                    dict(stage=stage.name, state="running", updated_utc=time.time()),
                )
                stage.run(context)
                save(
                    directory / "progress.json",
                    dict(stage=stage.name, state="complete", updated_utc=time.time()),
                )
            # Arm outputs are durable before the evaluation-only reference is opened.
            save(
                directory / "progress.json",
                dict(
                    stage="v11_reference_evaluation",
                    state="running",
                    updated_utc=time.time(),
                ),
            )
            evaluation = V11ReferenceEvaluationStage().run(
                context, self.metadata[human_eval["task_id"]]
            )
            result = dict(evaluation, state="complete")
            save(
                directory / "progress.json",
                dict(
                    stage="v11_reference_evaluation",
                    state="complete",
                    updated_utc=time.time(),
                ),
            )
        except (TransportError, CompletionRetryLimit):
            raise
        except (
            RuntimeError,
            ValueError,
            SyntaxError,
            KeyError,
            TypeError,
            StopIteration,
            AttributeError,
        ) as error:
            result = dict(
                case_id=case_id,
                task_id=human_eval["task_id"],
                program_id=program["id"],
                state="preparation_or_execution_failed",
                error_type=type(error).__name__,
                error=str(error)[:500],
            )
            save(
                directory / "progress.json",
                dict(
                    stage="case",
                    state="failed",
                    error_type=type(error).__name__,
                    updated_utc=time.time(),
                ),
            )
        save(path, result)
        return result

    def summary(self, include_comparisons=False):
        rows = [
            json.loads(path.read_text())
            for path in (self.directory / "cases").glob("*/result.json")
        ]
        totals = {
            arm: dict(detected=0, valid_inputs=0, logical_calls=0) for arm in ARM_NAMES
        }
        for row in rows:
            for arm, record in row.get("arms", {}).items():
                totals[arm]["detected"] += record["detected"]
                totals[arm]["valid_inputs"] += record["valid_inputs"]
                totals[arm]["logical_calls"] += record["llm_calls"]
        requests = list((self.directory / "requests").glob("*/calls/*/attempt.json"))
        responses = list((self.directory / "requests").glob("*/calls/*/response.json"))
        tokens = 0
        incomplete_usage_responses = 0
        for path in responses:
            usage = json.loads(path.read_text()).get("usage", {})
            tokens += usage.get("total_tokens", 0)
            incomplete_usage_responses += usage.get("usage_footer_complete") is False
        summary = dict(
            expected_programs=1634,
            expected_base_pass=1465,
            finished=len(rows),
            states={
                state: sum(row["state"] == state for row in rows)
                for state in sorted({row["state"] for row in rows})
            },
            arms=totals,
            physical_attempts=len(requests),
            received_responses=len(responses),
            unknown_usage_attempts=len(requests) - len(responses),
            known_tokens=tokens,
            received_responses_with_unknown_token_usage=incomplete_usage_responses,
        )
        observer_records = [
            json.loads(path.read_text())
            for path in (self.directory / "keepalive").glob("*.json")
        ]
        summary["observer"] = dict(
            attempts=len(observer_records),
            received=sum(record["state"] == "received" for record in observer_records),
            not_sent=sum(record["state"] == "not_sent" for record in observer_records),
            unknown=sum(
                record["state"] not in ("received", "not_sent")
                for record in observer_records
            ),
            known_tokens=sum(
                record.get("usage", {}).get("total_tokens", 0)
                for record in observer_records
            ),
        )
        grouped = {}
        for case_id, human_eval, program in self.cases():
            if program["base"]["status"] != "pass":
                continue
            task_id = human_eval["task_id"]
            task_row = grouped.setdefault(
                task_id,
                dict(
                    task_id=task_id,
                    base_pass=0,
                    outcomes={},
                    arm_indices={arm: [] for arm in ARM_NAMES},
                ),
            )
            task_row["base_pass"] += 1
            task_row["outcomes"][str(program["id"])] = dict(failing=[])
        for row in rows:
            if row.get("state") != "complete":
                continue
            task_row = grouped[row["task_id"]]
            offset = row["case_id"] * 100000
            task_row["outcomes"][str(row["program_id"])]["failing"] = [
                offset + index for index in row["failing_indices"]
            ]
            for arm, record in row["arms"].items():
                task_row["arm_indices"][arm] += [
                    offset + index for index in record["selected_indices"]
                ]
        if include_comparisons:
            from final.modular.stages.reporting import ReportingStage

            reporter = ReportingStage()
            task_rows = sorted(
                grouped.values(),
                key=lambda record: int(record["task_id"].split("/")[1]),
            )
            summary["matched_valid_input_comparisons"] = [
                reporter.compare(task_rows, "v11_concept", baseline)
                for baseline in ("v11_plain", "v11_placebo", "v11_toolinput")
            ]
        save(self.directory / "summary.json", summary)
        return summary

    def run(self):
        with (
            (self.directory / ".run.lock").open("a+") as lock,
            KeepAlive(self.directory),
        ):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            manifest = dict(
                protocol="v11-clean-family-k1",
                cohort_sha256=self.cohort["cohort_sha256"],
                model=self.calls.model.model_id,
                samples=1,
                stages=[
                    factory.__module__ + "." + factory.__qualname__
                    for factory in self.stage_factories
                ],
                arms=ARM_NAMES,
                source_hashes=source_hashes(),
                programs=len(self.cases()),
                python=sys.version,
                packages={
                    name: importlib.metadata.version(name)
                    for name in ("evalplus", "numpy")
                },
                worker_packages={
                    "hypothesis": "6.169.0",
                    "mutmut": "3.8.0",
                    "coverage": "7.16.2",
                    "libcst": "1.9.0",
                },
                worker_runtime={
                    "coverage_core": "pytrace",
                    "idle_timeout_seconds": 120,
                    "max_idle_restarts": 1,
                },
                runtime_import_manifest_sha256=hashlib.sha256(
                    (self.directory / "import_manifest.json").read_bytes()
                ).hexdigest(),
                adaptations=[
                    "qwen3.5-27b-awq",
                    "K1",
                    "original spec metadata restored",
                    "canonical oracle",
                    "per-PUT seed alias",
                ],
            )
            manifest = json.loads(json.dumps(manifest))
            path = self.directory / "manifest.json"
            if path.exists() and json.loads(path.read_text()) != manifest:
                raise ValueError("Frozen V11 manifest changed")
            save(path, manifest)
            save(self.directory / "status.json", dict(state="running", pid=os.getpid()))
            executor = ThreadPoolExecutor(max_workers=2)
            pending = {}
            iterator = iter(self.cases())

            def submit():
                case = next(iterator, None)
                if case is not None:
                    pending[executor.submit(self.one_case, case)] = case[0]

            for _ in range(2):
                submit()
            try:
                while pending:
                    future = next(as_completed(pending))
                    case_id = pending.pop(future)
                    result = future.result()
                    summary = self.summary()
                    save(
                        self.directory / "status.json",
                        dict(
                            state="running",
                            pid=os.getpid(),
                            last_case=case_id,
                            summary=summary,
                        ),
                    )
                    print(
                        f"V11 {summary['finished']}/1634 case={case_id} state={result['state']}",
                        flush=True,
                    )
                    submit()
            except BaseException as error:
                for future in pending:
                    future.cancel()
                executor.shutdown(wait=True, cancel_futures=True)
                save(
                    self.directory / "status.json",
                    dict(
                        state="interrupted",
                        pid=os.getpid(),
                        error_type=type(error).__name__,
                        error=error.details()
                        if isinstance(error, TransportError)
                        else None,
                        summary=self.summary(),
                    ),
                )
                return 2
            executor.shutdown(wait=True)
            save(
                self.directory / "status.json",
                dict(
                    state="complete",
                    pid=os.getpid(),
                    summary=self.summary(include_comparisons=True),
                ),
            )
            return 0


if __name__ == "__main__":
    raise SystemExit(V11BenchmarkRunner().run())
