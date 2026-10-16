"""Contract regressions only; authored claims never measure semantic accuracy."""
import copy
import pytest
from . import schemas as s,prompt_aliases,source_view
from .test_chain_interfaces import task,objects,send,through3


def registry(task):
    one,two,*_=objects(task);r={}
    s.register('S1',one,task['task_hash'],r);s.register('S2',two,task['task_hash'],r)
    return r


def test_unconditional_behavior_and_no_separate_effect_are_accepted(task):
    two=objects(task)[1];two['items'][0].update(guard='',effect='')
    s.validate('S2',two,task,{})
    two['items'][0]['statement']=''
    with pytest.raises(s.ArtifactError,match='statement'):s.validate('S2',two,task,{})


def test_missing_optional_alternative_is_not_a_rejection(task):
    three=objects(task)[2];three['items'][0]['alternative']=''
    s.validate('S3',three,task,registry(task))
    three['items'][0]['condition']=''
    with pytest.raises(s.ArtifactError,match='condition'):s.validate('S3',three,task,registry(task))


@pytest.mark.parametrize('change,error',[
    ('missing','comparison_coverage'),('duplicate','comparison_duplicate'),
    ('foreign','comparison_obligation_refs'),('no_hypothesis','unrepresented_mismatch'),
    ('no_selection','mismatch_requires_selection'),('false_consistency','hypothesis_without_mismatch')])
def test_alignment_invariants(task,change,error):
    three=objects(task)[2]
    if change=='missing':three['comparisons']=[]
    if change=='duplicate':three['comparisons']*=2
    if change=='foreign':three['comparisons'][0]['obligation_ids']=['foreign']
    if change=='no_hypothesis':three.update(status='abstain',reason='claimed consistent',items=[],selected_ids=[])
    if change=='no_selection':three['selected_ids']=[]
    if change=='false_consistency':three['comparisons'][0]['verdict']='consistent'
    with pytest.raises(s.ArtifactError,match=error):s.validate('S3',three,task,registry(task))


def test_unknown_is_not_all_consistent_abstention(task):
    three=objects(task)[2];three.update(status='unknown',reason='meaning unresolved',items=[],selected_ids=[])
    three['comparisons'][0]['verdict']='unknown';s.validate('S3',three,task,registry(task))
    three['status']='abstain'
    with pytest.raises(s.ArtifactError,match='comparison_terminal_status'):s.validate('S3',three,task,registry(task))


def test_comparison_aliases_are_expanded_and_preserved_in_registered_artifact(task):
    r=registry(task);art={stage:dict(items=[row for row in r.values() if row['stage']==stage]) for stage in ('S1','S2')}
    _,aliased,_,back=prompt_aliases.view(task,art,[])
    three=objects(task)[2];_,mapped,_,_=prompt_aliases.view(task,dict(art, S3=dict(items=[],comparisons=three['comparisons'])),[])
    aliased_three=copy.deepcopy(three);aliased_three['comparisons']=mapped['S3']['comparisons']
    decoded=prompt_aliases.expand('S3',aliased_three,back)
    assert decoded['comparisons']==three['comparisons']
    result=s.register('S3',decoded,task['task_hash'],r)
    assert result['comparisons']==three['comparisons']
    malformed=copy.deepcopy(aliased_three);malformed['comparisons'][0]['source_ids']='N1'
    with pytest.raises(ValueError,match='alias_comparison_reference_shape'):prompt_aliases.expand('S3',malformed,back)


@pytest.mark.parametrize('decision',['withdraw','unknown','keep','revise'])
def test_s5_condition_optional_only_for_withdraw_or_unknown(task,decision):
    r=registry(task);three=objects(task)[2];h=s.register('S3',three,task['task_hash'],r)['selected_ids']
    five=objects(task)[4];five['decisions'][0].update(decision=decision,condition='')
    if decision in ('withdraw','unknown'):s.validate('S5',five,task,r,h,['F1'])
    else:
        with pytest.raises(s.ArtifactError,match='condition'):s.validate('S5',five,task,r,h,['F1'])


def test_absent_upstream_claims_cannot_prove_consistency(task):
    for missing in ('S1','S2'):
        r={k:v for k,v in registry(task).items() if v['stage']!=missing}
        three=objects(task)[2];three.update(status='unknown',reason='upstream unavailable',items=[],selected_ids=[])
        if missing=='S1':three['comparisons']=[]
        else:three['comparisons'][0].update(verdict='unknown',behavior_ids=[])
        s.validate('S3',three,task,r)
        three['status']='abstain'
        with pytest.raises(s.ArtifactError,match='comparison_terminal_status'):s.validate('S3',three,task,r)
