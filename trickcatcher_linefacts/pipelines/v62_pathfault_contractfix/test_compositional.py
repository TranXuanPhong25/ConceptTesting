import ast
import time
from .predicates import evaluate,validate
from .joint_constructor import solve_inputs,construct_case
from .semantic_contract import writer_packet,admit


def lit(x):return {'op':'literal','value':x}
def inp(i):return {'op':'input','arg':i}
def length(i):return {'op':'len','value':inp(i)}
def eq(a,b):return {'op':'eq','left':a,'right':b}


def test_joint_string_integer_predicate_is_solved_together():
    p={'op':'and','items':[eq(length(0),{'op':'add','left':inp(1),'right':lit(2)}),{'op':'lt','left':lit(0),'right':inp(1)}]}
    result=solve_inputs([('a',99)],p,time.monotonic()+2)
    assert result['inputs'] and all(len(s)==k+2 and k>0 for s,k in result['inputs'])


def test_nested_sequence_profile_runs_without_opaque_type_rejection():
    p=eq(length(0),lit(3))
    result=solve_inputs([([[1,2]],1)],p,time.monotonic()+2)
    assert result['inputs'] and all(len(args[0])==3 and all(len(point)==2 for point in args[0]) for args in result['inputs'])


def test_writer_uses_tool_ids_and_rejects_invented_binding():
    req={'case_id':'fixture','source':'def f(x):\n    """Return x plus one."""\n    return x+1\n','entry':'f','spec':'Return x plus one.','public_examples':[{'arguments':'(1,)','expected':'2'}]}
    packet=writer_packet(req)
    site=next(n for n in packet['sites'] if n['kind']=='BinOp')
    p={'site_id':site['id'],'family':'OPERATOR','required_relation':'x+1','observed_relation':'x+1',
       'spec_quote':'Return x plus one.','trigger':eq(inp(0),lit(2)),'priority':1,'alternative':'x-1'}
    accepted,rejected=admit(req,[p,dict(p,site_id='invented')])
    assert len(accepted)==1 and len(rejected)==1 and accepted[0]['semantic_status']=='unverified'
    cfg={'max_case_seconds':3,'repeat_seeds':[1,2],'repeats_per_program_seed':2}
    report=construct_case(req,accepted,cfg)
    assert report['records'][0]['runs'][0]['output_sensitivity']is True


def test_predicate_ir_rejects_arbitrary_calls():
    import pytest
    with pytest.raises(ValueError):validate({'op':'call','function':'eval'},1)


def test_scalar_search_enumerates_multiple_models_not_one_arbitrary_value():
    p={'op':'lt','left':lit(0),'right':inp(0)}
    result=solve_inputs([(1,)],p,time.monotonic()+2)
    assert len(result['inputs'])>=2 and result['queries']>=2


def test_string_literal_equality_uses_codepoints_and_rechecks_native_predicate():
    result=solve_inputs([('x',)],eq(inp(0),lit('abc')),time.monotonic()+2)
    assert ('abc',)in result['inputs']


def test_explicit_local_event_and_final_replay_detect_masking():
    from .pipeline import final_audit
    req={'case_id':'local','source':'def f(x):\n    """Return x plus one."""\n    n=x\n    return n+1\n','entry':'f',
         'spec':'Return x plus one.','public_examples':[{'arguments':'(1,)','expected':'2'}]}
    site=next(n for n in writer_packet(req)['sites']if n['kind']=='BinOp')
    proposal={'site_id':site['id'],'family':'BOUNDARY','required_relation':'x+1','observed_relation':'n+1',
              'spec_quote':'Return x plus one.','trigger':{'op':'literal','value':True},
              'event_predicate':eq({'op':'local','name':'n'},lit(3)),'priority':1,'alternative':'n-1'}
    accepted,rejected=admit(req,[proposal]);assert accepted and not rejected
    audit=final_audit(req,[{'arguments':'(3,)','expected':'4'},{'arguments':'(4,)','expected':'5'}],accepted)
    yes,no=[r['realization'][0]for r in audit['rows']]
    assert yes['event_realized'] and yes['output_sensitivity']is True
    assert not no['event_realized'] and no['output_sensitivity']=='unknown'
