"""HumanEval-style independent completion generation for HumanEval and MBPP."""
from __future__ import annotations

import ast
import json
import math
import re
from contextlib import nullcontext
from pathlib import Path

from final.src.models.core_model import ModelError
from .PUT_generation import run_base_tests
from .datasets import load_humaneval, load_mbpp
from .pipeline import adapter_task


def prompt_for(task: dict) -> str:
    """Build the one-function prompt used by the official sample loop."""
    if task["task_id"].startswith("HumanEval/"):
        return task["prompt"]
    tree = ast.parse(task["declaration"])
    function = tree.body[0]
    function.body = [ast.Expr(value=ast.Constant(task["prompt"]))]
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def trim_completion(text: str) -> str:
    """Remove an enclosing Markdown fence while preserving Python indentation."""
    fenced = re.fullmatch(r"\s*```(?:python|py)?[^\S\n]*\n(.*?)\n```\s*", text, re.DOTALL)
    return fenced.group(1) if fenced else text


def source_for(task: dict, completion: str) -> str:
    """Accept a whole chat implementation or a function-body completion."""
    code = trim_completion(completion)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return prompt_for(task) + code
    if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
           and node.name == task['entry_point'] for node in tree.body):
        return code
    return prompt_for(task) + code


def pass_at_k(num_samples: list[int], num_correct: list[int], k: int) -> float | None:
    if (type(k) is not int or k < 1 or len(num_samples) != len(num_correct)
            or any(type(n) is not int or type(c) is not int or not 0 <= c <= n
                   for n, c in zip(num_samples, num_correct))):
        raise ValueError("Invalid pass@k counts")
    if not num_samples or any(n < k for n in num_samples):
        return None
    values = []
    for n, correct in zip(num_samples, num_correct):
        if n - correct < k:
            values.append(1.0)
        else:
            values.append(1.0 - math.prod(1.0 - k / i for i in range(n - correct + 1, n + 1)))
    return sum(values) / len(values)


def load_selected(dataset: str, path: Path | None = None, task_numbers: list[int] | None = None) -> list[dict]:
    if dataset not in ('he-py', 'mbpp-py'):
        raise ValueError('Unknown dataset')
    if dataset == 'he-py' and path is not None:
        raise ValueError('Explicit dataset paths are supported for MBPP')
    tasks = load_humaneval() if dataset == "he-py" else load_mbpp(path)
    if dataset == "mbpp-py":
        tasks = [adapter_task(task) for task in tasks]
    if task_numbers is not None:
        selected = set(task_numbers)
        if len(selected) != len(task_numbers):
            raise ValueError('Duplicate task number')
        tasks = [task for task in tasks if int(task["task_id"].rsplit("/", 1)[1]) in selected]
        if len(tasks) != len(selected):
            raise ValueError("Unknown task number")
    return tasks


def generate(model, tasks: list[dict], *, samples_per_task: int, seed: int,
             temperature: float = .8, max_tokens: int = 1024,
             output: Path | None = None) -> dict:
    if type(samples_per_task) is not int or samples_per_task < 1:
        raise ValueError("samples_per_task must be positive")
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    context = output.open("x", encoding="utf-8") if output is not None else nullcontext(None)
    with context as handle:
        for task_index, task in enumerate(tasks):
            messages = [{"role": "user", "content": (
                "Implement the specification in Python. Return one complete standalone implementation, "
                "including the function signature, helpers and required imports. "
                "Return only Python code.\n\n" + prompt_for(task))}]
            for sample_index in range(samples_per_task):
                sample_seed = seed + task_index * samples_per_task + sample_index
                record = {"task_id": task["task_id"], "sample_index": sample_index, "seed": sample_seed}
                try:
                    response = model.generate(
                        messages,
                        temperature=temperature, max_tokens=max_tokens, seed=sample_seed,
                    )
                    record.update(raw_response=response.text, completion=trim_completion(response.text),
                                  usage=response.usage, finish_reason=response.finish_reason)
                except ModelError as exc:
                    record['error'] = type(exc).__name__
                records.append(record)
                if handle is not None:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    handle.flush()
    return {"tasks": len(tasks), "requested_samples": len(tasks) * samples_per_task,
            "received_samples": sum("completion" in r for r in records), "records": records}


def evaluate(tasks: list[dict], records: list[dict], *, timeout: float = 8) -> dict:
    by_id = {task["task_id"]: task for task in tasks}
    per_task = {task_id: {"samples": 0, "correct": 0, "results": []} for task_id in by_id}
    programs = {task_id: [] for task_id in by_id}
    seen = set()
    for record in records:
        key = record['task_id'], record['sample_index']
        if key in seen or key[0] not in by_id:
            raise ValueError('Duplicate sample or unknown task')
        seen.add(key)
        if "completion" not in record:
            continue
        task = by_id[record["task_id"]]
        source = source_for(task, record["completion"])
        result = run_base_tests(task, {"code": source}, timeout=timeout)
        programs[record['task_id']].append({
            'id': record['sample_index'], 'code': source, 'base': result,
        })
        row = per_task[record["task_id"]]
        row["samples"] += 1
        row["correct"] += result["status"] == "pass"
        row["results"].append({"sample_index": record["sample_index"], **result})
    counts = list(per_task.values())
    return {
        "tasks": len(tasks),
        "evaluated_tasks": sum(row['samples'] > 0 for row in counts),
        "pass_at_k": {f"pass@{k}": pass_at_k([r["samples"] for r in counts],
                                                [r["correct"] for r in counts], k)
                       for k in (1, 5, 10)},
        "per_task": {task_id: value for task_id, value in per_task.items()},
        "cohort": {"tasks": [{
            'task_id': task_id, 'programs': programs[task_id],
            'generated': row['samples'], 'base_pass': row['correct'],
            'base_input_keys': sorted({key for program in programs[task_id]
                                       for key in program['base'].get('input_keys', [])}),
            'status': 'complete' if row['samples'] else 'no_programs',
        } for task_id, row in per_task.items()]},
    }
