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
import subprocess
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


def inventory(directory):
    return {str(path): checksum(path) for path in directory.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.name not in ('.worker.lock', '.run.lock')}


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


def load_model_environment(workspace, backend):
    if backend == 'vertex':
        keys = ('VERTEX_PROJECT', 'VERTEX_LOCATION', 'GOOGLE_CLOUD_PROJECT', 'GOOGLE_CLOUD_LOCATION',
                'LLM_THINKING_BUDGET', 'GOOGLE_APPLICATION_CREDENTIALS', 'CLOUDSDK_CONFIG')
    elif backend == 'openrouter' and not os.environ.get('OPENROUTER_API_KEY'):
        keys = ('OPENROUTER_API_KEY',)
    else:
        return
    script = '''source scripts/research_env.sh >/dev/null 2>&1 && source "scripts/${1}_env.sh" >/dev/null 2>&1 || exit 1
shift
for key in "$@"; do
    if [[ -v $key ]]; then printf '%s\\0%s\\0' "$key" "${!key}"; fi
done'''
    values = subprocess.check_output(['/bin/bash', '-c', script, 'provider-env', backend, *keys],
                                     cwd=workspace, stderr=subprocess.DEVNULL).decode().split('\0')
    os.environ.update(zip(values[:-1:2], values[1::2], strict=True))


def prepare(values, directory):
    description=preview(values);config=description['config']
    if directory.exists():raise ValueError('New run requires a new artifact directory')
    directory.mkdir(parents=True)
    runtime=directory/'runtime';hashes={}
    paths=[path for path in (ROOT/'final/src').rglob('*.py') if 'tests' not in path.parts and '__pycache__' not in path.parts]
    paths += [ROOT/'final/__init__.py',ROOT/'final/data/humaneval.jsonl',ROOT/'final/data/contracts.json',
              ROOT/'final/data/humanevalplus_v0.1.10_references.json']
    if config['mode'] == 'pynguin':
        paths += [ROOT/'final/pynguin-requirements.txt']
    for source in paths:
        target=runtime/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target);target.chmod(0o444);hashes[str(target)]=checksum(target)
    cohort=runtime/'cohort.json';shutil.copyfile(description['cohort_path'],cohort);cohort.chmod(0o444);hashes[str(cohort)]=checksum(cohort)
    endpoint=private_endpoint(directory,config['model_name']) if config['mode'] != 'pynguin' and config['model_backend']=='qwen' else None
    save(directory/'config_snapshot.json',config)
    save(directory/'preview.json',description)
    launch_plan={'runtime':str(runtime),'cohort':str(cohort),'workspace':str(ROOT),
        'endpoint_env_file':str(endpoint) if endpoint is not None else None,'native_lock':str(ROOT/'final/out/.boundary_native.lock'),
        'execution_cache':str(ROOT/'final/out/execution_cache'),'task_numbers':description['selected_task_numbers'],
        'target_program_count':description['target_program_count'],'logical_call_cap':description['logical_call_cap']}
    if 'control_flow_4tool' in config['arms']:
        resolved_tools = (ROOT / config['tool_runs_dir']).resolve() if config.get('tool_runs_dir') else (ROOT / 'final/out/put_pytest_tools_20261122')
        launch_plan['tool_runs_dir'] = str(resolved_tools)
    save(directory/'launch_plan.json',launch_plan)
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


