"""Control-flow engineering checks on authored functions, not benchmark runs."""
import json

import pytest

from final.src.models.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext

SOURCE = '''def f(xs: list[int], k: int):
    if k < 1:
        return False
    unique = set(xs)
    count = len(unique)
    if count == k:
        return True
    return False
'''
SPEC = 'def f(xs: list[int], k: int):\n    """Return whether the number of distinct integers in xs equals k."""\n'


def program(source=SOURCE):
    return {'id': 'p0', 'code': source, 'base': {'status': 'pass', 'calls': [
        {'args': '([1, 1], 2)', 'kwargs': '{}'}],
        'coverage': {'lines': [1, 2, 4, 5, 6, 8],
                     'arcs': [[-1, 2], [2, 4], [4, 5], [5, 6], [6, 8], [8, -1]]}}}


def context(tmp_path, calls=None):
    return TaskContext({'task_id':'HumanEval/0', 'entry_point':'f', 'prompt':SPEC, 'test':''},
        {'contract':'    assert isinstance(xs, list)\n    assert isinstance(k, int)\n'},
        ArtifactStore(tmp_path), PipelineSettings(input_budget=4, input_tokens=4096, context_tokens=8192), calls,
        cohort_task={'generated':1, 'programs':[program()]},
        packet={'visible_put_ids':['p0'], 'common':''})


def test_analysis_binds_uncovered_branch_to_guards():
    from final.src.modular.control_flow.analysis import analyze
    result = analyze(program(), 'f')
    target = next(t for t in result['targets'] if t.get('arc') == [6, 7])
    assert target['criterion'] == 'C2'
    assert [2, 4] in [step['arc'] for step in target['path']]
    assert 'count = len(unique)' in str(target['path'])
    assert 'def_use' not in result
    assert 'data_flow_status' not in result
    assert result['source_sha256']


def test_missing_measurement_never_becomes_zero_coverage():
    from final.src.modular.control_flow.analysis import analyze
    candidate = program()
    candidate['base'].pop('coverage')
    result = analyze(candidate, 'f')
    assert result['coverage_status'] == 'unknown'
    assert result['targets'] == []


def response(target_id):
    return {'concepts':[{'id':'distinct_equal', 'target_id':target_id,
        'name':'Distinct cardinality equals threshold',
        'input_relation':'The count after deduplication equals k; list length can differ.',
        'instruction':'Use repeated values and exactly k distinct values; pass the earlier guard.',
        'evidence_lines':[2,4,5,6], 'predicate':'distinct_count(xs) == k and k >= 1',
        'strategies':{'xs':{'kind':'sampled','values':[[1,1,2]]},
                      'k':{'kind':'sampled','values':[2]}}}],
        'inputs':[{'arguments':{'xs':[1,1,2],'k':2}, 'concept_id':'distinct_equal'}]}


