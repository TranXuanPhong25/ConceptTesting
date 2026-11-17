import json

import pytest

from final.src.models.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.benchmarks.pipeline import adapter_task, load_candidates, preview, run_benchmark


def fixture_task():
    return adapter_task({'task_id':'MBPP/11', 'language':'python', 'prompt':'Add one.',
        'entry_point':'f', 'canonical_solution':'def f(x):\n    return x+1\n',
        'test':'assert f(1)==2', 'tests':['assert f(1)==2'], 'test_setup_code':''})


def test_mbpp_packet_never_contains_reference_body():
    from final.src.benchmarks.pipeline import messages_for
    task = fixture_task()
    task['reference_source'] += '# reference-only-marker\n'
    messages = messages_for(task, [{'id':'p', 'code':'def f(x): return 2'}], 'ep_bva_v2', 20)
    assert 'reference-only-marker' not in json.dumps(messages)
    assert 'Add one.' in json.dumps(messages)
    assert 'EP with normal BVA' in json.dumps(messages)


def test_candidate_import_rejects_unknown_and_duplicate_ids(tmp_path):
    path = tmp_path/'puts.jsonl'
    row = {'task_id':'MBPP/11', 'id':'p', 'code':'def f(x): return x'}
    path.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n')
    with pytest.raises(ValueError, match='duplicate'):
        load_candidates(path, [fixture_task()])


def test_preview_missing_cohort_does_no_execution():
    description = preview({'dataset':'humaneval_x_java', 'task_numbers':[0]})
    assert description['requested_task_count'] == 1
    assert description['cohort_status'] == 'pending'
    assert description['base_pass_put_count'] is None
    assert description['logical_call_cap'] == 3


def test_python_pipeline_freezes_before_reference_and_replays_without_work(tmp_path, monkeypatch):
    from final.src.benchmarks import pipeline
    task = fixture_task()
    cohort = {'MBPP/11':[{'id':'p', 'code':'def f(x):\n    return 2\n'}]}
    store = ArtifactStore(tmp_path/'run')
    class Calls:
        model_id = 'fixture'
        def token_count(self, messages): return 50
        def complete(self, *args, **kwargs):
            assert not store.exists('generation_frozen.json')
            return ModelResponse(json.dumps({'inputs':[{'arguments':{'x':3}}]}))
    real_execute = pipeline.execute_program
    def guarded_execute(task, code, inputs, **options):
        if not options.get('base'):
            assert store.exists('generation_frozen.json')
        return real_execute(task, code, inputs, **options)
    monkeypatch.setattr(pipeline, 'execute_program', guarded_execute)
    config = {'dataset':'mbpp', 'task_numbers':[11], 'arms':['plain','ep_bva_v2']}
    result = run_benchmark([task], cohort, store, config, calls=Calls())
    assert result['arms']['plain']['detected'] == 1
    assert result['evaluated_base_pass'] == 1
    monkeypatch.setattr(pipeline, 'execute_program', lambda *a,**k: pytest.fail('execution during replay'))
    replay = run_benchmark([task], cohort, ArtifactStore(store.directory, read_only=True), config)
    assert replay == result


def test_unsupported_environment_does_not_become_zero_detection(tmp_path):
    from final.src.benchmarks import pipeline
    with pytest.raises(RuntimeError, match='unsupported_environment'):
        run_benchmark([fixture_task()], {'MBPP/11':[{'id':'p','code':'def f(x): return 2'}]},
            ArtifactStore(tmp_path/'run'), {'arms':['plain']},
            executor=lambda *a,**k: {'status':'unsupported_environment','tests':[]})


def test_replay_rejects_removed_generation_provenance(tmp_path):
    store = ArtifactStore(tmp_path/'run')
    class Calls:
        model_id = 'fixture'
        def token_count(self, messages): return 50
        def complete(self, number, arm, messages, **options):
            store.write(f'tasks/{number}/calls/{arm}/request.json', {'messages':messages})
            store.write(f'tasks/{number}/calls/{arm}/response.json', {'text':'fixture','usage':{}})
            return ModelResponse(json.dumps({'inputs':[{'arguments':{'x':3}}]}))
    cohort = {'MBPP/11':[{'id':'p','code':'def f(x): return 2'}]}
    values = {'arms':['plain']}
    run_benchmark([fixture_task()], cohort, store, values, calls=Calls())
    store.path('tasks/11/calls/plain/request.json').unlink()
    with pytest.raises(ValueError, match='Artifact changed'):
        run_benchmark([fixture_task()], cohort, ArtifactStore(store.directory, read_only=True), values)
