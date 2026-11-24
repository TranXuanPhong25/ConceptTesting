"""Pure evaluation script: rescore saved inputs against a cohort with 0 LLM calls.

Run from repo root:
    PYTHONPATH=. final/.venv/bin/python -m final.src.scripts.evaluate_saved \
        --source final/out/some_run --cohort final/out/cohorts/.../cohort.json --output final/out/eval_only
"""
from __future__ import annotations

import argparse
from pathlib import Path

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings
from final.src.modular.execution_cache import InputExecutionCache
from final.src.modular.generators.frozen import FrozenInputsGenerator
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.scripts._formatting import (
    collect_run_results,
    load_dataset_bundle,
    render_arm_union_tables,
    render_banner,
    select_tasks,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Source run directory containing modular_manifest.json and tasks/*/inputs.json",
    )
    parser.add_argument("--cohort", type=Path, required=True, help="Frozen PUT cohort JSON")
    parser.add_argument("--output", type=Path, required=True, help="New output directory for evaluation results")
    parser.add_argument("--dataset", choices=("he-py", "mbpp-py"), default="he-py")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--task-ids", nargs="+", help="Explicit task IDs or numbers to evaluate")
    selection.add_argument("--num-tasks", type=int, help="Evaluate only the first N tasks from source")
    parser.add_argument(
        "--scorer",
        choices=("confirm_first_failures", "full_two_repeats"),
        default="confirm_first_failures",
    )
    parser.add_argument("--input-budget", type=int, default=20)
    parser.add_argument("--target-programs", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=8)
    parser.add_argument("--execution-cache", type=Path, default=Path("final/out/execution_cache"))
    parser.add_argument("--no-execution-cache", action="store_true")
    parser.add_argument("--per-task", action="store_true", help="Also print per-task breakdown table")
    return parser


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)

    generator = FrozenInputsGenerator(options.source)
    manifest_task_ids = generator.manifest.get("tasks")

    dataset, all_tasks, metadata = load_dataset_bundle(options.dataset)
    if options.task_ids:
        tasks = select_tasks(all_tasks, task_ids=options.task_ids)
    elif manifest_task_ids:
        tasks = select_tasks(all_tasks, task_ids=manifest_task_ids)
        if options.num_tasks is not None:
            tasks = tasks[: options.num_tasks]
    else:
        tasks = select_tasks(all_tasks, num_tasks=options.num_tasks)

    artifacts = ArtifactStore(options.output)
    settings = PipelineSettings(
        target_programs=options.target_programs,
        input_budget=options.input_budget,
        timeout_seconds=options.timeout,
        scorer=options.scorer,
    )
    cache = False if options.no_execution_cache else InputExecutionCache(options.execution_cache)

    pipeline = BenchmarkPipeline(
        options.cohort,
        artifacts,
        input_generator=generator,
        settings=settings,
        execution_cache=cache,
        dataset=dataset,
    )
    pipeline.run(tasks, metadata)

    stats = collect_run_results([options.output])
    print(render_banner(f"Pure Evaluation Summary ({options.output})"))
    print(
        f"Source inputs: {options.source} (0 LLM calls)\n"
        f"Tasks: {stats['eligible_tasks']} eligible / {stats['scored_tasks']} scored | "
        f"Eligible PUTs: {stats['eligible_puts']}\n"
    )
    print(render_arm_union_tables(stats, show_per_task=options.per_task, show_gain=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