@pytest.mark.parametrize('first_hits,invalid_concept,expected_calls', [
    ([3], False, 2), ([3, 7], False, 1), ([3, 7], True, 2),
])
def test_retry_keeps_original_targets_and_base_examples(
    tmp_path, monkeypatch, first_hits, invalid_concept, expected_calls,
):
    from final.src.modular.control_flow import ControlFlowArm, ControlFlowSettings

    targets = [
        {'id': f'p0:C1:{line}', 'program_id': 'p0', 'criterion': 'C1',
         'line': line, 'evidence_lines': [line]}
        for line in (3, 7)
    ]

    class Calls:
        def __init__(self):
            self.payloads = []

        def token_count(self, messages):
            return 100

        def complete(self, task_number, name, messages, **options):
            payload = json.loads(messages[-1]['content'])
            self.payloads.append(payload)
            target = payload['targets'][0]
            raw = response(target['id'])
            raw['concepts'][0].update(evidence_lines=target['evidence_lines'], predicate='', strategies={})
            if invalid_concept and len(self.payloads) == 1:
                raw['concepts'][0]['predicate'] = 'sum([1,2]) == 3'
            values = [1, 2] if len(self.payloads) == 1 else [1, 3]
            raw['inputs'][0]['arguments'] = {'xs': values, 'k': 2}
            return ModelResponse(json.dumps(raw), finish_reason='stop')

    calls = Calls()
    arm = ControlFlowArm(ControlFlowSettings(target_limit=2))
    monkeypatch.setattr(arm, '_analyze_programs', lambda *args: ([{
        'program_id': 'p0', 'source_sha256': 'fixture',
        'coverage_status': 'measured',
        'targets': targets,
    }], []))
    monkeypatch.setattr(arm, 'trace', lambda context, program, records: [
        {'domain': 'valid', 'status': 'executed', 'coverage': {
            'lines': first_hits if call['args'] == '([1, 2], 2)' else [7, 8],
        }}
        for call in records
    ])
    result = arm.run(context(tmp_path, calls))
    assert len(calls.payloads) == expected_calls
    first = calls.payloads[0]
    assert first['targets'] == targets[:2]
    if expected_calls == 2:
        second = calls.payloads[1]
        assert second['targets'] == first['targets']
        assert second['programs'] == first['programs']
        assert second['analysis'] == first['analysis']
        assert second['feedback']['remaining_target_ids'] == ([] if 7 in first_hits else ['p0:C1:7'])
        assert second['feedback']['candidates'][0]['hit_targets']
        assert second['feedback']['candidates'][0]['call'] == {
            'args': '([1, 2], 2)', 'kwargs': '{}', 'guidance_id': None,
        }
        assert bool(second['feedback']['errors']) == invalid_concept
        assert 'concepts' in second['feedback'] and 'concept_checks' in second['feedback']
    assert result['target_coverage'] == {'covered': 2, 'total': 2, 'selected_covered': 2}
    assert len(result['inputs']) == expected_calls


def test_schema_checks_bindings_without_losing_direct_input():
    from final.src.modular.control_flow.schema import parse_response
    from final.src.modular.control_flow.analysis import analyze
    targets = analyze(program(), 'f')['targets']
    target = next(t for t in targets if t.get('arc')==[6,7])
    raw=response(target['id'])
    parsed=parse_response(raw, targets, ['xs','k'])
    assert len(parsed['concepts'])==1 and not parsed['errors']
    raw['concepts'][0]['target_id']='invented'
    parsed=parse_response(raw, targets, ['xs','k'])
    assert parsed['concepts']==[] and parsed['errors']
    assert parsed['inputs']==raw['inputs']


def test_schema_rejects_unsafe_predicate_and_source_lines():
    from final.src.modular.control_flow.schema import parse_response
    from final.src.modular.control_flow.analysis import analyze
    targets=analyze(program(),'f')['targets']
    raw=response(targets[0]['id'])
    raw['concepts'][0]['predicate']='__import__("os").system("true")'
    parsed=parse_response(raw,targets,['xs','k'])
    assert not parsed['concepts'] and parsed['errors']
    raw=response(targets[0]['id'])
    raw['concepts'][0]['evidence_lines']=[999]
    assert parse_response(raw,targets,['xs','k'])['errors']


def test_native_trace_preserves_source_and_checks_domain():
    from final.src.runtime.execution import execute
    result=execute({'mode':'control_flow', 'source':SOURCE, 'entry':'f', 'context':SPEC,
        'contract':'    assert k >= 1\n', 'timeout':1, 'tests':[
            {'args':'([1, 1, 2], 2)', 'kwargs':'{}'},
            {'args':'([], 0)', 'kwargs':'{}'}]})
    assert result['tests'][0]['domain']=='valid'
    assert [6,7] in result['tests'][0]['coverage']['arcs']
    assert 'actual' not in result['tests'][0]
    assert result['tests'][1]['domain']=='invalid'
    assert 'coverage' not in result['tests'][1]


