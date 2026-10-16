"""Adversarial offline contract checks. Hand-authored responses are not Qwen outputs."""
import ast
import copy
import json
from pathlib import Path
import pytest
from . import source_view as sv,schemas as s,chain_prompts as cp
from .chain import OfflineChain
from .chain_store import Store
from .chain_inputs import parse_literal,parse_arguments,check_topology,literal_for_transport
from .evidence import compare_prediction,project_feedback
from .execution_adapter import execute

SOURCE='''"""MODULE_SECRET"""
# COMMENT_SECRET 平
literal = "executable#data"
def helper(x):
    """HELPER_SECRET"""
    return x
def f(xs):
    """SPEC_SECRET: preserve eligible duplicate occurrences."""
    return sorted(set(xs))
'''


@pytest.fixture
def task():return sv.prepare(SOURCE,'f','BASE_ONLY_SENTINEL')


def counter(messages):return sum(len(x['content']) for x in messages)  # Explicit test-only character counter.


def send(chain,stage,obj,**kw):return chain.ingest_fixture(stage,json.dumps(obj),count_tokens=counter,context_window=100000,**kw)


def objects(task,registry=None):
    registry=registry or {};nodes=task['nodes'];return_id=max((x for x in nodes if x['kind']=='Return'),key=lambda x:x['span'][0])['id']
    one=dict(status='ok',reason='',items=[dict(id='O1',statement='arbitrary open vocabulary concept',quote=task['spec'],span=[0,len(task['spec'])],domain='input domain',eligibility=None,relation='candidate relation',ambiguity='',applicability='all valid inputs')])
    two=dict(status='ok',reason='',items=[dict(id='B1',statement='candidate code behavior',source_ids=[return_id],guard='unconditional',effect='candidate observable effect',uncertainty='')])
    oid=s.namespace(task['task_hash'],'S1',1,'O1');bid=s.namespace(task['task_hash'],'S2',1,'B1');hid=s.namespace(task['task_hash'],'S3',1,'H1')
    three=dict(status='ok',reason='',items=[dict(id='H1',statement='candidate mismatch',obligation_ids=[oid],behavior_ids=[bid],source_ids=[return_id],condition='duplicates',effect='candidate count change',alternative='other interpretation',uncertainty='')],selected_ids=['H1'])
    probe=dict(id='P1',input_repr="(['aa', 'aa'],)",hypothesis_ids=[hid],domain_justification='literal input',prediction=dict(kind='exact_value',value_repr="['aa']"),observe=[dict(source_id=return_id,kind='statement_reach')])
    four=dict(status='ok',reason='',items=[probe])
    five=dict(status='ok',reason='',items=[dict(probe,id='P1')],decisions=[dict(id='H1',supersedes=hid,decision='keep',statement='candidate only',evidence_ids=['F1'],condition='duplicates',uncertainty='not an oracle')])
    return one,two,three,four,five


def through3(task,tmp_path):
    chain=OfflineChain(task,tmp_path);one,two,three,_,_=objects(task)
    assert send(chain,'S2',two)['state']=='valid';assert send(chain,'S1',one)['state']=='valid';assert send(chain,'S3',three)['state']=='valid'
    return chain


def test_source_mask_retains_original_byte_coordinates_and_executable_strings(task):
    masked=task['source_masked'];raw=SOURCE.encode();view=masked.encode()
    assert len(raw)==len(view)
    assert [i for i,x in enumerate(raw) if x in (10,13)]==[i for i,x in enumerate(view) if x in (10,13)]
    for secret in ('MODULE_SECRET','COMMENT_SECRET','HELPER_SECRET','SPEC_SECRET'):assert secret not in masked
    assert 'executable#data' in masked and 'def helper' in masked
    for n in task['nodes']:
        if n['kind']=='Return':
            line=SOURCE.split('\n')[n['span'][0]-1].encode();vline=masked.split('\n')[n['span'][0]-1].encode()
            assert line[n['span'][1]:n['span'][3]]==vline[n['span'][1]:n['span'][3]]


@pytest.mark.parametrize('separator',['\u2028','\u0085'])
def test_unicode_separator_is_not_a_physical_source_line(separator):
    source='def f(xs):\n    """spec a'+separator+'b"""\n    return xs # hidden'+separator+'tail\n'
    task=sv.prepare(source,'f')
    assert 'hidden' not in task['source_masked'] and 'tail' not in task['source_masked']
    assert len(source.encode())==len(task['source_masked'].encode())
    assert next(n for n in task['nodes'] if n['kind']=='Return')['span'][0]==3


