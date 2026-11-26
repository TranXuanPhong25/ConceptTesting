"""Authored contract checks; no model endpoint or benchmark outcomes."""
import json

from final.src.models.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext

SPEC = 'def f(xs):\n    """Return the total of every occurrence in xs."""\n'
SOURCE = 'def f(xs):\n    unique = set(xs)\n    return sum(unique)\n'


def context(tmp_path, calls):
    base = {'args': '([2, 3],)', 'kwargs': '{}'}
    program = {'id': 'p0', 'code': SOURCE, 'base': {'status': 'pass', 'calls': [base],
        'coverage': {'lines': [2, 3], 'arcs': [[-1, 2], [2, 3], [3, -1]]}}}
    return TaskContext({'task_id': 'HumanEval/0', 'entry_point': 'f', 'prompt': SPEC, 'test': ''},
        {'contract': '    assert isinstance(xs, list)\n    assert all(type(x) is int for x in xs)\n'},
        ArtifactStore(tmp_path), PipelineSettings(input_budget=4, input_tokens=2048, context_tokens=8192), calls,
        cohort_task={'generated': 1, 'programs': [program]}, packet={'visible_put_ids': ['p0'], 'common': ''})


def obligation():
    return {'program_id': 'p0', 'line': 2, 'requirement': 'every occurrence',
        'pattern': 'dedup loses contributions', 'scenario': 'equal positive values must both contribute',
        'predicate': 'len(xs) > distinct_count(xs) and sum(xs) > 0',
        'instruction': 'Repeat a nonzero positive value.',
        'counterexample': 'Dedup is correct when the spec asks for distinct values.',
        'strategies': {'xs': {'kind': 'sampled', 'values': [[4, 4], [5, 5]]}}}


class Calls:
    def __init__(self, first=None, second=None, third=None):
        self.first = first if first is not None else {'obligations': [obligation()]}
        self.second = second if second is not None else {'inputs': [
            {'arguments': {'xs': [2, 3]}}, {'arguments': {'xs': [4, 4]}}]}
        self.third = third
        self.requests = []
        self.names = []
        self.seeds = []

    def token_count(self, messages):
        return 100

    def complete(self, number, name, messages, **kwargs):
        self.requests.append(messages)
        self.names.append(name)
        self.seeds.append(kwargs['seed'])
        if len(self.requests) == 1:
            raw = self.first
        elif len(self.requests) == 2:
            raw = self.second
        else:
            raw = self.third if self.third is not None else self.second
        return ModelResponse(raw if isinstance(raw, str) else json.dumps(raw), finish_reason='stop')


def test_repaired_arm_hands_failed_proposal_to_construct_without_a_target(tmp_path):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm

    draft = '{"obligations":[{"instruction":"Try two identical values"'
    calls = Calls(first=draft, second=draft, third={'inputs': [{'arguments': {'xs': [4, 4]}}]})
    ctx = context(tmp_path / 'repair', calls)
    arm = RepairedControlFlowObligationArm()
    result = arm.run(ctx)
    assert 'At most 6 concise obligations' in json.loads(calls.requests[0][-1]['content'])['response_contract']
    assert [round_['phase'] for round_ in result['rounds']] == ['propose', 'construct']
    assert 'model_calls' not in result
    seed = ctx.settings.input_seed + ctx.task_number
    assert calls.seeds == [seed, seed + 1000, seed + 2]
    assert calls.names == [
        'control_flow_obligation_v1_repair_propose',
        'control_flow_obligation_v1_repair_propose_retry',
        'control_flow_obligation_v1_repair_construct',
    ]
    assert result['propose_retry'] == {
        'retried': True, 'succeeded': False,
        'trigger': 'no_complete_input_records', 'retry_error': 'no_complete_input_records',
    }
    retry_payload = json.loads(calls.requests[1][-1]['content'])
    assert 'Previous propose response failed (no_complete_input_records)' in retry_payload['response_contract']
    followup = calls.requests[2]
    assert [m['role'] for m in followup] == ['system', 'user', 'assistant', 'user']
    assert followup[2]['content'] == draft
    payload = json.loads(followup[-1]['content'])
    assert 'no_complete_input_records' in payload['response_contract']
    assert payload['obligations'] == [] and payload['coverage_targets'] == []
    assert result['proposal_history_supplied'] and result['inputs'][0]['args'] == '([4, 4],)'
    ctx.inputs = {'arms': {arm.name: result}}
    summary = {}
    arm.extend_summary([ctx], summary, None)
    assert summary[arm.name]['model_calls'] == len(calls.requests) == 3
    ctx.artifacts = ArtifactStore(ctx.artifacts.directory, read_only=True)
    ctx.calls = None
    assert RepairedControlFlowObligationArm().run(ctx) == result