def test_arm_discovers_then_uses_tool_feedback_and_replays(tmp_path):
    from final.src.modular.control_flow import ControlFlowArm
    class Calls:
        def __init__(self):self.requests=[]
        def token_count(self,messages):return 100
        def complete(self, task_number, name, messages, **kwargs):
            self.requests.append((name,messages))
            payload=json.loads(messages[-1]['content'])
            target=next(t for t in payload['targets'] if t.get('arc')==[6,7])
            raw=response(target['id'])
            # First round deliberately misses; feedback must expose the miss.
            if len(self.requests)==1:
                raw['inputs'][0]['arguments']={'xs':[1,1],'k':2}
                raw['concepts'][0]['strategies']={}
            return ModelResponse(json.dumps(raw),finish_reason='stop')
    calls=Calls(); ctx=context(tmp_path,calls)
    result=ControlFlowArm().run(ctx)
    assert len(calls.requests)==2
    feedback=json.loads(calls.requests[1][1][-1]['content'])['feedback']
    assert feedback['remaining_target_ids']
    assert all('actual' not in str(item) for item in feedback['candidates'])
    assert result['concepts'] and result['inputs']
    assert any([6,7] in row.get('coverage',{}).get('arcs',[]) for row in result['candidate_receipts'])
    assert result['target_coverage']['covered'] > 0
    ctx.artifacts=ArtifactStore(tmp_path,read_only=True); ctx.calls=None
    assert ControlFlowArm().run(ctx)==result


def test_arm_is_explicit_and_default_stays_plain():
    from final.src.modular import selected_arms, default_arms
    assert selected_arms(['control_flow'])[0].name=='control_flow'
    assert [a.name for a in default_arms()]==['plain']


def test_native_error_still_witnesses_a_reached_branch():
    from final.src.runtime.execution import execute
    from final.src.modular.control_flow.analysis import hit
    source='def f(x):\n    if x == 0:\n        return 1 / x\n    return x\n'
    result=execute({'mode':'control_flow','source':source,'entry':'f',
        'context':'def f(x):\n    """A fixture."""\n','contract':'', 'timeout':1,
        'tests':[{'args':'(0,)','kwargs':'{}'}]})['tests'][0]
    assert result['status']=='error' and result['exception']=='ZeroDivisionError'
    assert hit({'criterion':'C2','arc':[2,3]}, result)
    assert 'actual' not in result


def test_empty_concepts_do_not_silently_pass_contract():
    from final.src.modular.control_flow.schema import parse_response
    parsed=parse_response({'concepts':[], 'inputs':[{'arguments':{'xs':[1],'k':1}}]},
                          [{'id':'target','evidence_lines':[1]}], ['xs','k'])
    assert parsed['errors'] and parsed['inputs']


def test_unknown_concept_never_discards_a_valid_direct_attempt(tmp_path):
    from final.src.modular.control_flow import ControlFlowArm, ControlFlowSettings
    class Calls:
        def token_count(self,messages):return 100
        def complete(self,*args,**kwargs):
            return ModelResponse(json.dumps(response('invented')),finish_reason='stop')
    batch=ControlFlowArm(ControlFlowSettings(rounds=1)).run(context(tmp_path, Calls()))
    assert not batch['concepts'] and batch['errors']
    assert batch['inputs'][0]['args']=='([1, 1, 2], 2)'


def test_tiny_candidate_budget_counts_native_pairs(tmp_path):
    from final.src.modular.control_flow import ControlFlowArm, ControlFlowSettings
    class Calls:
        def token_count(self,messages):return 100
        def complete(self,number,name,messages,**kwargs):
            payload=json.loads(messages[-1]['content'])
            target=payload['targets'][0]
            raw=response(target['id'])
            raw['concepts'][0]['strategies']={}
            return ModelResponse(json.dumps(raw),finish_reason='stop')
    ctx=context(tmp_path,Calls())
    other=program();other['id']='p1';ctx.cohort_task['programs'].append(other)
    ctx.packet['visible_put_ids'].append('p1')
    batch=ControlFlowArm(ControlFlowSettings(rounds=2,candidate_limit=1)).run(ctx)
    assert [row['program_id'] for row in batch['candidate_receipts']] == ['p0', 'p1', 'p1']


