import json
import shutil
from types import SimpleNamespace

import pytest

from final.src.benchmarks.PUT_generation import generate_puts, run_base_tests, save_cohort
from final.src.modular.cohort import load_cohort
from final.src.models.core_model import ModelError, ModelResponse
from final.src.models.model import TransportError
from final.src.runtime.execution import ExecutionError

TASK = {"prompt": "def f(x):\n    return x\n", "entry_point": "f"}


def test_generation_calls_model_once_and_logs_invalid_source(caplog):
    source = "raise RuntimeError('must not execute')\ndef f(x): return x\n"
    candidates = [
        {"code": "def wrong(x): return x", "approach": "wrong entry"},
        {"code": source, "approach": "identity"},
        {"code": "def f(x): return -x", "approach": "over budget"},
    ]
    requests = []

    def generate(messages, **kwargs):
        requests.append((messages, kwargs))
        return ModelResponse(json.dumps({"programs": candidates}))

    result = generate_puts(SimpleNamespace(generate=generate), TASK, count=2, seed=17)
    assert [p["code"] for p in result] == [source]
    assert result[0]["id"] == 0
    assert set(result[0]) == {"id", "code", "approach"}
    assert "Skipping invalid PUT" in caplog.text
    assert len(requests) == 1
    assert requests[0][1] == {"temperature": .9, "max_tokens": 4072, "seed": 17}


@pytest.mark.parametrize("text", ["invalid JSON", '{}', '{"programs":null}', '{"programs":{}}'])
def test_bad_response_is_logged_without_retry(text, caplog):
    requests = []

    def generate(*args, **kwargs):
        requests.append(1)
        return ModelResponse(text)

    assert generate_puts(SimpleNamespace(generate=generate), TASK) == []
    assert len(requests) == 1
    assert "PUT generation failed" in caplog.text


def test_model_failure_is_logged_without_retry_or_exposing_details(caplog):
    requests = []

    def generate(*args, **kwargs):
        requests.append(1)
        raise ModelError("private endpoint and credentials")

    assert generate_puts(SimpleNamespace(generate=generate), TASK) == []
    assert len(requests) == 1
    assert "ModelError" in caplog.text
    assert "private" not in caplog.text


@pytest.mark.parametrize("failures", [1, 3])
def test_inline_retry_is_bounded_and_preserves_request(monkeypatch, failures):
    requests = []
    delays = []
    monkeypatch.setattr("final.src.benchmarks.PUT_generation.time.sleep", delays.append)

    def generate(messages, **kwargs):
        requests.append((messages, kwargs))
        if len(requests) <= failures:
            raise TransportError("completion", "HTTPError", http_status=503, retryable=True)
        return ModelResponse('{"programs":[{"code":"def f(x): return x", "approach":"identity"}]}')

    result = generate_puts(SimpleNamespace(generate=generate), TASK)
    assert len(requests) == min(failures + 1, 3)
    assert all(request == requests[0] for request in requests)
    assert delays == [5, 20][:min(failures, 2)]
    assert bool(result) is (failures < 3)


@pytest.mark.parametrize("count", [0, 31, True])
def test_invalid_count_is_rejected_before_call(count):
    with pytest.raises(ValueError, match="count"):
        generate_puts(None, TASK, count=count)


@pytest.mark.parametrize("status", ["pass", "fail", "timeout", "error"])
def test_base_tests_preserve_sandbox_job_and_outcome(monkeypatch, status):
    task = dict(TASK, test="def check(candidate): assert candidate(1) == 1")
    program = {"code": "def f(x): return x"}
    outcome = {"status": status, "input_keys": ["fixture"], "call_records": []}
    jobs = []

    def execute(job):
        jobs.append(job)
        return outcome

    monkeypatch.setattr("final.src.benchmarks.PUT_generation.execute", execute)
    assert run_base_tests(task, program, timeout=2, seed=42) is outcome
    assert jobs == [{"mode": "base", "context": task["prompt"], "source": program["code"],
                     "entry": "f", "base": task["test"], "timeout": 2, "seed": 42, "trace": True}]


def test_base_test_infrastructure_failure_is_logged_and_propagated(monkeypatch, caplog):
    def execute(job):
        raise ExecutionError("sandbox failed")

    monkeypatch.setattr("final.src.benchmarks.PUT_generation.execute", execute)
    with pytest.raises(ExecutionError, match="sandbox failed"):
        run_base_tests(dict(TASK, test="fixture"), {"code": "fixture"})
    assert "Base test execution failed: ExecutionError" in caplog.text


