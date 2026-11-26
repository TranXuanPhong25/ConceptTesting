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
    messages = messages_for(task, [{'id':'p', 'code':'def f(x): return 2'}], 'ep_bva_single', 20)
    assert 'reference-only-marker' not in json.dumps(messages)
    assert 'Add one.' in json.dumps(messages)
    assert 'Equivalence Partitioning (EP)' in json.dumps(messages)


def test_candidate_import_rejects_unknown_and_duplicate_ids(tmp_path):
    path = tmp_path/'puts.jsonl'
    row = {'task_id':'MBPP/11', 'id':'p', 'code':'def f(x): return x'}
    path.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n')
    with pytest.raises(ValueError, match='duplicate'):
        load_candidates(path, [fixture_task()])


def test_preview_missing_cohort_does_no_execution():
    description = preview({'dataset':'mbpp', 'task_numbers':[11]})
    assert description['requested_task_count'] == 1
    assert description['cohort_status'] == 'pending'
    assert description['base_pass_put_count'] is None
    assert description['logical_call_cap'] == 3
    assert description['config']['arms'] == ['plain', 'ep_bva_single', 'decision_table_single']


def test_python_pipeline_freezes_before_reference_and_replays_without_work(tmp_path, monkeypatch):
    from final.src.benchmarks import pipeline
    task = fixture_task()
    cohort = {'MBPP/11':[{'id':'p', 'code':'def f(x):\n    return 2\n'}]}
    store = ArtifactStore(tmp_path/'run')
    class Calls:
        model_id = 'fixture'
        def token_count(self, messages): return 50
        def complete(self, *args, **kwargs):
            assert not store.exists('tasks/11/inputs.json')
            return ModelResponse(json.dumps({'inputs':[{'arguments':{'x':3}}]}))
    real_execute = pipeline.execute_program
    def guarded_execute(task, code, inputs, **options):
        if not options.get('base'):
            assert store.exists('tasks/11/inputs.json')
        return real_execute(task, code, inputs, **options)
    monkeypatch.setattr(pipeline, 'execute_program', guarded_execute)
    config = {'dataset':'mbpp', 'task_numbers':[11], 'arms':['plain','ep_bva_single']}
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


def test_replay_reads_saved_results_without_generation_provenance(tmp_path):
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
    expected = run_benchmark([fixture_task()], cohort, store, values, calls=Calls())
    store.path('tasks/11/calls/plain/request.json').unlink()
    assert not store.exists('generation_frozen.json')
    assert not store.exists('execution_frozen.json')
    replay = ArtifactStore(store.directory, read_only=True)
    assert run_benchmark([], {}, replay, {}) == expected


def test_mbpp_preview_control_flow_4tool_leaves_caps_pending_and_validates_tool_dir():
    description = preview({
        'dataset': 'mbpp',
        'task_numbers': [11],
        'arms': ['control_flow_4tool'],
        'context_tokens': 40960,
        'completion_tokens': 8192,
    })
    assert description['logical_call_cap'] == 'pending'
    assert description['transport_attempt_cap'] == 'pending'
    assert description['completion_token_cap'] == 'pending'

    with pytest.raises(ValueError, match='control_flow_4tool'):
        preview({'dataset': 'mbpp', 'task_numbers': [11], 'arms': ['plain'], 'tool_runs_dir': 'final/out/x'})