@pytest.mark.parametrize('prompt_put_cap, blocked_puts, oversized_target, expected_batch_sizes', [
    (6, [], None, [6, 6, 6, 6, 4]),
    (1, [], None, [4] * 7),
    (1, ['p0'], None, [4] * 6),
    (1, [], 'p0:C1:3', [3] + [4] * 6),
])
def test_control_flow_splits_prompt_and_traces_each_base_pass_put(
    tmp_path, monkeypatch, prompt_put_cap, blocked_puts, oversized_target, expected_batch_sizes,
):
    from final.src.modular.control_flow import ControlFlowArm
    from final.src.modular.plain import PlainArm
    from final.src.modular.generators.methods import MethodInputGenerator

    class Calls:
        def __init__(self):
            self.requests = []

        def token_count(self, messages):
            payload = json.loads(messages[-1]['content'])
            put_ids = {row['id'] for row in payload['programs']}
            if len(put_ids) > prompt_put_cap or put_ids.intersection(blocked_puts):
                return 10000
            if any(target['id'] == oversized_target for target in payload['targets']):
                return 10000
            return 100

        def complete(self, number, name, messages, **kwargs):
            payload = json.loads(messages[-1]['content'])
            self.requests.append(payload)
            assert payload['feedback'] is None
            targets = payload['targets']
            raw = response(targets[0]['id'])
            raw['concepts'][0].update(evidence_lines=targets[0]['evidence_lines'], predicate='', strategies={})
            if len(self.requests) > 1:
                raw['inputs'] = []
            return ModelResponse(json.dumps(raw), finish_reason='stop')

    ctx = context(tmp_path, Calls())
    ctx.packet['prompt_tokens'] = {'plain': ctx.settings.context_tokens}
    ctx.cohort_task['programs'] = [{**program(), 'id': f'p{n}'} for n in range(7)]
    arm = ControlFlowArm()
    monkeypatch.setattr(arm, 'trace', lambda ctx, pr, calls, **kwargs: [
        {'domain': 'valid', 'status': 'executed', 'coverage': {'lines': [3, 7]}} for _ in calls
    ])
    result = MethodInputGenerator((PlainArm(), arm)).generate(ctx)
    assert result['arms']['plain']['status'] == 'prompt_too_large'
    batch = result['arms']['control_flow']
    prompts = ctx.calls.requests
    assert [len(row['targets']) for row in prompts] == expected_batch_sizes
    analysis = ctx.artifacts.read('tasks/0/control_flow/analysis.json')
    targets = [target for row in analysis['programs'] for target in row['targets']]
    dropped = [target['id'] for target in targets
               if target['program_id'] in blocked_puts or target['id'] == oversized_target]
    assert analysis['context_dropped_target_ids'] == dropped
    assert [target['id'] for row in prompts for target in row['targets']] == [
        target['id'] for target in targets if target['id'] not in dropped
    ]
    assert [row['program_id'] for row in batch['candidate_receipts']] == [
        program['id'] for prompt in prompts for program in prompt['programs']
    ]
    assert batch['target_puts_without_trace'] == blocked_puts
    assert analysis['context_blocked_put_ids'] == blocked_puts


def test_tool_draw_budget_is_separate_from_llm_trace_budget(tmp_path, monkeypatch):
    from final.src.modular.control_flow import ControlFlowArm, ControlFlowSettings

    class Calls:
        def token_count(self, messages):
            return 100

        def complete(self, number, name, messages, **kwargs):
            target = json.loads(messages[-1]['content'])['targets'][0]
            raw = response(target['id'])
            raw['concepts'][0]['strategies'] = {
                'xs': {'kind': 'sampled', 'values': [[1, 2]]},
                'k': {'kind': 'int', 'min': -10000, 'max': -1},
            }
            return ModelResponse(json.dumps(raw), finish_reason='stop')

    arm = ControlFlowArm(ControlFlowSettings(rounds=2, candidate_limit=1))
    monkeypatch.setattr(arm, 'trace', lambda ctx, program, records, **kwargs: [
        {'domain': 'valid', 'status': 'executed'} for _ in records
    ])
    batch = arm.run(context(tmp_path, Calls()))

    assert [row['llm_candidate_count'] for row in batch['rounds']] == [1, 0]
    assert [sum(receipt['draws'] for receipt in row['sampling']) for row in batch['rounds']] == [20, 20]
    assert all(row['sampled_candidate_count'] > 0 for row in batch['rounds'])
    assert len(batch['candidate_receipts']) == 1 + sum(row['sampled_candidate_count'] for row in batch['rounds'])


