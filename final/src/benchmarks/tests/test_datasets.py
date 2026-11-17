import gzip
import json

import pytest

from final.src.benchmarks.datasets import DatasetLoader, load_humaneval, load_humaneval_x, load_mbpp
from final.src.benchmarks.datasets import load_tasks


def test_humaneval_preserves_existing_python_tasks():
    rows = load_humaneval()
    assert {row['task_id'] for row in rows} == {f'HumanEval/{i}' for i in range(164)}
    assert rows == [{**task, 'language': 'python'} for task in load_tasks()]


def test_bundled_datasets_have_official_task_sets():
    with gzip.open('final/data/benchmarks/mbppplus_v0.2.0.jsonl.gz', 'rt') as handle:
        official = [json.loads(line) for line in handle if line.strip()]
    tasks = load_mbpp()
    assert len(tasks) == 378
    assert {row['task_id'] for row in tasks} == {f'MBPP/{row["task_id"]}' for row in official}
    assert all(task['canonical_solution'] == row['code'] for task, row in zip(tasks, sorted(official, key=lambda r: int(r['task_id']))))
    assert {row['task_id'] for row in load_humaneval_x('cpp')} == {f'CPP/{i}' for i in range(164)}
    assert {row['task_id'] for row in load_humaneval_x('java')} == {f'Java/{i}' for i in range(164)}


def test_load_mbpp_normalizes_entry_and_tests(tmp_path):
    path = tmp_path / "mbpp.jsonl"
    path.write_text(json.dumps({
        "task_id": 11,
        "text": "Add two numbers.",
        "code": "def add(a, b):\n    return a + b\n",
        "test_list": ["assert add(1, 2) == 3"],
        "test_setup_code": "from math import prod",
        "challenge_test_list": [],
    }) + "\n")

    rows = load_mbpp(path)

    assert rows == [{
        "task_id": "MBPP/11",
        "language": "python",
        "prompt": "Add two numbers.",
        "entry_point": "add",
        "canonical_solution": "def add(a, b):\n    return a + b\n",
        "test": "from math import prod\nassert add(1, 2) == 3",
        "test_setup_code": "from math import prod",
        "tests": ["assert add(1, 2) == 3"],
    }]


@pytest.mark.parametrize('config,prefix,count', [
    ('HE-py', 'HumanEval', 164), ('he-cpp', 'CPP', 164),
    ('HE-java', 'Java', 164), ('MBPP-py', 'MBPP', 378),
])
def test_loader_selects_dataset_from_config(config, prefix, count):
    tasks = DatasetLoader(config).load_tasks()
    assert len(tasks) == count
    assert all(task['task_id'].startswith(prefix + '/') for task in tasks)


@pytest.mark.parametrize('config', ['HE-c', 'unknown'])
def test_loader_rejects_unavailable_datasets(config):
    with pytest.raises(ValueError):
        DatasetLoader(config)


def test_loader_loads_humaneval_metadata():
    loader = DatasetLoader('HE-py')
    assert set(loader.load_metadata()) == {task['task_id'] for task in loader.load_tasks()}


def test_load_humaneval_x_reads_gzip_and_validates_language(tmp_path):
    path = tmp_path / "cpp.jsonl.gz"
    row = {
        "task_id": "CPP/0",
        "prompt": "bool f(int x){\n",
        "declaration": "bool f(int x){\n",
        "canonical_solution": "return x > 0;\n}\n",
        "test": "int main(){}",
        "example_test": "int main(){}",
    }
    with gzip.open(path, "wt") as handle:
        handle.write(json.dumps(row) + "\n")

    assert load_humaneval_x("cpp", path) == [{**row, "language": "cpp"}]

    with pytest.raises(ValueError, match="language"):
        load_humaneval_x("rust", path)
