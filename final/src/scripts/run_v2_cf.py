"""Hardcoded runner for v2 (EP/BVA v2, DT v2) + Control Flow generation, evaluation, and union table.

Run from repo root:
    PYTHONPATH=. final/.venv/bin/python -m final.src.scripts.run_v2_cf
"""
from __future__ import annotations

import argparse
from pathlib import Path

from final.src.modular.arms import available_arms, selected_arms
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.context import PipelineSettings
from final.src.modular.execution_cache import InputExecutionCache
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.scripts._formatting import (
    collect_run_results,
    load_dataset_bundle,
    render_arm_union_tables,
    render_banner,
    select_tasks,
)

# ---------------------------------------------------------------------------
# Hardcoded defaults (edit here or override via CLI flags)
# ---------------------------------------------------------------------------
CONFIG = {
    "dataset": "he-py",
    "arms": ("ep_bva_v2", "decision_table_v2", "control_flow"),
    "cohort": Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"),
    "artifacts": Path("final/out/scripts_v2_cf"),
    "model_backend": "vertex",
    "model_name": None,
    "task_ids": None,
    "num_tasks": None,
    "input_budget": 20,
    "target_programs": 10,
    "input_tokens": 4096,
    "context_tokens": 8192,
    "scorer": "confirm_first_failures",
    "execution_cache": Path("final/out/execution_cache"),
    "use_execution_cache": True,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("he-py", "mbpp-py"), default=CONFIG["dataset"])
    parser.add_argument(
        "--arms",
        nargs="+",
        choices=[arm.name for arm in available_arms()],
        default=list(CONFIG["arms"]),
        help="Arms to generate and evaluate (default: ep_bva_v2 decision_table_v2 control_flow)",
    )
    parser.add_argument("--cohort", type=Path, default=CONFIG["cohort"])
    parser.add_argument("--artifacts", type=Path, default=CONFIG["artifacts"])
    parser.add_argument(
        "--model-backend",
        choices=("qwen", "vertex", "openrouter"),
        default=CONFIG["model_backend"],
    )
    parser.add_argument("--model-name", default=CONFIG["model_name"])
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--task-ids", nargs="+", default=CONFIG["task_ids"])
    selection.add_argument("--num-tasks", type=int, default=CONFIG["num_tasks"])
    parser.add_argument("--input-budget", type=int, default=CONFIG["input_budget"])
    parser.add_argument("--target-programs", type=int, default=CONFIG["target_programs"])
    parser.add_argument("--input-tokens", type=int, default=CONFIG["input_tokens"])
    parser.add_argument("--context-tokens", type=int, default=CONFIG["context_tokens"])
    parser.add_argument(
        "--scorer",
        choices=("confirm_first_failures", "full_two_repeats"),
        default=CONFIG["scorer"],
    )
    parser.add_argument("--execution-cache", type=Path, default=CONFIG["execution_cache"])
    parser.add_argument("--no-execution-cache", action="store_true")
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Do not call models; print tables from existing --artifacts results",
    )
    parser.add_argument("--per-task", action="store_true", help="Also print per-task table")
    return parser


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)

    if not options.replay:
        dataset, all_tasks, metadata = load_dataset_bundle(options.dataset)
        tasks = select_tasks(all_tasks, task_ids=options.task_ids, num_tasks=options.num_tasks)
        arms = selected_arms(options.arms)
        artifacts = ArtifactStore(options.artifacts)

        from final.src.models import create_model

        model = create_model(
            backend=options.model_backend,
            model_name=options.model_name,
            context=options.context_tokens,
        )
        calls = RecordedModelCalls(model, artifacts)
        settings = PipelineSettings(
            target_programs=options.target_programs,
            input_budget=options.input_budget,
            input_tokens=options.input_tokens,
            context_tokens=options.context_tokens,
            scorer=options.scorer,
        )
        use_cache = CONFIG["use_execution_cache"] and not options.no_execution_cache
        cache = InputExecutionCache(options.execution_cache) if use_cache else False

        pipeline = BenchmarkPipeline(
            options.cohort,
            artifacts,
            arms=arms,
            settings=settings,
            calls=calls,
            execution_cache=cache,
            dataset=dataset,
        )
        pipeline.run(tasks, metadata)

    stats = collect_run_results(
        [options.artifacts],
        arms=options.arms if not options.replay else None,
        task_ids=options.task_ids,
    )
    print(render_banner(f"V2 + CF Evaluation & Union ({options.artifacts})"))
    print(
        f"Tasks: {stats['eligible_tasks']} eligible / {stats['scored_tasks']} scored "
        f"(skipped: {len(stats['skipped_tasks'])}) | Eligible PUTs: {stats['eligible_puts']}\n"
    )
    print(render_arm_union_tables(stats, show_per_task=options.per_task, show_gain=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