def test_saved_cohort_loads_with_existing_reader_and_preserves_outcomes(tmp_path):
    programs = [{"id": index, "code": "def f(x): return x", "base": {"status": status}}
                for index, status in enumerate(["pass", "fail", "timeout"])]
    tasks = [{"task_id": "HumanEval/0", "programs": programs, "generated": 3,
              "base_pass": 1, "base_input_keys": ["fixture"], "status": "complete"}]
    path = tmp_path / "nested/cohort.json"
    cohort = save_cohort(tasks, str(path))
    assert json.loads(path.read_text()) == {"tasks": tasks}
    assert load_cohort(path)["tasks"] == tasks
    assert cohort["tasks"] == tasks
    assert not path.with_suffix(".json.tmp").exists()


@pytest.mark.parametrize("field", ["cohort_sha256", "dataset_sha256"])
def test_stored_hash_does_not_block_cohort_loading(tmp_path, field):
    path = tmp_path / "cohort.json"
    path.write_text(json.dumps({"tasks": [], field: "incorrect"}))
    assert load_cohort(path)["tasks"] == []


def test_console_accepts_cohort_without_stored_hash(tmp_path, monkeypatch):
    from final.src.orchestration import config

    path = tmp_path / "cohort.json"
    save_cohort([], path)
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setitem(config.COHORTS, "fixture", "cohort.json")
    loaded_path, cohort = config.load_cohort({"cohort": "fixture"})
    assert loaded_path == path
    assert cohort == load_cohort(path)
    assert json.loads(path.read_text()) == {"tasks": []}


@pytest.mark.parametrize("status", ["pass", "fail", None])
def test_main_saves_pipeline_task_record(tmp_path, monkeypatch, status):
    from final.src.benchmarks import PUT_generation as module
    from final.src.modular.stages.cohort_loader import CohortLoaderStage

    task = dict(TASK, task_id="HumanEval/0", test="fixture")
    program = {"id": 0, "code": "def f(x): return x", "approach": "identity"}
    outcome = {"status": status, "input_keys": ["b", "a", "a"],
               "calls": [{"args": "(1,)", "kwargs": "{}"}], "coverage": {"lines": [1]}}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "DatasetLoader", lambda _: SimpleNamespace(load_tasks=lambda: [task]))
    monkeypatch.setattr(module, "create_model", lambda **kwargs: object())
    monkeypatch.setattr(module, "generate_puts", lambda *args, **kwargs: [dict(program)] if status else [])
    monkeypatch.setattr(module, "run_base_tests", lambda *args: outcome)
    module.main([])
    path = tmp_path / "final/out/put_generation/cohort_he-py.json"
    stored = json.loads(path.read_text())
    assert set(stored) == {"tasks"}
    context = SimpleNamespace(task=task)
    CohortLoaderStage(path).run(context)
    record = context.cohort_task
    assert record["generated"] == (1 if status else 0)
    assert record["base_pass"] == (1 if status == "pass" else 0)
    assert record["base_input_keys"] == (["a", "b"] if status else [])
    assert record["programs"] == ([dict(program, base=outcome)] if status else [])
    assert record["status"] == ("complete" if status else "no_programs")


@pytest.mark.parametrize("selection,expected", [
    (["--num-tasks", "2"], ["HumanEval/0", "HumanEval/1"]),
    (["--task-ids", "2", "HumanEval/0"], ["HumanEval/2", "HumanEval/0"]),
])
def test_cli_selects_tasks_and_passes_model_and_put_count(tmp_path, monkeypatch, selection, expected):
    from final.src.benchmarks import PUT_generation as module

    tasks = [dict(TASK, task_id=f"HumanEval/{index}") for index in range(3)]
    models, generations = [], []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "DatasetLoader", lambda _: SimpleNamespace(load_tasks=lambda: tasks))
    monkeypatch.setattr(module, "create_model", lambda **kwargs: models.append(kwargs))

    def generate(model, task, **kwargs):
        generations.append((task["task_id"], kwargs["count"]))
        return []

    monkeypatch.setattr(module, "generate_puts", generate)
    module.main(["--dataset-type", "HE-py", "--model-backend", "qwen",
                 "--model-name", "fixture", "--puts-per-task", "5", *selection])
    assert models == [{"backend": "qwen", "model_name": "fixture"}]
    assert generations == [(identifier, 5) for identifier in expected]


@pytest.mark.parametrize("arguments", [
    ["--num-tasks", "0"], ["--num-tasks", "4"], ["--puts-per-task", "31"],
    ["--task-ids", "999"], ["--task-ids", "0", "HumanEval/0"],
    ["--num-tasks", "1", "--task-ids", "0"],
])
def test_bad_cli_arguments_fail_before_constructing_model(monkeypatch, arguments):
    from final.src.benchmarks import PUT_generation as module

    monkeypatch.setattr(module, "DatasetLoader", lambda _: SimpleNamespace(
        load_tasks=lambda: [dict(TASK, task_id="HumanEval/0")]))
    monkeypatch.setattr(module, "create_model", lambda **kwargs: pytest.fail("Unexpected model construction"))
    with pytest.raises(SystemExit) as error:
        module.main(arguments)
    assert error.value.code == 2


