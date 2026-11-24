from pathlib import Path
import json

import pytest

from final.src.orchestration import config,worker,service


def test_default_batch_keeps_per_task_per_arm_budget():
    batch=config.preview({})
    assert batch['logical_call_cap']==471 and batch['eligible_task_count']==157
    assert batch['evaluated_base_pass_put_count']==1454
    assert batch['max_input_slots_per_arm']==3140


def test_openrouter_preview_resolves_flint_without_credentials(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    batch = config.preview({'model_backend': 'openrouter', 'arms': ['plain'], 'task_numbers': [0]})
    assert batch['config']['model_name'] == 'recursive/flint-v1.0:free'
    assert batch['logical_call_cap'] == 1


def test_worker_sources_only_the_openrouter_key(tmp_path, monkeypatch, capsys):
    import os

    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    (scripts / 'research_env.sh').write_text('export RESEARCH_FIXTURE_SECRET=fixture\n')
    (scripts / 'openrouter_env.sh').write_text('export OPENROUTER_API_KEY=fixture-key\necho fixture-key\n')
    monkeypatch.setenv('OPENROUTER_API_KEY', '')
    monkeypatch.delenv('RESEARCH_FIXTURE_SECRET', raising=False)
    worker.load_model_environment(tmp_path, 'openrouter')
    assert os.environ['OPENROUTER_API_KEY'] == 'fixture-key'
    assert 'RESEARCH_FIXTURE_SECRET' not in os.environ
    assert capsys.readouterr() == ('', '')


def test_control_flow_preview_leaves_batch_dependent_call_caps_pending():
    limits = config.preview({'arms': ['plain', 'control_flow']})
    assert limits['logical_calls_by_arm'] == {
        'plain': limits['eligible_task_count'],
        'control_flow': 'pending',
    }
    assert limits['logical_call_cap'] == limits['completion_token_cap_total'] == 'pending'


def test_control_flow_usage_counts_split_rounds_and_archived_attempts(tmp_path):
    from final.src.modular.catalogue_reporting import usage_by_arm

    for name in ('control_flow_round_5', 'control_flow_round_5_unknown_attempt_0000'):
        worker.save(tmp_path / 'tasks' / '0' / 'calls' / name / 'attempt.json', {})
    usage = usage_by_arm(tmp_path, ['control_flow'])
    assert usage['control_flow']['invocations'] == 2


@pytest.mark.parametrize('values',[
    {'temperature':float('nan')},{'inputs_per_task':True},{'task_numbers':[2,2]},
    {'mode':'per_put','arms':['boundary']},{'mode':'batch','arms':['plain','plain']},
    {'context_tokens':512,'completion_tokens':512},{'input_seed':-1},
    {'api_key':'never-a-config-field'},{'task_numbers':[999]},
])
def test_invalid_or_credential_configuration_rejected_before_run(values):
    with pytest.raises(ValueError):config.preview(values)


def test_private_endpoint_profiles_are_unique_even_when_artifact_leaf_is_run(tmp_path,monkeypatch):
    home=tmp_path/'home';source=home/'.config/concepttester/final-qwen.env'
    source.parent.mkdir(parents=True)
    source.write_text('export FINAL_BASE_URL=http://fixture.invalid/v1\nexport FINAL_API_KEY=fixture-secret\nexport FINAL_MODEL=old\n')
    monkeypatch.setattr(Path,'home',lambda:home)
    monkeypatch.setenv('FINAL_ENDPOINT_ENV_FILE',str(source))
    old=source.read_bytes()
    first=worker.private_endpoint(tmp_path/'first/run','fixture-model')
    second=worker.private_endpoint(tmp_path/'second/run','fixture-model')
    assert first!=second and first.stat().st_mode&0o777==0o600
    assert 'fixture-secret' in first.read_text() and 'FINAL_MODEL=fixture-model' in first.read_text()
    assert source.read_bytes()==old


@pytest.fixture
def prepared(tmp_path,monkeypatch):
    monkeypatch.setattr(worker,'private_endpoint',lambda directory,name:tmp_path/'private.env')
    path=tmp_path/'original'
    worker.prepare({'cohort':'humaneval164','task_numbers':[72],'arms':['plain','ep_bva_v2']},path)
    return path


def test_prepare_freezes_resolved_config_cohort_and_code(prepared):
    snapshot=worker.read(prepared/'config_snapshot.json')
    assert snapshot['inputs_per_task']==20
    plan=worker.read(prepared/'launch_plan.json')
    assert plan['target_program_count']==10 and plan['logical_call_cap']==2
    assert Path(plan['cohort']).is_relative_to(prepared/'runtime')

    worker.save(prepared/'config_snapshot.json',{**snapshot,'inputs_per_task':99})
    assert worker.read(prepared/'config_snapshot.json')['inputs_per_task']==99


def test_resume_keeps_attempt_history_and_rebuilds_only_path_metadata(prepared,tmp_path):
    from final.src.runtime.artifacts import digest
    from final.src.orchestration.worker import inventory
    request={'messages':[],'temperature':.7,'max_tokens':2048,'seed':314231}
    attempt={'state':'unknown','request_id':digest(request),'attempt_number':1,'error':{'retryable':True}}
    worker.save(prepared/'tasks/72/calls/ep_bva_v2_unknown_attempt_0000/request.json',request)
    worker.save(prepared/'tasks/72/calls/ep_bva_v2_unknown_attempt_0000/attempt.json',attempt)
    worker.save(prepared/'tasks/72/reference_program.json',{'old_path':'fixture'})
    worker.save(prepared/'tasks/72/boundary/soft_bva/4/identity.json',{'old_path':'fixture'})
    worker.save(prepared/'status.json',{'state':'interrupted'})
    (prepared/'.worker.lock').touch()
    before=inventory(prepared)
    target=tmp_path/'resumed'
    worker.prepare_resume(prepared,target)
    assert inventory(prepared)==before
    assert not (target/'tasks/72/reference_program.json').exists()
    assert not (target/'tasks/72/boundary/soft_bva/4/identity.json').exists()
    assert worker.read(target/'tasks/72/calls/ep_bva_v2_unknown_attempt_0000/attempt.json')['attempt_number']==1



def test_service_rejects_port_change_for_owned_live_server(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'STATE',tmp_path)
    (tmp_path/'services.json').write_text(json.dumps({'port':4200,'processes':{'server':{'pid':123,'start_token':'fixture'}}}))
    monkeypatch.setattr(service,'alive',lambda record:bool(record))
    monkeypatch.setattr(service.subprocess,'Popen',
        lambda *args,**kwargs:pytest.fail('Port-change rejection must not launch a service'))
    with pytest.raises(ValueError,match='changing its port'):service.start(4201)


def test_stale_running_status_can_resume_only_after_worker_lock_is_free(prepared,tmp_path):
    import fcntl
    worker.save(prepared/'status.json',{'state':'running','pid':999999})
    worker.save(prepared/'worker_started.json',{'pid':999999})
    with (prepared/'.worker.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):worker.prepare_resume(prepared,tmp_path/'blocked')
    target=tmp_path/'resumed'
    worker.prepare_resume(prepared,target)
    receipt=worker.read(target/'import_receipts.json')
    assert receipt['stop_inferred_from_free_worker_lock'] is True
    assert worker.read(prepared/'status.json')['state']=='running'




def test_managed_adapter_freezes_and_replays_with_offline_empty_writer(prepared,tmp_path,monkeypatch,capsys):
    """Exercise actual orchestration wiring; fixture transport makes0real calls."""
    from final.src.models.core_model import ModelResponse
    import final.src.models.model as transport
    import final.src.modular.reference_oracle as reference
    import final.src.modular.put_evaluation as evaluation
    calls=[]
    class Model:
        model_id='qwen3.5-27b-awq'
        def __init__(self,**kwargs):pass
        def check_endpoint(self):return {'model':self.model_id,'context':8192}
        def tokens(self,messages):return 1
        def prepare_generation(self,messages,max_tokens):return messages
        def generate_prepared(self,messages,**kwargs):
            calls.append(messages)
            return ModelResponse('{"inputs":[]}',{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2},'stop')
    monkeypatch.setattr(transport,'QwenModel',Model)
    monkeypatch.setattr(reference,'execute',lambda job:pytest.fail('Unexpected native execution in empty-input fixture'))
    monkeypatch.setattr(evaluation,'execute',lambda job:pytest.fail('Unexpected native execution in empty-input fixture'))
    monkeypatch.setattr(worker.signal,'signal',lambda *args:None)
    monkeypatch.setenv('FINAL_ENDPOINT_ENV_FILE','fixture-before')
    plan=worker.read(prepared/'launch_plan.json')
    plan.update(native_lock=str(tmp_path/'native.lock'),execution_cache=str(tmp_path/'cache'))
    worker.save(prepared/'launch_plan.json',plan)
    snapshot=worker.read(prepared/'source_snapshot.json')
    snapshot['sources'][str(prepared/'launch_plan.json')]=worker.checksum(prepared/'launch_plan.json')
    worker.save(prepared/'source_snapshot.json',snapshot)
    worker.run(prepared)
    result=worker.read(prepared/'result_digest.json')
    assert len(calls)==2 and result['writer_usage']['received']==2
    assert result['read_only_replay_matches'] is None
    assert all(row['valid_inputs']==row['detected']==0 for row in result['arms'].values())
    assert (prepared/'tasks/72/inputs.json').exists()


def test_task_error_log_reads_saved_records(tmp_path):
    import json
    from final.src.orchestration.task_log import task_error_rows
    task = tmp_path / 'tasks' / '7'
    (task / 'evaluation').mkdir(parents=True)
    (task / 'calls' / 'direct').mkdir(parents=True)
    (task / 'calls' / 'direct' / 'response.json').write_text(json.dumps({'text': '{', 'finish_reason': 'length'}))
    (task / 'inputs.json').write_text(json.dumps({'task_id': 'HumanEval/7', 'arms': {
        'direct': {'inputs': [], 'rejected': [{'reason': 'invalid_response'}]}}}))
    (task / 'oracle_valid.json').write_text(json.dumps({'tests': [], 'rejected': [
        {'index': 0, 'reason': 'domain_or_reference_rejects', 'outcomes': [{'status': 'timeout'}, {'status': 'timeout'}]}]}))
    (task / 'result.json').write_text(json.dumps({'arms': {'direct': {'detected': 1}}, 'outcomes': {
        '3': {'failing': [0], 'unstable': [], 'retested': [0]}}}))
    (task / 'evaluation' / '3_0.json').write_text(json.dumps({'tests': [{'status': 'error', 'exception': 'RecursionError'}]}))
    row = task_error_rows(tmp_path)[0]
    assert row['task'] == 'HumanEval/7'
    assert 'rejected invalid_response×1' in row['generation'] and 'truncated' in row['generation']
    assert row['reference_rejected'] == 'domain_or_reference_rejects(timeout)×1'
    assert row['put_confirmed_failures'] == 'error:RecursionError×1'
