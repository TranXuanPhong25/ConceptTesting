"""P1 CPU checks for flow services, tracing, tool budgets and packages. Fixtures are hand-written; no Qwen claims."""
import json
import pytest
from . import source_view as sv, flow_cfg, flow_trace, flow_tools, flow_packages
from .paths import CONFIG

F = CONFIG['flowtools']
LOOP = '''def f(xs, k):
    """Sum non-negative values up to k."""
    total = 0
    for x in xs:
        if x < 0:
            continue
        if x > k:
            break
        total += x
    else:
        total = -1
    while total > 10:
        total -= 3
    return total
'''


def task(src, entry='f'):
    return sv.prepare(src, entry)


def node(cfg, key):
    hits = [n for n in cfg['nodes'] if key in n]
    assert len(hits) == 1, (key, hits)
    return hits[0]


def edge(cfg, a, b):
    return flow_cfg.edge_lookup(cfg)[(a, b)]


@pytest.fixture
def session(tmp_path):
    def make(src, arm='agent-tools', entry='f'):
        return flow_tools.FlowSession(task(src, entry), tmp_path / arm, arm=arm)
    return make


# ---- CFG -------------------------------------------------------------------------------------------------------
def test_loop_cfg_edges_break_continue_else():
    cfg = flow_cfg.build(task(LOOP))
    assert cfg['supported']
    loop, cont, brk, els, wh = (node(cfg, k) for k in (':For:', ':Continue:', ':Break:', ':Assign:11:', ':While:'))
    assert edge(cfg, cont, loop)['label'] == 'continue'
    assert edge(cfg, brk, wh)['label'] == 'break'
    assert edge(cfg, loop, els)['label'] == 'exhausted'
    assert (brk, els) not in flow_cfg.edge_lookup(cfg)  # break skips loop-else
    assert edge(cfg, wh, node(cfg, ':Return:'))['label'] == 'false'
    assert edge(cfg, node(cfg, ':Return:'), flow_cfg.EXIT)['label'] == 'return'
    assert {'source': node(cfg, ':If:5:'), 'label': 'true'} in cfg['control_dependence'][cont]


def test_early_return_unreachable_and_fall_off_end():
    src = '''def f(x):
    if x:
        return 1
        y = 2
    x += 1
'''
    cfg = flow_cfg.build(task(src))
    assert not cfg['nodes'][node(cfg, ':Assign:4:')]['reachable']
    assert cfg['nodes'][node(cfg, ':AugAssign:')]['reachable']
    assert edge(cfg, node(cfg, ':AugAssign:'), flow_cfg.EXIT)['label'] == 'fall_off_end'
    assert node(cfg, ':Assign:4:') not in cfg['control_dependence']


def test_while_true_has_no_false_edge_and_raise_exit():
    src = '''def f(n):
    while True:
        if n > 3:
            raise ValueError(n)
        n += 1
        if n == 3:
            return n
'''
    cfg = flow_cfg.build(task(src))
    wh = node(cfg, ':While:')
    assert all(e['source'] != wh or e['label'] == 'true' for e in cfg['edges'])
    assert edge(cfg, node(cfg, ':Raise:'), flow_cfg.RAISE_EXIT)['label'] == 'raise'
    assert cfg['control_dependence'] is not None


def test_infinite_loop_without_exit_makes_control_dependence_unknown():
    src = '''def f(n):
    while True:
        n += 1
'''
    cfg = flow_cfg.build(task(src))
    assert cfg['supported'] and cfg['control_dependence'] is None and cfg['control_dependence_scope'] == 'unknown'


@pytest.mark.parametrize('body', ['    try:\n        return 1\n    except Exception:\n        return 2\n',
                                  '    def g():\n        return 1\n    return g()\n',
                                  '    with open(x) as h:\n        return 1\n',
                                  '    yield x\n'])