def test_crlf_mapping_and_standalone_cr_rejection():
    task=sv.prepare('def f(x):\r\n """spec"""\r\n return x # hidden\r\n','f')
    assert task['source_masked'].count('\r\n')==3 and 'hidden' not in task['source_masked']
    with pytest.raises(ValueError,match='CR'):sv.prepare('def f(x):\r return x','f')


def test_source_parse_size_depth_fail_closed():
    for source in ['x'*65537,'def f(x):\n return '+' + '.join(['x']*2000),'def f(x):\n return '+ '('*1000+'x'+')'*1000]:
        with pytest.raises(ValueError):sv.prepare(source,'f')


def test_contexts_are_explicit_and_s1_s2_independent(task):
    fake={'S1':{'S1_PRIVATE_SENTINEL':True},'S2':{'B1_PRIVATE_SENTINEL':True}}
    first=cp.messages('S1',task,fake,[])[1]['content'];second=cp.messages('S2',task,fake,[])[1]['content']
    assert 'SPEC_SECRET' in first and 'BASE_ONLY_SENTINEL' in first and 'sorted(set' not in first
    assert 'SPEC_SECRET' not in second and 'BASE_ONLY_SENTINEL' not in second and 'S1_PRIVATE' not in second
    assert 'sorted(set' in second and 'def helper' in second


@pytest.mark.parametrize('raw',['[]','null','{} {}','prefix {"a":1} suffix','```json\n{}\n```\n```json\n{}\n```','{"a":1,"a":2}'])
def test_ambiguous_or_nonobject_json_rejected(raw):
    with pytest.raises(s.ArtifactError):s.extract(raw)


def test_unique_fenced_json_offsets_and_truncation():
    raw='Explanation\n```json\n{"a":1}\n```\nDone'
    obj,span=s.extract(raw);assert obj=={'a':1} and raw[span[0]:span[1]]=='{"a":1}'
    with pytest.raises(s.ArtifactError,match='truncated'):s.extract('{"a":1}',finish_reason='length')


def test_schema_quote_uses_decoded_characters_and_no_semantic_catalog(task):
    obj=objects(task)[0];obj['items'][0]['statement']='RECENT_WINDOW_AND_COVERAGE concept not in a static registry'
    s.validate('S1',obj,task,{})
    obj['items'][0]['span']=[1,len(task['spec'])]
    with pytest.raises(s.ArtifactError,match='quote'):s.validate('S1',obj,task,{})


def test_reference_cross_task_stage_and_unknown_ids_rejected(task,tmp_path):
    chain=through3(task,tmp_path);four=objects(task)[3]
    for reference in ['other:S3:v1:H1',s.namespace(task['task_hash'],'S1',1,'O1'),s.namespace(task['task_hash'],'S3',2,'H1')]:
        bad=copy.deepcopy(four);bad['items'][0]['hypothesis_ids']=[reference]
        with pytest.raises(s.ArtifactError):s.validate('S4',bad,task,chain.data['registry'],chain.selected())


def test_malformed_container_fields_raise_validation_errors(task):
    obj=objects(task)[1];obj['items'][0]['source_ids']=[{}]
    with pytest.raises(s.ArtifactError):s.validate('S2',obj,task,{})
    with pytest.raises(s.ArtifactError):s.prediction({'kind':[]})


def test_global_ids_and_s5_revision_preserve_prior_artifact(task,tmp_path):
    chain=through3(task,tmp_path);_,_,_,four,five=objects(task)
    before=copy.deepcopy(chain.data['registry'][chain.selected()[0]])
    assert send(chain,'S4',four)['state']=='valid'
    slots=chain.input_slots('S4')
    chain.attach_feedback([dict(slots[0],status='unresolved',reason='offline fixture observation unsupported')])
    assert send(chain,'S5',five)['state']=='valid'
    revised=chain.data['stages']['S5']['artifact']['decisions'][0]
    assert revised['supersedes']==before['id'] and revised['id']!=before['id']
    assert chain.data['registry'][before['id']]==before
    assert revised['obligation_ids']==before['obligation_ids']


def test_failed_upstream_blocks_but_s2_can_still_complete(task,tmp_path):
    chain=OfflineChain(task,tmp_path)
    bad=chain.ingest_fixture('S1','invalid',count_tokens=counter,context_window=100000)
    assert bad['state']=='failed' and chain.status('S3')=='blocked' and chain.status('S2')=='ready'
    assert send(chain,'S2',objects(task)[1])['state']=='valid'
    assert chain.status('S4')=='blocked' and chain.report()['scheduled_slots']==5


