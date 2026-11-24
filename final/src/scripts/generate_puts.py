"""Generate PUTs with configurable dataset (datatype), generation mode, and PUT count.

Run from repo root:
    PYTHONPATH=. final/.venv/bin/python -m final.src.scripts.generate_puts --datatype he-py --mode fresh --puts-per-task 10 --num-tasks 5
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from final.src.benchmarks.PUT_generation import generate_puts, run_base_tests, save_cohort
from final.src.scripts._formatting import (
    format_table,
    load_dataset_bundle,
    render_banner,
    select_tasks,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--datatype",
        "--dataset",
        dest="datatype",
        type=str.lower,
        choices=("he-py", "mbpp-py"),
        default="he-py",
        help="Benchmark dataset/datatype to generate PUTs for (he-py or mbpp-py)",
    )
    parser.add_argument(
        "--mode",
        choices=("fresh", "resume", "dry-run"),
        default="fresh",
        help="Generation mode: fresh (generate all), resume (skip saved tasks with programs), dry-run (preview only)",
    )
    parser.add_argument(
        "--puts-per-task",
        type=int,
        default=10,
        help="Maximum PUTs to generate per task (1-30)",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--num-tasks", type=int, help="First N tasks (default: 1)")
    selection.add_argument("--task-ids", nargs="+", help="Explicit task IDs or numbers, e.g. HumanEval/0 7")
    parser.add_argument(
        "--model-backend",
        choices=("qwen", "vertex", "openrouter"),
        default="vertex",
    )
    parser.add_argument("--model-name", help="Override default model name for the backend")
    parser.add_argument("--seed", type=int, default=20261030)
    parser.add_argument("--timeout", type=int, default=8, help="Base test timeout in seconds")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output cohort JSON path (default: final/out/put_generation/cohort_<datatype>.json)",
    )
    parser.add_argument(
        "--resume-from",
        type=Path,
        help="Existing cohort JSON to resume from (defaults to --output when --mode resume)",
    )
    return parser


def _upsert_record(records: list[dict], record: dict) -> None:
    for index, saved in enumerate(records):
        if saved["task_id"] == record["task_id"]:
            records[index] = record
            return
    records.append(record)


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)

    if options.num_tasks is not None and options.num_tasks < 1:
        parser.error("--num-tasks must be positive")
    if not 1 <= options.puts_per_task <= 30:
        parser.error("--puts-per-task must be between 1 and 30")

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _, all_tasks, _ = load_dataset_bundle(options.datatype)
    num_tasks = options.num_tasks if options.task_ids is None else None
    if options.task_ids is None and num_tasks is None:
        num_tasks = 1
    tasks = select_tasks(all_tasks, task_ids=options.task_ids, num_tasks=num_tasks)

    output = options.output or Path(f"final/out/put_generation/cohort_{options.datatype}.json")
    model_name = options.model_name
    if model_name is None and options.model_backend == "vertex":
        model_name = "gemini-3.1-flash-lite"

    task_records: list[dict] = []
    if options.mode == "resume":
        resume_path = options.resume_from or output
        if resume_path.exists():
            task_records = json.loads(resume_path.read_text())["tasks"]
            completed = {record["task_id"] for record in task_records if record.get("programs")}
            tasks = [task for task in tasks if task["task_id"] not in completed]

    if options.mode == "dry-run":
        print(render_banner("PUT Generation Dry-Run"))
        print(
            format_table(
                ["Setting", "Value"],
                [
                    ["datatype", options.datatype],
                    ["mode", options.mode],
                    ["puts_per_task", options.puts_per_task],
                    ["selected_tasks", len(tasks)],
                    ["model_backend", options.model_backend],
                    ["model_name", model_name or "(backend default)"],
                    ["output", str(output)],
                ],
                alignments=["<", "<"],
            )
        )
        print(
            "\nSelected Tasks:\n"
            + format_table(
                ["#", "Task ID", "Entry Point"],
                [[index + 1, task["task_id"], task["entry_point"]] for index, task in enumerate(tasks)],
                alignments=[">", "<", "<"],
            )
        )
        return 0

    if not tasks:
        save_cohort(task_records, output)
        print(f"All selected tasks already completed. Cohort saved at {output}")
        return 0

    from final.src.models import create_model

    model = create_model(backend=options.model_backend, model_name=model_name)

    raw_programs: list[tuple[dict, list[dict]]] = []
    with logging_redirect_tqdm(), tqdm(
        tasks, desc=f"Generating PUTs ({options.datatype})", unit="task", dynamic_ncols=True
    ) as progress:
        for task in progress:
            progress.set_postfix_str(task["task_id"])
            programs = generate_puts(model, task, count=options.puts_per_task, seed=options.seed)
            raw_programs.append((task, programs))
            _upsert_record(
                task_records,
                {
                    "task_id": task["task_id"],
                    "programs": programs,
                    "generated": len(programs),
                    "base_pass": 0,
                    "base_input_keys": [],
                    "status": "complete" if programs else "no_programs",
                },
            )
            save_cohort(task_records, output)

    with logging_redirect_tqdm(), tqdm(
        raw_programs, desc=f"Base tests ({options.datatype})", unit="task", dynamic_ncols=True
    ) as test_progress:
        for task, programs in test_progress:
            base_input_keys: set[str] = set()
            for program in programs:
                outcome = run_base_tests(task, program, timeout=options.timeout, seed=options.seed)
                program["base"] = outcome
                base_input_keys.update(outcome.get("input_keys", []))
            base_pass = sum(program["base"]["status"] == "pass" for program in programs)
            _upsert_record(
                task_records,
                {
                    "task_id": task["task_id"],
                    "programs": programs,
                    "generated": len(programs),
                    "base_pass": base_pass,
                    "base_input_keys": sorted(base_input_keys),
                    "status": "complete" if programs else "no_programs",
                },
            )
            save_cohort(task_records, output)

    total_generated = sum(record["generated"] for record in task_records)
    total_base_pass = sum(record["base_pass"] for record in task_records)
    rows = [
        [record["task_id"], record["generated"], record["base_pass"], record["status"]]
        for record in task_records
    ]
    rows.append(["---"])
    rows.append(["TOTAL", total_generated, total_base_pass, f"{len(task_records)} tasks"])

    print(render_banner(f"PUT Generation Summary ({options.datatype})"))
    print(f"Saved cohort: {output}\n")
    print(
        format_table(
            ["Task ID", "Generated PUTs", "Base Pass", "Status"],
            rows,
            alignments=["<", ">", ">", "<"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
