"""Index existing experiment artifacts into Prefect without executing their code."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import re
import time
import uuid

from prefect import flow
from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import ArtifactCreate
from prefect.states import Completed,Failed,Running,Pending

from .config import ROOT

PREFIXES=('boundary_prompt_style','boundary_soft_humaneval164','bva_batch_matched164',
          'naive_vs_soft_bva','naive_packaging_audit','v11_concept_inputs')


def read_if(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {}


@contextmanager
def history_index_lock(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.history-index.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield


def clean(value):
    if isinstance(value,str):return re.sub(r'https?://[^\s\"\']*ngrok[^\s\"\']*','<private-endpoint>',value)
    if isinstance(value,list):return [clean(item) for item in value]
    if isinstance(value,dict):return {key:clean(item) for key,item in value.items() if not re.search(r'api.?key|secret|password|base_url',key,re.I)}
    return value


def inspect_run(directory):
    status_path=next((path for path in (directory/'status.json',directory/'evaluation/status.json') if path.exists()),None)
    if status_path is None:return None
    status=read_if(status_path)
    result=read_if(directory/'result_digest.json') or read_if(directory/'evaluation/result_digest.json')
    manifest=read_if(directory/'modular_manifest.json') or read_if(directory/'evaluation/modular_manifest.json')
    plan=read_if(directory/'run_plan.json') or read_if(directory/'launch_plan.json')
    settings=manifest.get('settings') or plan.get('settings',{})
    if not settings and (directory/'repaired_view/modular_manifest.json').exists():settings=read_if(directory/'repaired_view/modular_manifest.json').get('settings',{})
    mode='batch' if directory.name.startswith('bva_batch') else 'single-PUT prompt-style' if directory.name.startswith('boundary_prompt_style') else 'per-PUT shared task budget' if directory.name.startswith('boundary_soft_humaneval164') else 'historical/replay'
    parameters=clean({'source_directory':str(directory.relative_to(ROOT)), 'mode':mode, 'settings':settings,
        'cohort_sha256':manifest.get('cohort_sha256',plan.get('cohort_sha256')),
        'model':manifest.get('model') or result.get('reused_generation',{}).get('source_model') or 'see generation provenance',
        'input_budget_unit':'per task per arm','generation_state':status.get('state'),
        'continuation_source':plan.get('continuation_source'),'protocol':manifest.get('protocol')})
    metrics=result.get('arms') or read_if(directory/'modular_summary.json').get('arms') or read_if(directory/'evaluation/modular_summary.json').get('arms',{})
    state=status.get('state','unknown')
    progress=read_if(directory/'progress.json') or read_if(directory/'evaluation/progress.json')
    source=directory/'generation' if (directory/'generation/tasks').exists() else directory
    responses=list(source.glob('tasks/*/calls/*/response.json'))
    received=len(responses)
    usage=result.get('writer_usage') or result.get('source_generation_usage') or result.get('tester_calls',{})
    if usage:received=usage.get('received',received)
    description=clean({'source_state':state,'progress':progress,'received_responses':received,
        'metrics':metrics,'error':status.get('error'),'original_oracle_warning':directory.name=='v11_concept_inputs'})
    report_path=next((path for path in (directory/'REPORT.md',directory/'evaluation/REPORT.md') if path.exists()),None)
    report=clean(report_path.read_text()[:70000]) if report_path else ''
    if state=='complete':prefect_state=Completed(message='Imported completed artifacts; no execution')
    elif state in ('interrupted','failed'):prefect_state=Failed(message='Imported interrupted artifacts; checkpoints preserved')
    elif state in ('running','preflight','waiting_native_lock','waiting_endpoint'):prefect_state=Running(message='External worker; monitoring artifacts only')
    else:prefect_state=Pending(message='Imported state: '+str(state))
    return parameters,description,report,prefect_state


@flow(name='Historical experiment record',retries=0,persist_result=False)
def historical_record(source_directory:str,mode:str,settings:dict,**metadata):
    """Read-only index. This flow is never deployed to execute experiments."""
    return {'source_directory':source_directory,'settings':settings,'mode':mode,**metadata}


async def sync_once(state_directory):
    state_directory.mkdir(parents=True,exist_ok=True)
    with history_index_lock(state_directory):
        mapping_path=state_directory/'history_index.json';mapping=read_if(mapping_path)
        changed=0
        async with get_client() as client:
            for directory in sorted((ROOT/'final/out').iterdir()):
                if not directory.is_dir() or not directory.name.startswith(PREFIXES):continue
                if directory.name in mapping.get('suppressed_sources',{}):continue
                record=inspect_run(directory)
                if record is None:continue
                parameters,description,report,state=record
                signature=hashlib.sha256(json.dumps([parameters,description,report],sort_keys=True).encode()).hexdigest()
                previous=mapping.get(directory.name,{})
                flow_run_id=previous.get('flow_run_id')
                if previous.get('signature')==signature and flow_run_id:
                    try:await client.read_flow_run(flow_run_id)
                    except Exception:flow_run_id=None
                    else:continue
                if not flow_run_id:
                    run=await client.create_flow_run(historical_record,name=directory.name,parameters=parameters,
                        tags=['ConceptTester','historical','read-only-index'],state=state)
                    flow_run_id=run.id
                    await client.create_artifact(ArtifactCreate(key='historical-config',type='markdown',
                        data='### Original config\n\n```json\n'+json.dumps(parameters,ensure_ascii=False,indent=2)+'\n```',flow_run_id=flow_run_id))
                else:await client.set_flow_run_state(flow_run_id,state,force=True)
                await client.create_artifact(ArtifactCreate(key='historical-progress',type='markdown',
                    data='### Artifact status\n\n```json\n'+json.dumps(description,ensure_ascii=False,indent=2)+'\n```',flow_run_id=flow_run_id))
                if description['metrics']:
                    await client.create_artifact(ArtifactCreate(key='historical-results',type='table',
                        data=[{'arm':arm,**metrics} for arm,metrics in description['metrics'].items()],flow_run_id=flow_run_id))
                if report and description['source_state']=='complete':
                    await client.create_artifact(ArtifactCreate(key='historical-report',type='markdown',data=report,flow_run_id=flow_run_id))
                mapping[directory.name]={'flow_run_id':str(flow_run_id),'signature':signature}
                changed+=1
        temporary=mapping_path.with_suffix('.tmp');temporary.write_text(json.dumps(mapping,indent=2)+'\n');temporary.replace(mapping_path)
        return changed


async def clean_stale_historical_rows(state_directory):
    """Back up then remove only imported Failed/Pending rows; preserve every source artifact."""
    await sync_once(state_directory)
    with history_index_lock(state_directory):
        mapping_path=state_directory/'history_index.json';mapping=read_if(mapping_path)
        targets=[]
        async with get_client() as client:
            for name,item in list(mapping.items()):
                if name=='suppressed_sources' or not isinstance(item,dict) or not item.get('flow_run_id'):continue
                try:run=await client.read_flow_run(item['flow_run_id'])
                except Exception:continue
                if run.state_name not in ('Failed','Pending'):continue
                source=ROOT/'final/out'/name
                source_status=read_if(source/'status.json') or read_if(source/'evaluation/status.json')
                if source_status.get('state') not in ('interrupted','prepared'):continue
                targets.append({'source_directory':str(source),'flow_run_id':str(run.id),'name':run.name,
                    'prefect_state':run.state_name,'prefect_created':run.created.isoformat() if run.created else None,
                    'parameters':clean(run.parameters),'prefect_state_message':clean(run.state.message if run.state else None),
                    'source_state':source_status.get('state'),'source_error_type':source_status.get('error_type'),
                    'source_error':clean(source_status.get('error')),'retry_checkpoint_count':len(list(source.glob('tasks/*/calls/*/attempt.json'))),
                    'source_directory_still_exists':source.is_dir(),'user_action':'archive metadata and remove this stale Prefect history row only'})
        if not targets:return {'removed_history_rows':0,'source_files_deleted':0,'rows':[]}
        archive=state_directory/('history_cleanup_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
        backup={'policy':'Delete only imported historical Prefect Failed/Pending rows backed by stopped interrupted/prepared sources. Preserve all run files/checkpoints.',
                'created_epoch':time.time(),'removed_rows':targets,'source_files_deleted':0,'prefect_rows_deleted':[]}
        temporary=archive.with_suffix('.tmp');temporary.write_text(json.dumps(backup,ensure_ascii=False,indent=2)+'\n');temporary.replace(archive)
        mapping.setdefault('suppressed_sources',{})
        for record in targets:mapping['suppressed_sources'][Path(record['source_directory']).name]={'archive':str(archive),'flow_run_id':record['flow_run_id']}
        temporary=mapping_path.with_suffix('.tmp');temporary.write_text(json.dumps(mapping,indent=2)+'\n');temporary.replace(mapping_path)
        for record in targets:
            # Use the server's documented CSRF token/header API directly; the SDK
            # CSRF refresh callback can reuse its already-closed internal client.
            import httpx
            from prefect.settings import PREFECT_API_URL
            root=PREFECT_API_URL.value().rstrip('/')
            client_id=str(uuid.uuid4())
            async with httpx.AsyncClient(timeout=20) as http:
                token_response=await http.get(root+'/csrf-token',params={'client':client_id})
                if token_response.status_code==422 and 'CSRF protection is disabled' in token_response.text:
                    headers={}
                else:
                    token_response.raise_for_status()
                    headers={'Prefect-Csrf-Token':token_response.json()['token'],'Prefect-Csrf-Client':client_id}
                response=await http.delete(root+'/flow_runs/'+record['flow_run_id'],headers=headers)
                if response.status_code not in (200,204,404):response.raise_for_status()
            backup['prefect_rows_deleted'].append(record['flow_run_id'])
            temporary=archive.with_suffix('.tmp');temporary.write_text(json.dumps(backup,ensure_ascii=False,indent=2)+'\n');temporary.replace(archive)
        return {'removed_history_rows':len(backup['prefect_rows_deleted']),'source_files_deleted':0,'archive':str(archive),'rows':targets}


async def preview_stale_historical_rows(state_directory):
    await sync_once(state_directory)
    mapping=read_if(state_directory/'history_index.json');rows=[]
    async with get_client() as client:
        for name,item in mapping.items():
            if name=='suppressed_sources' or not isinstance(item,dict) or not item.get('flow_run_id'):continue
            try:run=await client.read_flow_run(item['flow_run_id'])
            except Exception:continue
            if run.state_name not in ('Failed','Pending'):continue
            source=ROOT/'final/out'/name
            status=read_if(source/'status.json') or read_if(source/'evaluation/status.json')
            if status.get('state') in ('interrupted','prepared'):
                rows.append({'name':name,'prefect_state':run.state_name,'source_state':status.get('state'),
                    'source_error_type':status.get('error_type'),'source_dir_exists':source.is_dir(),
                    'checkpoint_attempt_records':len(list(source.glob('tasks/*/calls/*/attempt.json')))})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--watch',action='store_true')
    actions=parser.add_mutually_exclusive_group();actions.add_argument('--clean-stale-historical-rows',action='store_true')
    actions.add_argument('--preview-stale-historical-rows',action='store_true')
    args=parser.parse_args();folder=ROOT/'final/out/run_console'
    if args.clean_stale_historical_rows:
        print(json.dumps(asyncio.run(clean_stale_historical_rows(folder)),ensure_ascii=False),flush=True);return
    if args.preview_stale_historical_rows:
        print(json.dumps(asyncio.run(preview_stale_historical_rows(folder)),ensure_ascii=False,indent=2),flush=True);return
    while True:
        try:
            changed=asyncio.run(sync_once(folder))
            if changed:print(json.dumps({'history_records_updated':changed}),flush=True)
        except Exception as error:
            print(json.dumps({'history_index_error':type(error).__name__,'detail':clean(str(error))}),flush=True)
            if not args.watch:raise
        if not args.watch:return
        time.sleep(20)


if __name__=='__main__':main()
