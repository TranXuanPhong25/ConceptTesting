"""Run the full real pipeline (PUT generation -> v2 & CF input generation -> oracle -> evaluation -> union)
on random task(s), printing every stage and its intermediate data to the terminal.

Run from repo root:
    PYTHONPATH=. final/.venv/bin/python -m final.src.scripts.test_random_pipeline --dataset he-py --seed 42
    PYTHONPATH=. final/.venv/bin/python -m final.src.scripts.test_random_pipeline --cohort final/out/cohorts/.../cohort.json
"""
from __future__ import annotations

import argparse
from pathlib import Path
import random
import time

from final.src.benchmarks.PUT_generation import generate_puts, run_base_tests, save_cohort
from final.src.modular import available_arms, selected_arms
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.cohort import load_cohort
from final.src.modular.context import PipelineSettings
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.scripts._formatting import (
    collect_run_results,
    format_table,
    load_dataset_bundle,
    render_arm_union_tables,
    render_banner,
)

DEFAULT_ARMS = ("ep_bva_vf3_hybrid", "decision_table_vf3_hybrid", "control_flow")


def _preview(value, max_len: int = 90) -> str:
    import json

    rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    rendered = " ".join(rendered.split())
    return rendered if len(rendered) <= max_len else rendered[: max_len - 3] + "..."


def _inspect_stage_data(context, stage_name: str) -> None:
    """Print structured intermediate data produced by a completed pipeline stage."""
    if stage_name == "input_context":
        packet = context.packet or {}
        print(
            f"  packet: visible_put_ids={packet.get('visible_put_ids', [])} | "
            f"prompt_tokens={packet.get('prompt_tokens', 'n/a')}"
        )

    elif stage_name == "input_generation":
        arms_data = (context.inputs or {}).get("arms", {})
        rows = []
        for arm_name, batch in arms_data.items():
            inputs = batch.get("inputs", [])
            sample = _preview(inputs[0]) if inputs else "(none)"
            extra = batch.get("catalogue_status", "-")
            if "concepts" in batch:
                extra = f"concepts={len(batch['concepts'])}"
            rows.append([arm_name, len(inputs), extra, sample])
        print(
            format_table(
                ["Arm", "Generated Inputs", "Catalogue / Concepts", "Sample Input #0"],
                rows,
                alignments=["<", ">", "<", "<"],
            )
        )

    elif stage_name == "reference_oracle":
        oracle = context.oracle or {}
        tests = oracle.get("tests", [])
        rejected = oracle.get("rejected", [])
        arm_counts = {name: len(indices) for name, indices in oracle.get("arm_indices", {}).items()}
        print(f"  valid_unique_inputs={len(tests)} | rejected={len(rejected)} | per_arm_valid={arm_counts}")
        if tests:
            sample_rows = [
                [
                    index,
                    _preview(test.get("args"), 45),
                    _preview(test.get("kwargs"), 20),
                    _preview(test.get("expected", test.get("status")), 35),
                ]
                for index, test in enumerate(tests[:3])
            ]
            print(
                format_table(
                    ["Idx", "Args", "Kwargs", "Reference Expected"],
                    sample_rows,
                    alignments=[">", "<", "<", "<"],
                )
            )
        if rejected:
            rej_rows = [
                [item.get("index", "-"), item.get("reason", item.get("status", "rejected"))]
                for item in rejected[:3]
            ]
            print(
                "  Sample rejected inputs:\n"
                + format_table(["Idx", "Reason"], rej_rows, alignments=[">", "<"])
            )

    elif stage_name == "catalogue_measurement":
        cat_dir = context.artifacts.path(context.task_directory + "/catalogue")
        files = sorted(path.name for path in cat_dir.glob("*.json")) if cat_dir.exists() else []
        print(f"  catalogue measurement artifacts: {files or '(none)'}")

    elif stage_name == "put_evaluation":
        result = context.result or {}
        if result.get("skip"):
            print(f"  task skipped: {result['skip']}")
            return
        arm_indices = {name: set(indices) for name, indices in result.get("arm_indices", {}).items()}
        rows = []
        for put_id, outcome in sorted(result.get("outcomes", {}).items(), key=lambda item: str(item[0])):
            failing = outcome.get("failing", [])
            failing_set = set(failing)
            caught_by = [name for name, idxs in arm_indices.items() if idxs & failing_set]
            verdict = "DETECTED" if failing else "survived"
            rows.append(
                [
                    put_id,
                    verdict,
                    len(failing),
                    ", ".join(caught_by) if caught_by else "-",
                    _preview(failing[:5], 30),
                ]
            )
        print(
            format_table(
                ["PUT ID", "Verdict", "Failing Inputs", "Caught By Arms", "Failing Indices"],
                rows,
                alignments=["<", "<", ">", "<", "<"],
            )
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", "--datatype", dest="dataset", choices=("he-py", "mbpp-py"), default="he-py")
    parser.add_argument(
        "--cohort",
        type=Path,
        help="Optional existing cohort JSON. If omitted, Stage 1 generates PUTs live for the random task(s).",
    )
    parser.add_argument(
        "--puts-per-task",
        type=int,
        default=5,
        help="Number of PUTs to generate in Stage 1 when --cohort is not supplied (1-30)",
    )
    parser.add_argument(
        "--arms",
        nargs="+",
        choices=[arm.name for arm in available_arms()],
        default=list(DEFAULT_ARMS),
        help="Input generation arms (default: ep_bva_vf3_hybrid decision_table_vf3_hybrid control_flow)",
    )
    parser.add_argument("--num-tasks", type=int, default=1, help="Number of random tasks to run")
    parser.add_argument("--task-id", help="Optional explicit task ID instead of random selection")
    parser.add_argument("--seed", type=int, help="Random seed for task selection (default: random)")
    parser.add_argument("--model-backend", choices=("qwen", "vertex", "openrouter"), default="vertex")
    parser.add_argument("--model-name", help="Tester/writer model name (defaults to backend default)")
    parser.add_argument("--input-budget", type=int, default=20)
    parser.add_argument("--input-tokens", type=int, default=4096)
    parser.add_argument("--context-tokens", type=int, default=8192)
    parser.add_argument(
        "--scorer",
        choices=("confirm_first_failures", "full_two_repeats"),
        default="confirm_first_failures",
    )
    parser.add_argument("--timeout", type=int, default=8)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("final/out/random_pipeline_test"),
        help="Output directory for this run's artifacts",
    )
    return parser


