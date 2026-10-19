"""Offline runner checks only; no HTTP/model/native or canonical execution."""
import copy
import json
from pathlib import Path
import pytest
from . import run


def fixture_packet():
    task = run.source_view.prepare('def f(x):\n    y=x+1\n    z=y+1\n    w=z+1\n    return w\n', 'f')
    ids = list(run.new_cfg.build(task)['nodes'])
    return dict(case='0', task=task, concepts=[dict(id='O1', statement='sample relation', relation='sample relation')],
                hypotheses=[dict(id='H1', source_ids=ids, obligation_ids=['O1'], statement='sample hypothesis')],
                common=[], common_traces={})


class FakeClient:
    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        ctx = json.loads(request['messages'][1]['content'])['context']
        if request['stage'] == 'final':
            body = dict(tests=[], reason='fixture only')
        else:
            new = 'Contract: ' in ctx['tool_protocol']
            body = dict(actions=[dict(tool='inspect_flow', ids=['L2', 'L3', 'L4', 'L5'] + ([] if new else ['ENTRY']))], reason='fixture only')
        return dict(text=json.dumps(body), finish_reason='stop', input_tokens=1, output_tokens=1)


def test_same_context_seed_independent_history_and_resume(tmp_path):
    p = fixture_packet()
    run.paired_context_assertion(p, tmp_path)
    clients = [FakeClient(), FakeClient()]
    old = run.run_arm(p, run.ARMS[0], tmp_path, clients[0])
    new = run.run_arm(p, run.ARMS[1], tmp_path, clients[1])
    assert [r['seed'] for r in clients[0].requests] == [r['seed'] for r in clients[1].requests]
    assert [r['slot'] for r in clients[0].requests] == ['0/old_contract/1', '0/old_contract/2', '0/old_contract/3']
    assert old['tool_report']['errors'] == 2 and new['tool_report']['errors'] == 0
    assert all(not r['final_executions'] for r in (old, new))
    assert clients[0].requests[1]['messages'] != clients[1].requests[1]['messages']
    count = len(clients[1].requests)
    assert run.run_arm(p, run.ARMS[1], tmp_path, clients[1]) == new
    assert len(clients[1].requests) == count
    assert not list(tmp_path.rglob('executions/*/job.json'))


def test_bad_reply_uses_fixed_remaining_slots_without_extra_call(tmp_path):
    class InvalidClient(FakeClient):
        def complete(self, request):
            self.requests.append(request)
            return dict(text='not JSON', finish_reason='stop', input_tokens=1, output_tokens=1)
    c = InvalidClient()
    result = run.run_arm(fixture_packet(), 'repaired_contract', tmp_path, c)
    assert len(c.requests) == 3 and len(result['calls']) == 3
    assert all(x['error'] for x in result['calls']) and not result['final_executions']
    assert all(r['feedback'][0]['status'] == 'reply_invalid' for r in result['rounds'])


def test_context_failure_stays_fatal_and_no_fake_result(tmp_path):
    class FailedClient:
        def complete(self, request):
            raise run.live.SlotFailure('context_budget_exceeded')
    with pytest.raises(run.live.SlotFailure):
        run.run_arm(fixture_packet(), 'repaired_contract', tmp_path, FailedClient())
    assert not list(tmp_path.rglob('result.json'))


def test_empty_report_preserves_all60_not_attempted(tmp_path):
    r = run.report(tmp_path)
    assert r['scheduled_slots'] == 60 and r['received'] == r['physical_attempts'] == 0
    assert len(r['slots']) == 60 and {x['state'] for x in r['slots']} == {'not_attempted'}