def test_unsupported_constructs_fail_closed(body):
    cfg = flow_cfg.build(task('def f(x):\n' + body))
    assert not cfg['supported'] and cfg['nodes'] == {} and cfg['unsupported']


def test_expression_limits_and_data_facts():
    src = '''def f(xs, d):
    ys = [x for x in xs if x]
    d['k'] = len(ys) or 0
    return ys
'''
    cfg = flow_cfg.build(task(src))
    comp = cfg['nodes'][node(cfg, ':Assign:2:')]
    assert 'nested_expression_scope_not_modeled' in comp['limits']
    assert comp['data']['reads'] == ['xs'] and comp['data']['writes'] == ['ys']
    store = cfg['nodes'][node(cfg, ':Assign:3:')]
    assert store['data']['heap_writes_through'] == ['d'] and 'call_semantics_and_effects_unknown' in store['limits']
    assert store['data']['reaching_definitions'] == 'unknown'


def test_unicode_byte_columns_match_source_view_ids():
    src = 'def f(s):\n    t = "平平"; u = s\n    return t + u\n'
    t = task(src)
    cfg = flow_cfg.build(t)
    ids = {n['id'] for n in t['nodes']}
    assert set(cfg['nodes']) <= ids
    assert any(':Assign:2:18:' in n for n in cfg['nodes'])  # UTF-8 byte column (character column would be 14)


# ---- tracing / tools -----------------------------------------------------------------------------------------
def test_replay_trace_edges_and_ordered_paths(session):
    s = session(LOOP)
    cfg = s.cfg
    s.begin_round()
    r = s.act(dict(tool='replay_input', input='([1, -2, 3, 20], 5)', ids=[s.forward[node(cfg, ':Continue:')], s.forward[node(cfg, ':Assign:11:')]]))
    assert r['status'] == 'ok' and r['native_checked'] and r['output'] == '4'
    reach = {x['id']: x['reach'] for x in r['reach']}
    assert reach[node(cfg, ':Continue:')] == 'observed' and reach[node(cfg, ':Assign:11:')] == 'not_observed'
    brk = edge(cfg, node(cfg, ':Break:'), node(cfg, ':While:'))['id']
    assert brk in r['edges_covered']
    a, b = node(cfg, ':If:5:'), node(cfg, ':Continue:')
    assert s.act(dict(tool='check_path', trace=r['trace'], sequence=[s.forward[a], s.forward[b]]))['path'] == 'observed'
    # Reverse order is not a CFG edge sequence: typed error, slot consumed.
    bad = s.act(dict(tool='check_path', trace=r['trace'], sequence=[s.forward[b], s.forward[a]]))
    assert bad['status'] == 'error' and bad['error'].startswith('path:not_a_cfg_edge_sequence')
    assert s.report()['actions'] == 3


def test_same_line_statements_break_proof_segments(session):
    s = session('def f(x):\n    if x: return 1\n    return 2\n')
    s.begin_round()
    r = s.act(dict(tool='replay_input', input='(1,)', ids=[s.forward[node(s.cfg, ':Return:2:')]]))
    assert r['reach'][0]['reach'] == 'unknown' and not r['all_invocations_proven']
    assert r['trace_summary']['breaks'] >= 1


def test_recursion_keeps_invocations_separate(session):
    src = '''def f(n):
    if n <= 0:
        return 0
    return n + f(n - 1)
'''
    s = session(src)
    s.begin_round()
    r = s.act(dict(tool='replay_input', input='(2,)'))
    proj = s.traces[r['trace']]['projection']
    assert [i['inv'] for i in proj['invocations']] == [1, 2, 3] and proj['all_invocations_proven']
    base, rec = node(s.cfg, ':Return:3:'), node(s.cfg, ':Return:4:')
    # Base-case return and recursive return never appear contiguous inside one invocation.
    assert s.act(dict(tool='check_path', trace=r['trace'], sequence=[s.forward[node(s.cfg, ':If:')], s.forward[base]]))['path'] == 'observed'
    assert s.act(dict(tool='check_path', trace=r['trace'], sequence=[s.forward[base], s.forward[rec]]))['status'] == 'error'