def test_legitimate_no_mismatch_is_terminal_not_failure(task,tmp_path):
    chain=OfflineChain(task,tmp_path);one,two,*_=objects(task)
    send(chain,'S1',one);send(chain,'S2',two)
    result=send(chain,'S3',dict(status='abstain',reason='no candidate mismatch supported',items=[],selected_ids=[]))
    assert result['state']=='valid' and chain.status('S4')=='not_applicable' and chain.status('S5')=='not_applicable'


def test_context_overflow_does_not_reserve_request_and_tokens_need_explicit_counter(task,tmp_path):
    chain=OfflineChain(task,tmp_path)
    result=chain.ingest_fixture('S1','{}',count_tokens=counter,context_window=10)
    assert result['reason']=='context_overflow' and not list((tmp_path/'requests').glob('*.json'))
    with pytest.raises(ValueError):cp.request('S1',task,{},[],count_tokens=None,context_window=1000,counter_id='')


def test_cumulative_attempts_resume_pending_cache_and_metadata_drift(task,tmp_path):
    req=cp.request('S1',task,{},[],count_tokens=counter,context_window=100000,counter_id='fixture_counter')
    for i in range(1,4):
        store=Store(tmp_path);r=store.reserve(req);assert r['attempt']==i
        assert store.reserve(req)['state']=='pending_unknown_usage'
        store.finish(req['key'],i,transport_error=True)
    assert Store(tmp_path).reserve(req)['state']=='exhausted'
    other=dict(req,input_tokens=req['input_tokens']+1)
    with pytest.raises(ValueError,match='drift'):Store(tmp_path).reserve(other)


def test_content_failure_does_not_retry_transport(task,tmp_path):
    chain=OfflineChain(task,tmp_path);chain.ingest_fixture('S1','invalid JSON',count_tokens=counter,context_window=100000)
    record=next((tmp_path/'requests').glob('*.json'));data=json.loads(record.read_text())
    assert len(data['attempts'])==1
    resumed=OfflineChain(task,tmp_path)
    assert resumed.status('S1')=='failed'
    assert resumed.ingest_fixture('S1','{}',count_tokens=counter,context_window=100000)['state']=='failed'


@pytest.mark.parametrize('text',['[1,2]','(__import__("os"),)','(float("nan"),)','(1e999,)'])
def test_literal_transport_rejects_code_nonfinite_and_non_tuple(text,task):
    with pytest.raises(ValueError):parse_arguments(text,task['arity'])


def test_alias_cycle_rejected_before_repr_and_positional_defaults():
    xs=[]
    with pytest.raises(ValueError,match='alias'):literal_for_transport((xs,xs))
    xs.append(xs)
    with pytest.raises(ValueError,match='cycle'):check_topology((xs,))
    task=sv.prepare('def f(x,y=1):\n return x+y\n','f')
    assert parse_arguments('(2,)',task['arity'])==(2,)
    with pytest.raises(ValueError,match='arity'):parse_arguments('()',task['arity'])


@pytest.mark.parametrize('expected,actual',[('True','1'),('[1]','(1,)'),('{True: 2}','{1: 2}')])
def test_prediction_is_type_aware(expected,actual):
    result=compare_prediction(dict(kind='exact_value',value_repr=expected),dict(status='ok',native_checked=True,output_capture='literal',output_repr=actual))
    assert result['result']=='observed_contradiction'


def test_relation_prose_timeout_and_oversize_are_unverified():
    assert compare_prediction(dict(kind='relation_text',text='count should be2'),dict(status='ok',native_checked=True))['result']=='unverified'
    assert compare_prediction(dict(kind='exception_type',exception_type='ValueError'),dict(status='timeout',native_checked=True))['result']=='unverified'
    assert compare_prediction(dict(kind='exact_value',value_repr='[1]'),dict(status='ok',native_checked=True,output_capture='oversize'))['result']=='unverified'


def test_feedback_preserves_all_attempts_counterevidence_and_retention():
    rows=project_feedback([dict(proposal_id='a',status='filtered',reason='domain uncertain'),dict(proposal_id='b',status='ok',prediction_check={'result':'observed_contradiction'},execution={'status':'ok','observations':[dict(source_id='x',kind='statement_reach',status='observed',events=[{'line':i} for i in range(5)])]})])
    assert len(rows)==2 and rows[0]['status']=='filtered' and rows[1]['prediction_check']['result']=='observed_contradiction'
    obs=rows[1]['observations'][0];assert obs['events']==[{'line':0},{'line':4}] and obs['omitted_events']==3


