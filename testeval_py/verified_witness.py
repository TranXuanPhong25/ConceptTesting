"""Bounded, isolated search for executable TestEval line witnesses.

The search uses small deterministic domains for common LeetCode parameter
types. A result proves that the original Python solution reached the target
line and returned normally for that input; it does not prove the input
satisfies every natural-language constraint of the problem.
"""

from __future__ import annotations

import ast
import copy
import itertools
import multiprocessing
import sys
import time
from collections import deque
from typing import Any


WITNESS_VERSION = "typed-small-domains-v3"
SOURCE_FILENAME = "testeval_witness_under_test.py"


def _parameter_kinds(source: str, func_name: str) -> tuple[str, ...] | None:
    tree = ast.parse(source)
    method = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == func_name
        ),
        None,
    )
    if method is None:
        return None
    args = [arg for arg in method.args.args if arg.arg not in {"self", "cls"}]
    if not args or len(args) > 3 or method.args.vararg or method.args.kwarg or method.args.kwonlyargs:
        return None
    names = {
        "List[int]": "int_list", "list[int]": "int_list", "Sequence[int]": "int_list",
        "List[List[int]]": "int_matrix", "list[list[int]]": "int_matrix",
        "List[str]": "str_list", "list[str]": "str_list",
        "List[List[str]]": "str_matrix", "list[list[str]]": "str_matrix",
        "str": "str", "int": "int",
    }
    kinds = tuple(names.get(ast.unparse(arg.annotation) if arg.annotation else "") for arg in args)
    return kinds if all(kinds) else None


def _candidate_arrays(description: str):
    description = description.lower()
    if "binary array" in description or "only 0 and 1" in description:
        values = (0, 1)
    elif "non-negative" in description or "nonnegative" in description:
        values = (0, 1, 2, 3)
    elif "positive integer" in description or "positive numbers" in description:
        values = (1, 2, 3)
    else:
        values = (-2, -1, 0, 1, 2)
    ordered = "sorted" in description or "non-decreasing" in description
    for length in range(1, 7):
        for combination in itertools.combinations_with_replacement(values, length):
            yield list(combination)
            if not ordered and length > 1 and combination[0] != combination[-1]:
                yield list(reversed(combination))


def _small_int_arrays() -> list[list[int]]:
    return [
        [], [0], [1], [-1], [0, 0], [0, 1], [1, 0], [1, 1], [-1, 1],
        [0, 0, 0], [0, 1, 2], [2, 1, 0], [-2, 0, 2], [1, 1, 1],
        [-2, -1, 0, 1, 2], [-2, 0, 0, 0, 2], [-2, 0, 1, 2, 2],
    ]