def test_no_gaps_makes_no_model_call(tmp_path):
    from final.src.modular.control_flow import ControlFlowArm
    class Calls:
        def token_count(self,messages):raise AssertionError('No prompt needed')
        def complete(self,*args,**kwargs):raise AssertionError('No gaps')
    ctx=context(tmp_path,Calls())
    ctx.cohort_task['programs'][0]['base']['coverage']={
        'lines':list(range(1,9)), 'arcs':[[1,-1],[2,3],[2,4],[3,-1],[4,5],[5,6],[6,7],[6,8],[7,-1],[8,-1]]}
    assert ControlFlowArm().run(ctx)['status']=='no_measured_gaps'


def test_baseline_replay_includes_recorded_call_33(tmp_path):
    from final.src.modular.control_flow import ControlFlowArm
    class Calls:
        def token_count(self,messages):return 100
        def complete(self,*args,**kwargs):return ModelResponse('{"concepts":[],"inputs":[]}',finish_reason='stop')
    ctx=context(tmp_path,Calls())
    base=ctx.cohort_task['programs'][0]['base']
    base.pop('coverage');base['calls']*=32
    base['calls'].append({'args':'([1,1,2],2)','kwargs':'{}'})
    arm=ControlFlowArm()
    # Use real sandbox baseline replay; no model or benchmark oracle.
    arm.run(ctx)
    analysis=ctx.artifacts.read('tasks/0/control_flow/analysis.json')['programs'][0]
    assert not any(t.get('arc')==[6,7] for t in analysis['targets'])
    assert analysis['baseline']['recorded_calls']==33


def test_duplicate_input_keeps_new_concept_provenance(tmp_path):
    from final.src.modular.control_flow import ControlFlowArm
    class Calls:
        def __init__(self):self.count=0
        def token_count(self,messages):return 100
        def complete(self,number,name,messages,**kwargs):
            self.count+=1;payload=json.loads(messages[-1]['content'])
            target = (
                next(t for t in payload['targets'] if t.get('arc') == [6, 7])
                if self.count == 1 else payload['targets'][0]
            )
            raw=response(target['id']);raw['concepts'][0]['strategies']={}
            raw['concepts'][0]['id']='concept'+str(self.count)
            raw['inputs'][0]['concept_id']='concept'+str(self.count)
            return ModelResponse(json.dumps(raw),finish_reason='stop')
    batch=ControlFlowArm().run(context(tmp_path,Calls()))
    check=batch['rounds'][1]['concept_checks'][0]
    assert check['predicate_checks']
    assert not check['realized_candidate_keys']
    assert len(batch['candidate_receipts'])==1


def test_trace_uses_singleton_sandboxes(tmp_path,monkeypatch):
    from final.src.modular.control_flow import arm as module
    sizes=[]
    def execute(job):
        sizes.append(len(job['tests']))
        return {'tests':[{'domain':'unknown','status':'timeout'}]}
    monkeypatch.setattr(module,'execute',execute)
    observations=module.ControlFlowArm.trace(context(tmp_path),program(),[
        {'args':'([],1)','kwargs':'{}'},{'args':'([],2)','kwargs':'{}'}])
    assert sizes==[1,1] and len(observations)==2


def test_c_level_hard_timeout_becomes_unknown_trace():
    from final.src.runtime.execution import execute
    source='import hashlib\ndef f(x):\n    return hashlib.pbkdf2_hmac("sha256", b"x", b"y", x)\n'
    result=execute({'mode':'control_flow','source':source,'entry':'f',
        'context':'def f(x):\n    """Engineering timeout fixture."""\n',
        'contract':'', 'timeout':.01,'tests':[{'args':'(2147483647,)','kwargs':'{}'}]})['tests'][0]
    assert result['status']=='timeout' and result['domain']=='unknown'
    assert result['timeout_source']=='sandbox_wall_guard'
    assert 'coverage' not in result