def test_exceptions_explicit_raise_and_implicit(session):
    src = '''def f(x):
    if x < 0:
        raise ValueError("neg")
    return 10 // x
'''
    s = session(src)
    s.begin_round()
    raised = s.act(dict(tool='replay_input', input='(-1,)'))
    assert raised['execution_status'] == 'exception' and raised['exception_type'] == 'ValueError' and raised['native_checked']
    assert edge(s.cfg, node(s.cfg, ':Raise:'), flow_cfg.RAISE_EXIT)['id'] in raised['edges_covered']
    implicit = s.act(dict(tool='replay_input', input='(0,)'))
    assert implicit['exception_type'] == 'ZeroDivisionError' and not implicit['all_invocations_proven']


def test_input_mutation_is_recorded_and_native_agrees(session):
    s = session('def f(xs):\n    xs.append(1)\n    return len(xs)\n')
    s.begin_round()
    r = s.act(dict(tool='replay_input', input='([0],)'))
    assert r['native_checked'] and r['output'] == '2'


def test_trace_truncation_is_explicit_unknown(session):
    s = session('def f(n):\n    t = 0\n    for i in range(n):\n        t += i\n    return t\n')
    s.begin_round()
    r = s.act(dict(tool='replay_input', input='(%d,)' % F['max_events'], ids=[s.forward[node(s.cfg, ':Return:')]]))
    assert r['native_checked'] and not r['trace_complete']
    assert r['reach'][0]['reach'] in ('observed', 'unknown')
    assert s.traces[r['trace']]['projection']['truncated']


def test_snapshots_are_bounded_and_labeled(session):
    s = session('def f(s):\n    t = s * 2\n    return t\n')
    s.begin_round()
    r = s.act(dict(tool='replay_input', input="('x' * 0 + '%s',)" % ('a' * 300), ids=[s.forward[node(s.cfg, ':Return:')]], names=['t']))
    assert r['status'] == 'error' and r['error'].startswith('input:')  # expressions are not literals
    r = s.act(dict(tool='replay_input', input="('%s',)" % ('a' * 300), ids=[s.forward[node(s.cfg, ':Return:')]], names=['t']))
    snap = r['snapshots'][0]
    assert snap['kind'] == 'pre_statement_locals' and snap['values']['t']['capture'] == 'truncated'
    assert len(snap['values']['t']['repr'].encode()) <= F['snapshot_bytes']


def test_invalid_actions_consume_budget_and_rounds_are_capped(session):
    s = session(LOOP)
    s.begin_round()
    errors = [s.act('not json'), s.act({'tool': 'shell', 'cmd': 'ls'}), s.act({'tool': 'inspect_flow', 'ids': ['N1'], 'extra': 1}),
              s.act({'tool': 'inspect_flow', 'ids': ['nope']}), s.act({'tool': 'check_path', 'trace': 'T9', 'sequence': ['N1']}),
              s.act({'tool': 'replay_input', 'input': '[1]'})]
    assert [e['status'] for e in errors] == ['error'] * 6
    assert s.act({'tool': 'inspect_flow', 'ids': ['ENTRY']}) == dict(status='refused', error='action_budget_exhausted')
    assert s.report()['execution_requests'] == 1  # the invalid replay still used an execution slot
    s.begin_round()
    with pytest.raises(ValueError):
        s.begin_round()


