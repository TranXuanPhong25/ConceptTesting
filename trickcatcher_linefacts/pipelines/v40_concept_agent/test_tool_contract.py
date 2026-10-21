"""Contract disclosure, charging, corrective feedback and CPU-only guard regressions."""
import copy
import importlib
import json
from pathlib import Path
import subprocess
import pytest
from . import flow_tools as ft, flow_packages as fp, tool_contract as tc, flow_run, source_view
from .paths import CONFIG

SOURCE = 'def f(x):\n    y = x + 1\n    z = y + 2\n    w = z + 3\n    return w\n'


def session(tmp_path):
    s = ft.FlowSession(source_view.prepare(SOURCE, 'f'), tmp_path, arm='agent-tools')
    s.begin_round()
    return s


@pytest.mark.parametrize('tool', ['inspect_flow', 'inspect_data', 'replay_input'])
def test_ids_four_allowed_five_rejected_and_replay_charge(tmp_path, tool):
    s = session(tmp_path)
    base = dict(tool=tool, ids=['L2', 'L3', 'L4', 'L5'])
    if tool == 'replay_input':
        base['input'] = '(1,)'
    tc.validate(base)
    over = dict(base, ids=base['ids'] + ['ENTRY'])
    r = s.act(over)
    assert r['status'] == 'error'
    assert r['error_details']['field'] == '/ids' and r['error_details']['limit'] == 4
    assert s.actions == 1 and s.executions == int(tool == 'replay_input') and s.executor.physical == 0
    if tool != 'replay_input':
        assert s.act(base)['status'] == 'ok'


def test_tolerant_envelope_preserves_valid_sibling_and_corrective_round(tmp_path):
    s = session(tmp_path)
    actions = [dict(tool='inspect_flow', ids=['L2']), dict(tool='inspect_flow', ids=['L2'] * 5)]
    # Outer parse remains object-shaped; dispatch is strict per slot.
    reply = flow_run.validate('agent', json.dumps(dict(actions=actions, reason='inspect')))
    results = [s.act(a) for a in reply['actions']]
    assert [r['status'] for r in results] == ['ok', 'error'] and s.actions == 2
    assert results[1]['error_details']['action'] == 2 and results[1]['error_details']['round'] == 1
    s.begin_round()
    assert s.act(dict(tool='inspect_flow', ids=['L2'] * 4))['status'] == 'ok'
    assert s.actions == 3 and s.executor.physical == 0


@pytest.mark.parametrize('value,ok', [(1, True), (1.0, False), (True, False), (-1, False), (4, False)])
def test_exact_integer_radius(tmp_path, value, ok):
    r = session(tmp_path).act(dict(tool='inspect_flow', ids=['L2'], radius=value))
    assert (r['status'] == 'ok') is ok


@pytest.mark.parametrize('bad', [True, 2.0, {}, ['L2']])
def test_invalid_id_type_is_a_typed_error(tmp_path, bad):
    r = session(tmp_path).act(dict(tool='inspect_flow', ids=[bad]))
    assert r['status'] == 'error' and r['error_details']['constraint'] == 'anyOf'


def test_required_fields_names_and_path_caps():
    for value in [dict(tool='check_path', trace='T1', sequence=['L2'] * 64),
                  dict(tool='inspect_data', names=['x'] * 4),
                  dict(tool='inspect_data', ids=None, names=['x']),
                  dict(tool='replay_input', input='(1,)', ids=None, names=None, hypothesis=None)]:
        tc.validate(value)
    for value, field, limit in [
        (dict(tool='check_path', trace='T1', sequence=['L2'] * 65), '/sequence', 64),
        (dict(tool='inspect_data', names=['x'] * 5), '/names', 4),
        (dict(tool='inspect_data', names=['x' * 65]), '/names/0', 64),
        (dict(tool='replay_input'), '/input', None),
    ]:
        with pytest.raises(tc.ActionError) as error:
            tc.validate(value)
        assert error.value.details['field'] == field
        assert error.value.details.get('limit') == limit
    for bad in [dict(tool='inspect_data'), dict(tool='inspect_data', ids=[], names=[]),
                dict(tool='inspect_data', names=False), dict(tool='inspect_data', ids='')]:
        with pytest.raises(tc.ActionError):
            tc.validate(bad)


