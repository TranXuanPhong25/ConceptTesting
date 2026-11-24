"""Preparation/flow fixtures: no model or benchmark program execution."""
import importlib.util
from pathlib import Path
import json

import pytest

pytestmark=pytest.mark.skipif(importlib.util.find_spec('prefect') is None,reason='Use orchestration venv')


def test_prepare_full_saved_baseline_pins_data_and_uses_new_cache(tmp_path):
    from final.src.orchestration.reevaluate_v2 import prepare,DEFAULT_SOURCE,ARMS
    output=tmp_path/'eval';receipts,config=prepare(DEFAULT_SOURCE,output)
    assert len(receipts)==164 and config['expected_PUTs']==1454
    assert config['arms']==list(ARMS) and config['new_model_calls']==0
    assert not (output/'evaluation').exists() and not (output/'execution_cache').exists()
    assert not list(output.rglob('response.json')) and not list(output.rglob('result.json'))
    assert (output/'cohort.json').read_bytes()==(DEFAULT_SOURCE/'cohort.json').read_bytes()
    with pytest.raises(ValueError,match='new output'):prepare(DEFAULT_SOURCE,output)


def test_flow_invokes_only_rescore_and_replay_using_author_fixture(tmp_path,monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from uuid import uuid4
    from final.src.orchestration import reevaluate_v2 as m
    output=tmp_path/'out';flowid=uuid4();calls=[];artifacts=[]
    def prepare(source,out):
        out.mkdir();return [{'task_id':'HumanEval/0','generation_directory':'fixture_source'}],{
            'expected_PUTs':1,'settings':{'timeout_seconds':8},'new_model_calls':0}
    class Client:
        def update_flow_run(self,*args,**kwargs):pass
        def update_artifact(self,*args,**kwargs):artifacts.append(kwargs)
    @contextmanager
    def client(**kwargs):yield Client()
    monkeypatch.setattr(m,'prepare',prepare)
    monkeypatch.setattr(m,'get_run_context',lambda:SimpleNamespace(flow_run=SimpleNamespace(id=flowid)))
    monkeypatch.setattr(m,'get_client',client);monkeypatch.setattr(m,'create_markdown_artifact',lambda **kwargs:uuid4())
    monkeypatch.setattr(m,'ROOT',tmp_path);(tmp_path/'final/out').mkdir(parents=True)
    def fake_subprocess(command,**kwargs):
        calls.append(command)
        if '--replay' in command:return
        leaf=output/'evaluation/0';leaf.mkdir(parents=True)
        summary={'evaluated_base_pass':1,'arms':{a:{'valid_inputs':1,'detected':1,'tasks_detected':1} for a in m.ARMS}}
        (leaf/'modular_summary.json').write_text(json.dumps(summary))
        (leaf/'rescore_metrics.json').write_text(json.dumps({'detection_kinds':{a:{'wrong_value':1,'crash':0,'resource':0} for a in m.ARMS},
            'union':{'wrong_value':1,'crash':0,'resource':0,'total':1,'non_resource':1}}))
    monkeypatch.setattr(m.subprocess,'run',fake_subprocess)
    result=m.reevaluate.fn('fixture',str(output))
    assert result['state']=='complete' and result['union']['total']==1 and result['new_model_calls']==0
    assert len(calls)==1 and '--replay' not in calls[0]
    assert all(c[c.index('-m')+1]=='final.src.modular.rescore' for c in calls)
    assert all('--model-backend' not in c and '--execution-cache' in c for c in calls)
    assert artifacts and (output/'REPORT.md').exists()