def test_repaired_arm_retries_propose_once_and_recovers_obligations(tmp_path):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm

    draft = '{"obligations":[{"instruction":"broken json"'
    calls = Calls(
        first=draft,
        second={'obligations': [obligation()]},
        third={'inputs': [{'arguments': {'xs': [4, 4]}, 'obligation_id': 'O1'}]},
    )
    ctx = context(tmp_path, calls)
    result = RepairedControlFlowObligationArm().run(ctx)
    assert len(result['rounds']) == 2
    assert calls.names == [
        'control_flow_obligation_v1_repair_propose',
        'control_flow_obligation_v1_repair_propose_retry',
        'control_flow_obligation_v1_repair_construct',
    ]
    assert result['propose_retry'] == {'retried': True, 'succeeded': True, 'trigger': 'no_complete_input_records'}
    assert 'proposal_history_supplied' not in result
    assert len(result['obligations']) == 1 and result['obligations'][0]['id'] == 'O1'
    assert [m['role'] for m in calls.requests[2]] == ['system', 'user']
    construct_obls = json.loads(calls.requests[2][-1]['content'])['obligations']
    assert len(construct_obls) == 1 and 'strategies' not in construct_obls[0]
    assert any(row['args'] == '([4, 4],)' for row in result['inputs'])


def test_repair_triggers_only_on_a_proposal_decode_failure(tmp_path):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm

    for index, first in enumerate(({'obligations': [obligation()]}, {'obligations': [], 'inputs': []},
                                   '{"inputs":[{"arguments":{"xs":[8,8]}},{"arguments":')):
        new = Calls(first=first)
        result = RepairedControlFlowObligationArm().run(context(tmp_path / str(index) / 'new', new))
        assert 'proposal_history_supplied' not in result
        assert all([m['role'] for m in req] == ['system', 'user'] for req in new.requests)
        if len(new.requests) == 2:
            construct_obls = json.loads(new.requests[1][-1]['content'])['obligations']
            assert all('strategies' not in row and 'base_membership' not in row for row in construct_obls)


def test_repair_fits_history_by_compacting_analysis_and_preserves_sources(tmp_path):
    from final.src.modular.spec_obligation.prompts import repair_construct

    ctx = context(tmp_path, Calls())
    payload = {'programs': [{'program_id': 'other', 'numbered_source': '1: other'},
                            {'program_id': 'owner', 'numbered_source': '1: owner'}],
               'specification': SPEC, 'trusted_contract': ctx.metadata['contract'], 'response_contract': 'Emit inputs.',
               'coverage_targets': [{'id': 't', 'program_id': 'owner', 'line': 1}],
               'analysis': [{'program_id': p, 'source_sha256': p, 'executable_lines': [1]} for p in ('owner', 'other')]}
    original = [{'role': 'system', 'content': 'instruction'}, {'role': 'user', 'content': json.dumps(payload)}]
    seen = []

    def size(request):
        analyses = json.loads(request[-1]['content'])['analysis']
        seen.append([a['program_id'] for a in analyses])
        return ctx.settings.context_tokens if any('executable_lines' in a for a in analyses) else 1

    ctx.calls.token_count = size
    repaired = repair_construct(ctx, original, 'partial draft', 'parse error')
    packed = json.loads(repaired[-1]['content'])
    assert seen == [['owner', 'other'], ['owner'], ['owner']]
    assert repaired[2] == {'role': 'assistant', 'content': 'partial draft'}
    assert packed['analysis'] == [{'program_id': 'owner', 'source_sha256': 'owner'}]
    assert all(packed[key] == payload[key] for key in ('programs', 'coverage_targets', 'specification', 'trusted_contract'))
    ctx.calls.token_count = lambda request: ctx.settings.context_tokens
    assert repair_construct(ctx, original, 'too large', 'parse error') is None
    assert json.loads(original[-1]['content']) == payload


