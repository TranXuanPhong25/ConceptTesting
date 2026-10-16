"""Offline tests for real-transport contracts. Reply data are hand-authored, not Qwen results."""
import json
from pathlib import Path
import pytest
from . import source_view,prompt_aliases,pilot_fixtures,chain_prompts,schemas
from .chain_store import Store
from .online_transport import OnlineTransport,ProtocolMismatch,TransportIncomplete
from .execution_adapter import execute
from .chain_inputs import typed_value,parse_literal


def test_fixture_count_labels_and_no_context_leakage():
    rows=pilot_fixtures.cases();assert len(rows)==16 and sum(r['evaluator']['probe_applicable'] for r in rows)==7
    for row in rows:
        task=source_view.prepare(row['source'],row['entry'],row['base'],valid_code=row['valid_code'])
        for stage in ('S1','S2'):
            text=chain_prompts.messages(stage,task,{},[])[1]['content']
            assert 'probe_applicable' not in text and 'critical_items' not in text and 'required_output' not in text


def test_alias_mapping_is_bijective_and_does_not_rewrite_prose():
    row=pilot_fixtures.cases()[0];task=source_view.prepare(row['source'],'f')
    oid=schemas.namespace(task['task_hash'],'S1',1,'O1');artifact={'S1':{'items':[dict(id=oid,local_id='O1',statement=oid)]}}
    view,art,_,back=prompt_aliases.view(task,artifact,[])
    assert art['S1']['items'][0]['id']=='O1' and art['S1']['items'][0]['statement']==oid
    assert len(back)==len(set(back.values()))
    decoded=prompt_aliases.expand('S2',dict(items=[dict(id='B1',source_ids=['N1'],statement='N1')]),back)
    assert decoded['items'][0]['source_ids']==[task['nodes'][0]['id']] and decoded['items'][0]['statement']=='N1'
    with pytest.raises(ValueError):prompt_aliases.expand('S2',dict(items=[dict(source_ids=['N999'])]),back)


def test_protocol_failure_remains_quarantined_on_cache_resume(tmp_path):
    from .source_view import digest
    from .paths import CONFIG
    c=CONFIG['chain'];payload=dict(model=c['model'],temperature=0,top_p=1,max_tokens=c['max_tokens']['S1'],seed=1,messages=[])
    request=dict(key=digest(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':'))),payload=payload,stage='S1',task_hash='a'*64,input_tokens=10)
    class HandAuthoredProtocolReply:
        def __init__(self):self.calls=0
        def call(self,*a,**kw):
            self.calls+=1
            return dict(choices=[dict(message=dict(content='{}'),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=9999))
        def redact(self,x):return x
    connection=HandAuthoredProtocolReply();transport=OnlineTransport(connection,tmp_path/'calls.jsonl');store=Store(tmp_path/'requests')
    with pytest.raises(ProtocolMismatch):transport.completion(request,store)
    assert store.load(request['key'])['protocol_failure']
    with pytest.raises(TransportIncomplete):OnlineTransport(connection,tmp_path/'calls.jsonl').completion(request,Store(tmp_path/'requests'))
    assert connection.calls==1 and len(store.load(request['key'])['attempts'])==1


@pytest.mark.parametrize('index',[1,3,5,7,9,11,15])
def test_authored_discriminating_witness_is_consistent_with_fixture(index,tmp_path):
    row=pilot_fixtures.cases()[index];task=source_view.prepare(row['source'],'f',row['base'],valid_code=row['valid_code'])
    result=execute(task,row['evaluator']['witness'],[],tmp_path)
    actual=row['evaluator']['actual_output']
    assert result['native_checked']
    if actual.startswith('exception:'):assert result['exception_type']==actual.split(':',1)[1]
    else:assert typed_value(parse_literal(result['output_repr'],output=True))==typed_value(parse_literal(actual,output=True))


@pytest.mark.parametrize('index',range(16))
def test_public_base_example_runs_on_both_pair_members(index,tmp_path):
    import ast
    row=pilot_fixtures.cases()[index];task=source_view.prepare(row['source'],'f',row['base'],valid_code=row['valid_code'])
    assertion=ast.parse(row['base']).body[0];comparison=assertion.test;call=comparison.left
    args=tuple(ast.literal_eval(x) for x in call.args);expected=ast.literal_eval(comparison.comparators[0])
    result=execute(task,repr(args),[],tmp_path)
    assert result['native_checked'] and result['status']=='ok'
    assert typed_value(parse_literal(result['output_repr'],output=True))==typed_value(expected)
