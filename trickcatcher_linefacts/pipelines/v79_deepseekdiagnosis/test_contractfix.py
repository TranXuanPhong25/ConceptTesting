import ast
import json
import time
import pytest
from .semantic_contract import writer_packet,admit
from .literal_contract import parse_expected
from .frozen_score import normalize_slot
from .pipeline import final_audit,admission_gate
from .construction import replay
from .joint_constructor import verify_input


REQ={'case_id':'fixture','source':'def f(x):\n    """Return x plus one."""\n    if x == 1: return 2\n    return x-1\n',
     'entry':'f','spec':'Return x plus one.','public_examples':[{'arguments':'(1,)','expected':'2'}]}


def proposal(request=REQ):
    packet=writer_packet(request)
    site=next(s for s in packet['sites']if s['kind']=='BinOp')
    return {'site_id':site['id'],'spec_clause_id':packet['spec_clauses'][0]['id'],
            'family':'OPERATOR','required_relation':'add one','observed_relation':'subtract one',
            'priority':3,'trigger':{'op':'eq','left':{'op':'input','arg':0},'right':{'op':'literal','value':2}},
            'event_predicate':{'op':'literal','value':True},'alternative':'x+1',
            'alternative_rationale':'The spec requires adding one; replacing subtraction with addition satisfies that relation.'}


def test_model_packet_has_executable_grammar_and_source_bound_clauses():
    packet=writer_packet(REQ);p=proposal()
    assert 'INTEGER 0..3'in packet['hypothesis_fields']['priority']
    assert packet['writer_schema']=='v71_claim_trigger_edit'
    assert 'predicate_grammar' not in packet
    good,bad=admit(REQ,[p]);assert len(good)==1 and not bad
    assert good[0]['spec_quote']==REQ['spec'] and good[0]['semantic_status']=='unverified'
    changed=dict(REQ,spec='Return x plus two.')
    assert admit(changed,[p])[1][0]['reason']=='ValueError:spec_clause_binding'
    assert not admit(REQ,[dict(p,priority='high')])[0]
    assert not admit(REQ,[dict(p,trigger='x == 2')])[0]


def test_json_literal_types_are_preserved_by_audit_and_scorer():
    for raw,expected in [(2,2),(True,True),(None,None),([1,False],[1,False]),('2',2),("'2'",'2')]:
        value=parse_expected(raw);assert type(value)is type(expected)and value==expected
        item={'arguments':'(2,)','expected':raw}
        row=normalize_slot({'raw_status':'present','raw':item})
        assert row['parse_status']=='parsed'and type(row['expected'])is type(expected)
        assert final_audit(REQ,[item],[])['rows'][0]['status']=='parsed'
    for value in ('abc',float('nan'),float('inf')):
        with pytest.raises((ValueError,SyntaxError)):parse_expected(value)


def test_plain_probe_has_no_branch_instrumentation_cap():
    source='def f(x):\n    total=0\n    for i in range(x):\n        if i>=0: total+=1\n    return total\n'
    observed=replay(source,'f',(2000,),None)
    assert observed['put']['status']=='ok'and observed['put']['output']['repr']=='2000'
    assert not observed['put']['branches']and not any(observed['put']['capture'].values())


def test_trace_overflow_retains_output_but_cannot_certify():
    req=dict(REQ,source='def f(x):\n    """Return x plus one."""\n    total=0\n    for i in range(x):\n        if i>=0: total=total+1\n    return total\n')
    p=proposal(req);p.update(trigger={'op':'literal','value':True},alternative=None)
    good,bad=admit(req,[p]);assert good and not bad
    observed=verify_input(req,good[0],(700,),{'repeat_seeds':[1,2],'repeats_per_program_seed':2},time.monotonic()+8)
    assert observed['normal']and observed['event_unknown']and observed['output_sensitivity']=='unknown'
    assert observed['observations'][0]['put']['output']['repr']=='700'


def test_gate_blocks_schema_only_without_native_realization(monkeypatch,tmp_path):
    import importlib
    pipeline=importlib.import_module(__package__+'.pipeline')
    monkeypatch.setattr(pipeline,'prepare_case',lambda *args:([{'id':'fixture'}],[],{'records':[],'candidates_tested':0}))
    requests=[dict(REQ,case_id=str(i))for i in range(6)]
    gate=admission_gate(None,requests,tmp_path)
    assert not gate['passed']and all(row['admitted']==1 for row in gate['rows'])


def test_gate_reuses_writer_slot_and_constructs_native_witness(tmp_path):
    from .pipeline import prepare_case
    from .test_pipeline import Client
    class Writer(Client):
        def complete(self,messages,max_tokens,seed):
            self.calls+=1
            return {'content':json.dumps({'hypotheses':[writer_proposal()]}),'finish_reason':'stop','input_tokens':1,'output_tokens':1}
    client=Writer();first=prepare_case(client,REQ,tmp_path)
    assert first[0]and first[2]['candidates_tested']>0
    assert prepare_case(client,REQ,tmp_path)==first and client.calls==1


def test_digit_string_construction_uses_public_character_category():
    from .joint_constructor import solve_inputs
    predicate={'op':'eq','left':{'op':'input','arg':0},'right':{'op':'literal','value':'909'}}
    solved=solve_inputs([('123',)],predicate,time.monotonic()+3)
    assert ('909',)in solved['inputs']
    assert solved['domain']['input_profiles'][0]['alphabet']==list(range(48,58))


def writer_proposal(request=REQ):
    p=proposal(request)
    p['trigger']='arg0 == 2'
    p['event_condition']='True'
    p.pop('event_predicate')
    p['edit']={'kind':'operator','operator':'+'}
    p.pop('alternative')
    return p