def test_resume_replays_log_and_rejects_drift(tmp_path):
    t = task(LOOP)
    a = flow_tools.FlowSession(t, tmp_path / 'arm', arm='agent-tools')
    a.begin_round()
    first = a.act(dict(tool='replay_input', input='([1], 5)'))
    b = flow_tools.FlowSession(t, tmp_path / 'arm', arm='agent-tools')
    b.begin_round()
    again = b.act(dict(tool='replay_input', input='([1], 5)'))
    assert again == first and b.executor.physical == 0 and b.report()['execution_requests'] == 1
    c = flow_tools.FlowSession(t, tmp_path / 'arm', arm='agent-tools')
    c.begin_round()
    with pytest.raises(ValueError, match='ledger_replay_drift'):
        c.act(dict(tool='replay_input', input='([2], 5)'))
    with pytest.raises(ValueError, match='ledger_context_drift'):
        flow_tools.FlowSession(t, tmp_path / 'arm', arm='fixed-tools')


def test_executions_are_shared_across_arms_but_counted_logically(tmp_path):
    t = task(LOOP)
    one = flow_tools.FlowSession(t, tmp_path / 'a1', arm='agent-tools')
    two = flow_tools.FlowSession(t, tmp_path / 'a2', arm='fixed-tools')
    for s in (one, two):
        s.begin_round()
        s.act(dict(tool='replay_input', input='([1], 5)'))
    assert one.executor.physical == 2 and two.executor.cache_hits == 2
    assert one.report()['execution_requests'] == two.report()['execution_requests'] == 1


def test_discovery_and_final_inputs_have_separate_budgets(session):
    s = session(LOOP)
    common = s.discover(['([1], 5)', '([], 5)'])
    assert [c['trace'] for c in common] == ['C1', 'C2'] and s.report()['common_executions'] == 2 and s.report()['execution_requests'] == 0
    finals = s.final_inputs(['([3], 5)', '([3], 5)', 'bad'])
    assert len(finals) == 2 and finals[1]['status'] == 'error' and s.report()['final_inputs'] == 2
    with pytest.raises(ValueError):
        s.final_inputs([f'([{i}], 5)' for i in range(F['final_inputs'] + 1)])


def test_fixed_schedule_is_deterministic_and_capped():
    hyps = [dict(id='H1', source_ids=['a', 'b']), dict(id='H2', source_ids=['c']), dict(id='H3', source_ids=['d'])]
    one = flow_tools.fixed_schedule(hyps, [f'({i},)' for i in range(10)], 1)
    assert one == flow_tools.fixed_schedule(hyps, [f'({i},)' for i in range(10)], 1)
    assert len(one) == F['actions_per_round'] and [a['tool'] for a in one[:2]] == ['inspect_flow'] * 2
    assert flow_tools.fixed_schedule(hyps, [], 2)[0]['tool'] == 'inspect_data'


# ---- packages ------------------------------------------------------------------------------------------------
def test_packages_keep_rank_provenance_and_hide_values_from_concept_arm(session):
    s = session(LOOP)
    witnesses = s.discover(['([1, -2, 3, 20], 5)'])
    ret = node(s.cfg, ':Return:')
    concepts = [dict(id='O1', statement='sum eligible values', relation='output equals sum of non-negative values <= k', quote='Sum non-negative values up to k.')]
    hyps = [dict(id='H2', statement='second', source_ids=[ret], obligation_ids=['O1']),
            dict(id='H1', statement='first', source_ids=[node(s.cfg, ':Break:')], obligation_ids=['O1'])]
    concept = flow_packages.build('concept+hyp', s, concepts=concepts, hypotheses=hyps, witnesses=witnesses)
    assert [h['id'] for h in concept['sections']['hypotheses']] == ['H2', 'H1']  # model rank kept
    assert 'inputs' not in concept['sections'] and 'traces' not in concept['sections']
    assert '20' not in json.dumps(concept['sections'])
    full = flow_packages.build('concept+input+hyp', s, concepts=concepts, hypotheses=hyps, witnesses=witnesses)
    assert full['sections']['inputs'][0]['output_provenance'] == 'observed_PUT_output_not_expected_oracle'
    flow = flow_packages.build('flow+input', s, concepts=concepts, hypotheses=hyps, witnesses=witnesses)
    assert 'hypotheses' not in flow['sections']
    assert flow['sections']['structure'] == full['sections']['structure']  # same structural facts
    assert flow_packages.build('plain', s, concepts=concepts, hypotheses=hyps, witnesses=witnesses)['sections'] == {}
    assert flow_packages.build('witness-only', s, concepts=concepts, hypotheses=hyps, witnesses=witnesses) is None
    assert all(len(x) < 20 for x in json.dumps(full['sections']['structure']).split('"') if x.startswith('N'))  # aliased IDs only