def prepare_resume(source,directory, *, timeout_seconds=None, retry_404_request_id=None):
    """Clone immutable config/code/checkpoints; retain per-request attempt budgets."""
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
        original=inventory(source);original_config=normalize(read(source/'config_snapshot.json'));old_plan=read(source/'launch_plan.json')
        config, timeout_amendment = validate_timeout_amendment(source, original_config, timeout_seconds)
        retry_grant = None
        for attempt_path in source.glob('tasks/*/calls/*/attempt.json'):
            request=read(attempt_path.parent/'request.json');attempt=read(attempt_path)
            if attempt.get('request_id')!=digest(request):raise ValueError('Imported call request checksum differs')
            if (attempt_path.parent/'response.json').exists() and attempt['state']!='received':raise ValueError('Response is not received')
            error = attempt.get('error', {})
            if error.get('retryable') is False:
                name, archived, _ = attempt_path.parent.name.partition('_unknown_attempt_')
                if archived and (attempt_path.parent.parent/name/'response.json').is_file():
                    continue
                if (retry_404_request_id != attempt['request_id'] or retry_grant is not None or archived
                        or error.get('http_status') != 404 or error.get('operation') != 'completion'
                        or attempt.get('state') != 'unknown' or attempt.get('attempt_number') not in (1, 2)
                        or config['model_backend'] != 'qwen'):
                    raise ValueError('Permanent historical transport failure')
                retry_grant = (attempt_path.parent.relative_to(source), attempt['request_id'])
        if retry_404_request_id is not None and retry_grant is None:
            raise ValueError('No matching completion 404 with attempts remaining')
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
        endpoint=private_endpoint(directory,config['model_name']) if config['mode'] != 'pynguin' and config['model_backend']=='qwen' else None
        plan={**old_plan,'runtime':str(runtime),'cohort':str(runtime/Path(old_plan['cohort']).relative_to(Path(old_plan['runtime']))),
              'endpoint_env_file':str(endpoint) if endpoint is not None else None,'resume_from':str(source)}
        save(directory/'launch_plan.json',plan)
        receipts={'source':str(source),'source_files':original,'source_state':previous_state,
                  'stop_inferred_from_free_worker_lock':inferred_stop,
                  'metadata_rebuilt_for_new_runtime_paths':rebased,
                  'original_writer_usage':call_usage(source)}
        if timeout_amendment is not None:
            receipts['config_amendment'] = timeout_amendment
        if retry_grant is not None:
            call, request_id = retry_grant
            grant = {'request_id': request_id, 'max_attempts': 3, 'retry_stored_http_statuses': [404],
                     'authorization': 'User confirmed endpoint restoration and requested continuation'}
            save(directory/call.parent/(call.name + '.retry_extension.json'), grant)
            receipts['retry_grant'] = {'call': str(call), **grant}
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
        return read(directory/'preview.json')