def test_replay_reservation_precedence_and_generic_errors(tmp_path):
    s = session(tmp_path)
    tests = [dict(tool='replay_input', ids=['L2'] * 5, input='(1,)'),
             dict(tool='replay_input'), dict(tool='replay_input', input='(1,)', names=5),
             dict(tool='replay_input', input='(1,)', unexpected=True),
             dict(tool='replay_input', input='(1,)', hypothesis=4),
             dict(tool=['replay_input'], input='(1,)')]
    for a in tests:
        assert s.act(a)['status'] == 'error'
    assert s.executions == 3 and s.actions == 6 and s.executor.physical == 0
    assert s.act(dict(tool='inspect_flow', ids=['L2']))['error'] == 'action_budget_exhausted'
    s.begin_round()
    s.executions = CONFIG['flowtools']['max_execution_requests']
    r = s.act(dict(tool='replay_input', input='(1,)'))
    assert r['error'] == 'execution_budget_exhausted' and not r['charges']


def test_unknown_source_trace_and_safe_errors(tmp_path):
    s = session(tmp_path)
    a = s.act(dict(tool='inspect_flow', ids=['not-source'], hypothesis='H1'))
    b = s.act(dict(tool='check_path', trace='not-trace', sequence=['L2', 'L3']))
    c = s.act(dict(tool='inspect_flow', ids=['L2'], **{'private_malformed_key': 'do not echo'}))
    assert a['error_details']['field'] == '/ids' and a['error_details']['hypothesis'] == 'H1'
    assert b['error_details']['field'] == '/trace'
    assert 'private_malformed_key' not in json.dumps(c) and 'do not echo' not in json.dumps(c)


def test_prompt_schema_dispatch_match_and_defaults_do_not_modify_request(tmp_path):
    contract = json.loads(fp.TOOL_PROTOCOL.split('Contract: ', 1)[1])
    assert contract['tools'] == tc.action_schemas()
    assert contract['tools']['check_path']['properties']['sequence']['maxItems'] == 64
    s = session(tmp_path)
    request = dict(tool='inspect_flow', ids=['L2'])
    original = copy.deepcopy(request)
    assert s.act(request)['status'] == 'ok'
    assert request == original == s.log[-1]['request']['action']


def test_error_feedback_after_third_slot_survives_history_projection():
    feedback = [dict(status='ok', nodes='x' * 5000) for _ in range(3)]
    feedback += [dict(status='error', error='action_schema:maxItems',
                      error_details=dict(code='action_schema:maxItems', field='/ids', limit=4, action=4, round=1))]
    h = [dict(round=1, feedback=feedback)]
    projected = tc.project_history(h)
    assert len(projected[0]['feedback']) == 3 and projected[0]['omitted'] == 1
    assert projected[0]['error_digest'][0]['action'] == 4
    assert projected[0]['error_digest'][0]['limit'] == 4
    assert tc.project_history(projected) == projected


def test_resume_reconstructs_error_charges_and_rejects_request_drift(tmp_path):
    a = dict(tool='replay_input', input='(1,)', ids=['L2'] * 5, hypothesis='H1')
    first = session(tmp_path)
    error = first.act(a)
    old = (tmp_path / 'ledger.json').read_bytes()
    second = session(tmp_path)
    assert second.act(a) == error and second.actions == second.executions == 1
    assert (tmp_path / 'ledger.json').read_bytes() == old
    third = session(tmp_path)
    with pytest.raises(ValueError, match='ledger_replay_drift'):
        third.act(dict(a, ids=['L2']))


def test_clients_and_all_generation_clis_are_disabled_before_transport(tmp_path, monkeypatch):
    from . import flow_client, llm_client
    def forbidden(*args, **kwargs):
        raise AssertionError('transport constructed')
    monkeypatch.setattr(flow_client.httpx, 'Client', forbidden)
    monkeypatch.setattr(llm_client.urllib.request, 'build_opener', forbidden)
    for factory in [lambda: flow_client.Client(tmp_path / 'online'),
                    lambda: llm_client.Client(tmp_path / 'legacy', offline=False)]:
        with pytest.raises(RuntimeError, match='v30 CPU-only'):
            factory()
    assert not (tmp_path / 'online').exists() and not (tmp_path / 'legacy').exists()
    package = __package__
    for name in ['run', 'run_gen', 'run_v4', 'generate', 'flow_run']:
        module = importlib.import_module(package + '.' + name)
        with pytest.raises(SystemExit, match='v30 CPU-only'):
            module.main()
    root = Path(__file__).resolve().parents[3]
    for name in ('run_v6', 'offline'):
        result = subprocess.run([CONFIG['V4_PYTHON'], '-B', '-m', 'trickcatcher_linefacts.pipelines.v30_flowcontract.' + name],
                                cwd=root, capture_output=True, text=True, timeout=10)
        assert result.returncode and 'v30 CPU-only' in result.stderr
    assert not CONFIG['flowtools']['online_enabled'] and not CONFIG['flowrun']['online_enabled']