# ---- online runner with a fake client (no network; hand-written responses, not Qwen evidence) -----------------
class FakeClient:
    def __init__(self):
        self.calls = []

    def complete(self, request):
        self.calls.append(request['slot'])
        stage = request['stage']
        body = {
            'concept': dict(relation='sorted list keeps every occurrence', domain='list of int', uncertainty=''),
            'behavior': dict(summary='returns sorted(set(xs))', source_lines=[3], limitations=''),
            'hypothesis': dict(hypotheses=[dict(verdict='mismatch', required_relation='keep duplicates', actual_relation='set drops duplicates',
                                                source_lines=[3], trigger='xs with a repeated value', alternative='', reason='set collapses')], reason='x'),
            'probe': dict(inputs=[dict(arguments='([1, 1],)', expected='[1, 1]', predicted_actual='[1]', purpose='trigger')], reason='x'),
            'agent': dict(actions=[{'tool': 'inspect_flow', 'ids': ['L3']}, {'tool': 'replay_input', 'input': '([2, 2],)', 'ids': ['L3']}], reason='x'),
            'final': dict(tests=[dict(arguments='([1, 1],)', expected='[1, 1]'), dict(arguments='([2, 1],)', expected='[1, 2]'),
                                 dict(arguments='([3],)', expected='[4]')], reason='x'),
        }[stage]
        if 'f01' in request['slot'] and stage == 'final':
            return dict(text='not json', input_tokens=1, output_tokens=1)
        text = json.dumps(body)
        if stage == 'hypothesis':
            text = '```json\n' + text + '\n```'  # Qwen fences nested objects; one fenced object is accepted
        return dict(text=text, input_tokens=10, output_tokens=5)


def test_flow_run_end_to_end_with_fake_client(tmp_path):
    from . import flow_run
    run = flow_run.Run('diag16', client=FakeClient())
    run.cases = [c for c in run.cases if c['case_id'] in ('f01', 'f02')]
    run.root = tmp_path / 'diag16'
    run.generate(workers=2)
    assert (run.root / 'generation_frozen.json').exists()
    n_calls = len(run.client.calls)
    assert n_calls == 2 * (3 + 9 * 3)  # shared 3 calls + 9 LLM arms x 3 calls per case
    report = flow_run.score(run)
    arms = report['arms']
    # f02 = sorted(set(xs)): ([1, 1],) exposes the bug with the spec-correct expected value.
    assert arms['plain']['tasks_confirmed'] == 1 and arms['plain']['false_alarms'] >= 1  # ([3],)->[4] is a false alarm
    assert arms['witness-only']['confirmed_tests'] == 0
    agent = [r for r in report['rows'] if r['arm'] == 'agent-tools' and r['case_id'] == 'f02'][0]
    assert agent['tool_actions'] == 4 and agent['tool_errors'] == 0
    f01 = [r for r in report['rows'] if r['case_id'] == 'f01' and r['arm'] == 'plain'][0]
    assert f01['schema_errors'] == 1 and f01.get('admissible', 0) == 0  # failed final call stays in the denominator
    run.generate(workers=2)  # frozen: no new calls
    assert len(run.client.calls) == n_calls


