"""Offline timeout amendment: received generation bytes and source stay immutable."""
import json
from pathlib import Path

import pytest

from final.src.orchestration import worker
from final.src.audits.resume_bva_batch import inventory
from final.src.runtime.artifacts import digest


@pytest.fixture
def stopped_generation(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, 'private_endpoint', lambda directory, name: tmp_path/'private-fixture.env')
    source=tmp_path/'source'
    worker.prepare({'cohort':'humaneval164','task_numbers':[72],'timeout_seconds':3},source)
    request={'messages':[{'role':'user','content':'fixture input generation'}],
             'temperature':.7,'max_tokens':2048,'seed':314231}
    call=source/'tasks/72/calls/direct'
    worker.save(call/'request.json',request)
    worker.save(call/'attempt.json',{'state':'received','request_id':digest(request),'attempt_number':1})
    worker.save(call/'response.json',{'text':'{"inputs":[]}','finish_reason':'stop','usage':{'total_tokens':3}})
    worker.save(source/'status.json',{'state':'interrupted'})
    (source/'.worker.lock').touch()
    return source


def test_resume_timeout_eight_keeps_source_and_received_generation_bytes(stopped_generation,tmp_path):
    source=stopped_generation
    before=inventory(source)
    target=tmp_path/'resumed'
    description=worker.prepare_resume(source,target,timeout_seconds=8)
    assert inventory(source)==before
    assert worker.read(source/'config_snapshot.json')['timeout_seconds']==3
    assert worker.read(target/'config_snapshot.json')['timeout_seconds']==8
    assert description['config']['timeout_seconds']==8
    assert description['logical_call_cap']==worker.read(source/'preview.json')['logical_call_cap']
    for name in ['request.json','attempt.json','response.json']:
        relative=Path('tasks/72/calls/direct')/name
        assert (source/relative).read_bytes()==(target/relative).read_bytes()
    receipts=worker.read(target/'import_receipts.json')
    assert receipts['source']==str(source)
    assert receipts['config_amendment']['previous']==3
    assert receipts['config_amendment']['current']==8
    assert receipts['original_writer_usage']['received']==1
    assert worker.read(target/'launch_plan.json')['resume_from']==str(source)



@pytest.mark.parametrize('native_path',[
    'tasks/72/oracle_0.json','tasks/72/oracle_valid.json','tasks/72/evaluation/0_0.json',
    'tasks/72/result.json','tasks/72/reference_program.json','tasks/72/catalogue_measurements.json',
])
def test_timeout_amendment_rejects_native_checkpoints_before_new_output(stopped_generation,tmp_path,native_path):
    worker.save(stopped_generation/native_path,{'fixture':True})
    target=tmp_path/'rejected'
    with pytest.raises(ValueError,match='native checkpoints'):
        worker.prepare_resume(stopped_generation,target,timeout_seconds=8)
    assert not target.exists()


@pytest.mark.parametrize('timeout',[True,0,float('nan'),61])
def test_timeout_amendment_validates_budget_before_copy(stopped_generation,tmp_path,timeout):
    target=tmp_path/'rejected'
    with pytest.raises(ValueError):
        worker.prepare_resume(stopped_generation,target,timeout_seconds=timeout)
    assert not target.exists()