def test_mbpp_control_flow_4tool_end_to_end_with_tuple_args_mixed_arms_and_replay(tmp_path):
    from final.src.modular.control_flow import ControlFlowFourToolArm, ControlFlowSettings
    from final.src.modular.call_builder import CallBuilder

    task = adapter_task({
        'task_id': 'MBPP/2',
        'language': 'python',
        'prompt': 'Return shared elements of two tuples; if empty return empty tuple.',
        'entry_point': 'similar_elements',
        'canonical_solution': (
            'def similar_elements(a, b):\n'
            '    if not a:\n'
            '        return ()\n'
            '    shared = sorted(set(a) & set(b))\n'
            '    if len(shared) > 1:\n'
            '        return tuple(shared)\n'
            '    return tuple(shared)\n'
        ),
        'test': 'assert similar_elements((1, 2), (2, 3)) == (2,)',
        'tests': ['assert similar_elements((1, 2), (2, 3)) == (2,)'],
        'test_setup_code': '',
    })
    buggy_code = (
        'def similar_elements(a, b):\n'
        '    if not a:\n'
        '        return ()\n'
        '    shared = sorted(set(a) & set(b))\n'
        '    if len(shared) > 1:\n'
        '        return ()\n'  # Bug on len(shared) > 1 branch!
        '    return tuple(shared)\n'
    )
    cohort = {'MBPP/2': [{'id': 'p0', 'code': buggy_code}]}

    # Fixture 4-tool dir covering ONLY the `not a` branch, leaving `len(shared) > 1` residual.
    tools_dir = tmp_path / 'mbpp_tools'
    receipt_path = tools_dir / 'tasks' / '2' / '0' / 'crosshair' / 'receipt.json'
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps({
        'task_id': 'MBPP/2',
        'put': 0,
        'tool': 'crosshair',
        'base': 'pass',
        'calls': [{'args': '((), (1,))', 'kwargs': '{}'}],
    }))

    def fake_base_tracer(task_row, program, *, timeout, seed):
        return {
            'status': 'pass',
            'calls': [{'args': '((1, 2), (2, 3))', 'kwargs': '{}'}],
            'input_keys': ['base0'],
            'coverage': {
                'lines': [1, 2, 4, 5, 7],
                'arcs': [[-1, 2], [2, 4], [4, 5], [5, 7], [7, -1]],
            },
        }

    def fake_executor(task_row, code, inputs, *, timeout=8, base=False):
        if base:
            return {'status': 'ok', 'tests': [{'status': 'ok'}]}
        builder = CallBuilder.for_source(task_row['declaration'], task_row['entry_point'])
        ns = {}
        exec(code, ns)
        fn = ns[task_row['entry_point']]
        tests = []
        for arguments in inputs:
            call = builder.build(arguments)
            val = fn(*eval(call['args']), **eval(call['kwargs']))
            tests.append({'status': 'ok', 'value': list(val) if isinstance(val, tuple) else val})
        return {'status': 'ok', 'tests': tests}

    class FixtureCalls:
        model_id = 'fixture'

        def __init__(self):
            self.cf_payloads = []

        def token_count(self, messages):
            return 100

        def complete(self, number, arm_name, messages, **kwargs):
            if arm_name == 'plain':
                return ModelResponse(json.dumps({
                    'inputs': [{'arguments': {
                        'a': {'__python_type__': 'tuple', 'items': [1]},
                        'b': {'__python_type__': 'tuple', 'items': [1]},
                    }}]
                }), finish_reason='stop')
            payload = json.loads(messages[-1]['content'])
            self.cf_payloads.append(payload)
            target = next(t for t in payload['targets'] if t['line'] == 6)
            return ModelResponse(json.dumps({
                'concepts': [{
                    'id': 'multi_shared',
                    'target_id': target['id'],
                    'name': 'Multiple shared elements',
                    'input_relation': 'a and b share at least 2 values',
                    'instruction': 'Provide two tuples sharing 2 elements.',
                    'evidence_lines': [2, 4, 5, 6],
                    'predicate': '',
                    'strategies': {},
                }],
                'inputs': [{
                    'arguments': {
                        'a': {'__python_type__': 'tuple', 'items': [1, 2, 3]},
                        'b': {'__python_type__': 'tuple', 'items': [2, 3, 4]},
                    },
                    'concept_id': 'multi_shared',
                }],
            }), finish_reason='stop')

    def make_cf_4tool():
        arm = ControlFlowFourToolArm(ControlFlowSettings(rounds=1), tool_runs_dir=tools_dir)
        def fake_trace(ctx, program, records):
            out = []
            for rec in records:
                if rec['args'] == '((), (1,))':
                    out.append({'domain': 'valid', 'status': 'executed', 'coverage': {
                        'lines': [1, 2, 3], 'arcs': [[-1, 2], [2, 3], [3, -1]],
                    }})
                else:
                    out.append({'domain': 'valid', 'status': 'executed', 'coverage': {
                        'lines': [1, 2, 4, 5, 6], 'arcs': [[-1, 2], [2, 4], [4, 5], [5, 6], [6, -1]],
                    }})
            return out
        arm.trace = fake_trace
        return arm

    store = ArtifactStore(tmp_path / 'mbpp_run')
    calls = FixtureCalls()
    config = {
        'dataset': 'mbpp',
        'task_numbers': [2],
        'arms': ['plain', 'control_flow_4tool'],
        'context_tokens': 40960,
        'completion_tokens': 8192,
        'tool_runs_dir': str(tools_dir),
    }
    result = run_benchmark(
        [task], cohort, store, config,
        calls=calls,
        executor=fake_executor,
        base_tracer=fake_base_tracer,
        arm_factories={'control_flow_4tool': make_cf_4tool},
    )
    assert len(calls.cf_payloads) == 1
    # Branch line 3 was eliminated by crosshair input ((), (1,)), leaving ONLY line 6 / arc [5, 6].
    assert {t['id'] for t in calls.cf_payloads[0]['targets']} == {'p0:C1:6', 'p0:C2:5:6'}
    assert result['arms']['plain']['detected'] == 0
    assert result['arms']['control_flow_4tool']['detected'] == 1
    assert result['control_flow_4tool']['base_targets_before_4tool'] == 4
    assert result['control_flow_4tool']['residual_targets_after_4tool'] == 2
    assert result['control_flow_4tool']['targets_eliminated_by_4tool'] == 2

    # Read-only replay must match identically with zero native/model calls.
    replay = run_benchmark(
        [task], cohort, ArtifactStore(store.directory, read_only=True), config,
        executor=lambda *a, **k: pytest.fail('executor called during replay'),
        base_tracer=lambda *a, **k: pytest.fail('base_tracer called during replay'),
    )
    assert replay == result