def test_repaired_arm_still_constructs_when_full_draft_cannot_fit(tmp_path):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm

    calls = Calls(first='broken proposal', second='broken retry', third={'inputs': [{'arguments': {'xs': [4, 4]}}]})
    calls.token_count = lambda request: 10_000 if len(request) == 4 else 100
    result = RepairedControlFlowObligationArm().run(context(tmp_path, calls))
    assert len(calls.requests) == 3 and result['inputs']
    assert [m['role'] for m in calls.requests[2]] == ['system', 'user']
    assert not result['proposal_history_supplied']


def test_repaired_arm_keeps_llm_quota_separate_from_hypothesis_inputs(tmp_path, monkeypatch):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm
    from final.src.modular.input_contract import validate_generated_inputs
    from final.src.modular.spec_obligation.evidence import Evidence

    calls = Calls()
    ctx = context(tmp_path, calls)
    ctx.settings = PipelineSettings(input_budget=20)
    programs = ctx.cohort_task['programs']
    programs.extend({**programs[0], 'id': p} for p in ('p1', 'p2'))
    ctx.packet['visible_put_ids'] = [p['id'] for p in programs]
    calls.first = {
        'obligations': [{**obligation(), 'program_id': p['id']} for p in programs],
        'inputs': [{'arguments': {'xs': [1000 + i]}} for i in range(5)],
    }
    calls.second = {'inputs': [{'arguments': {'xs': [i]}, 'obligation_id': ['bad label']} for i in range(20)]}

    def sample(ledger, *, draws, seed, seconds, predicate, source):
        number = int(source['obligation_id'][1:])
        for i in range(draws):
            value = number * 100 + i
            ledger.add({'arguments': {'xs': [value, value]}}, {'tool': 'hypothesis', **source})
        return {'status': 'complete', 'draws': draws}

    monkeypatch.setattr('final.src.modular.tool_sampling.constructors.sample_hypothesis', sample)
    monkeypatch.setattr(Evidence, 'observe', lambda *args, **kwargs:
                        {'domain': 'valid', 'status': 'executed', 'coverage': {'lines': [2, 3], 'arcs': []}})
    result = RepairedControlFlowObligationArm().run(ctx)
    receipts = result['candidate_receipts']
    assert len(receipts) == 64 and len({r['candidate_id'] for r in receipts}) == 64
    # All 25 LLM candidates are traced first; the remaining 39 traces interleave O1, O2, O3 evenly.
    assert all(any(s['tool'] == 'llm' for s in r['sources']) for r in receipts[:25])
    hyp_receipts = receipts[25:]
    assert len(hyp_receipts) == 39
    for position, owner in enumerate(('p0', 'p1', 'p2')):
        group = hyp_receipts[position::3]
        assert len(group) == 13
        assert all(r['program_id'] == owner and r['sources'][0]['obligation_id'] == f'O{position + 1}' for r in group)
    selected = [r for r in result['candidate_ledger'] if r['selected']]
    assert result['llm_input_count'] == 20
    assert result['hypothesis_input_count'] == 39
    assert len(selected) == len(result['inputs']) == 59
    assert {r['canonical_args']['args'] for r in selected} == {r['args'] for r in result['inputs']}
    assert sum(any(s['tool'] == 'llm' for s in r['sources']) for r in selected) == 20
    assert {r['sources'][0]['obligation_id'] for r in selected if not any(s['tool'] == 'llm' for s in r['sources'])} == {'O1', 'O2', 'O3'}
    validate_generated_inputs({'task_id': ctx.task['task_id'], 'arms': {RepairedControlFlowObligationArm.name: result}},
                          task_id=ctx.task['task_id'])


