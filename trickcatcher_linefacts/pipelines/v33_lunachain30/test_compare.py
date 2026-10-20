"""Meaningful mechanical-compiler and budget regressions; no model calls."""
import copy,json
import pytest
from .test_chain_interfaces import task,objects
from . import schemas,prompt_aliases,compare_interface as ci
from .compare_run import retained,direct_inputs

def compile_fixture(stage,obj):
    if stage in ('S1','S2','S4'):raw=dict(items=obj['items'],summary='fixture explanation')
    elif stage=='S3':raw=dict(comparisons=obj['comparisons'],hypotheses=obj['items'],selected=[1],summary='fixture mismatch')
    else:
        ds=[]
        for d in obj['decisions']:
            d=copy.deepcopy(d);d.pop('id');d['hypothesis_id']=d.pop('supersedes');ds.append(d)
        raw=dict(items=obj['items'],decisions=ds,retain=[],summary='fixture feedback')
    raw=copy.deepcopy(raw)
    for x in raw.get('hypotheses',raw.get('items',[])):x.pop('id')
    return raw

def test_all_stages_compile_into_unchanged_grounded_validator(task):
    registry={};artifacts={};selected=[]
    for stage,obj in zip(schemas.STAGES,objects(task)):
        raw=compile_fixture(stage,obj);compiled=ci.compile_output(stage,raw,artifacts)
        schemas.validate(stage,compiled,task,registry,selected,['F1'])
        artifact=schemas.register(stage,compiled,task['task_hash'],registry);artifacts[stage]=artifact
        if stage=='S3':selected=artifact['selected_ids']
    assert artifacts['S2']['items'][0]['local_id']=='B1'
    assert artifacts['S5']['decisions'][0]['supersedes']==selected[0]

@pytest.mark.parametrize('verdict,status',[('consistent','abstain'),('unknown','unknown'),('mismatch','ok')])
def test_status_is_mechanically_derived_from_explicit_verdict(task,verdict,status):
    three=compile_fixture('S3',objects(task)[2]);three['comparisons'][0]['verdict']=verdict
    if verdict!='mismatch':three.update(hypotheses=[],selected=[])
    assert ci.compile_output('S3',three,{'S1':{'items':[{}]},'S2':{'items':[{}]}})['status']==status

def test_model_id_or_status_is_not_silently_repaired(task):
    raw=compile_fixture('S2',objects(task)[1]);raw['items'][0]['id']='N1'
    with pytest.raises(ValueError,match='model_row_ids_forbidden'):ci.compile_output('S2',raw,{})
    raw=compile_fixture('S2',objects(task)[1]);raw['status']='ok'
    with pytest.raises(ValueError,match='interface_fields'):ci.compile_output('S2',raw,{})

def test_empty_upstream_remains_unknown():
    raw=dict(comparisons=[],hypotheses=[],selected=[],summary='upstream unavailable')
    assert ci.compile_output('S3',raw,{})['status']=='unknown'

def test_boolean_selected_index_rejected(task):
    raw=compile_fixture('S3',objects(task)[2]);raw['selected']=[True]
    with pytest.raises(ValueError,match='selected_indices'):ci.compile_output('S3',raw,{})

def test_retention_cannot_smuggle_never_proposed_input(task):
    records=retained(["(['a'],)","(['b'],)","bad"],{'key':{'input_repr':"(['a'],)"}},task)
    assert [x['status'] for x in records]==['accepted','rejected','rejected']
    assert records[1]['reason']=='never_proposed'

def test_direct_budget_and_duplicate_cache(task,tmp_path,monkeypatch):
    from . import compare_run
    calls=[]
    def execute(*args):calls.append(args);return dict(status='ok',native_checked=True)
    monkeypatch.setattr(compare_run,'execute',execute)
    inputs={};rows=direct_inputs(task,[f'([{n}],)' for n in range(13)],inputs,tmp_path)
    assert len(inputs)==12 and rows[-1]['reason']=='input_budget' and len(calls)==12
    direct_inputs(task,['([1],)'],inputs,tmp_path);assert len(calls)==12

def test_direct_context_has_only_task_and_arm_local_feedback(task):
    m=ci.direct_messages(task,2,[{'input_repr':'PRIVATE_ARM_FEEDBACK'}],3)
    assert 'PRIVATE_ARM_FEEDBACK' in m[1]['content'] and 'concept_facts' not in m[1]['content']
    assert 'S1' not in json.loads(m[1]['content'])
