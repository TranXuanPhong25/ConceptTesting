import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from final.src.benchmarks import java_run
from final.src.models.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.runtime.artifacts import save


def test_java_prepare_is_offline_and_pins_the_worker(tmp_path, monkeypatch):
    monkeypatch.setattr(java_run, 'create_model', lambda **options: pytest.fail('model during prepare'))
    config = java_run.prepare(tmp_path / 'run')
    assert config['config']['arms'] == ['plain', 'decision_table_v2']
    assert (tmp_path / 'run/runtime/final/src/benchmarks/java_run.py').is_file()
    assert config['writer_logical_call_cap'] == 164
    assert config['tester_logical_call_cap'] == 328


def test_budget_charges_unknown_attempt_and_refuses_next_call(tmp_path):
    calls = []
    def failed(*args, **kwargs):
        calls.append(True)
        raise ConnectionError('authored failure')
    store = ArtifactStore(tmp_path)
    save(store.path('budget.json'), {'cap_usd': .01, 'reserved_usd': 0, 'attempts': 0})
    model = java_run.BudgetModel(SimpleNamespace(generate_prepared=failed), store)
    prepared = SimpleNamespace(prompt_tokens=1000, output_tokens=1000)
    with pytest.raises(ConnectionError):
        model.generate_prepared(prepared)
    assert store.read('budget.json')['reserved_usd'] == .006
    with pytest.raises(RuntimeError, match='budget exhausted'):
        model.generate_prepared(prepared)
    assert calls == [True]


def test_java_worker_uses_independent_put_and_only_requested_arms(tmp_path, monkeypatch):
    class Model:
        model_id = 'authored-gemini-fixture'
        def tokens(self, messages):
            return 100
        def prepare_generation(self, messages, max_tokens):
            return SimpleNamespace(messages=messages, prompt_tokens=100, output_tokens=max_tokens)
        def generate_prepared(self, prepared, **options):
            assert 'REFERENCE_BODY_MARKER' not in json.dumps(prepared.messages)
            if 'write correct' in prepared.messages[0]['content']:
                return ModelResponse(json.dumps({'programs': [{'approach': 'fixture',
                    'code': 'class Solution { int f(int x) { return x; } }'}]}), {}, 'stop')
            return ModelResponse('{"inputs":[{"arguments":{"x":2}}]}', {}, 'stop')

    config = {'dataset': 'humaneval_x_java', 'arms': ['plain', 'decision_table_v2'],
        'model_name': 'authored-fixture', 'backend': 'vertex', 'inputs_per_task': 2,
        'context_tokens': 18192, 'completion_tokens': 4096, 'timeout_seconds': 8}
    save(tmp_path / 'config_snapshot.json', config)
    save(tmp_path / 'experiment_config.json', {'puts_per_task': 1})
    save(tmp_path / 'budget.json', {'cap_usd': 20, 'reserved_usd': 0, 'attempts': 0})
    root = Path(java_run.__file__).resolve().parents[3]
    save(tmp_path / 'launch_plan.json', {'runtime': str(root), 'workspace': str(root)})
    task = {'task_id': 'Java/0', 'language': 'java', 'prompt': 'Return x + 1.',
        'declaration': 'class Solution { int f(int x) {', 'example_test': 'public fixture',
        'reference_source': 'REFERENCE_BODY_MARKER'}
    save(tmp_path / 'tasks_snapshot.json', [task])
    monkeypatch.setattr(java_run, 'create_model', lambda **options: Model())
    monkeypatch.setattr(java_run.fcntl, 'flock', lambda *args: None)
    def execute(task, source, calls, **options):
        if options.get('base'):
            return {'status': 'ok', 'tests': [{'status': 'ok'}]}
        assert (tmp_path / 'generation_frozen.json').exists()
        return {'status': 'ok', 'tests': [{'status': 'ok', 'value': 3 if source == 'REFERENCE_BODY_MARKER' else 2} for _ in calls]}
    monkeypatch.setattr(java_run, 'execute_program', execute)
    result = java_run.run(tmp_path)
    assert set(result['arms']) == {'plain', 'decision_table_v2'}
    assert result['generated_PUTs'] == 1
    assert all(row['detected'] == 1 for row in result['arms'].values())
    assert result['budget']['attempts'] == 3
    cohort = json.loads((tmp_path / 'put_cohort.json').read_text())
    assert 'REFERENCE_BODY_MARKER' not in json.dumps(cohort)
    assert json.loads((tmp_path / 'status.json').read_text())['state'] == 'complete'
