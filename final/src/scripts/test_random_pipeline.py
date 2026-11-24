"""End-to-end pipeline test on random task(s), printing each stage and its intermediate data.

Run from repo root (safe offline mock mode by default):
    PYTHONPATH=. final/.venv/bin/python -m final.src.scripts.test_random_pipeline --seed 42
"""
from __future__ import annotations

from dataclasses import asdict
import argparse
import ast
import json
from pathlib import Path
import random
import tempfile
import time

from final.src.models.core_model import ModelResponse
from final.src.modular.arms import available_arms, selected_arms
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.cohort import load_cohort
from final.src.modular.context import PipelineSettings
from final.src.modular.generators.frozen import FrozenInputsGenerator
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.runtime.artifacts import digest, save
from final.src.scripts._formatting import (
    collect_run_results,
    format_table,
    load_dataset_bundle,
    render_arm_union_tables,
    render_banner,
)


class _DemoStubModel:
    """Offline deterministic stub model for inspecting the full pipeline without API calls."""

    model_id = "demo-offline-stub"

    def __init__(self, sample_inputs: dict[str, list[dict]]):
        self.sample_inputs = sample_inputs
        self.call_count = 0

    def tokens(self, messages) -> int:
        return max(1, len(json.dumps(messages)) // 4)

    def generate(self, messages, **kwargs) -> ModelResponse:
        self.call_count += 1
        text = json.dumps(messages)
        # Pick sample inputs matching the task if available, else fallback.
        chosen = []
        for task_key, records in self.sample_inputs.items():
            if task_key in text:
                chosen = records
                break
        if not chosen:
            chosen = next(iter(self.sample_inputs.values()), [{"args": "()", "kwargs": "{}"}])

        if "catalogue" in text.lower() or "equivalence" in text.lower() or "decision" in text.lower():
            payload = {
                "catalogue": {
                    "status": "applicable",
                    "classes": [{"id": "C1", "description": "demo class"}],
                    "boundaries": [],
                    "rules": [],
                },
                "inputs": [
                    {**record, "covers": ["C1"]}
                    for record in chosen
                ],
            }
        elif "concept" in text.lower() and "target" in text.lower():
            payload = {
                "concepts": [
                    {
                        "target_ids": ["T1"],
                        "instruction": "demo concept",
                        "inputs": chosen,
                    }
                ]
            }
        else:
            payload = {
                "inputs": [
                    {**record, "guidance_id": None}
                    for record in chosen
                ]
            }
        return ModelResponse(
            text=json.dumps(payload),
            usage={"prompt_tokens": 64, "completion_tokens": 48, "total_tokens": 112},
            finish_reason="stop",
        )


class _StubCalls:
    """Minimal recorded call adapter for offline mock mode."""

    def __init__(self, model: _DemoStubModel, artifacts: ArtifactStore):
        self.model = model
        self.artifacts = artifacts

    @property
    def model_id(self) -> str:
        return self.model.model_id

    def token_count(self, messages) -> int:
        return self.model.tokens(messages)

    def complete_structured(self, task_number, call_name, messages, *, schema, temperature, max_tokens, seed):
        return self.complete(
            task_number,
            call_name,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
        )

    def complete(self, task_number, call_name, messages, **parameters) -> ModelResponse:
        directory = self.artifacts.path(f"tasks/{task_number}/calls/{call_name}")
        request = dict(messages=messages, **parameters)
        save(directory / "request.json", request)
        save(directory / "attempt.json", {"request_id": digest(request), "state": "started"})
        response = self.model.generate(messages, **parameters)
        save(directory / "response.json", asdict(response))
        save(directory / "attempt.json", {"request_id": digest(request), "state": "received"})
        return response


def _preview(value, max_len: int = 100) -> str:
    rendered = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    rendered = " ".join(rendered.split())
    return rendered if len(rendered) <= max_len else rendered[: max_len - 3] + "..."


def _extract_example_calls(task: dict, limit: int = 3) -> list[dict]:
    """Extract sample argument tuples from task base tests for offline mock mode."""
    calls: list[dict] = []
    source = task.get("test", "")
    entry = task.get("entry_point", "")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("candidate", entry):
                try:
                    arg_values = tuple(ast.literal_eval(arg) for arg in node.args)
                    kw_values = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords if kw.arg}
                except (ValueError, TypeError):
                    continue
                calls.append({"args": repr(arg_values), "kwargs": repr(kw_values)})
                if len(calls) >= limit:
                    break
    return calls