def test_freeze_covers_raw_responses_before_reporting_and_detects_mutation(tmp_path):
    run.write(tmp_path / 'protocol.json', {})
    response = tmp_path / 'transport/calls/0/old_contract/1/response.json'
    run.write(response, dict(text='fixture', input_tokens=1, output_tokens=1))
    run.write(tmp_path / 'packets/0.json', {})
    run.write(tmp_path / 'metadata_events.json', [])
    run.write(tmp_path / 'launches.json', [])
    manifest = run.freeze(tmp_path)
    assert str(response.relative_to(tmp_path)) in manifest
    assert 'metadata_events.json' in manifest and 'launches.json' in manifest
    run.verify_freeze(tmp_path)
    run.report(tmp_path)
    run.verify_freeze(tmp_path)
    run.write(response, dict(text='changed'))
    with pytest.raises(ValueError, match='generation_freeze_drift'):
        run.verify_freeze(tmp_path)


def test_native_attempt_accounting_is_durable_and_bounded(tmp_path, monkeypatch):
    calls = []
    def fake_sandbox(*args, **kwargs):
        calls.append(1)
        return dict(status='ok')
    monkeypatch.setattr(run.old_tools, 'sandbox', fake_sandbox)
    monkeypatch.setattr(run.new_tools, 'sandbox', fake_sandbox)
    job = tmp_path / 'job.json'
    run.write(job, dict(source='fixture only'))
    run.instrument_workers(tmp_path)
    for module in (run.old_tools, run.new_tools):
        module.sandbox('python', 'worker', job, tmp_path / 'out.json', 8)
    assert len(calls) == 2
    ledger = run.read(tmp_path / 'native_attempts.json')
    assert len(ledger) == 2 and {x['state'] for x in ledger} == {'returned'}
    run.write(tmp_path / 'native_attempts.json', [dict(state='returned')] * 840)
    with pytest.raises(ValueError, match='native_process_budget_exhausted'):
        run.old_tools.sandbox('python', 'worker', job, tmp_path / 'out.json', 8)
    assert len(calls) == 2


def test_terminal_transport_failure_stops_all_and_keeps_partial_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    p = fixture_packet()
    monkeypatch.setattr(run, 'prepare', lambda: ([p], dict(arm_order=[list(run.ARMS)])))
    monkeypatch.setattr(run, 'paired_context_assertion', lambda *args: None)
    monkeypatch.setattr(run, 'instrument_workers', lambda *args: None)
    monkeypatch.setenv('QWEN_BASE_URL', 'http://localhost:1')
    class OfflineFailure:
        def __init__(self, *args):
            raise run.live.SlotFailure('context_budget_exceeded')
    monkeypatch.setattr(run.live, 'Client', OfflineFailure)
    monkeypatch.setattr('sys.argv', ['diagnostic', 'run'])
    run.main()
    status = run.read(tmp_path / 'status.json')
    assert status['state'] == 'stopped_preflight_or_transport' and status['received'] == 0
    assert (tmp_path / 'partial_snapshot.json').exists() and not (tmp_path / 'generation_frozen.json').exists()
    assert {x['state'] for x in run.read(tmp_path / 'report.json')['slots']} == {'not_attempted'}


def test_cap_metric_only_counts_cap_rejections():
    action = dict(tool='inspect_flow', ids=['L2'] * 5)
    assert run.is_id_cap_error(action, dict(status='error', error='ids_shape_or_count'))
    assert run.is_id_cap_error(action, dict(status='error', error='action_schema:maxItems', error_details=dict(field='/ids')))
    for result in [dict(status='error', error='unknown_field'), dict(status='error', error='unknown_tool'),
                   dict(status='error', error='action_schema:maxItems', error_details=dict(field='/names'))]:
        assert not run.is_id_cap_error(action, result)


def test_cfg_equivalence_uses_structure_not_networkx_identity():
    task = fixture_packet()['task']
    a, b = run.old_cfg.build(task), run.new_cfg.build(task)
    assert a['graph'] is not b['graph'] and run.cfg_equivalent(a, b)
    b['graph'].remove_edge(*next(iter(b['graph'].edges())))
    assert not run.cfg_equivalent(a, b)