def test_validate_rejects_two_fenced_objects():
    from . import flow_run
    good = json.dumps(dict(relation='r', domain='d', uncertainty=''))
    assert flow_run.validate('concept', '```json\n' + good + '\n```')['relation'] == 'r'
    with pytest.raises(ValueError):
        flow_run.validate('concept', '```json\n' + good + '\n```\n```json\n' + good + '\n```')


def test_parse_call_normalization_is_bounded():
    one = dict(positional=1, required=1, varargs=False, required_keyword_only=False)
    two = dict(positional=2, required=2, varargs=False, required_keyword_only=False)
    assert flow_tools.parse_call('([1, 1],)', one) == ([1, 1],)
    assert flow_tools.parse_call('[1, 1]', one) == ([1, 1],)
    assert flow_tools.parse_call('(1, 2)', one) == ((1, 2),)
    assert flow_tools.parse_call('[1, 2], [1]', two) == ([1, 2], [1])
    assert flow_tools.parse_call('([1, 2], [1])', two) == ([1, 2], [1])
    for bad in ('[1]', 'f([1], [2])', '1, 2, 3'):
        with pytest.raises(ValueError):
            flow_tools.parse_call(bad, two)


def test_fixed_schedule_replay_without_hypotheses_is_valid(session):
    s = session(LOOP)
    s.begin_round()
    for action in flow_tools.fixed_schedule([], ['([1], 5)'], 1):
        assert s.act(action)['status'] == 'ok'


# ---- v26 oracle runner with a fake client (hand-written responses, not Qwen evidence) ----------------------------
class FakeOracleClient:
    def __init__(self):
        self.calls = []

    def complete(self, request):
        self.calls.append(request['slot'])
        stage = request['stage']
        ctx = json.loads(request['messages'][1]['content'])['context']
        if stage.startswith('exact'):
            body = dict(expected=[dict(input_id=i['id'], expected=repr(sorted(eval(i['arguments'])[0]))) for i in ctx['inputs']], reason='x')
        elif stage == 'property':
            body = dict(properties=[dict(id='P1', description='same multiset', code='def check(args, output, error):\n    return error is None and sorted(args[0]) == output'),
                                    dict(id='P2', description='broken', code='def check(args, output, error):\n    raise RuntimeError()')], reason='x')
        else:
            body = dict(relations=[dict(id='M1', description='append max', code='def follow(args):\n    return (args[0] + [9],)\ndef relation(a, o, a2, o2):\n    return len(o2) == len(o) + 1')], reason='x')
        return dict(text=json.dumps(body), input_tokens=10, output_tokens=5)


def test_oracle_run_end_to_end_with_fake_client(tmp_path):
    from . import oracle_run
    run = oracle_run.Run('diag16', client=FakeOracleClient())
    run.cases = [c for c in run.cases if c['case_id'] in ('f01', 'f02')]
    run.root = tmp_path / 'diag16'
    run.generate(workers=2)
    report = oracle_run.score(run)
    arms = report['arms']
    # f02 = sorted(set(xs)): the exact sorted-list oracle and the multiset property both flag duplicate inputs only.
    assert arms['exact_spec']['false_alarms'] == 0 and arms['property']['false_alarms'] == 0
    assert arms['property']['tasks_confirmed'] == arms['exact_spec']['tasks_confirmed']
    assert report['property_soundness']['fails_on_reference'] == 0 and report['property_soundness']['errors_on_reference'] > 0
    assert len(run.client.calls) == 2 * 4


def test_oracle_validate_wraps_bare_arrays_identically():
    from . import oracle_run
    arr = '[{"input_id": "I1", "expected": "True"}]'
    for text in (arr, '```json\n' + arr + '\n```'):
        v = oracle_run.validate('exact_spec', text)
        assert v['expected'][0]['expected'] == 'True' and v['reason'] == 'wrapped_bare_array'
    props = '[{"id": "P1", "description": "d", "code": "def check(a, o, e):\\n    return True"}]'
    assert oracle_run.validate('property', props)['properties'][0]['id'] == 'P1'