def _create_synthetic_cohort(path: Path, tasks: list[dict]) -> Path:
    """Build a minimal local cohort with 1 canonical + 1 buggy PUT per task for offline demos."""
    records = []
    for task in tasks:
        entry = task["entry_point"]
        canonical = task["prompt"] + task["canonical_solution"]
        # A simple buggy implementation that returns None on every call.
        buggy = f"def {entry}(*args, **kwargs):\n    return None\n"
        records.append(
            {
                "task_id": task["task_id"],
                "generated": 2,
                "base_pass": 2,
                "base_input_keys": [],
                "programs": [
                    {
                        "id": 0,
                        "approach": "canonical_clone",
                        "code": canonical,
                        "base": {"status": "pass", "calls": [], "coverage": {"lines": [], "arcs": []}},
                    },
                    {
                        "id": 1,
                        "approach": "synthetic_return_none_bug",
                        "code": buggy,
                        "base": {"status": "pass", "calls": [], "coverage": {"lines": [], "arcs": []}},
                    },
                ],
            }
        )
    save(path, {"tasks": records, "cohort_sha256": digest(records), "dataset_sha256": "synthetic-demo"})
    return path


def _inspect_stage_data(context, stage_name: str) -> None:
    """Print structured intermediate data produced by a completed pipeline stage."""
    if stage_name == "input_context":
        packet = context.packet or {}
        print(
            f"    -> packet prepared: visible_put_ids={packet.get('visible_put_ids', [])}, "
            f"keys={sorted(packet.keys())}"
        )
    elif stage_name == "input_generation":
        arms_data = (context.inputs or {}).get("arms", {})
        rows = []
        for arm_name, batch in arms_data.items():
            inputs = batch.get("inputs", [])
            sample = _preview(inputs[0]) if inputs else "(none)"
            rows.append([arm_name, len(inputs), batch.get("catalogue_status", "-"), sample])
        print(
            format_table(
                ["Arm", "Generated Inputs", "Catalogue", "Sample Input #0"],
                rows,
                alignments=["<", ">", "<", "<"],
            )
        )
    elif stage_name == "reference_oracle":
        oracle = context.oracle or {}
        tests = oracle.get("tests", [])
        rejected = oracle.get("rejected", [])
        print(
            f"    -> valid unique inputs: {len(tests)}, rejected: {len(rejected)}, "
            f"arm_indices: { {k: len(v) for k, v in oracle.get('arm_indices', {}).items()} }"
        )
        if tests:
            sample = tests[0]
            print(
                f"    -> sample oracle[0]: args={_preview(sample.get('args'))}, "
                f"expected={_preview(sample.get('expected', sample.get('status')))}"
            )
    elif stage_name == "catalogue_measurement":
        print("    -> catalogue_measurement completed (saved under task catalogue/ artifacts)")
    elif stage_name == "put_evaluation":
        result = context.result or {}
        if result.get("skip"):
            print(f"    -> task skipped: {result['skip']}")
            return
        rows = []
        for put_id, outcome in sorted(result.get("outcomes", {}).items(), key=lambda item: str(item[0])):
            failing = outcome.get("failing", [])
            verdict = "DETECTED" if failing else "survived"
            rows.append([put_id, verdict, len(failing), _preview(failing[:5])])
        print(
            format_table(
                ["PUT ID", "Verdict", "Failing Inputs", "Sample Failing Indices"],
                rows,
                alignments=["<", "<", ">", "<"],
            )
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("he-py", "mbpp-py"), default="he-py")
    parser.add_argument(
        "--cohort",
        type=Path,
        default=Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"),
        help="Path to PUT cohort JSON (ignored if --synthetic is set)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Create a temporary 2-PUT cohort (canonical + buggy) for quick self-contained testing",
    )
    parser.add_argument(
        "--mode",
        choices=("mock", "live", "replay"),
        default="mock",
        help="mock (offline stub model), live (real LLM), or replay (frozen inputs from --source)",
    )
    parser.add_argument(
        "--arms",
        nargs="+",
        choices=[arm.name for arm in available_arms()],
        default=["plain"],
        help="Arms to run in mock/live mode (default: plain)",
    )
    parser.add_argument("--source", type=Path, help="Source run directory when --mode replay")
    parser.add_argument("--num-tasks", type=int, default=1, help="Number of random tasks to pick")
    parser.add_argument("--task-id", help="Optional explicit task ID instead of random pick")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for task selection")
    parser.add_argument("--model-backend", choices=("qwen", "vertex", "openrouter"), default="vertex")
    parser.add_argument("--model-name")
    parser.add_argument("--input-budget", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Artifact output directory (defaults to temp dir)")
    return parser


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)

    if options.mode == "replay" and options.source is None:
        parser.error("--source is required when --mode replay")

    dataset, all_tasks, metadata = load_dataset_bundle(options.dataset)

    temp_ctx = tempfile.TemporaryDirectory(prefix="final-random-pipeline-") if options.output is None else None
    try:
        work_dir = Path(temp_ctx.name) if temp_ctx is not None else options.output
        artifacts_dir = work_dir / "run" if temp_ctx is not None else work_dir

        if options.synthetic or not options.cohort.exists():
            candidate_tasks = all_tasks
            if options.task_id:
                selected = [task for task in candidate_tasks if task["task_id"] == options.task_id]
                if not selected:
                    parser.error(f"Unknown task_id: {options.task_id}")
            else:
                rng = random.Random(options.seed)
                selected = rng.sample(candidate_tasks, min(options.num_tasks, len(candidate_tasks)))
            cohort_path = _create_synthetic_cohort(work_dir / "synthetic_cohort.json", selected)
            cohort_source = "synthetic (2 PUTs/task)"
        else:
            cohort_data = load_cohort(options.cohort)
            cohort_ids = {row["task_id"] for row in cohort_data["tasks"] if row.get("base_pass", 0) > 0}
            candidate_tasks = [task for task in all_tasks if task["task_id"] in cohort_ids]
            if options.task_id:
                selected = [task for task in candidate_tasks if task["task_id"] == options.task_id]
                if not selected:
                    parser.error(f"Task {options.task_id} not found with base_pass > 0 in {options.cohort}")
            else:
                rng = random.Random(options.seed)
                selected = rng.sample(candidate_tasks, min(options.num_tasks, len(candidate_tasks)))
            cohort_path = options.cohort
            cohort_source = str(options.cohort)

        cohort_loaded = load_cohort(cohort_path)
        cohort_by_id = {row["task_id"]: row for row in cohort_loaded["tasks"]}

        print(render_banner("Stage 0: Dataset, Random Task & Cohort Selection"))
        print(
            format_table(
                ["Field", "Value"],
                [
                    ["mode", options.mode],
                    ["dataset", options.dataset],
                    ["seed", options.seed],
                    ["cohort", cohort_source],
                    ["artifacts", str(artifacts_dir)],
                ],
                alignments=["<", "<"],
            )
        )
        task_rows = []
        sample_inputs: dict[str, list[dict]] = {}
        for task in selected:
            ctask = cohort_by_id[task["task_id"]]
            base_calls = []
            for prog in ctask.get("programs", []):
                base_calls.extend(prog.get("base", {}).get("calls", []))
            if base_calls:
                sample_inputs[task["entry_point"]] = [
                    {"args": call.get("args", "()"), "kwargs": call.get("kwargs", "{}")}
                    for call in base_calls[:3]
                ]
            else:
                extracted = _extract_example_calls(task, limit=3)
                if extracted:
                    sample_inputs[task["entry_point"]] = extracted
            task_rows.append(
                [
                    task["task_id"],
                    task["entry_point"],
                    ctask.get("generated", 0),
                    ctask.get("base_pass", 0),
                    _preview(task["prompt"], 60),
                ]
            )
        print(
            "\nSelected Task(s):\n"
            + format_table(
                ["Task ID", "Entry Point", "Generated PUTs", "Base Pass", "Spec Preview"],
                task_rows,
                alignments=["<", "<", ">", ">", "<"],
            )
        )

        artifacts = ArtifactStore(artifacts_dir)
        target_programs = max(1, max(cohort_by_id[t["task_id"]].get("generated", 1) for t in selected))
        settings = PipelineSettings(
            target_programs=target_programs,
            input_budget=options.input_budget,
            input_tokens=2048,
            context_tokens=8192,
        )

        calls = None
        arms = None
        input_generator = None
        if options.mode == "replay":
            input_generator = FrozenInputsGenerator(options.source)
        elif options.mode == "mock":
            arms = selected_arms(options.arms)
            model = _DemoStubModel(sample_inputs)
            calls = _StubCalls(model, artifacts)
        else:
            from final.src.models import create_model

            arms = selected_arms(options.arms)
            model = create_model(
                backend=options.model_backend,
                model_name=options.model_name,
                context=settings.context_tokens,
            )
            calls = RecordedModelCalls(model, artifacts)

        step_timers: dict[tuple[str, str], float] = {}

        def on_step(context, stage_name: str, state: str) -> None:
            key = (context.task["task_id"], stage_name)
            if state == "started":
                step_timers[key] = time.monotonic()
                print(render_banner(f"Stage [{stage_name}] — {context.task['task_id']} (STARTED)"))
            elif state == "complete":
                elapsed = time.monotonic() - step_timers.get(key, time.monotonic())
                print(f"  [COMPLETE] {stage_name} ({elapsed:.2f}s)")
                _inspect_stage_data(context, stage_name)
            elif state == "failed":
                elapsed = time.monotonic() - step_timers.get(key, time.monotonic())
                print(f"  [FAILED] {stage_name} after {elapsed:.2f}s")

        pipeline = BenchmarkPipeline(
            cohort_path,
            artifacts,
            arms=arms,
            input_generator=input_generator,
            settings=settings,
            calls=calls,
            execution_cache=False,
            dataset=dataset,
            on_step=on_step,
        )
        pipeline.run(selected, metadata)

        stats = collect_run_results([artifacts_dir])
        print(render_banner("Final Stage: Reporting & Union Summary"))
        print(render_arm_union_tables(stats, show_per_task=True, show_gain=True))
        print(f"\nArtifacts written to: {artifacts_dir}")
        return 0
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