def test_feedback_never_omits_a_proposal_and_is_immutable(task,tmp_path):
    chain=through3(task,tmp_path);send(chain,'S4',objects(task)[3]);slots=chain.input_slots('S4')
    with pytest.raises(ValueError,match='all_proposal'):chain.attach_feedback([])
    chain.attach_feedback([dict(slots[0],status='rejected',reason='fixture')])
    with pytest.raises(ValueError,match='immutable'):chain.attach_feedback([dict(slots[0],status='rejected',reason='different')])


def test_probe_cap_and_idempotent_budget(task,tmp_path):
    chain=through3(task,tmp_path);four=objects(task)[3]
    bad=copy.deepcopy(four);bad['items']=[dict(four['items'][0],id='P'+str(i)) for i in range(1,8)]
    with pytest.raises(s.ArtifactError):s.validate('S4',bad,task,chain.data['registry'],chain.selected())
    send(chain,'S4',four);chain.input_slots('S4');chain.input_slots('S4')
    assert chain.report()['unique_inputs']==1 and chain.report()['proposal_slots']['S4']==1


def test_native_fixture_validity_signature_and_statement_not_operation(tmp_path):
    task=sv.prepare('def f(xs):\n return sorted(set(xs))\n','f',valid_code='def valid(xs):\n return isinstance(xs,list)\n')
    ret=next(n['id'] for n in task['nodes'] if n['kind']=='Return');call=next(n['id'] for n in task['nodes'] if n['kind']=='Call')
    result=execute(task,"(['aa', 'aa'],)",[dict(source_id=ret,kind='statement_reach'),dict(source_id=call,kind='operation_value')],tmp_path)
    assert result['native_checked'] and result['output_repr']=="['aa']"
    assert result['observations'][0]['status']=='observed' and result['observations'][1]['status']=='unknown'


def test_native_fixture_mined_filter_reject_keeps_uncertainty(tmp_path):
    task=sv.prepare('def f(xs):\n return xs\n','f',valid_code='def valid(xs):\n return False\n')
    result=execute(task,'([1],)',[],tmp_path)
    assert result['status']=='filtered' and result['native_checked'] is False


def test_duplicate_input_different_observation_keeps_both_proposals_without_extra_execution(task,tmp_path):
    chain=through3(task,tmp_path/'chain');four=objects(task)[3]
    second=copy.deepcopy(four['items'][0]);second['id']='P2';second['observe']=[dict(source_id=task['entry_source_id'],kind='function_output')]
    four['items'].append(second);assert send(chain,'S4',four)['state']=='valid'
    rows=chain.execute_fixture_slots('S4')
    assert len(rows)==2 and all(r['execution']['native_checked'] for r in rows)
    assert len(list((tmp_path/'chain'/'native_executions').glob('*/ordinary_result.json')))==1
    assert len(list((tmp_path/'chain'/'native_executions').glob('*/traced_result.json')))==1
    assert len(chain.data['feedback'])==2 and chain.report()['proposal_slots']['S4']==2


def test_context_drift_rejected_on_resume(task,tmp_path):
    OfflineChain(task,tmp_path)
    different=dict(task,base='different')
    with pytest.raises(ValueError,match='context_drift'):OfflineChain(different,tmp_path)


def test_old_online_client_rejects_before_network(tmp_path):
    from .llm_client import Client
    with pytest.raises(RuntimeError,match='disabled'):Client(tmp_path,offline=False)


def test_s5_covers_every_selected_hypothesis_and_cites_feedback(task,tmp_path):
    chain=through3(task,tmp_path);five=objects(task)[4]
    empty=dict(status='ok',reason='',items=[],decisions=[])
    with pytest.raises(s.ArtifactError,match='per_hypothesis'):s.validate('S5',empty,task,chain.data['registry'],chain.selected(),['F1'])
    five['decisions'][0]['evidence_ids']=[]
    with pytest.raises(s.ArtifactError,match='feedback'):s.validate('S5',five,task,chain.data['registry'],chain.selected(),['F1'])