def test_seed_miss_reaches_construct_and_repeated_seed_is_traced_once(tmp_path):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm

    class SeedCalls(Calls):
        def complete(self, number, name, messages, **kwargs):
            self.requests.append(messages)
            payload = json.loads(messages[-1]['content'])
            labels = [t['id'] for t in payload['coverage_targets']]
            assert len(labels) == 2
            if payload['phase'] == 'propose':
                assert '"inputs" FIRST' in payload['response_contract']
                assert all(t['base_trace_gap'] == {'first_unobserved_arc':[2, 3], 'observed_exits':[[2, 4]]}
                           for t in payload['coverage_targets'])
                inputs = [{'arguments': {'xs': [5, 7]}, 'target_id': label} for label in labels]
                # The seed array is complete. Only the metadata tail was cut off.
                self.draft = '{"inputs":' + json.dumps(inputs) + ',"obligations":[{"instruction":"unfinished'
                return ModelResponse(self.draft, finish_reason='length')
            assert messages[2] == {'role':'assistant', 'content':self.draft}
            assert {r['target_id'] for r in payload['seed_feedback']} == set(labels)
            for row in payload['seed_feedback']:
                assert row['status'] == 'miss' and row['first_unobserved_arc'] == [2, 3]
                assert [2, 4] in row['observed_exits']
                assert row['input']['args'] == '([5, 7],)'
            return ModelResponse(json.dumps({'inputs': [
                {'arguments': {'xs': [9]}, 'target_id': labels[0], 'obligation_id': 'invented'},
                {'arguments': {'xs': [5, 7]}, 'target_id': labels[1]}]}), finish_reason='stop')

    calls = SeedCalls()
    ctx = context(tmp_path, calls)
    put = ctx.cohort_task['programs'][0]
    put['code'] = 'def f(xs):\n    if len(xs) == 1:\n        return xs[0]\n    return sum(xs)\n'
    put['base']['coverage'] = {'lines':[2, 4], 'arcs':[[-1, 2], [2, 4], [4, -1]]}
    result = RepairedControlFlowObligationArm().run(ctx)
    assert len(calls.requests) == 3
    assert result['propose_retry'] == {
        'retried': True, 'succeeded': False,
        'trigger': 'complete_input_records_salvaged', 'retry_error': 'complete_input_records_salvaged',
    }
    assert result['proposal_history_supplied'] and result['seed_observation_count'] == 1
    assert len(result['candidate_receipts']) == 2 and result['target_coverage'] == {'covered':2,'total':2}
    assert {row['args'] for row in result['inputs']} == {'([5, 7],)', '([9],)'}
    first = result['candidate_receipts'][0]
    assert first['trace_phase'] == 'propose'
    assert all(origin['phase'] == 'propose' for origin in first['sources'])
    recovered = next(row for row in result['candidate_receipts'] if row['call']['args'] == '([9],)')
    assert recovered['trace_phase'] == 'construct'
    assert recovered['sources'][0]['obligation_id'] is None
    assert recovered['sources'][0]['unbound_obligation_id'] == 'invented'


def test_partial_and_missing_seed_traces_keep_uncertainty_and_hide_outputs():
    from final.src.modular.spec_obligation.arm import feedback_for_targets

    target = {'id':'t', 'program_id':0, 'path':[{'arc':[7,9]}]}
    seed = {'program_id':0, 'sources':[], 'call':{'args':'(1,)', 'kwargs':'{}'},
            'domain':'valid', 'status':'timeout', 'coverage':{'arcs':[[7,8]]}, 'hit_targets':[],
            'actual':'OUTPUT_MARKER', 'expected':'ORACLE_MARKER'}
    assert feedback_for_targets([target], [])[0]['status'] == 'untried'
    feedback = feedback_for_targets([target], [seed])[0]
    assert feedback['status'] == 'unknown' and feedback['reason'] == 'timeout'
    assert 'observed_exits' not in feedback and 'MARKER' not in json.dumps(feedback)
    seed['hit_targets'] = ['t']
    assert feedback_for_targets([target], [seed])[0]['status'] == 'hit'


def test_initial_and_final_traces_share_64_pairs_and_exclude_base_seeds(tmp_path, monkeypatch):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm
    from final.src.modular.spec_obligation.evidence import Evidence

    calls = Calls()
    ctx = context(tmp_path, calls)
    ctx.settings = PipelineSettings(input_budget=20)
    put = ctx.cohort_task['programs'][0]
    put['code'] = 'def f(xs):\n    if not xs:\n        return 0\n    unique = set(xs)\n    return sum(unique)\n'
    put['base']['coverage'] = {'lines':[2, 4, 5], 'arcs':[[-1,2],[2,4],[4,5],[5,-1]]}
    calls.first = {'inputs':[{'arguments':{'xs':[2, 3]}}, {'arguments':{'xs':[41]}, 'target_id':['bad']}],
                   'obligations':[{**obligation(),'line':4} for _ in range(3)]}
    observations = []

    def observe(evidence, program, call, *, base=False):
        if not base:
            observations.append((len(calls.requests), program['id'], call['args']))
        return {'domain':'valid','status':'executed','coverage':{'lines':[2, 4, 5],'arcs':[[2,4]]}}

    def sample(ledger, *, draws, seed, seconds, predicate, source):
        start = int(source['obligation_id'][1:]) * 100
        for i in range(start, start + draws):
            ledger.add({'arguments':{'xs':[i, i]}}, {'tool':'hypothesis', **source})
        return {'status':'complete','draws':draws}

    monkeypatch.setattr(Evidence, 'observe', observe)
    monkeypatch.setattr('final.src.modular.tool_sampling.constructors.sample_hypothesis', sample)
    result = RepairedControlFlowObligationArm().run(ctx)
    assert observations[0] == (1, 'p0', '([41],)')
    assert all(round_count == 2 for round_count, _, _ in observations[1:])
    assert len(observations) == len({(owner, args) for _, owner, args in observations}) == 64
    assert result['seed_observation_count'] == 1
    assert len(result['candidate_receipts']) == 64
    assert result['llm_input_count'] == 2
    assert result['hypothesis_input_count'] == 62
    assert len(result['inputs']) == 64
    assert all(args != '([2, 3],)' for _, owner, args in observations)


