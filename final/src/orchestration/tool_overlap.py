"""One persisted LLM producer overlaps one isolated tool/evaluation consumer."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def overlap(items, produce, consume, executor):
    pending=[]
    for item in items:
        receipt=produce(item)
        if receipt is not None:
            pending.append(executor.submit(consume,receipt))
    return pending


def read(path):
    return json.loads(Path(path).read_text())


def save(path,value):
    from final.src.runtime.artifacts import save as atomic_save
    atomic_save(Path(path),value)


def settings(config,target_programs):
    from final.src.modular.context import PipelineSettings
    return PipelineSettings(input_budget=config['inputs_per_task'],input_tokens=config['completion_tokens'],
        input_temperature=config['temperature'],input_seed=config['input_seed'],reference_seed=config['reference_seed'],
        context_tokens=config['context_tokens'],timeout_seconds=config['timeout_seconds'],target_programs=target_programs)


def collect(directory):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.calls import RecordedModelCalls
    from final.src.modular.cohort import load_cohort
    from final.src.modular.context import TaskContext
    from final.src.benchmarks.datasets import load_tasks,load_metadata
    from final.src.modular.generators.tools import ToolInputGenerator
    from final.src.modular.input_preparation import prepare_task_packet
    from final.src.models.model import QwenModel
    config=read(directory/'config_snapshot.json');plan=read(directory/'launch_plan.json')
    os.environ['FINAL_ENDPOINT_ENV_FILE']=plan['endpoint_env_file']
    model=QwenModel(context=config['context_tokens'],expected_model=config['model_name'])
    save(directory/'endpoint_readiness.json',model.check_endpoint())
    artifacts=ArtifactStore(directory);calls=RecordedModelCalls(model,artifacts)
    generator=ToolInputGenerator(config['tool_sampling'])
    cohort_tasks={row['task_id']:row for row in load_cohort(Path(plan['cohort']))['tasks']};metadata=load_metadata()
    slots=[];started=time.time()
    save(directory/'status.json',{'state':'running','phase':'overlapping_generation_evaluation','pid':os.getpid()})
    def progress():
        save(directory/'progress.json',{'producer_slots_finished':len(slots),'expected_slots':len(plan['task_numbers']),
            'responses_received':len(list(directory.glob('tasks/*/calls/tool_preparation/response.json'))),
            'consumer_slots_finished':len(list(directory.glob('task_receipts/*.json'))),'updated_epoch':time.time()})
    def produce(task):
        context=TaskContext(task,metadata[task['task_id']],artifacts,settings(config,plan['target_program_count']),calls)
        context.cohort_task=cohort_tasks[task['task_id']]
        context.packet=prepare_task_packet(context)
        number=context.task_number;slot={'task_id':task['task_id'],'task_number':number}
        if context.packet.get('skip'):
            slot.update(state='skipped',reason=context.packet['skip']);slots.append(slot)
            save(directory/'task_receipts'/f'{number}.json',slot);progress();return None
        try:
            raw,error=generator.prepare(context)
        except Exception as exc:
            slot.update(state='generation_failed',reason=type(exc).__name__+':'+str(exc))
            save(directory/'task_receipts'/f'{number}.json',slot);slots.append(slot);progress();return None
        response_path=directory/f'tasks/{number}/calls/tool_preparation/response.json'
        if not response_path.exists():
            slot.update(state='unsupported',reason=error)
            save(directory/'task_receipts'/f'{number}.json',slot);slots.append(slot);progress();return None
        if read(response_path.parent/'attempt.json')['state']!='received':
            raise ValueError('Consumer must not receive an unpersisted response')
        preparation_path=directory/f'preparations/{number}.json'
        save(preparation_path,{'raw':raw,'preparation_error':error,'response_sha256':hashlib.sha256(response_path.read_bytes()).hexdigest()})
        slot.update(state='response_persisted',preparation_path=str(preparation_path))
        slots.append(slot);progress()
        return slot
    def consume(slot):
        number=slot['task_number'];log_path=directory/f'consumer_logs/{number}.log';log_path.parent.mkdir(exist_ok=True)
        command=[sys.executable,'-P','-B','-m','final.src.orchestration.tool_overlap','--directory',str(directory),'--consume',str(number)]
        with log_path.open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        receipt_path=directory/'task_receipts'/f'{number}.json'
        if not receipt_path.exists():
            save(receipt_path,{'task_id':slot['task_id'],'state':'failed','reason':'Consumer process exited '+str(result.returncode),'log':str(log_path)})
        return result.returncode
    tasks=[task for task in load_tasks() if int(task['task_id'].split('/')[-1]) in plan['task_numbers']]
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending=overlap(tasks,produce,consume,executor)
        save(directory/'responses_collected.json',{'slots':slots,'finished_epoch':time.time(),'note':'Responses were persisted before submitting each task; CPU consumption overlapped later requests.'})
        for future in pending:future.result()
    receipts=[read(path) for path in sorted((directory/'task_receipts').glob('*.json'))]
    failed=[row for row in receipts if row['state'] not in {'complete','skipped'}]
    save(directory/'status.json',{'state':'failed' if failed else 'complete','phase':'terminal','elapsed_seconds':time.time()-started,'task_receipts':len(receipts),'failed_or_unsupported_tasks':len(failed)})


def consume_task(directory,number):
    import fcntl
    from final.src.modular.artifacts import ArtifactStore
    from final.src.benchmarks.datasets import load_tasks,load_metadata
    from final.src.modular.execution_cache import InputExecutionCache
    from final.src.modular.generators.tools import ToolInputGenerator
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.modular.cohort import call_usage
    config=read(directory/'config_snapshot.json');plan=read(directory/'launch_plan.json')
    tid='HumanEval/'+str(number);prepared=read(directory/f'preparations/{number}.json')
    response_path=directory/f'tasks/{number}/calls/tool_preparation/response.json'
    if hashlib.sha256(response_path.read_bytes()).hexdigest()!=prepared['response_sha256']:
        raise ValueError('Persisted response changed')
    leaf=directory/'evaluation'/str(number);task=next(t for t in load_tasks() if t['task_id']==tid)
    receipt={'task_id':tid,'output_directory':str(leaf),'state':'running','started_epoch':time.time()}
    save(directory/'consumer_active.json',receipt)
    try:
        if prepared['preparation_error']:
            raise ValueError('Preparation response unusable: '+str(prepared['preparation_error']))
        generator=ToolInputGenerator(config['tool_sampling'],preparations={tid:prepared['raw']})
        with Path(plan['native_lock']).open('a+') as native_lock:
            fcntl.flock(native_lock,fcntl.LOCK_EX)
            pipeline=BenchmarkPipeline(Path(plan['cohort']),ArtifactStore(leaf),input_generator=generator,
                settings=settings(config,plan['target_program_count']),execution_cache=InputExecutionCache(Path(plan['execution_cache'])))
            summary=pipeline.run([task],load_metadata())
        receipt.update(state='complete',arms=summary['arms'],evaluated_base_pass=summary['evaluated_base_pass'],
            detection_kinds=summary.get('detection_kinds'),read_only_replay_matches=None,source_hashes_verified=None)
    except Exception as exc:
        receipt.update(state='failed',reason=type(exc).__name__+':'+str(exc))
    receipt['finished_epoch']=time.time()
    save(directory/'task_receipts'/f'{number}.json',receipt)
    save(directory/'consumer_active.json',{'state':'idle','last_task':tid})


def report(directory):
    rows=[read(path) for path in sorted((directory/'task_receipts').glob('*.json'))]
    totals={};counts={};evaluated=0
    for row in rows:
        counts[row['state']]=counts.get(row['state'],0)+1
        if row['state']=='complete':
            evaluated+=row['evaluated_base_pass']
            for arm,metrics in row['arms'].items():
                total=totals.setdefault(arm,{'valid_inputs':0,'detected':0,'tasks_detected':0})
                for key in total:total[key]+=metrics[key]
    from final.src.modular.cohort import call_usage
    result={'task_states':counts,'evaluated_puts':evaluated,'arms':totals,'tester_calls':call_usage(directory),'tasks':rows,
        'freeze_scope':'per-task before oracle; outcomes never fed to producer','semantic_controls':'not supplied; semantic grounding unproven'}
    save(directory/'result_digest.json',result)
    lines=['# Full tool run: generation chồng với sampling/evaluation','',
        f'Đã xử lý {len(rows)}/164 task slots; trạng thái: {counts}. Đã evaluation {evaluated} base-pass PUT; metric task chưa chấm là pending.',
        '','Model Qwen3.5-27B-AWQ, 1 preparation/task, chung5arms, cap20input/task/arm;4096completion/context8192/temp0.7/native8s. Source/config/cohort frozen.',
        '','Producer lưu response trước rồi submit task tới một CPU process; CPU chạy đủ arms/gate/freeze theo task trước oracle/PUT. Producer không đọc outcomes. Freeze scope này thay global freeze; không coi là cùng scheduling protocol cũ.',
        '','| Arm | Valid inputs | Detected PUTs | Tasks detected |','|---|---:|---:|---:|']
    for arm,m in totals.items():lines.append(f"|{arm}|{m['valid_inputs']}|{m['detected']}|{m['tasks_detected']}|")
    lines+=['','Input per-arm có overlap, không cộng thành unique independent inputs. Không có independent signed controls; targets rỗng không chứng minh semantic pass. Unsupported contracts và gate failures không bị bypass. Native cache/replay dùng existing runtime; mỗi task complete chỉ sau required audit/replay.','',
        'Usage thực tế: `'+json.dumps(result['tester_calls'],ensure_ascii=False)+'`','',
        '## Task chưa hoàn tất / bị chặn','']
    for row in rows:
        if row['state']!='complete':lines.append(f"- {row['task_id']}: {row['state']} — {row.get('reason','pending')}")
    (directory/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return result


def produce_run(directory):
    import fcntl
    with (directory/'.producer.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            collect(directory)
        except BaseException as exc:
            save(directory/'status.json',{'state':'failed','phase':'terminal','reason':type(exc).__name__+':'+str(exc)})
            raise


def report_snapshot(directory):
    state=read(directory/'status.json')
    return state,report(directory)


def observe(directory):
    import asyncio
    from uuid import UUID
    from prefect.client.orchestration import get_client
    from prefect.client.schemas.actions import ArtifactCreate,ArtifactUpdate
    from prefect.states import Completed,Failed
    receipt=read(directory/'prefect_record.json');rid=UUID(receipt['flow_run_id'])
    async def publish():
        async with get_client() as client:
            while True:
                state,result=report_snapshot(directory);terminal=state.get('phase')=='terminal'
                await client.update_artifact(UUID(receipt['artifact_ids']['full-tools-progress']),ArtifactUpdate(data='```json\n'+json.dumps({'state':state,'task_states':result['task_states'],'evaluated_puts':result['evaluated_puts'],'usage':result['tester_calls']},ensure_ascii=False,indent=2)+'\n```'))
                for key,kind,data in [('full-tools-results','table',[{'arm':arm,**metrics,'evaluated_puts':result['evaluated_puts']} for arm,metrics in result['arms'].items()]),('full-tools-report','markdown',(directory/'REPORT.md').read_text())]:
                    if key in receipt['artifact_ids']:
                        await client.update_artifact(UUID(receipt['artifact_ids'][key]),ArtifactUpdate(data=data))
                    else:
                        artifact=await client.create_artifact(ArtifactCreate(key=key,type=kind,data=data,flow_run_id=rid));receipt['artifact_ids'][key]=str(artifact.id);save(directory/'prefect_record.json',receipt)
                if terminal:
                    final=Completed(message='Evaluation/audits/replay xong; report published.') if state['state']=='complete' else Failed(message='Run kết thúc với unsupported/gate failures; xem report, metric thiếu giữ pending.')
                    await client.set_flow_run_state(rid,final,force=True)
                    run=await client.read_flow_run(rid);receipt['verified_state']=run.state.type.value
                    import urllib.request
                    for key,aid in receipt['artifact_ids'].items():
                        with urllib.request.urlopen('http://127.0.0.1:4200/api/artifacts/'+aid,timeout=10) as response:artifact=json.load(response)
                        assert artifact['flow_run_id']==str(rid) and artifact['key']==key
                    receipt['verified_artifact_count']=len(receipt['artifact_ids']);save(directory/'prefect_record.json',receipt)
                    break
                await asyncio.sleep(15)
    asyncio.run(publish())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--consume',type=int);parser.add_argument('--observe',action='store_true');args=parser.parse_args();directory=args.directory.resolve()
    if args.observe:observe(directory)
    elif args.consume is not None:consume_task(directory,args.consume)
    else:produce_run(directory)


if __name__=='__main__':main()
