"""Pinned dataset readers; no network access is performed here."""
from __future__ import annotations

import ast
import gzip
import json
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / 'data/contracts.json'
DATA = ROOT / 'data' / 'benchmarks'
MBPP_PATH = DATA / "mbppplus_v0.2.0.jsonl.gz"


class DatasetLoader:
    """Select a bundled benchmark using its config code."""

    def __init__(self, config: str):
        self.config = config.lower()
        if self.config not in ('he-py', 'mbpp-py'):
            raise ValueError(f'Unsupported dataset: {config}')

    def load_tasks(self) -> list[dict]:
        if self.config == 'he-py':
            return load_tasks()
        return load_mbpp()

    def load_metadata(self):
        if self.config != 'he-py':
            raise ValueError(f'No domain metadata bundled for {self.config}')
        return load_metadata()


def _read_json_lines(path: Path, *, compressed: bool = False) -> list[dict]:
    opener = gzip.open if compressed or path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _infer_entry_point(code: str, tests: list[str]) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        raise ValueError("MBPP canonical code is not valid Python") from error
    functions = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not functions:
        raise ValueError("MBPP canonical code has no top-level function")
    called = []
    for test in tests:
        try:
            test_tree = ast.parse(test)
        except SyntaxError:
            continue
        called.extend(node.func.id for node in ast.walk(test_tree)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Name))
    for name in functions:
        if name in called:
            return name
    return functions[0]


def load_tasks() -> list[dict]:
    """Load the pinned HumanEval Python tasks in their original format."""
    tasks = _read_json_lines(ROOT / 'data/humaneval.jsonl')
    return sorted(tasks, key=lambda task: int(task['task_id'].split('/')[1]))


def load_metadata():
    from .humaneval_types import input_types_for_source
    metadata = json.loads(METADATA_PATH.read_text())
    for task in load_tasks():
        types = input_types_for_source(task['prompt'], task['entry_point'])
        if types:
            metadata[task['task_id']]['input_types'] = types
    return metadata


def load_humaneval() -> list[dict]:
    """Load the existing HumanEval Python tasks with language metadata."""
    return [{**task, 'language': 'python'} for task in load_tasks()]


def load_mbpp(path: Path | None = None) -> list[dict]:
    """Load pinned MBPP+ v0.2.0; explicit paths also accept original MBPP."""
    source = Path(path) if path is not None else MBPP_PATH
    rows = _read_json_lines(source)
    normalized = []
    for row in rows:
        task_id = row['task_id']
        identifier = f"MBPP/{task_id}"
        text = row['text'] if 'text' in row else row['prompt']
        code = row['code']
        tests = row['test_list']
        setup = row.get("test_setup_code", "") or "\n".join(row.get("test_imports", []))
        entry = _infer_entry_point(code, tests)
        test_source = "\n".join(part for part in (setup, *tests) if part)
        normalized.append({
            "task_id": identifier,
            "language": "python",
            "prompt": text,
            "entry_point": entry,
            "canonical_solution": code,
            "test": test_source,
            "test_setup_code": setup,
            "tests": tests,
        })
    return sorted(normalized, key=lambda task: int(task['task_id'].split('/')[1]))


def dataset_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