def test_targeted_construct_preserves_owners_and_obligations_under_token_pressure(tmp_path):
    from final.src.modular.spec_obligation.prompts import messages, repair_construct
    from final.src.modular.spec_obligation.evidence import Evidence

    ctx = context(tmp_path, Calls())
    for name in ('other','last'):
        ctx.cohort_task['programs'].append({**ctx.cohort_task['programs'][0], 'id': name})
        ctx.packet['visible_put_ids'].append(name)
    evidence = Evidence(ctx, 'control_flow_obligation_v1_repair')
    target = {'program_id':'last', 'id':'last:C1:3'}
    obligation = {'program_id':'p0', 'id':'O1'}
    def count(request):
        payload = json.loads(request[-1]['content'])
        return 10000 if any(a['program_id']=='other' for a in payload['analysis']) else 1
    ctx.calls.token_count = count
    req = messages(ctx,evidence,phase='construct',input_budget=4,targets=[target],
                   obligations=[obligation],seed_feedback=[{'target_id':target['id'],'status':'untried'}])
    d = json.loads(req[-1]['content'])
    assert [p['program_id'] for p in d['programs']] == ['p0','other','last']
    assert [a['program_id'] for a in d['analysis']] == ['p0','last']
    assert d['coverage_targets'] == [target] and d['obligations'] == [obligation]
    ctx.calls.token_count = lambda req: 1
    initial = messages(ctx,evidence,phase='propose',input_budget=4,targets=[target])
    recovered = repair_construct(ctx, initial, 'public draft', 'decode_error', seed_feedback=d['seed_feedback'])
    # When context fits, repair_construct keeps non-owner PUTs alongside target owners.
    assert [p['program_id'] for p in json.loads(recovered[-1]['content'])['programs']] == ['p0', 'other', 'last']
    # When context overflows even after compacting analysis, only non-owner PUTs are dropped first.
    ctx.calls.token_count = lambda req: 10000 if len(json.loads(req[-1]['content'])['programs']) > 1 else 1
    trimmed = repair_construct(ctx, initial, 'public draft', 'decode_error', seed_feedback=d['seed_feedback'])
    assert [p['program_id'] for p in json.loads(trimmed[-1]['content'])['programs']] == ['last']


def test_repaired_arm_accepts_up_to_6_obligations_and_compacts_construct_payload(tmp_path, monkeypatch):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm
    from final.src.modular.spec_obligation.evidence import Evidence

    obls = [obligation() for _ in range(7)]
    calls = Calls(first={'obligations': obls})
    ctx = context(tmp_path, calls)
    monkeypatch.setattr(Evidence, 'observe', lambda *args, **kwargs:
                        {'domain': 'valid', 'status': 'executed', 'coverage': {'lines': [2, 3], 'arcs': []}})
    result = RepairedControlFlowObligationArm().run(ctx)
    assert len(result['obligations']) == 6
    assert 'obligation_limit_6' in result['errors']
    construct_payload = json.loads(calls.requests[1][-1]['content'])
    assert len(construct_payload['obligations']) == 6
    assert all('strategies' not in row and 'base_membership' not in row and 'source_sha256' not in row
               for row in construct_payload['obligations'])
    assert 'functional correctness mismatches' in json.loads(calls.requests[0][-1]['content'])['response_contract']
    assert 'functional correctness mismatches' in construct_payload['response_contract']
    assert 'memory scaling' not in construct_payload['response_contract']