def test_resume_keeps_saved_puts_retries_empty_and_saves_before_next_task(tmp_path, monkeypatch):
    from final.src.benchmarks import PUT_generation as module

    source = tmp_path / 'source.json'
    output = tmp_path / 'continued.json'
    kept = {'task_id': 'HumanEval/0', 'programs': [{'id': 0, 'code': 'saved source'}], 'base_pass': 0}
    source.write_text(json.dumps({'tasks': [kept, {'task_id': 'HumanEval/1', 'programs': []}]}))
    original = source.read_bytes()
    tasks = [dict(TASK, task_id=f'HumanEval/{i}') for i in range(3)]
    monkeypatch.setattr(module, 'DatasetLoader', lambda _: SimpleNamespace(load_tasks=lambda: tasks))
    monkeypatch.setattr(module, 'create_model', lambda **kwargs: object())
    called = []

    def generate(model, task, **kwargs):
        called.append(task['task_id'])
        if task['task_id'] == 'HumanEval/2':
            saved = json.loads(output.read_text())['tasks']
            assert saved[0] == kept
            assert saved[1]['programs']
            raise RuntimeError('interrupted')
        return [{'id': 0, 'code': 'def f(x): return x'}]

    monkeypatch.setattr(module, 'generate_puts', generate)
    monkeypatch.setattr(module, 'run_base_tests', lambda *args: {'status': 'pass', 'input_keys': []})
    with pytest.raises(RuntimeError, match='interrupted'):
        module.main(['--num-tasks', '3', '--resume', str(source), '--output', str(output)])
    assert called == ['HumanEval/1', 'HumanEval/2']
    assert source.read_bytes() == original


def test_resume_with_no_missing_tasks_never_constructs_model(tmp_path, monkeypatch):
    from final.src.benchmarks import PUT_generation as module

    source = tmp_path / 'source.json'
    output = tmp_path / 'continued.json'
    cohort = {'tasks': [{'task_id': 'HumanEval/0', 'programs': [{'code': 'saved'}]}]}
    source.write_text(json.dumps(cohort))
    monkeypatch.setattr(module, 'DatasetLoader', lambda _: SimpleNamespace(
        load_tasks=lambda: [dict(TASK, task_id='HumanEval/0')]))
    monkeypatch.setattr(module, 'create_model', lambda **kwargs: pytest.fail('Unexpected model construction'))
    module.main(['--resume', str(source), '--output', str(output)])
    assert json.loads(output.read_text()) == cohort


@pytest.mark.parametrize("dataset_type", ["he-py", "mbpp-py"])
@pytest.mark.parametrize("correct", [True, False])
def test_all_datasets_generate_and_save_real_sandbox_outcomes(tmp_path, monkeypatch, dataset_type, correct):
    from final.src.benchmarks import PUT_generation as module

    if shutil.which("bwrap") is None:
        pytest.skip("bwrap is not installed")
    increment = 1 if correct else 2
    task = {"task_id": "HumanEval/0", "prompt": "def f(x):\n    pass\n", "entry_point": "f",
            "test": "def check(candidate):\n    assert candidate(1) == 2\n"}
    source = f"def f(x): return x + {increment}"
    if dataset_type == "mbpp-py":
        task = {"task_id": "MBPP/11", "language": "python", "prompt": "Add one.", "entry_point": "f",
                "canonical_solution": "def f(x): return x + 1 # reference-only-marker",
                "test": "assert f(1) == 2", "tests": ["assert f(1) == 2"], "test_setup_code": ""}
    prompts = []

    def generate(messages, **kwargs):
        prompts.append(messages)
        return ModelResponse(json.dumps({"programs": [{"code": source, "approach": "addition"}]}))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "DatasetLoader", lambda _: SimpleNamespace(load_tasks=lambda: [task]))
    monkeypatch.setattr(module, "create_model", lambda **kwargs: SimpleNamespace(generate=generate))
    module.main(["--dataset-type", dataset_type])
    record = json.loads((tmp_path / f"final/out/put_generation/cohort_{dataset_type}.json").read_text())["tasks"][0]
    assert record["generated"] == 1
    assert record["base_pass"] == int(correct)
    assert (record["programs"][0]["base"]["status"] == "pass") is correct
    assert len(prompts) == 1
    assert "reference-only-marker" not in json.dumps(prompts)
    language = {"he-py": "Python", "mbpp-py": "Python"}[dataset_type]
    assert language in prompts[0][0]["content"]
