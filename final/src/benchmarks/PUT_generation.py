"""Generate PUTs, run base tests, and save cohort task records."""

import ast
import argparse
import logging
import json
import time
from textwrap import indent
from pathlib import Path

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from final.src.models.core_model import ModelError

from final.src.runtime.artifacts import save
from final.src.runtime.contracts import parse_json
from final.src.runtime.execution import ExecutionError, execute
from ..models import create_model
from .datasets import DatasetLoader
from .pipeline import adapter_task
logger = logging.getLogger(__name__)


def build_messages(task, count):
    language = "Python"
    prompt = f"""
        Implement this specification in {language}. Return up to {count}
        solutions as one JSON object: {{"programs":[{{"approach":"algorithm description",
        "code":"complete standalone {language} source"}}]}}.
        Every solution must aim to satisfy the ENTIRE specification, including edge cases.
        Do not deliberately introduce bugs or just target examples. Preserve the public
        function name/signature and any required class. Include required standard-library
        imports/includes. Do not include a main function or test runner; those are supplied separately.
        Correctness and clarity take priority over the number of solutions. {count} is an
        upper limit, not a quota. For a simple function, one natural implementation may
        be enough. Return fewer solutions when there are no other sensible approaches;
        do not repeat solutions or introduce mistakes just to fill the list.
        Where natural alternatives exist, vary the algorithm, data structure, or
        decomposition. Avoid forced complexity, unreachable code, dummy statements,
        no-op wrappers, and changes limited to names, formatting, or comments.
        Return JSON only, without markdown fences.

        SPECIFICATION:
        {task['prompt']}
        DECLARATION:
        {task.get('declaration', '')}
    """
    return [
        {
            "role": "system",
            "content": f"You write correct, clear {language} implementations.",
        },
        {"role": "user", "content": prompt},
    ]


def generate_puts(model, task, *, count=10, seed=20261030):
    if type(count) is not int or not 1 <= count <= 30:
        raise ValueError("count must be an integer from 1 to 30")
    messages = build_messages(task, count)
    for attempt in range(3):
        try:
            response = model.generate(messages, temperature=.9, max_tokens=4072, seed=seed)
            break
        except ModelError as error:
            logger.warning("PUT generation failed, attempt %d/3: %s", attempt + 1, type(error).__name__)
            if not getattr(error, "retryable", False) or attempt == 2:
                return []
            time.sleep((5, 20)[attempt])
    try:
        candidates = parse_json(response.text)["programs"]
        if not isinstance(candidates, list) or len(candidates) > 30:
            raise ValueError("Invalid programs array")
    except (ValueError, TypeError, KeyError) as error:
        logger.error("PUT generation failed: %s", type(error).__name__)
        return []
    programs = []
    for candidate in candidates[:count]:
        try:
            if not isinstance(candidate, dict) or not isinstance(candidate.get("code"), str):
                raise ValueError("Missing source")
            if len(candidate["code"]) > 30000 or not isinstance(candidate.get("approach"), str):
                raise ValueError("Invalid source or approach")
            if not candidate["code"].strip():
                raise ValueError("Empty source")
            tree = ast.parse(candidate["code"])
            if not any(isinstance(node, ast.FunctionDef) and node.name == task["entry_point"]
                       for node in tree.body):
                raise ValueError("Missing entry point")
        except (ValueError, SyntaxError, RecursionError, TypeError, KeyError) as error:
            logger.warning("Skipping invalid PUT: %s", type(error).__name__)
            continue
        programs.append({"id": len(programs), "code": candidate["code"], "approach": candidate["approach"]})
    logger.info("Generated %d/%d PUTs", len(programs), count)
    return programs


def run_base_tests(task, program, *, timeout=8, seed=20261030):
    """Run one PUT's base tests in the existing sandbox and return its outcome."""
    context, base = task["prompt"], task["test"]
    if "tests" in task:
        context = task["declaration"]
        base = "def check(candidate):\n" + indent(base, "    ")
    job = {
        "mode": "base", "context": context, "source": program["code"],
        "entry": task["entry_point"], "base": base,
        "timeout": timeout, "seed": seed, "trace": True,
    }
    try:
        outcome = execute(job)
    except ExecutionError as error:
        logger.error("Base test execution failed: %s", type(error).__name__)
        raise
    logger.info("Base tests: %s", outcome["status"])
    return outcome