@pytest.mark.parametrize('kind', ['deep_string', 'deep_host', 'non_json', 'non_string_key'])
def test_unrepresentable_actions_get_logged_errors_and_resume(tmp_path, kind):
    if kind == 'deep_string':
        action = '[' * 1800 + '0' + ']' * 1800
    elif kind == 'deep_host':
        action = 0
        for _ in range(5000):
            action = {'nested': action}
    elif kind == 'non_json':
        action = dict(tool='inspect_data', names={'a', 'b'})
    else:
        action = {1: 'unsupported key'}
    first = session(tmp_path)
    result = first.act(action)
    assert result['status'] == 'error' and first.actions == 1 and first.executor.physical == 0
    old = (tmp_path / 'ledger.json').read_bytes()
    second = session(tmp_path)
    assert second.act(action) == result and second.actions == 1
    assert (tmp_path / 'ledger.json').read_bytes() == old


def test_generic_error_fields_limits_and_literal_disclosure(tmp_path):
    s = session(tmp_path)
    too_long = s.act(' ' * (CONFIG['flowtools']['max_action_chars'] + 1))
    assert too_long['error_details']['field'] == ''
    assert too_long['error_details']['limit'] == CONFIG['flowtools']['max_action_chars']
    bad_hyp = s.act(dict(tool='inspect_flow', ids=['L2'], hypothesis={}))
    assert bad_hyp['error_details']['field'] == '/hypothesis'
    extra = s.act(dict(tool='inspect_flow', ids=['L2'], secret_key=1))
    assert extra['error_details']['field'] == '/unknown_field'
    # Short in characters but over UTF8-byte limit; central schema permits it, literal parser rejects it.
    unicode_input = repr(('é' * 600,))
    assert len(unicode_input) < CONFIG['chain']['max_input_chars'] < len(unicode_input.encode())
    r = s.act(dict(tool='replay_input', input=unicode_input))
    assert r['status'] == 'error' and r['error_details']['field'] == '/input'
    assert r['error_details']['limit'] == dict(UTF8_bytes=CONFIG['chain']['max_input_chars'])
    assert s.executions == 1 and s.executor.physical == 0
    protocol = json.loads(fp.TOOL_PROTOCOL.split('Contract: ', 1)[1])
    assert protocol['literal_limits']['max_input_nodes'] == CONFIG['chain']['max_input_nodes']
    assert protocol['literal_limits']['max_input_depth'] == CONFIG['chain']['max_input_depth']
    assert protocol['literal_limits']['max_items'] == CONFIG['chain']['max_items']
    assert protocol['integer_bits'] == 4096 and 'tuple' in protocol['input_format']
    assert ft.TOOLS == {name: set(schema['properties']) for name, schema in protocol['tools'].items()}


def test_cache_integrity_failure_is_not_reclassified_as_action_error(tmp_path):
    class DriftExecutor:
        physical = cache_hits = 0

        def run(self, *args):
            raise ValueError('execution_cache_drift')

    s = ft.FlowSession(source_view.prepare(SOURCE, 'f'), tmp_path, arm='agent-tools', executor=DriftExecutor())
    s.begin_round()
    with pytest.raises(ValueError, match='execution_cache_drift'):
        s.act(dict(tool='replay_input', input='(1,)'))
    ledger = json.loads((tmp_path / 'ledger.json').read_text())
    assert [r['type'] for r in ledger['events']] == ['round']
    assert 'action_serialization' not in json.dumps(ledger)


def test_deep_dictionary_inside_json_string_has_typed_error(tmp_path):
    action = '{"tool":"inspect_flow","ids":' + '[' * 1200 + '"L2"' + ']' * 1200 + '}'
    s = session(tmp_path)
    r = s.act(action)
    assert r['status'] == 'error' and s.actions == 1 and s.executor.physical == 0
    assert len(s.log) == 2