def _build_live_cohort(model, tasks: list[dict], output_path: Path, *, puts_per_task: int, timeout: int, seed: int):
    """Stage 1: Generate PUTs with the real LLM and run base tests in bwrap."""
    records = []
    for task in tasks:
        programs = generate_puts(model, task, count=puts_per_task, seed=seed)
        base_input_keys: set[str] = set()
        for program in programs:
            outcome = run_base_tests(task, program, timeout=timeout, seed=seed)
            program["base"] = outcome
            base_input_keys.update(outcome.get("input_keys", []))
        base_pass = sum(program["base"]["status"] == "pass" for program in programs)
        records.append(
            {
                "task_id": task["task_id"],
                "programs": programs,
                "generated": len(programs),
                "base_pass": base_pass,
                "base_input_keys": sorted(base_input_keys),
                "status": "complete" if programs else "no_programs",
            }
        )
    save_cohort(records, output_path)
    return output_path


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)

    if options.num_tasks < 1:
        parser.error("--num-tasks must be >= 1")
    if not 1 <= options.puts_per_task <= 30:
        parser.error("--puts-per-task must be between 1 and 30")

    seed = options.seed if options.seed is not None else random.SystemRandom().randint(1, 10**6)
    dataset, all_tasks, metadata = load_dataset_bundle(options.dataset)

    if options.cohort is not None:
        cohort_data = load_cohort(options.cohort)
        eligible_ids = {row["task_id"] for row in cohort_data["tasks"] if row.get("base_pass", 0) > 0}
        pool = [task for task in all_tasks if task["task_id"] in eligible_ids]
    else:
        pool = all_tasks

    if options.task_id:
        selected = [task for task in pool if task["task_id"] == options.task_id]
        if not selected:
            parser.error(f"Task {options.task_id} not available in the selected dataset/cohort pool")
    else:
        rng = random.Random(seed)
        selected = rng.sample(pool, min(options.num_tasks, len(pool)))

    run_dir = options.output.resolve()
    artifacts = ArtifactStore(run_dir)

    print(render_banner("Stage 0: Random Task & Pipeline Configuration"))
    print(
        format_table(
            ["Setting", "Value"],
            [
                ["dataset", options.dataset],
                ["random_seed", seed],
                ["arms", ", ".join(options.arms)],
                ["model_backend", options.model_backend],
                ["model_name", options.model_name or "(backend default)"],
                ["cohort_source", str(options.cohort) if options.cohort else f"live PUT generation ({options.puts_per_task}/task)"],
                ["scorer", options.scorer],
                ["output_dir", str(run_dir)],
            ],
            alignments=["<", "<"],
        )
    )
    print(
        "\nSelected Random Task(s):\n"
        + format_table(
            ["Task ID", "Entry Point", "Has Contract", "Spec Preview"],
            [
                [
                    task["task_id"],
                    task["entry_point"],
                    "yes" if metadata[task["task_id"]].get("contract", "").strip() else "no",
                    _preview(task["prompt"], 60),
                ]
                for task in selected
            ],
            alignments=["<", "<", "<", "<"],
        )
    )

    from final.src.models import create_model

    model = create_model(
        backend=options.model_backend,
        model_name=options.model_name,
        context=options.context_tokens,
    )

    print(render_banner("Stage 1: PUT Cohort & Base Tests"))
    if options.cohort is not None:
        cohort_path = options.cohort
        print(f"Loaded existing cohort: {cohort_path}")
    else:
        cohort_path = run_dir / "cohort.json"
        started = time.monotonic()
        _build_live_cohort(
            model,
            selected,
            cohort_path,
            puts_per_task=options.puts_per_task,
            timeout=options.timeout,
            seed=seed,
        )
        print(f"Generated PUTs & ran base tests in {time.monotonic() - started:.2f}s -> {cohort_path}")

    cohort_loaded = load_cohort(cohort_path)
    cohort_by_id = {row["task_id"]: row for row in cohort_loaded["tasks"]}
    put_rows = []
    for task in selected:
        ctask = cohort_by_id[task["task_id"]]
        for program in ctask.get("programs", []):
            base = program.get("base", {})
            cov = base.get("coverage") or {}
            put_rows.append(
                [
                    task["task_id"],
                    program.get("id"),
                    base.get("status", "unknown"),
                    len(base.get("calls", [])),
                    len(cov.get("lines", [])),
                    _preview(program.get("approach", "-"), 45),
                ]
            )
    if put_rows:
        print(
            format_table(
                ["Task ID", "PUT ID", "Base Status", "Base Calls", "Cov Lines", "Approach"],
                put_rows,
                alignments=["<", ">", "<", ">", ">", "<"],
            )
        )

    arms = selected_arms(options.arms)
    settings = PipelineSettings(
        input_budget=options.input_budget,
        input_tokens=options.input_tokens,
        context_tokens=options.context_tokens,
        timeout_seconds=options.timeout,
        scorer=options.scorer,
    )
    calls = RecordedModelCalls(model, artifacts)

    step_timers: dict[tuple[str, str], float] = {}

    def on_step(context, stage_name: str, state: str) -> None:
        key = (context.task["task_id"], stage_name)
        if state == "started":
            step_timers[key] = time.monotonic()
            print(render_banner(f"Stage [{stage_name}] — {context.task['task_id']}"))
        elif state == "complete":
            elapsed = time.monotonic() - step_timers.get(key, time.monotonic())
            print(f"[COMPLETE] {stage_name} ({elapsed:.2f}s)")
            _inspect_stage_data(context, stage_name)
        elif state == "failed":
            elapsed = time.monotonic() - step_timers.get(key, time.monotonic())
            print(f"[FAILED] {stage_name} after {elapsed:.2f}s")

    pipeline = BenchmarkPipeline(
        cohort_path,
        artifacts,
        arms=arms,
        settings=settings,
        calls=calls,
        dataset=dataset,
        on_step=on_step,
    )
    pipeline.run(selected, metadata)

    stats = collect_run_results([run_dir])
    print(render_banner("Final Stage: Per-Arm & UNION Summary"))
    print(render_arm_union_tables(stats, show_per_task=True, show_gain=True))
    print(f"\nArtifacts saved to: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
