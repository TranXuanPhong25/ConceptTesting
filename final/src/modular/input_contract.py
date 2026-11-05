"""Shared output contract between input producers and reference execution."""
from __future__ import annotations

import ast


def validate_generated_inputs(result, *, task_id, input_budget):
    """Validate transport shape and literals, preserving producer-specific evidence."""
    if not isinstance(result, dict) or result.get("task_id") != task_id:
        raise ValueError("Input generator must return a result for the current task")
    if result.get("skip"):
        if not isinstance(result["skip"], str) or result.get("arms"):
            raise ValueError("A skipped input task must have a reason and no method inputs")
        return result
    methods = result.get("arms")
    if not isinstance(methods, dict) or not methods:
        raise ValueError("Input generator must return at least one named method batch")
    for name, batch in methods.items():
        if not isinstance(name, str) or not name or not name.replace("_", "").isalnum():
            raise ValueError("Input method names must be nonempty identifiers")
        if not isinstance(batch, dict) or not isinstance(batch.get("inputs"), list):
            raise ValueError("Each input method must provide an inputs list")
        if len(batch["inputs"]) > input_budget:
            raise ValueError("Input method exceeded the task input budget")
        for input_record in batch["inputs"]:
            validate_input_literal(input_record)
    return result


def validate_input_literal(record):
    """Parse args/kwargs as data; generated expressions never execute here."""
    if not isinstance(record, dict):
        raise ValueError("An input call must be an object")
    for name in ("args", "kwargs"):
        if not isinstance(record.get(name), str) or len(record[name]) > 16000:
            raise ValueError("Input arguments must be bounded Python literal strings")
    arguments = ast.literal_eval(record["args"])
    keywords = ast.literal_eval(record["kwargs"])
    if not isinstance(arguments, (list, tuple)) or not isinstance(keywords, dict):
        raise ValueError("Input call requires positional list/tuple and keyword dict")
    if any(not isinstance(name, str) for name in keywords):
        raise ValueError("Input keyword names must be strings")
