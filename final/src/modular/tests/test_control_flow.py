"""Control-flow engineering checks on authored functions, not benchmark runs."""
import json

import pytest

from final.src.core_model import ModelResponse
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
        ArtifactStore(tmp_path), PipelineSettings(input_budget=4, input_tokens=4096), calls,
        cohort_task={'generated':1, 'programs':[program()]},
        packet={'visible_put_ids':['p0'], 'common':''})


def test_analysis_binds_uncovered_branch_to_guards_and_def_use():
    from final.src.modular.control_flow.analysis import analyze
    result = analyze(program(), 'f')
    target = next(t for t in result['targets'] if t.get('arc') == [6, 7])
    assert target['criterion'] == 'C2'
    assert [2, 4] in [step['arc'] for step in target['path']]
    assert 'count = len(unique)' in str(target['path'])
    assert any(e['variable']=='count' and e['definition']==5 and e['use']==6 for e in result['def_use'])
    assert any(e['variable']=='unique' and e['definition']==4 and e['use']==5 for e in result['def_use'])
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
    from final.src.modular.arms.control_flow import ControlFlowArm
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
    from final.src.modular.arms import selected_arms, default_arms
    assert selected_arms(['control_flow'])[0].name=='control_flow'
    assert [a.name for a in default_arms()]==['plain']


def test_unknown_graph_keeps_cfg_obligations(monkeypatch):
    from python_graphs import program_graph
    from final.src.modular.control_flow.analysis import analyze
    def unsupported(_):raise NotImplementedError('authored unsupported syntax')
    monkeypatch.setattr(program_graph, 'get_program_graph', unsupported)
    result=analyze(program(),'f')
    assert result['data_flow_status']=='unsupported'
    assert result['targets'] and result['coverage_status']=='measured'


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
    from final.src.modular.arms.control_flow import ControlFlowArm, ControlFlowSettings
    class Calls:
        def token_count(self,messages):return 100
        def complete(self,*args,**kwargs):
            return ModelResponse(json.dumps(response('invented')),finish_reason='stop')
    batch=ControlFlowArm(ControlFlowSettings(rounds=1)).run(context(tmp_path, Calls()))
    assert not batch['concepts'] and batch['errors']
    assert batch['inputs'][0]['args']=='([1, 1, 2], 2)'


def test_tiny_candidate_budget_counts_native_pairs(tmp_path):
    from final.src.modular.arms.control_flow import ControlFlowArm, ControlFlowSettings
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
    assert len(batch['candidate_receipts']) <= 1


def test_no_gaps_makes_no_model_call(tmp_path):
    from final.src.modular.arms.control_flow import ControlFlowArm
    class Calls:
        def token_count(self,messages):raise AssertionError('No prompt needed')
        def complete(self,*args,**kwargs):raise AssertionError('No gaps')
    ctx=context(tmp_path,Calls())
    ctx.cohort_task['programs'][0]['base']['coverage']={
        'lines':list(range(1,9)), 'arcs':[[1,-1],[2,3],[2,4],[3,-1],[4,5],[5,6],[6,7],[6,8],[7,-1],[8,-1]]}
    assert ControlFlowArm().run(ctx)['status']=='no_measured_gaps'


def test_baseline_replay_includes_recorded_call_33(tmp_path):
    from final.src.modular.arms.control_flow import ControlFlowArm
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
    from final.src.modular.arms.control_flow import ControlFlowArm
    class Calls:
        def __init__(self):self.count=0
        def token_count(self,messages):return 100
        def complete(self,number,name,messages,**kwargs):
            self.count+=1;payload=json.loads(messages[-1]['content'])
            target=next(t for t in payload['targets'] if t.get('arc')==[6,7])
            raw=response(target['id']);raw['concepts'][0]['strategies']={}
            raw['concepts'][0]['id']='concept'+str(self.count)
            raw['inputs'][0]['concept_id']='concept'+str(self.count)
            return ModelResponse(json.dumps(raw),finish_reason='stop')
    batch=ControlFlowArm().run(context(tmp_path,Calls()))
    check=batch['rounds'][1]['concept_checks'][0]
    assert check['realized_candidate_keys'] and check['predicate_checks']
    assert len(batch['candidate_receipts'])==1


def test_trace_uses_singleton_sandboxes(tmp_path,monkeypatch):
    import final.src.modular.arms.control_flow as module
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


def test_contract_feedback_runs_when_target_hits_but_concept_is_invalid(tmp_path):
    from final.src.modular.arms.control_flow import ControlFlowArm
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
