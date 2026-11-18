import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from final.src.audits import resume_bva_batch as resume
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.models.core_model import ModelResponse


@pytest.fixture
def source(tmp_path):
    directory = tmp_path / 'source'
    runtime = directory / 'runtime'
    resume.save(runtime / 'cohort.json', {'fixture': True})
    resume.save(directory / 'launch_plan.json', {'runtime': str(runtime), 'cohort': str(runtime/'cohort.json'),
        'logical_call_cap': 2, 'settings': {'input_budget':20}})
    request = {'messages':[{'role':'user','content':'fixture'}], 'temperature':.7,'max_tokens':2048,'seed':314159}
    requests = {f'0/{arm}':{'request':request,'request_sha256':resume.digest(request)} for arm in ('direct','soft_bva')}
    resume.save(directory / 'request_plan.json', {'requests':requests,'logical_calls':2})
    call = directory / 'generation/tasks/0/calls/direct'
    resume.save(call / 'request.json', request)
    resume.save(call / 'attempt.json', {'request_id':resume.digest(request),'state':'received','attempt_number':1})
    resume.save(call / 'response.json', {'text':'{"inputs":[]}', 'usage':{'total_tokens':10},'finish_reason':'stop'})
    unknown = directory / 'generation/tasks/0/calls/soft_bva_unknown_attempt_0000'
    resume.save(unknown / 'request.json', request)
    resume.save(unknown / 'attempt.json', {'request_id':resume.digest(request),'state':'unknown','attempt_number':1,
        'recovery_policy':'streaming-recovery-v1','error':{'retryable':True}})
    resume.save(directory / 'generation/tasks/0/packet.json', {'task_id':'HumanEval/0','common':'fixture'})
    resume.save(directory / 'keepalive/0.json', {'state':'received','usage':{'total_tokens':3}})
    resume.save(directory / 'source_snapshot.json', {'sources':{str(directory/'request_plan.json'):resume.checksum(directory/'request_plan.json')},'archive':{}})
    resume.save(directory / 'status.json', {'state':'interrupted'})
    (directory / '.worker.lock').touch()
    return directory


def test_prepare_preserves_original_bytes_calls_unknown_history_and_plan(source, tmp_path):
    before = resume.inventory(source)
    target = tmp_path/'resume'
    plan = resume.prepare(source,target)
    assert resume.inventory(source) == before
    assert plan['imported_received_calls'] == plan['remaining_logical_call_cap'] == 1
    assert (source/'request_plan.json').read_bytes() == (target/'request_plan.json').read_bytes()
    assert resume.read(target/'generation/tasks/0/calls/soft_bva_unknown_attempt_0000/attempt.json')['attempt_number'] == 1
    assert resume.frozen.keepalive_usage(target)['known_total_tokens'] == 3



def test_changed_request_plan_is_rejected_before_copy(source, tmp_path):
    resume.save(source/'request_plan.json', {'requests':{},'logical_calls':0})
    with pytest.raises(ValueError,match='Unregistered imported checkpoint'):
        resume.prepare(source,tmp_path/'resume')


def test_mismatched_received_identity_cannot_be_regenerated(source):
    path = source/'generation/tasks/0/calls/direct/attempt.json'
    record = resume.read(path);record['request_id']='wrong';resume.save(path,record)
    with pytest.raises(ValueError,match='identity'):
        resume.checkpoints(source,resume.read(source/'request_plan.json')['requests'])


def test_exhausted_unknown_history_stays_exhausted(source):
    original = source/'generation/tasks/0/calls/soft_bva_unknown_attempt_0000'
    for index in (1,2):
        target = original.with_name('soft_bva_unknown_attempt_'+f'{index:04d}')
        for name in ('request.json','attempt.json'):
            resume.save(target/name,resume.read(original/name))
    with pytest.raises(ValueError,match='cap exhausted'):
        resume.checkpoints(source,resume.read(source/'request_plan.json')['requests'])


def test_received_arm_uses_no_network_and_unknown_resumes_at_attempt_two(source,tmp_path):
    target = tmp_path/'resume';resume.prepare(source,target)
    class Model:
        model_id='fixture'
        def __init__(self):self.preparations=0;self.generations=0
        def prepare_generation(self,messages,max_tokens):
            self.preparations+=1
            return messages
        def generate_prepared(self,prepared,**kwargs):
            self.generations+=1
            return ModelResponse('{"inputs":[]}',{'total_tokens':4},'stop')
    model=Model();calls=RecordedModelCalls(model,ArtifactStore(target/'generation'))
    request=resume.read(source/'request_plan.json')['requests']['0/direct']['request']
    arguments={key:request[key] for key in ('temperature','max_tokens','seed')}
    calls.complete(0,'direct',request['messages'],**arguments)
    assert model.generations == model.preparations == 0
    calls.complete(0,'soft_bva',request['messages'],**arguments)
    assert model.generations == model.preparations == 1
    attempt=resume.read(target/'generation/tasks/0/calls/soft_bva/attempt.json')
    assert attempt['attempt_number']==2



def test_one_shot_launch_uses_frozen_runtime(source,tmp_path,monkeypatch):
    target=tmp_path/'resume';resume.prepare(source,target)
    captured={}
    def popen(command,**kwargs):
        captured.update(command=command,**kwargs);return SimpleNamespace(pid=123)
    monkeypatch.setattr(resume.subprocess,'Popen',popen)
    assert resume.launch(target)==123
    assert captured['env']['PYTHONPATH']==str(target/'runtime')
    assert '-P' in captured['command']
    with pytest.raises(FileExistsError):resume.launch(target)