def test_repaired_arm_retains_base_hit_obligations_instead_of_skipping_construct(tmp_path):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm

    coarse = obligation()
    # Coarse predicate matches base input ([2, 3],), marking base_membership='hit'.
    coarse['predicate'] = 'len(xs) >= 1'
    calls = Calls(first={'obligations': [coarse]}, second={'inputs': [{'arguments': {'xs': [4, 4]}}]})
    ctx = context(tmp_path, calls)
    result = RepairedControlFlowObligationArm().run(ctx)
    assert result['obligations'][0]['base_membership']['status'] == 'hit'
    assert result['base_hit_obligations_retained'] is True
    assert result['selected_obligation_ids'] == ['O1']
    assert len(calls.requests) == len(result['rounds']) == 2
    seed = ctx.settings.input_seed + ctx.task_number
    assert calls.seeds == [seed, seed + 1]
    assert any(row['status'] == 'complete' and row['draws'] > 0 for row in result['sampling'])
    assert any(row['args'] == '([4, 4],)' for row in result['inputs'])


def test_usage_accounting_separates_hybrid_from_control_flow(tmp_path):
    from final.src.modular.catalogue_reporting import usage_by_arm
    for name in ('spec_obligation_propose', 'spec_obligation_construct', 'control_flow_round_0',
                 'control_flow_obligation_propose', 'control_flow_obligation_v1_repair_propose',
                 'control_flow_obligation_v1_repair_propose_retry', 'control_flow_obligation_v1_repair_construct'):
        path = tmp_path / 'tasks/0/calls' / name
        path.mkdir(parents=True)
        (path / 'attempt.json').write_text('{}')
        (path / 'response.json').write_text(json.dumps({'usage': {
            'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}))
    result = usage_by_arm(tmp_path, ['spec_obligation', 'control_flow', 'control_flow_obligation',
                                     'control_flow_obligation_v1_repair'])
    assert result['spec_obligation']['received'] == 2
    assert result['spec_obligation']['known_usage']['total_tokens'] == 30
    assert result['control_flow']['received'] == 1
    assert result['control_flow_obligation']['received'] == 1
    assert result['control_flow_obligation_v1_repair']['received'] == 3
    assert result['control_flow_obligation_v1_repair']['known_usage']['total_tokens'] == 45


def test_repaired_arm_uses_shared_oracle_and_read_only_replay(tmp_path, monkeypatch):
    from final.src.modular.spec_obligation import RepairedControlFlowObligationArm
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.modular.references import TaskReferencePrograms
    from final.src.modular.tests.helpers import FixtureCalls
    from final.src.runtime.artifacts import digest, save
    from final.src.runtime.execution import execute

    ctx = context(tmp_path / 'unused', None)
    task = {**ctx.task, 'canonical_solution': '    return sum(xs)\n'}
    row = {**ctx.cohort_task, 'task_id': task['task_id'], 'base_pass': 1, 'base_input_keys': []}
    cohort = tmp_path / 'cohort.json'
    save(cohort, {'tasks': [row], 'cohort_sha256': digest([row]), 'dataset_sha256': 'fixture-dataset'})
    directory = tmp_path / 'run'

    class Model:
        model_id = 'authored-offline-obligation-fixture'
        def tokens(self, messages): return 100
        def generate(self, messages, **kwargs):
            phase = json.loads(messages[-1]['content'])['phase']
            raw = Calls().first if phase == 'propose' else Calls().second
            return ModelResponse(json.dumps(raw), {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}, 'stop')

    def oracle(job):
        frozen = json.loads((directory / 'tasks/0/inputs.json').read_text())
        assert set(frozen['arms']) == {'control_flow_obligation_v1_repair'}
        return execute(job)

    monkeypatch.setattr('final.src.modular.reference_oracle.execute', oracle)
    pipeline = BenchmarkPipeline(cohort, ArtifactStore(directory),
        arms=(RepairedControlFlowObligationArm(),),
        settings=PipelineSettings(input_budget=4),
        calls=FixtureCalls(Model(), directory), reference_programs=TaskReferencePrograms())
    metadata = {task['task_id']: {**ctx.metadata, 'atol': 0}}
    result = pipeline.run([task], metadata)
    assert result['arms']['control_flow_obligation_v1_repair']['detected'] == 1
    assert result['control_flow_obligation_v1_repair']['model_calls'] == 2
    assert result['control_flow_obligation_v1_repair']['call_usage']['received'] == 2
    replay = BenchmarkPipeline(cohort, ArtifactStore(directory, read_only=True),
        arms=(RepairedControlFlowObligationArm(),), settings=pipeline.settings,
        reference_programs=TaskReferencePrograms())
    assert replay.run([task], metadata) == result