def test_opaque_values_cannot_verify_native_agreement_and_sets_use_typed_signature(task):
    from .execution_adapter import observe
    opaque=dict(status='ok',exception_type=None,exception_module=None,output_capture='unsupported_or_oversize',output_repr=None,output_signature=None,input_before='x',input_after='x',output_aliases=[],trace_complete=True,events=[])
    assert observe(task,[],opaque,opaque)['native_checked'] is False
    base=dict(opaque,output_capture='literal',output_repr="{'a', 'b'}",output_signature="canonical typed set")
    traced=dict(base,output_repr="{'b', 'a'}")
    assert observe(task,[],base,traced)['native_checked'] is True


def test_worker_failure_reasons_reach_feedback(task):
    from .execution_adapter import observe
    failed=dict(status='unresolved',reason='validity:TypeError',events=[],validity_checks=1,validity_provenance='mined_filter_not_spec_proof')
    result=observe(task,[],failed,failed)
    projected=project_feedback([dict(proposal_id='p',status='unresolved',execution=result)])
    assert projected[0]['execution']['worker_details']['ordinary']['reason']=='validity:TypeError'
    assert projected[0]['execution']['worker_details']['traced']['validity_provenance']=='mined_filter_not_spec_proof'


def test_observation_source_cap_is_per_hypothesis_not_per_probe(task,tmp_path):
    chain=through3(task,tmp_path);four=objects(task)[3];ids=[n['id'] for n in task['nodes']][:3]
    four['items']=[dict(four['items'][0],id='P'+str(i+1),observe=[dict(source_id=uid,kind='statement_reach')]) for i,uid in enumerate(ids)]
    with pytest.raises(s.ArtifactError,match='source_cap'):s.validate('S4',four,task,chain.data['registry'],chain.selected())


def test_request_store_rejects_modified_output_cap_even_if_key_recomputed(task,tmp_path):
    from .chain import sha
    from .source_view import digest
    req=cp.request('S1',task,{},[],count_tokens=counter,context_window=100000,counter_id='fixture')
    req['payload']['max_tokens']=99999
    req['key']=digest(json.dumps(req['payload'],sort_keys=True,ensure_ascii=False,separators=(',',':')))
    with pytest.raises(ValueError,match='budget'):Store(tmp_path).reserve(req)


@pytest.mark.parametrize('raw_surrogate',[False,True])
def test_bad_unicode_content_is_cached_failure_not_coordinator_crash(task,tmp_path,raw_surrogate):
    chain=OfflineChain(task,tmp_path);one=objects(task)[0];one['items'][0]['statement']=chr(0xd800)
    raw=json.dumps(one,ensure_ascii=not raw_surrogate)
    result=chain.ingest_fixture('S1',raw,count_tokens=counter,context_window=100000)
    assert result['state']=='failed' and result['reason']=='invalid_unicode'
    saved=json.loads(next((tmp_path/'requests').glob('*.json')).read_text())
    assert len(saved['attempts'])==1 and saved['attempts'][0]['state']=='response_received'
    assert OfflineChain(task,tmp_path).status('S3')=='blocked'


def test_execution_cache_directory_cannot_change_or_replay(task,tmp_path):
    chain=through3(task,tmp_path/'chain');send(chain,'S4',objects(task)[3]);chain.execute_fixture_slots('S4')
    cache=chain.directory/'native_executions';before={str(p):p.stat().st_mtime_ns for p in cache.glob('*/*result.json')}
    chain.execute_fixture_slots('S4')
    after={str(p):p.stat().st_mtime_ns for p in cache.glob('*/*result.json')};assert after==before and len(after)==2
    with pytest.raises(ValueError,match='directory_drift'):chain.execute_fixture_slots('S4',tmp_path/'different')
    assert not (tmp_path/'different').exists()


def test_complete_five_stage_fixture_roundtrip_and_resume(task,tmp_path):
    chain=through3(task,tmp_path/'chain');_,_,_,four,five=objects(task)
    assert send(chain,'S4',four)['state']=='valid'
    chain.execute_fixture_slots('S4')
    assert chain.data['feedback'][0]['prediction_check']['result']=='observed_match'
    assert send(chain,'S5',five)['state']=='valid';chain.execute_fixture_slots('S5')
    assert chain.report()['unique_inputs']==1 and chain.report()['put_execution_upper_bound']==2
    assert len(list((chain.directory/'native_executions').glob('*/*result.json')))==2
    resumed=OfflineChain(task,tmp_path/'chain');assert resumed.report()==chain.report()
    assert all(resumed.status(stage)=='valid' for stage in s.STAGES)