@pytest.mark.parametrize('predicate',['sum([1,2]) == 3', 'len(xs) > 0 and sum([1,2]) == 3'])
def test_constant_example_is_not_an_input_predicate(predicate):
    from final.src.modular.control_flow.analysis import analyze
    from final.src.modular.control_flow.schema import parse_response
    targets=analyze(program(),'f')['targets']
    raw=response(targets[0]['id']);raw['concepts'][0]['predicate']=predicate
    parsed=parse_response(raw,targets,['xs','k'])
    assert not parsed['concepts']
    assert 'predicate_clause_must_depend_on_input' in str(parsed['errors'])
    assert parsed['inputs']


def test_retry_repairs_invalid_concept_after_all_targets_hit(tmp_path):
    from final.src.modular.control_flow import ControlFlowArm
    class Calls:
        def __init__(self):self.count=0
        def token_count(self,messages):return 100
        def complete(self,number,name,messages,**kwargs):
            self.count+=1;payload=json.loads(messages[-1]['content'])
            raw=response(payload['targets'][0]['id'])
            raw['inputs']=[{'arguments':{'xs':[],'k':0}}, {'arguments':{'xs':[1,2],'k':2}}]
            if self.count==1:raw['concepts'][0]['predicate']='sum([1,2]) == 3'
            return ModelResponse(json.dumps(raw),finish_reason='stop')
    calls=Calls();batch=ControlFlowArm().run(context(tmp_path,calls))
    assert calls.count==2
    assert batch['rounds'][0]['errors']
    assert not batch['rounds'][1]['errors']
    assert batch['target_coverage']['covered'] == batch['target_coverage']['total']


@pytest.mark.parametrize('target_count, expected_suite_budget', [
    (4, 20),
    (10, 20),
    (15, 25),
])
def test_suite_input_budget_scales_with_selected_targets(
    tmp_path, monkeypatch, target_count, expected_suite_budget,
):
    from final.src.modular.control_flow import ControlFlowArm, ControlFlowSettings

    targets = [
        {'id': f'p0:C1:{line}', 'program_id': 'p0', 'criterion': 'C1',
         'line': line, 'evidence_lines': [line]}
        for line in range(1, target_count + 1)
    ]

    class Calls:
        def __init__(self):
            self.round_index = 0

        def token_count(self, messages):
            return 100

        def complete(self, number, name, messages, **kwargs):
            payload = json.loads(messages[-1]['content'])
            target = payload['targets'][0]
            raw = response(target['id'])
            raw['concepts'][0].update(evidence_lines=target['evidence_lines'], predicate='', strategies={})
            offset = self.round_index * 20
            self.round_index += 1
            raw['inputs'] = [
                {'arguments': {'xs': [offset + idx], 'k': 1}, 'concept_id': 'distinct_equal'}
                for idx in range(20)
            ]
            return ModelResponse(json.dumps(raw), finish_reason='stop')

    ctx = TaskContext(
        {'task_id': 'HumanEval/0', 'entry_point': 'f', 'prompt': SPEC, 'test': ''},
        {'contract': '    assert isinstance(xs, list)\n    assert isinstance(k, int)\n'},
        ArtifactStore(tmp_path),
        PipelineSettings(input_budget=20, input_tokens=4096),
        Calls(),
        cohort_task={'generated': 1, 'programs': [program()]},
        packet={'visible_put_ids': ['p0'], 'common': ''},
    )
    arm = ControlFlowArm(ControlFlowSettings(rounds=2, target_limit=6, candidate_limit=64))
    monkeypatch.setattr(arm, '_analyze_programs', lambda *args: ([{
        'program_id': 'p0', 'source_sha256': 'fixture',
        'coverage_status': 'measured',
        'targets': targets,
    }], []))
    monkeypatch.setattr(arm, 'trace', lambda context, program, records: [
        {'domain': 'valid', 'status': 'executed', 'coverage': {'lines': [1]}}
        for _ in records
    ])
    result = arm.run(ctx)
    assert result['suite_input_budget'] == expected_suite_budget
    assert len(result['inputs']) == expected_suite_budget
