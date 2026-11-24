"""User-invoked native evaluation of saved Plain/EP-BVA V2/DT V2 inputs."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import UUID

from prefect import flow
from prefect.artifacts import create_markdown_artifact
from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import ArtifactUpdate
from prefect.context import get_run_context

from .config import ROOT

ARMS=('plain','ep_bva_v2','decision_table_v2')
DEFAULT_SOURCE=ROOT/'final/out/gemini_catalogue_full164_20261112_193646'


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def prepare(source,output):
    """Pin current evaluator and original task data; never copy old evaluation/cache."""
    source=source.resolve();output=output.resolve()
    if output.exists():raise ValueError('Evaluation requires a new output directory')
    if output==source or output.is_relative_to(source):raise ValueError('Output must be outside the source run')
    config=read(source/'config_snapshot.json')
    if config['arms']!=list(ARMS):raise ValueError('Source must contain exactly plain,ep_bva_v2,decision_table_v2')
    receipts=[read(p) for p in sorted((source/'task_receipts').glob('*.json'))]
    cohort=read(source/'cohort.json')
    if {r['task_id'] for r in receipts}!={t['task_id'] for t in cohort['tasks']}:
        raise ValueError('Source receipts must cover the entire cohort')
    if any(r['state'] not in ('complete','skipped') for r in receipts):raise ValueError('Source run is incomplete')
    leaf=Path(next(r['generation_directory'] for r in receipts if r['state']=='complete'))
    manifest=read(leaf/'modular_manifest.json')
    runtime_source=Path(read(source/'launch_plan.json').get('runtime',ROOT)) if (source/'launch_plan.json').exists() else ROOT
    pinned_data={name:runtime_source/'final/data'/name for name in ('humaneval.jsonl','contracts.json')}
    output.mkdir(parents=True)
    runtime=output/'runtime'
    code=[p for p in (ROOT/'final/src').rglob('*.py') if 'tests' not in p.parts and '__pycache__' not in p.parts]
    code += [ROOT/'final/__init__.py',*(ROOT/'final/src/modular/fault_oriented_testing').glob('*.json')]
    for p in code:
        target=runtime/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for name,p in {**pinned_data,'humanevalplus_v0.1.10_references.json':ROOT/'final/data/humanevalplus_v0.1.10_references.json'}.items():
        target=runtime/'final/data'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    shutil.copyfile(source/'cohort.json',output/'cohort.json')
    for p in runtime.rglob('*'):
        if p.is_file():p.chmod(0o444)
    resolved={'source_directory':str(source),'output_directory':str(output),'arms':list(ARMS),
        'source_flow_run_id':read(source/'prefect_record.json').get('flow_run_id') if (source/'prefect_record.json').exists() else None,
        'settings':config['settings'],'new_model_calls':0,'cache_directory':str(output/'execution_cache'),
        'cache_policy':'new isolated cache;reference and PUT run again;no historical evaluation copied',
        'references':'current workspace reference package frozen at script invocation',
        'dataset':'original generation dataset/contracts','expected_tasks':len(receipts),
        'expected_PUTs':sum(r.get('evaluated_base_pass',0) for r in receipts)}
    write(output/'config_snapshot.json',resolved)
    return receipts,resolved


@flow(name='Re-evaluate Plain + EP-BVA V2 + DT V2',retries=0,persist_result=False)
def reevaluate(source,output):
    source=Path(source);output=Path(output).resolve();receipts,config=prepare(source,output)
    run_id=str(get_run_context().flow_run.id)
    with get_client(sync_client=True) as client:
        client.update_flow_run(get_run_context().flow_run.id,name='Evaluation · Plain + EP/BVA V2 + DT V2 · saved inputs')
    write(output/'prefect_record.json',{'flow_run_id':run_id,'url':'http://127.0.0.1:4200/runs/flow-run/'+run_id})
    intro=('Evaluate lại inputs đã lưu,0model calls. Native reference/PUT chạy lại bằng evaluator hiện tại,'
        'cache mới trong output riêng; không copy kết quả evaluation cũ. Dataset/contracts gốc,reference package hiện tại được snapshot. '
        'Source không sửa; detected PUT là oracle disagreements,chưa tự động là confirmed semantic bugs.')
    config_id=create_markdown_artifact(key='v2-reevaluation-config',markdown=intro+'\n```json\n'+json.dumps(config,ensure_ascii=False,indent=2)+'\n```')
    progress_id=create_markdown_artifact(key='v2-reevaluation-progress',markdown='Chưa evaluation:metrics pending.')
    report_id=create_markdown_artifact(key='v2-reevaluation-report',markdown='Kết quả pending;chưa evaluation.')
    write(output/'prefect_record.json',{'flow_run_id':run_id,'url':'http://127.0.0.1:4200/runs/flow-run/'+run_id,
        'artifact_ids':[str(i) for i in (config_id,progress_id,report_id)]})
    totals={a:{'valid_inputs':0,'detected':0,'tasks_detected':0} for a in ARMS};done=puts=0
    kinds={a:{k:0 for k in ('wrong_value','crash','resource')} for a in ARMS};union={k:0 for k in ('wrong_value','crash','resource','total','non_resource')}
    python=ROOT/'final/.venv/bin/python';env={**os.environ,'PYTHONPATH':str(output/'runtime'),'PYTHONDONTWRITEBYTECODE':'1'}
    def publish(state,error=None):
        data={'state':state,'completed_tasks':done,'expected_tasks':len(receipts),'evaluated_base_pass':puts,
            'pending_base_pass':config['expected_PUTs']-puts,'new_model_calls':0,
            'arms':totals if puts else {a:{k:None for k in totals[a]} for a in ARMS},
            'detection_kinds':kinds if puts else None,'union':union if puts else None,'error':error}
        write(output/'progress.json',data);write(output/'status.json',data)
        text='Tiến độ evaluation;metrics còn pending cho task chưa xong.\n```json\n'+json.dumps(data,ensure_ascii=False,indent=2)+'\n```'
        with get_client(sync_client=True) as client:client.update_artifact(progress_id,ArtifactUpdate(data=text))
        return data
    publish('running')
    try:
        # One native evaluator at a time; this run never acquires a model writer.
        with (ROOT/'final/out/.boundary_native.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            for receipt in receipts:
                number=receipt['task_id'].split('/')[-1];leaf=output/'evaluation'/number
                command=[str(python),'-B','-P','-m','final.src.modular.rescore','--source-run',receipt['generation_directory'],
                    '--cohort',str(output/'cohort.json'),'--artifacts',str(leaf),'--execution-cache',str(output/'execution_cache')]
                with (output/'worker.log').open('a') as log:
                    subprocess.run(command,cwd=output/'runtime',env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
                summary=read(leaf/'modular_summary.json')
                metrics=read(leaf/'rescore_metrics.json')
                for arm in ARMS:
                    for metric in totals[arm]:totals[arm][metric]+=summary.get('arms',{}).get(arm,{}).get(metric,0)
                    for kind in kinds[arm]:kinds[arm][kind]+=metrics['detection_kinds'].get(arm,{}).get(kind,0)
                for kind in union:union[kind]+=metrics['union'][kind]
                done+=1;puts+=summary['evaluated_base_pass'];publish('running')
        if puts!=config['expected_PUTs']:raise ValueError('Incomplete PUT evaluation')
        report=f"Đủ{done}/{len(receipts)}task slots,{puts}PUT;0model calls. Mỗi task đã evaluate; tổng hợp outcomes đã lưu.\n\n"+intro+'\n\n| Arm | Valid input records | Detected PUT | Wrong-value | Exception | Resource |\n|---|---:|---:|---:|---:|---:|\n'
        for a,t in totals.items():report+=f"|{a}|{t['valid_inputs']}|{t['detected']}|{kinds[a]['wrong_value']}|{kinds[a]['crash']}|{kinds[a]['resource']}|\n"
        report+=f"|Union|không cộng input giữa arms|{union['total']}|{union['wrong_value']}|{union['crash']}|{union['resource']}|\n"
        report+='\nConfig/budget thực tế:\n```json\n'+json.dumps(config,ensure_ascii=False,indent=2)+'\n```'
        (output/'REPORT.md').write_text(report)
        with get_client(sync_client=True) as client:client.update_artifact(report_id,ArtifactUpdate(data=report))
        result=publish('complete');write(output/'result_digest.json',result)
        return result
    except BaseException as error:
        publish('failed',type(error).__name__+':'+str(error)[:500]);raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=DEFAULT_SOURCE)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    reevaluate(str(args.source.resolve()),str(output))
    record=read(output/'prefect_record.json')
    with get_client(sync_client=True) as client:
        run=client.read_flow_run(UUID(record['flow_run_id']))
        for artifact_id in record['artifact_ids']:
            artifact=client.read_artifact(UUID(artifact_id))
            if str(artifact.flow_run_id)!=record['flow_run_id']:raise ValueError('Prefect artifact belongs to another run')
        if run.state.type.value!='COMPLETED':raise ValueError('Prefect run did not complete')
    print('Prefect: '+record['url'])


if __name__=='__main__':main()
