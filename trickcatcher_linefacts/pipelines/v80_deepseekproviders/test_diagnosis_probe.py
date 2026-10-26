import copy
import pytest
from .diagnosis_probe import select_cases,packet,messages,summarize,PREMISE,SYSTEM
from .semantic_contract import writer_packet
from .test_contractfix import REQ,writer_proposal


def test_full_premise_intervention_is_exactly_one_added_field():
    original=writer_packet(REQ);before=copy.deepcopy(original)
    new=packet(REQ,'full_known');assert new.pop('known_bug_premise')==PREMISE
    assert new==original==before


def test_same_public_task_and_premise_are_present_in_both_arms():
    raw=packet(REQ,'raw_known');full=packet(REQ,'full_known')
    for key in ('source','entry','public_examples','known_bug_premise'):
        assert raw[key]==full[key]
    assert raw['spec']==REQ['spec']
    assert set(raw['output_schema'])=={'analysis'}
    assert 'hypothesis_fields'not in raw and 'sites'not in raw
    assert messages(REQ,'raw_known')[0]==messages(REQ,'full_known')[0]=={'role':'system','content':SYSTEM}


def test_case_selection_is_by_source_size_and_distinct_entry():
    requests=[dict(REQ,case_id='long',source='long_source',entry='f'),
              dict(REQ,case_id='short',source='a',entry='f'),
              dict(REQ,case_id='other',source='bb',entry='g')]
    assert [r['case_id']for r in select_cases(requests)]==['short','other']
    with pytest.raises(ValueError):select_cases([REQ,dict(REQ,case_id='duplicate')])


def test_nonempty_prose_is_not_automatically_semantic_success():
    result=summarize(REQ,'raw_known',{'error':None,'value':{'analysis':'An unverified guess.'}})
    assert result['simple_schema_valid']and result['semantic_status']=='unreviewed'
    assert 'semantic_correct'not in result


def test_raw_malformed_or_incomplete_outputs_are_preserved():
    for response in ({'error':'incomplete_completion','value':None},
                     {'error':None,'value':{'hypotheses':[]}}):
        result=summarize(REQ,'raw_known',response)
        assert not result['simple_schema_valid']and result['semantic_status']=='unreviewed'


def test_full_semantics_and_compiler_are_not_equated():
    result=summarize(REQ,'full_known',{'error':None,'value':{'hypotheses':[writer_proposal()]}})
    assert result['compiler_admitted']==1 and result['semantic_status']=='unreviewed'
    result=summarize(REQ,'full_known',{'error':None,'value':writer_proposal()})
    assert result['response_contract']['status']=='invalid'and not result['response_contract']['explicit_abstention']
