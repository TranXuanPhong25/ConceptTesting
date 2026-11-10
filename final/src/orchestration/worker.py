"""Benchmark subprocess entry point; never imports Prefect or its environment."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import sys
import time
import uuid

from .config import ROOT, normalize, preview


def read(path):return json.loads(Path(path).read_text())


def save(path, value):
    from final.src.runtime.artifacts import save as atomic_save
    atomic_save(Path(path), value)


def checksum(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private_endpoint(directory, model_name):
    source=Path(os.environ.get('FINAL_ENDPOINT_ENV_FILE',str(Path.home()/'.config/concepttester/final-qwen.env'))).expanduser()
    if not source.is_file():raise ValueError('Private endpoint profile is missing; configure ~/.config/concepttester/final-qwen.env')
    lines=[]
    for line in source.read_text().splitlines():
        fields=shlex.split(line, comments=True)
        if fields and fields[0]=='export':fields=fields[1:]
        if len(fields)==1 and fields[0].startswith('FINAL_MODEL='):continue
        lines.append(line)
    lines.append('export FINAL_MODEL='+shlex.quote(model_name))
    folder=Path.home()/'.config/concepttester/run-endpoints';folder.mkdir(parents=True,exist_ok=True);folder.chmod(0o700)
    import hashlib
    profile_id=hashlib.sha256(str(directory.resolve()).encode()).hexdigest()[:24]
    target=folder/(profile_id+'.env')
    with target.open('x') as output:output.write('\n'.join(lines)+'\n')
    target.chmod(0o600)
    return target


def prepare(values, directory):
    description=preview(values);config=description['config']
    if directory.exists():raise ValueError('New run requires a new artifact directory')
    directory.mkdir(parents=True)
    runtime=directory/'runtime';hashes={}
    paths=[path for path in (ROOT/'final/src').rglob('*.py') if 'tests' not in path.parts and '__pycache__' not in path.parts]
    paths += [ROOT/'final/__init__.py',ROOT/'final/data/humaneval.jsonl',ROOT/'final/data/contracts.json',
              ROOT/'final/data/humanevalplus_v0.1.10_references.json']
    paths += list((ROOT/'final/src/modular/fault_oriented_testing').glob('*.json'))
    for source in paths:
        target=runtime/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target);target.chmod(0o444);hashes[str(target)]=checksum(target)
    if config['scorer']=='full_two_repeats':
        original=ROOT/'final/out/boundary_soft_humaneval164_resume_20261107_195417/runtime/final/src/modular/stages/put_evaluation.py'
        target=runtime/'final/src/modular/stages/put_evaluation.py';target.chmod(0o644)
        shutil.copyfile(original,target);target.chmod(0o444);hashes[str(target)]=checksum(target)
    cohort=runtime/'cohort.json';shutil.copyfile(description['cohort_path'],cohort);cohort.chmod(0o444);hashes[str(cohort)]=checksum(cohort)
    endpoint=private_endpoint(directory,config['model_name'])
    save(directory/'config_snapshot.json',config)
    save(directory/'preview.json',description)
    save(directory/'launch_plan.json',{'runtime':str(runtime),'cohort':str(cohort),'workspace':str(ROOT),
        'endpoint_env_file':str(endpoint),'native_lock':str(ROOT/'final/out/.boundary_native.lock'),
        'execution_cache':str(ROOT/'final/out/execution_cache'),'task_numbers':description['selected_task_numbers'],
        'target_program_count':description['target_program_count'],'logical_call_cap':description['logical_call_cap']})
    for name in ('config_snapshot.json','preview.json','launch_plan.json'):hashes[str(directory/name)]=checksum(directory/name)
    save(directory/'source_snapshot.json',{'sources':hashes,'archive':{}})
    save(directory/'status.json',{'state':'prepared','new_model_calls':0})
    return description


def validate_timeout_amendment(source, original_config, timeout_seconds):
    """Only amend native timeout before any saved oracle/PUT evaluation exists."""
    if timeout_seconds is None:
        return original_config, None
    amended_config = normalize({**original_config, 'timeout_seconds': timeout_seconds})
    if amended_config['timeout_seconds'] == original_config['timeout_seconds']:
        return amended_config, None
    native_patterns = ('tasks/*/oracle_*.json', 'tasks/*/evaluation/*.json',
                       'tasks/*/result.json', 'tasks/*/reference_program.json',
                       'tasks/*/catalogue_measurements.json')
    if any(next(source.glob(pattern), None) is not None for pattern in native_patterns):
        raise ValueError('Timeout amendment requires generation-only source; native checkpoints already exist')
    return amended_config, {'field': 'timeout_seconds', 'previous': original_config['timeout_seconds'],
                            'current': amended_config['timeout_seconds'],
                            'scope': 'native evaluation only; received generation requests/responses preserved'}


def prepare_resume(source,directory, *, timeout_seconds=None):
    """Clone immutable config/code/checkpoints; retain per-request attempt budgets."""
    from final.src.audits.resume_bva_batch import inventory
    from final.src.audits.run_bva_full import SourceGuard
    from final.src.modular.cohort import call_usage
    from final.src.runtime.artifacts import digest
    if directory.exists():raise ValueError('Resume requires a new output directory')
    with (source/'.worker.lock').open('r') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        previous_state=read(source/'status.json')['state']
        inferred_stop=(previous_state in ('running','preflight','waiting_endpoint','waiting_native_lock')
                       and (source/'worker_started.json').is_file())
        if previous_state not in ('interrupted','cancelled') and not inferred_stop:
            raise ValueError('Only a stopped interrupted/cancelled run can resume')
        SourceGuard(source).verify()
        original=inventory(source);original_config=normalize(read(source/'config_snapshot.json'));old_plan=read(source/'launch_plan.json')
        config, timeout_amendment = validate_timeout_amendment(source, original_config, timeout_seconds)
        for attempt_path in source.glob('tasks/*/calls/*/attempt.json'):
            request=read(attempt_path.parent/'request.json');attempt=read(attempt_path)
            if attempt.get('request_id')!=digest(request):raise ValueError('Imported call request checksum differs')
            if (attempt_path.parent/'response.json').exists() and attempt['state']!='received':raise ValueError('Response is not received')
            if attempt.get('error',{}).get('retryable') is False:raise ValueError('Permanent historical transport failure')
        directory.mkdir(parents=True);runtime=directory/'runtime'
        shutil.copytree(source/'runtime',runtime,ignore=shutil.ignore_patterns('__pycache__'))
        if (source/'tasks').exists():shutil.copytree(source/'tasks',directory/'tasks')
        if (source/'keepalive').exists():shutil.copytree(source/'keepalive',directory/'keepalive')
        rebased=[]
        for path in (directory/'tasks').rglob('*.json'):
            if path.name=='reference_program.json' or (path.name=='identity.json' and 'boundary' in path.parts):
                rebased.append(str(path.relative_to(directory)));path.unlink()
        for name in ('config_snapshot.json','preview.json','generation_frozen.json'):
            if (source/name).exists():shutil.copyfile(source/name,directory/name)
        if timeout_amendment is not None:
            # New output records the amendment; the stopped source stays immutable.
            save(directory/'config_snapshot.json', config)
            description = read(source/'preview.json')
            description['config'] = config
            save(directory/'preview.json', description)
        endpoint=private_endpoint(directory,config['model_name'])
        plan={**old_plan,'runtime':str(runtime),'cohort':str(runtime/Path(old_plan['cohort']).relative_to(Path(old_plan['runtime']))),
              'endpoint_env_file':str(endpoint),'resume_from':str(source)}
        save(directory/'launch_plan.json',plan)
        receipts={'source':str(source),'source_files':original,'source_state':previous_state,
                  'stop_inferred_from_free_worker_lock':inferred_stop,
                  'metadata_rebuilt_for_new_runtime_paths':rebased,
                  'original_writer_usage':call_usage(source)}
        if timeout_amendment is not None:
            receipts['config_amendment'] = timeout_amendment
        save(directory/'import_receipts.json',receipts)
        hashes=dict(original)
        for path in directory.rglob('*'):
            if not path.is_file() or path.name=='status.json':continue
            mutable=False
            if 'calls' in path.parts and '_unknown_attempt_' not in path.parent.name and (path.parent/'attempt.json').exists():
                mutable=read(path.parent/'attempt.json')['state']!='received'
            if not mutable:hashes[str(path)]=checksum(path)
        save(directory/'source_snapshot.json',{'sources':hashes,'archive':{}})
        save(directory/'status.json',{'state':'prepared','new_model_calls':0,'resume_from':str(source)})
        if inventory(source)!=original:raise ValueError('Original run changed while preparing resume')
        return read(directory/'preview.json')


def run(directory):
    from final.src.modular.arms.batch import DirectBatchArm,SoftBvaBatchArm
    from final.src.modular.arms.boundary import BoundaryArm
    from final.src.modular.arms.plain import PlainArm
    from final.src.modular.arms.classical import CATALOGUE_ARMS, CatalogueSettings
    from final.src.modular.arms.fault_oriented import V2_ARMS
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.calls import RecordedModelCalls
    from final.src.modular.cohort import call_usage
    from final.src.modular.context import PipelineSettings
    from final.src.modular.dataset import load_tasks,load_metadata
    from final.src.modular.execution_cache import InputExecutionCache
    from final.src.modular.generators.methods import MethodInputGenerator
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.modular.stages.input_preparation import InputPreparationStage
    from final.src.runtime.model import QwenModel,TransportError
    from final.src.runtime.keepalive import KeepAlive
    from final.src.audits.run_bva_full import SourceGuard
    config=read(directory/'config_snapshot.json');plan=read(directory/'launch_plan.json')
    guard=SourceGuard(directory);guard.verify()
    os.environ['FINAL_ENDPOINT_ENV_FILE']=plan['endpoint_env_file']
    def state(name,**extra):save(directory/'status.json',{'state':name,'pid':os.getpid(),'updated_utc':time.time(),**extra})
    class Interrupted(Exception):pass
    def interrupted(*unused):raise Interrupted('Run interrupted; saved calls and retry history preserved')
    signal.signal(signal.SIGTERM,interrupted)
    model=QwenModel(context=config['context_tokens'],expected_model=config['model_name'])
    deadline=time.time()+21600
    while True:
        try:
            state('preflight');endpoint=model.check_endpoint();break
        except TransportError as error:
            state('waiting_endpoint',error=error.details())
            if not error.retryable or time.time()>deadline:raise
            time.sleep(30)
    save(directory/'endpoint_readiness.json',{'checked_utc':time.time(),**endpoint})
    factories={'direct':DirectBatchArm,'soft_bva':SoftBvaBatchArm,
               'plain':PlainArm,
               'boundary':lambda:BoundaryArm(base_example_limit=config['per_put_base_examples'])}
    for arm in (*CATALOGUE_ARMS, *V2_ARMS):
        factories[arm.name] = lambda arm=arm: arm(CatalogueSettings(catalogue=config.get('catalogue', True)))
    methods=tuple(factories[name]() for name in config['arms'])
    settings=PipelineSettings(input_budget=config['inputs_per_task'],input_tokens=config['completion_tokens'],
        input_temperature=config['temperature'],input_seed=config['input_seed'],reference_seed=config['reference_seed'],
        context_tokens=config['context_tokens'],timeout_seconds=config['timeout_seconds'],target_programs=plan['target_program_count'])
    tasks=[task for task in load_tasks() if int(task['task_id'].split('/')[-1]) in plan['task_numbers']]
    class Preparation(InputPreparationStage):
        def prepare(self,context):
            packet=super().prepare(context)
            if packet.get('skip')=='prompt_too_large':
                return {'task_id':packet['task_id'],'visible_put_ids':[],'common':'','prompt_tokens':{},'empty_context':True}
            return packet
    class Generator(MethodInputGenerator):
        def generate(self,context):
            if context.packet.get('skip'):return {'task_id':context.task['task_id'],'skip':context.packet['skip']}
            if context.packet.get('empty_context'):
                return {'task_id':context.task['task_id'],'arms':{method.name:{'inputs':[],'rejected':[],
                    'status':'prompt_too_large'} for method in self.methods}}
            order=self.methods if context.task_number%2==0 else tuple(reversed(self.methods))
            records={method.name:method.run(context) for method in order}
            return {'task_id':context.task['task_id'],'arms':{method.name:records[method.name] for method in self.methods}}
    generator=Generator(methods,preparation_stages=(Preparation(methods),))
    native_handle=None;observer=None;generated_count=0;evaluated_count=0
    class Pipeline(BenchmarkPipeline):
        def execute_stages(self,stages,context):
            nonlocal native_handle,observer
            guard.verify()
            if stages[0].name=='reference_oracle' and not self.artifacts.read_only and native_handle is None:
                if observer is not None:
                    observer.__exit__(None,None,None)
                    observer.thread.join()
                    observer=None
                state('waiting_native_lock')
                native_handle=Path(plan['native_lock']).open('a+');fcntl.flock(native_handle,fcntl.LOCK_EX)
                state('running',phase='evaluation')
            return super().execute_stages(stages,context)
        def record_stage_event(self,context,stage,status,**details):
            nonlocal generated_count,evaluated_count
            super().record_stage_event(context,stage,status,**details)
            if self.artifacts.read_only:return
            if stage.name=='input_generation':
                state('running',phase='generation',task_id=context.task['task_id'])
                if status=='complete':generated_count+=1
            if stage.name=='put_evaluation' and status=='complete':evaluated_count+=1
            save(directory/'progress.json',{'task_id':context.task['task_id'],'stage':stage.name,'event':status,
                'generated_tasks':generated_count,'evaluated_tasks':evaluated_count,'total_tasks':len(tasks),'updated_utc':time.time()})
    try:
        observer=KeepAlive(directory,model_factory=lambda:QwenModel(context=config['context_tokens'],timeout=60,expected_model=config['model_name']))
        observer.__enter__()
        pipeline=Pipeline(Path(plan['cohort']),ArtifactStore(directory),input_generator=generator,settings=settings,
            calls=RecordedModelCalls(model,ArtifactStore(directory)),execution_cache=InputExecutionCache(Path(plan['execution_cache'])))
        summary=pipeline.run(tasks,load_metadata())
        guard.verify()
        replay=Pipeline(Path(plan['cohort']),ArtifactStore(directory,read_only=True),input_generator=generator,
            settings=settings,execution_cache=InputExecutionCache(Path(plan['execution_cache']),read_only=True))
        if replay.run(tasks,load_metadata())!=summary:raise ValueError('Immutable replay differs')
        result={'arms':summary['arms'],'evaluated_base_pass':summary['evaluated_base_pass'],
            'writer_usage':call_usage(directory),'keepalive_usage':summary['keepalive_calls'],
            'read_only_replay_matches':True,'source_hashes_verified':True,'settings':config}
        if 'catalogues' in summary:
            result.update(catalogues=summary['catalogues'], comparisons=summary['comparisons'],
                          detection_kinds=summary['detection_kinds'])
        if set(config['arms'])=={'direct','soft_bva'}:
            from final.src.audits.run_bva_batch import paired_verdicts
            result['comparison']=paired_verdicts(directory)
        if plan.get('resume_from'):
            from final.src.audits.resume_bva_batch import inventory
            imports=read(directory/'import_receipts.json')
            if inventory(Path(plan['resume_from']))!=imports['source_files']:raise ValueError('Original run changed')
            old=imports['original_writer_usage'];current=result['writer_usage']
            result['new_writer_usage']={key:current[key]-old[key] for key in ('invocations','received','unknown')}
            result['original_run_unchanged']=True
        save(directory/'result_digest.json',result);state('complete',**result)
        print(json.dumps(result),flush=True)
    finally:
        if observer is not None:
            observer.__exit__(None,None,None)
            observer.thread.join()
        if native_handle is not None:native_handle.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path);parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--resume-from',type=Path)
    parser.add_argument('--timeout-seconds',type=float,
                        help='Amend native timeout for a generation-only stopped run; preserve saved generation')
    parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--worker',action='store_true')
    args=parser.parse_args();directory=args.artifacts.resolve()
    if args.worker:
        with (directory/'.worker.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with (directory/'worker_started.json').open('x') as marker:json.dump({'pid':os.getpid(),'automatic_restart':False},marker)
            try:run(directory)
            except BaseException as error:
                save(directory/'status.json',{'state':'interrupted','pid':os.getpid(),'updated_utc':time.time(),
                    'error_type':type(error).__name__,'error':error.details() if hasattr(error,'details') else str(error)})
                raise
    else:
        if args.resume_from:
            print(json.dumps(prepare_resume(args.resume_from.resolve(),directory,
                                           timeout_seconds=args.timeout_seconds)),flush=True)
            return
        if args.config is None:parser.error('--config required')
        print(json.dumps(prepare(read(args.config),directory)),flush=True)


if __name__=='__main__':main()