def save_cohort(tasks, output_path):
    cohort = {"tasks": tasks}
    save(Path(output_path), cohort)
    logger.info("Saved cohort with %d tasks", len(tasks))
    return cohort


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-type", type=str.lower,
                        choices=("he-py", "mbpp-py"), default="he-py")
    parser.add_argument("--model-backend", choices=("qwen", "vertex"), default="vertex")
    parser.add_argument("--model-name")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--num-tasks", type=int, help="First N tasks; defaults to 1")
    selection.add_argument("--task-ids", nargs="+", help="Full task IDs or numbers, e.g. HumanEval/0 7")
    parser.add_argument("--puts-per-task", type=int, default=1, help="Maximum PUTs per task (1–30)")
    parser.add_argument("--resume", type=Path, help="Keep saved PUTs; generate absent tasks and tasks with no programs")
    parser.add_argument("--output", type=Path, help="Output cohort (saved after every task)")
    options = parser.parse_args(arguments)
    if options.num_tasks is not None and options.num_tasks < 1:
        parser.error("--num-tasks must be positive")
    if not 1 <= options.puts_per_task <= 30:
        parser.error("--puts-per-task must be between 1 and 30")
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    dataset = DatasetLoader(options.dataset_type)
    tasks = dataset.load_tasks()
    if options.task_ids:
        by_id = {task["task_id"]: task for task in tasks}
        by_number = {task["task_id"].rsplit("/", 1)[-1]: task["task_id"] for task in tasks}
        selected_ids = [by_number.get(identifier, identifier) for identifier in options.task_ids]
        if len(set(selected_ids)) != len(selected_ids):
            parser.error("--task-ids contains duplicate tasks")
        missing = [identifier for identifier in selected_ids if identifier not in by_id]
        if missing:
            parser.error("Unknown task IDs: " + ", ".join(missing))
        tasks = [by_id[identifier] for identifier in selected_ids]
    else:
        limit = options.num_tasks or 1
        if limit > len(tasks):
            parser.error("--num-tasks exceeds the number of available tasks")
        tasks = tasks[:limit]
    task_records = []
    if options.resume:
        task_records = json.loads(options.resume.read_text())["tasks"]
        saved_ids = [record["task_id"] for record in task_records]
        available_ids = {task["task_id"] for task in dataset.load_tasks()}
        if len(saved_ids) != len(set(saved_ids)) or set(saved_ids) - available_ids:
            parser.error("Resume cohort contains duplicate or unknown task IDs")
        completed = {record["task_id"] for record in task_records if record["programs"]}
        tasks = [task for task in tasks if task["task_id"] not in completed]
    output = options.output or Path(f"final/out/put_generation/cohort_{options.dataset_type}.json")
    if not tasks:
        save_cohort(task_records, output)
        return
    if options.dataset_type == "mbpp-py":
        tasks = [adapter_task(task) for task in tasks]
    model_name = options.model_name
    if model_name is None and options.model_backend == "vertex":
        model_name = "gemini-3.1-flash-lite"
    model = create_model(backend=options.model_backend, model_name=model_name)
    with logging_redirect_tqdm(), tqdm(
        tasks, desc=f"Generating PUTs ({options.dataset_type})", unit="task", dynamic_ncols=True
    ) as progress:
        for task in progress:
            progress.set_postfix_str(task["task_id"])
            programs = generate_puts(model, task, count=options.puts_per_task)
            base_input_keys = set()
            for program in programs:
                outcome = run_base_tests(task, program)
                program["base"] = outcome
                base_input_keys.update(outcome.get("input_keys", []))
            base_pass = sum(program["base"]["status"] == "pass" for program in programs)
            logger.info(
                "Task %s complete: %d/%d programs passed base tests",
                task["task_id"],
                base_pass,
                len(programs),
            )
            record = {
                "task_id": task["task_id"], "programs": programs, "generated": len(programs),
                "base_pass": base_pass,
                "base_input_keys": sorted(base_input_keys),
                "status": "complete" if programs else "no_programs",
            }
            saved_index = next((index for index, saved in enumerate(task_records)
                                if saved["task_id"] == task["task_id"]), None)
            if saved_index is None:
                task_records.append(record)
            else:
                task_records[saved_index] = record
            save_cohort(task_records, output)


if __name__ == '__main__':
    main()