def _small_int_matrices() -> list[list[list[int]]]:
    return [
        [[0]], [[1]], [[2]], [[0, 0], [0, 0]], [[1, 1], [1, 1]],
        [[0, 1], [1, 0]], [[1, 0], [0, 1]], [[0, 1], [1, 2]],
        [[1, 2], [2, 3]], [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        [[1, 1, 1], [1, 1, 1], [1, 1, 1]],
        [[0, 1, 0], [1, 0, 1], [0, 1, 0]],
        [[1, 0, 1], [0, 1, 0], [1, 0, 1]],
        [[0, 1]], [[1, 0]], [[0], [1]], [[1], [0]],
        [[0, 1], [0, 2], [1, 2]], [[1], [0]], [[], []],
    ]


def _domain(kind: str) -> list[Any]:
    if kind == "int_list":
        return _small_int_arrays()
    if kind == "int_matrix":
        return _small_int_matrices()
    if kind == "str":
        return ["", "a", "b", "0", "1", "aa", "ab", "ba", "aba", "abc", "()", "(a)"]
    if kind == "str_list":
        return [[], ["a"], ["a", "b"], ["a", "a"], ["ab", "ba"], ["0", "1"]]
    if kind == "str_matrix":
        return [[['0']], [['1']], [['0', '1'], ['1', '0']], [['1', '1'], ['1', '1']]]
    if kind == "int":
        return [0, 1, 2, 3, 4, 5, -1, -2]
    raise ValueError(kind)


def _candidate_arguments(kinds: tuple[str, ...], description: str):
    description_lower = description.lower()
    if kinds == ("int_list",):
        for array in _candidate_arrays(description):
            if "triplet" in description_lower and len(array) < 3:
                continue
            yield (array,)
    elif len(kinds) == 1:
        for value in _domain(kinds[0]):
            yield (value,)
    else:
        domains = [_domain(kind) for kind in kinds]
        if "sorted" in description_lower or "non-decreasing" in description_lower:
            domains = [
                [item for item in domain if item == sorted(item)] if kind == "int_list" else domain
                for kind, domain in zip(kinds, domains)
            ]
        for values in itertools.product(*domains):
            if "median" in description_lower and all(
                kind == "int_list" for kind in kinds
            ) and not any(values):
                continue
            yield values


def _small_locals(locals_dict: dict[str, Any]) -> dict[str, int | float | bool | str]:
    values = {}
    for name, value in locals_dict.items():
        if isinstance(value, (int, float, bool)) or (isinstance(value, str) and len(value) <= 24):
            values[name] = value
    return dict(list(values.items())[:10])


def _run_one(compiled: Any, func_name: str, arguments: tuple[Any, ...], targets: set[int]) -> dict[int, dict[str, Any]]:
    namespace: dict[str, Any] = {}
    seen: dict[int, dict[str, Any]] = {}
    recent: deque[int] = deque(maxlen=8)

    def trace(frame: Any, event: str, arg: Any):
        if frame.f_code.co_filename == SOURCE_FILENAME and event == "line":
            recent.append(frame.f_lineno)
            if frame.f_lineno in targets and frame.f_lineno not in seen:
                seen[frame.f_lineno] = {
                    "args": list(arguments),
                    "call": f"solution.{func_name}({', '.join(repr(arg) for arg in arguments)})",
                    "target_line": frame.f_lineno,
                    "locals_at_target": _small_locals(frame.f_locals),
                    "recent_lines": list(recent),
                    "verification": "target observed; call returned normally",
                }
        return trace

    try:
        exec(compiled, namespace)
        solution = namespace["Solution"]()
        previous = sys.gettrace()
        sys.settrace(trace)
        try:
            getattr(solution, func_name)(*copy.deepcopy(arguments))
        finally:
            sys.settrace(previous)
    except Exception:
        return {}
    return seen


def _worker(record: dict[str, Any], seconds: float, max_candidates: int, queue: Any) -> None:
    try:
        source = record["python_solution"]
        func_name = record["func_name"]
        kinds = _parameter_kinds(source, func_name)
        if kinds is None:
            queue.put({"supported": False, "tried": 0, "witnesses": {}})
            return
        compiled = compile(source, SOURCE_FILENAME, "exec")
        targets = set(record["target_lines"])
        witnesses: dict[int, dict[str, Any]] = {}
        deadline = time.monotonic() + seconds
        tried = 0
        for arguments in _candidate_arguments(kinds, record.get("description", "")):
            if tried >= max_candidates or time.monotonic() >= deadline or len(witnesses) == len(targets):
                break
            tried += 1
            newly_seen = _run_one(compiled, func_name, arguments, targets - witnesses.keys())
            witnesses.update(newly_seen)
        queue.put({"supported": True, "tried": tried, "witnesses": witnesses})
    except Exception as exc:
        queue.put({"supported": False, "tried": 0, "witnesses": {}, "error": type(exc).__name__})


def find_verified_witnesses(
    record: dict[str, Any], seconds: float = 2.0, max_candidates: int = 800
) -> dict[str, Any]:
    """Search once per program; isolate execution and bound the wall time."""
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_worker, args=(record, seconds, max_candidates, queue))
    process.start()
    process.join(seconds + 1.0)
    timed_out = process.is_alive()
    if timed_out:
        process.terminate()
        process.join()
    result = {"supported": False, "tried": 0, "witnesses": {}}
    if not timed_out:
        try:
            result = queue.get(timeout=0.2)
        except Exception:
            pass
    queue.close()
    result["timed_out"] = timed_out
    result["version"] = WITNESS_VERSION
    return result
