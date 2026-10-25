"""Networkless engineering checks. Mock completions are never efficacy results."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import openai
import pytest

from . import ft_run, flow_run
from .context_preflight import check_request, preflight, token_count
from .openrouter_client import AccountingUnknown, BudgetExceeded, OpenRouterClient, WorkspacePaused
from .paths import CONFIG
from .run_v76 import V76Run, decision
from .seed_from_v31 import seed

HERE = Path(__file__).resolve().parent
PARENT = HERE.with_name('v34_ftplacebo')


def test_matched_source_prompts_schemas_arms_and_config():
    # Stronger than comparing a few prompt examples: every inherited source
    # except the two necessary transport/seeding files is byte-identical.
    manifest = json.loads((HERE / 'PARENT.json').read_text())['files']
    allowed = {'config.json', 'CHANGELOG.md', 'PREREG.md', 'PARENT.json', 'openrouter_client.py', 'seed_from_v31.py', 'run_openrouter.sh', 'paths.py', 'ft_run.py'}
    for rel in manifest:
        if rel not in allowed:
            assert (HERE / rel).read_bytes() == (PARENT / rel).read_bytes(), rel
    old = json.loads((PARENT / 'config.json').read_text())
    new = json.loads((HERE / 'config.json').read_text())
    for key in old:
        if key not in ('VERSION', 'K', 'openrouter', 'faulttemplate'):
            assert new[key] == old[key], key
    expected_ft = dict(old['faulttemplate'], reused_from_v31=['template-only', 'template-random', 'witness-only'])
    assert new['faulttemplate'] == expected_ft
    assert new['K'] == 1
    assert new['openrouter']['model'] == 'openai/gpt-oss-120b'
    for key in ('params', 'max_tokens', 'timeout_seconds'):
        assert new['openrouter'][key] == old['openrouter'][key]
    from ..v34_ftplacebo import flow_run as old_flow, ft_run as old_ft
    assert flow_run.SCHEMAS == old_flow.SCHEMAS
    assert ft_run.ARMS == old_ft.ARMS and ft_run.LLM_ARMS == old_ft.LLM_ARMS
    for stage in ('probe', 'final'):
        assert json.dumps(flow_run.message(flow_run.INSTR[stage], {'earlier_feedback': []}, stage)).encode() == json.dumps(old_flow.message(old_flow.INSTR[stage], {'earlier_feedback': []}, stage)).encode()


def test_all_297_historical_requests_fit_exact_tokenizer():
    result = preflight()
    assert result['requests'] == 297
    assert result['max_input_tokens'] + CONFIG['openrouter']['max_tokens'] <= result['context_length']
    messages = flow_run.message(flow_run.INSTR['probe'], {}, 'probe')
    assert check_request(messages) == token_count(messages)
    with patch.dict(CONFIG['openrouter'], context_length=CONFIG['openrouter']['max_tokens']):
        with pytest.raises(ValueError, match='exceeds_registered_context'):
            check_request(messages)


def test_seed_hashes_and_no_llm_results_reused(tmp_path):
    run = V76Run()
    run.cases = run.cases[:3]
    run.root = tmp_path
    records = seed(run)
    assert len(records) == 24
    for case in run.cases:
        for arm in ft_run.LLM_ARMS:
            assert not (tmp_path / 'cases' / case['case_id'] / 'arms' / arm / 'result.json').exists()
    seed(run)
    one = next(tmp_path.rglob('tool.json'))
    one.write_text('{}')
    with pytest.raises(ValueError, match='destination_drift'):
        seed(run)


class FakeClient:
    def __init__(self, cases):
        self.inputs = {c['case_id']: c['witnesses'][0] for c in cases}
        self.calls = []

    def complete(self, request):
        self.calls.append(request)
        literal = self.inputs[request['slot'].split('/')[1]]
        stage = request['stage']
        value = {'inputs': [{'arguments': literal, 'expected': '0', 'predicted_actual': '0', 'purpose': 'trigger'}], 'reason': 'CPU mock'} if stage == 'probe' else {'tests': [{'arguments': literal, 'expected': '0'}], 'reason': 'CPU mock'}
        return dict(text=json.dumps(value), input_tokens=1, output_tokens=1, cost_usd=0, finish_reason='stop')


@pytest.mark.parametrize('model', ['gpt-oss-120b','deepseek-v4-flash'])
def test_mock_end_to_end_three_real_cases(tmp_path,model):
    from .paths import select_model
    select_model(model)
    run = V76Run()
    run.cases = run.cases[:3]
    run.root = tmp_path
    run.client = FakeClient(run.cases)
    seed(run)
    with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        run.generate(workers=2)
        assert len(run.client.calls) == 27
        assert (tmp_path / 'generation_frozen.json').exists()
        for case in run.cases:
            for arm in ft_run.LLM_ARMS:
                record = json.loads((tmp_path / 'cases' / case['case_id'] / 'arms' / arm / 'result.json').read_text())
                assert len(record['calls']) == 3 and len(record['rounds']) == 2
                assert record['rounds'][0]['feedback'] and record['rounds'][1]['feedback']
        report = ft_run.score(run)
        assert set(report['arms']) == set(ft_run.ARMS)
        assert all(report['arms'][a]['calls'] == 9 for a in ft_run.LLM_ARMS)
        run.generate(workers=2)
        assert len(run.client.calls) == 27  # completed slots cannot resample
    select_model('gpt-oss-120b')


def sdk_response(cost=.001, text='{"tests":[],"reason":"unknown"}', finish='stop', usage=True):
    data = dict(prompt_tokens=100, completion_tokens=30, cost=cost, completion_tokens_details={'reasoning_tokens': 10})
    return SimpleNamespace(id='fake-id', usage=SimpleNamespace(model_dump=lambda: data) if usage else None,
                           model='openai/gpt-oss-120b', provider='fake', model_extra={},
                           choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason=finish)])


@pytest.fixture
def transport(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fake-cpu-only')
    monkeypatch.setenv('OPENROUTER_MODEL', CONFIG['openrouter']['model'])
    monkeypatch.setenv('OPENROUTER_MAX_USD', '3')
    monkeypatch.delenv('OPENROUTER_BASE_URL', raising=False)
    sdk = Mock()
    sdk.chat.completions.create.return_value = sdk_response()
    with patch('openai.OpenAI', return_value=sdk):
        client = OpenRouterClient(tmp_path)
        try:
            yield client, sdk
        finally:
            client.close()


def req(slot='vibepass_half/3/plain/round1'):
    return dict(slot=slot, stage='probe', seed=1, messages=flow_run.message(flow_run.INSTR['probe'], {}, 'probe'))


def test_transport_cache_payload_accounting_and_concurrency(transport):
    client, sdk = transport
    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(lambda _: client.complete(req()), range(3)))
    assert sdk.chat.completions.create.call_count == 1
    assert results[0] == results[1]
    body = sdk.chat.completions.create.call_args.kwargs
    assert body['extra_body']['provider'] == CONFIG['openrouter']['provider']
    assert body['extra_body']['reasoning']['effort'] == 'low'
    assert client.spent() == .001
    assert len(client.ledger()['entries']) == 1


def test_budget_reserves_before_dispatch_and_clamps_env(transport, monkeypatch):
    client, sdk = transport
    client.max_usd = .000001  # less than any full-context reservation
    with pytest.raises(BudgetExceeded):
        client.complete(req())
    sdk.chat.completions.create.assert_not_called()
    client.close()
    monkeypatch.setenv('OPENROUTER_MAX_USD', '30')
    with patch('openai.OpenAI', return_value=Mock()):
        other = OpenRouterClient(client.root)
        assert other.max_usd == 3
        other.close()


def test_missing_usage_and_transport_unknown_stop_paid_calls(transport):
    client, sdk = transport
    sdk.chat.completions.create.return_value = sdk_response(usage=False)
    with pytest.raises(AccountingUnknown):
        client.complete(req())
    with pytest.raises(AccountingUnknown):
        client.complete(req('vibepass_half/3/plain/round2'))
    assert sdk.chat.completions.create.call_count == 1
    assert next(iter(client.ledger()['entries'].values()))['state'] == 'unknown'


def test_incomplete_attempts_all_charged_and_capped(transport):
    client, sdk = transport
    sdk.chat.completions.create.return_value = sdk_response(text='', finish='length')
    result = client.complete(req())
    assert sdk.chat.completions.create.call_count == 1 and result['attempts'] == 1
    assert client.spent() == .001
    assert len(client.ledger()['entries']) == 1


def test_403_is_zero_cost_pause_without_retry(transport):
    client, sdk = transport
    response = httpx.Response(403, request=httpx.Request('POST', 'https://openrouter.ai/api/v1/chat/completions'))
    sdk.chat.completions.create.side_effect = openai.PermissionDeniedError('fake denied', response=response, body=None)
    with pytest.raises(WorkspacePaused):
        client.complete(req())
    with pytest.raises(AccountingUnknown):
        client.complete(req('vibepass_half/3/plain/round2'))
    assert client.spent() == 0
    assert sdk.chat.completions.create.call_count == 1
    assert next(iter(client.ledger()['entries'].values()))['state'] == 'workspace_403'


def test_primary_rule_and_ceiling_override():
    report = {'pairs': {'fault-template vs template-placebo': {'detection': {'wins': ['a', 'b'], 'losses': ['c']}}},
              'arms': {'plain': {'tasks_confirmed': 27}, 'fault-template': {'false_alarms': 2}, 'template-placebo': {'false_alarms': 2}}}
    assert decision(report)['verdict'] == 'concept adds value'
    report['arms']['fault-template']['false_alarms'] = 3
    assert decision(report)['verdict'] == 'rule not met'
    report['arms']['plain']['tasks_confirmed'] = 28
    assert decision(report)['verdict'] == 'ceiling, uninformative about concepts'


def test_unknown_reservation_survives_client_restart(transport):
    client, sdk = transport
    sdk.chat.completions.create.side_effect = RuntimeError('fake transport failure')
    with pytest.raises(AccountingUnknown):
        client.complete(req())
    client.close()
    with patch('openai.OpenAI', return_value=sdk):
        other = OpenRouterClient(client.root)
        try:
            with pytest.raises(AccountingUnknown):
                other.complete(req('vibepass_half/3/plain/round2'))
            assert sdk.chat.completions.create.call_count == 1
        finally:
            other.close()


def test_resume_archives_outside_pipeline_and_preserves_paid_attempts(tmp_path):
    run = V76Run()
    run.cases = run.cases[:1]
    run.root = tmp_path / 'runs/vibepass_half'
    cid = run.cases[0]['case_id']
    arm = run.root / 'cases' / cid / 'arms/plain'
    (arm / 'tools').mkdir(parents=True)
    (arm / 'tools/ledger.json').write_text('{"old":"partial round"}')
    transport_dir = run.root / 'transport/calls/vibepass_half' / cid / 'plain/round1'
    transport_dir.mkdir(parents=True)
    attempts = [{'state': 'incomplete', 'response': {'cost_usd': .1}}, {'state': 'workspace_403'}]
    (transport_dir / 'attempts.json').write_text(json.dumps(attempts))
    (transport_dir / 'request.json').write_text('{"cached":true}')
    # Execute exactly the CPU maintenance heredoc shipped in the launcher;
    # neither the credential source nor --launch is executed by this test.
    script = (HERE / 'run_openrouter.sh').read_text()
    maintenance = script.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
    with patch('trickcatcher_linefacts.pipelines.v76_ossmodel.run_v76.V76Run', return_value=run):
        exec(compile(maintenance, 'run_openrouter.sh:maintenance', 'exec'), {})
    assert not (arm / 'tools/ledger.json').exists()
    archives = list((run.root.parent / 'resume_archives').iterdir())
    assert len(archives) == 1
    assert (archives[0] / 'cases' / cid / 'arms/plain/tools/ledger.json').exists()
    assert len(json.loads((archives[0] / (transport_dir / 'attempts.json').relative_to(run.root)).read_text())) == 2
    assert json.loads((transport_dir / 'attempts.json').read_text()) == attempts[:1]
    assert (transport_dir / 'request.json').read_text() == '{"cached":true}'
