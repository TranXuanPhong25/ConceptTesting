"""Union replay must conserve native pool identity and confirmed evidence."""
from pathlib import Path

import pytest

from final.src.audits.evaluate_input_union import validate_union_pool,validate_native_evidence
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import TaskContext,PipelineSettings
from final.src.modular.put_evaluation import evaluate_programs
from final.src.runtime.artifacts import save


def test_union_uses_every_unique_source_input_once():
    oracle={'tests':[{'input_key':'one'},{'input_key':'two'}],
            'arm_indices':{'plain':[0],'ep_bva':[1],'decision_table':[0,1]}}
    assert validate_union_pool(oracle,('plain','ep_bva','decision_table'))==[0,1]
    oracle['tests'][1]['input_key']='one'
    with pytest.raises(ValueError,match='duplicate'):validate_union_pool(oracle,('plain','ep_bva','decision_table'))


def test_union_cannot_reuse_an_uncovered_or_invalid_native_pool():
    oracle={'tests':[{'input_key':'one'},{'input_key':'two'}],
            'arm_indices':{'plain':[0],'ep_bva':[0],'decision_table':[0]}}
    with pytest.raises(ValueError,match='exact native'):validate_union_pool(oracle,('plain','ep_bva','decision_table'))
    oracle['arm_indices']['ep_bva']=[True]
    with pytest.raises(ValueError,match='Invalid'):validate_union_pool(oracle,('plain','ep_bva','decision_table'))


def test_saved_failure_count_is_recomputed_from_confirmation_evidence(tmp_path):
    save(tmp_path/'evaluation/0_0.json',{'tests':[{'status':'pass'},{'status':'fail'},{'status':'timeout'}]})
    save(tmp_path/'evaluation/0_retry_1.json',{'tests':[{'status':'fail'},{'status':'pass'}]})
    result={'outcomes':{'0':{'failing':[1],'retested':[1,2],'unstable':[2]}}}
    validate_native_evidence(tmp_path,result,3)
    result['outcomes']['0']['failing']=[2]
    with pytest.raises(ValueError,match='confirmed failures'):validate_native_evidence(tmp_path,result,3)
    with pytest.raises(ValueError,match='length'):validate_native_evidence(tmp_path,result,4)


def test_shared_evaluator_adds_union_attribution_without_execution(tmp_path,monkeypatch):
    import final.src.modular.put_evaluation as evaluation
    monkeypatch.setattr(evaluation,'execute',lambda job:pytest.fail('Native execution during saved union replay'))
    task={'task_id':'HumanEval/0','prompt':'def f(x): pass','entry_point':'f'}
    context=TaskContext(task,{'atol':0},ArtifactStore(tmp_path,read_only=True),PipelineSettings(input_budget=60))
    context.cohort_task={'programs':[{'id':0,'code':'def f(x): return x+1','base':{'status':'pass'}}]}
    context.oracle={'tests':[{'args':'(1,)','kwargs':'{}','expected':'1','input_key':'one'},
                             {'args':'(2,)','kwargs':'{}','expected':'2','input_key':'two'}],
                    'rejected':[],'arm_indices':{'plain':[0],'ep_bva':[1],'decision_table':[1],'union':[0,1]}}
    context.inputs={'arms':{name:{'inputs':[]} for name in context.oracle['arm_indices']}}
    save(tmp_path/'tasks/0/evaluation/0_0.json',{'tests':[{'status':'fail'},{'status':'pass'}]})
    save(tmp_path/'tasks/0/evaluation/0_retry_1.json',{'tests':[{'status':'fail'}]})
    result=evaluate_programs(context)
    assert result['arms']['union']['detected']==1 and result['arms']['union']['valid_inputs']==2
    assert result['arms']['ep_bva']['detected']==0
    (tmp_path/'tasks/0/evaluation/0_retry_1.json').unlink()
    with pytest.raises(FileNotFoundError):evaluate_programs(context)