def run(directory):
    from final.src.modular.arms.batch import DirectBatchArm
    from final.src.modular.arms.plain import PlainArm
    from final.src.modular.arms.vf3_hybrid import VF3_HYBRID_ARMS
    from final.src.modular.arms.control_flow import ControlFlowArm, ControlFlowFourToolArm
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.calls import RecordedModelCalls
    from final.src.modular.cohort import call_usage
    from final.src.modular.context import PipelineSettings
    from final.src.benchmarks.datasets import DatasetLoader
    from final.src.modular.execution_cache import InputExecutionCache
    from final.src.modular.generators.methods import MethodInputGenerator
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.models import create_model
    from final.src.models.model import TransportError
    config=read(directory/'config_snapshot.json');plan=read(directory/'launch_plan.json')
    if plan.get('workspace'):
        os.environ.setdefault('CONCEPTTESTER_WORKSPACE', plan['workspace'])
    if plan.get('endpoint_env_file'):
        os.environ['FINAL_ENDPOINT_ENV_FILE']=plan['endpoint_env_file']
    def state(name,**extra):save(directory/'status.json',{'state':name,'pid':os.getpid(),'updated_utc':time.time(),**extra})
    class Interrupted(Exception):pass
    def interrupted(*unused):raise Interrupted('Run interrupted; saved calls and retry history preserved')
    signal.signal(signal.SIGTERM,interrupted)
    if config['mode'] == 'pynguin':
        from final.src.modular.pynguin.config import PynguinSettings
        pynguin_settings = PynguinSettings(**config['pynguin'])
        pynguin_settings.validate_environment()
    model = None
    if config['mode'] != 'pynguin':
        backend = config.get('model_backend', 'qwen')
        load_model_environment(plan['workspace'], backend)
        model=create_model(backend=backend, context=config['context_tokens'], model_name=config['model_name'])
        deadline=time.time()+21600
        while True:
            try:
                state('preflight');endpoint=model.check_endpoint();break
            except TransportError as error:
                state('waiting_endpoint',error=error.details())
                if not error.retryable or time.time()>deadline:raise
                time.sleep(30)
        save(directory/'endpoint_readiness.json',{'checked_utc':time.time(),**endpoint})
    tool_runs_dir = plan.get('tool_runs_dir') or config.get('tool_runs_dir')
    factories={
        'direct':DirectBatchArm,
        'plain':PlainArm,
        ControlFlowArm.name:ControlFlowArm,
        ControlFlowFourToolArm.name:lambda: ControlFlowFourToolArm(tool_runs_dir=tool_runs_dir),
    }
    for arm in VF3_HYBRID_ARMS:
        factories[arm.name] = arm
    methods=tuple(factories[name]() for name in config['arms']) if config['mode'] == 'batch' else ()
    settings=PipelineSettings(input_budget=config['inputs_per_task'],input_tokens=config['completion_tokens'],
        input_temperature=config['temperature'],input_seed=config['input_seed'],reference_seed=config['reference_seed'],
        context_tokens=config['context_tokens'],timeout_seconds=config['timeout_seconds'],target_programs=plan['target_program_count'],
        scorer=config['scorer'])
    dataset=DatasetLoader('HE-py')
    tasks=[task for task in dataset.load_tasks() if int(task['task_id'].split('/')[-1]) in plan['task_numbers']]
    if config['mode'] == 'pynguin':
        from final.src.modular.pynguin.adapter import PynguinInputGenerator
        generator = PynguinInputGenerator(pynguin_settings)
    elif config['mode'] == 'tools':
        from final.src.modular.generators.tools import ToolInputGenerator
        generator = ToolInputGenerator(config['tool_sampling'])
    else:
        generator=MethodInputGenerator(methods,empty_context_on_overflow=True,alternate_order=True)
    native_handle=None;generated_count=0;evaluated_count=0
    def before_evaluation():
        nonlocal native_handle
        if native_handle is None:
            state('waiting_native_lock')
            native_handle=Path(plan['native_lock']).open('a+');fcntl.flock(native_handle,fcntl.LOCK_EX)
        state('running',phase='evaluation')
    def record_step(context,stage_name,status):
        nonlocal generated_count,evaluated_count
        if stage_name=='input_generation':
            state('running',phase='generation',task_id=context.task['task_id'])
            if status=='complete':generated_count+=1
        if stage_name=='put_evaluation' and status=='complete':evaluated_count+=1
        save(directory/'progress.json',{'task_id':context.task['task_id'],'stage':stage_name,'event':status,
            'generated_tasks':generated_count,'evaluated_tasks':evaluated_count,'total_tasks':len(tasks),'updated_utc':time.time()})
    try:
        if config['mode'] == 'pynguin':
            state('waiting_native_lock')
            native_handle=Path(plan['native_lock']).open('a+')
            fcntl.flock(native_handle,fcntl.LOCK_EX)
        gen_workers = 6 if config['mode'] == 'batch' and config.get('model_backend', 'qwen') in ('qwen', 'openrouter') else 1
        pipeline=BenchmarkPipeline(Path(plan['cohort']),ArtifactStore(directory),input_generator=generator,settings=settings,
            calls=RecordedModelCalls(model,ArtifactStore(directory)) if model is not None else None,
            execution_cache=InputExecutionCache(Path(plan['execution_cache'])),dataset=dataset,
            on_before_evaluation=before_evaluation,on_step=record_step,generation_workers=gen_workers)
        summary=pipeline.run(tasks,dataset.load_metadata())
        result={'arms':summary['arms'],'evaluated_base_pass':summary['evaluated_base_pass'],
            'tested_base_pass':summary['tested_base_pass'],
            'writer_usage':call_usage(directory),'keepalive_usage':summary['keepalive_calls'],
            'read_only_replay_matches':None,'source_hashes_verified':None,'settings':config}
        for key in ('pynguin', 'tester_calls_by_arm', 'control_flow', 'control_flow_4tool'):
            if key in summary:
                result[key] = summary[key]
        if 'catalogues' in summary:
            result.update(catalogues=summary['catalogues'], comparisons=summary['comparisons'],
                          detection_kinds=summary['detection_kinds'])
        if 'tool_sampling' in summary:
            result['tool_sampling'] = summary['tool_sampling']
            result['tool_treatments'] = summary.get('tool_treatments', {})
            result['domain_authorities'] = summary.get('domain_authorities', {})
            result['detection_kinds'] = summary['detection_kinds']
        if plan.get('resume_from'):
            imports=read(directory/'import_receipts.json')
            old=imports['original_writer_usage'];current=result['writer_usage']
            result['new_writer_usage']={key:current[key]-old[key] for key in ('invocations','received','unknown')}
        save(directory/'result_digest.json',result);state('complete',**result)
        print(json.dumps(result),flush=True)
    finally:
        if native_handle is not None:native_handle.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path);parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--resume-from',type=Path)
    parser.add_argument('--retry-404-request-id')
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
                                           timeout_seconds=args.timeout_seconds,
                                           retry_404_request_id=args.retry_404_request_id)),flush=True)
            return
        if args.config is None:parser.error('--config required')
        print(json.dumps(prepare(read(args.config),directory)),flush=True)


if __name__=='__main__':main()
