"""Prepare/preview by default. Live work is launched only by an explicit Run."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import sys

from final.src.runtime.artifacts import save
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.orchestration.worker import checksum, load_model_environment, private_endpoint
from .datasets import DATA
from .pipeline import normalize, preview, tasks_for, load_candidates, run_benchmark
from .language_runtime import execute_program

ROOT = Path(__file__).resolve().parents[3]


def prepare(values, directory):
    description = preview(values)
    config = description['config']
    directory = Path(directory).resolve()
    if directory.exists():
        raise ValueError('Use a new artifact directory')
    tasks = tasks_for(config)
    cohort = load_candidates(config['candidate_path'], tasks) if config['candidate_path'] else {}
    directory.mkdir(parents=True)
    runtime = directory / 'runtime'
    sources = [p for p in (ROOT/'final/src').rglob('*')
        if p.is_file() and 'tests' not in p.parts and '__pycache__' not in p.parts and p.suffix in ('.py','.json')]
    sources += [ROOT/'final/__init__.py', ROOT/'final/data/humaneval.jsonl', ROOT/'final/data/contracts.json', *DATA.glob('*')]
    hashes = {}
    for source in sources:
        target = runtime / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target); target.chmod(0o444)
        hashes[str(target)] = checksum(target)
    save(directory/'config_snapshot.json', config)
    save(directory/'preview.json', description)
    save(directory/'tasks_snapshot.json', tasks)
    save(directory/'cohort.json', cohort)
    save(directory/'launch_plan.json', {'runtime':str(runtime), 'workspace':str(ROOT), 'dataset':config['dataset']})
    for name in ('config_snapshot.json','tasks_snapshot.json','cohort.json','launch_plan.json','preview.json'):
        hashes[str(directory/name)] = checksum(directory/name)
    save(directory/'source_snapshot.json', {'sources':hashes, 'archive':{}})
    save(directory/'status.json', {'state':'prepared', 'new_model_calls':0, 'cohort_status':description['cohort_status']})
    return description


def execute(directory, *, replay=False):
    directory = Path(directory).resolve()
    config = json.loads((directory/'config_snapshot.json').read_text())
    plan = json.loads((directory/'launch_plan.json').read_text())
    if not Path(__file__).resolve().is_relative_to(Path(plan['runtime'])):
        raise RuntimeError('Worker must use the frozen runtime from launch_plan.json')
    tasks = json.loads((directory/'tasks_snapshot.json').read_text())
    cohort = json.loads((directory/'cohort.json').read_text())
    if not cohort:
        raise ValueError('No PUT cohort supplied. Import saved complete source before Run; no automatic writer calls.')
    store = ArtifactStore(directory, read_only=replay)
    if replay:
        return store.read('result_digest.json')
    with (directory/'.worker.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory/'worker_started.json').open('x') as marker:
            json.dump({'pid':os.getpid(), 'automatic_restart':False}, marker)
        def interrupt(*unused):
            raise InterruptedError('User/orchestrator interrupted the worker')
        signal.signal(signal.SIGTERM, interrupt)
        save(directory/'status.json', {'state':'running','phase':'generation','pid':os.getpid()})
        try:
            if config['backend']=='qwen':
                os.environ['FINAL_ENDPOINT_ENV_FILE'] = str(private_endpoint(directory, config['model_name']))
            elif config['backend']=='openrouter':
                load_model_environment(plan['workspace'], config['backend'])
            from final.src.models import create_model
            model = create_model(backend=config['backend'], model_name=config['model_name'], context=config['context_tokens'])
            class Calls(RecordedModelCalls):
                def complete(self, *args, **kwargs):
                    return super().complete(*args, **kwargs)
            def native_execution(*args, **kwargs):
                # Release the shared CPU lock before the next model request.
                with (Path(plan['workspace'])/'final/out/.boundary_native.lock').open('a+') as native:
                    fcntl.flock(native, fcntl.LOCK_EX)
                    return execute_program(*args, **kwargs)
            result = run_benchmark(tasks, cohort, store, config, calls=Calls(model, store), executor=native_execution)
            save(directory/'status.json', {'state':'complete','pid':os.getpid(),'read_only_replay_matches':None,'source_hashes_verified':None})
            return result
        except BaseException as error:
            save(directory/'status.json', {'state':'interrupted' if isinstance(error, (InterruptedError, KeyboardInterrupt)) else 'failed',
                'pid':os.getpid(), 'error_type':type(error).__name__, 'results':'pending; see saved task receipts'})
            progress = json.loads((directory/'progress.json').read_text()) if (directory/'progress.json').exists() else {}
            from final.src.modular.cohort import call_usage
            (directory/'REPORT.md').write_text('# Run chưa hoàn tất\n\nMetric chưa có là pending; không coi là 0 detection. '
                'Lỗi: '+type(error).__name__+'. Xem receipts theo task và worker.log.\n\n```json\n'
                +json.dumps({'config':config,'progress':progress,'tester_calls':call_usage(directory)},ensure_ascii=False,indent=2)+'\n```\n')
            raise


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--action', choices=('preview','prepare','run','replay'), default='preview')
    args = parser.parse_args(arguments)
    if args.action in ('run','replay'):
        if args.artifacts is None:
            parser.error('--artifacts is required')
        result = execute(args.artifacts, replay=args.action=='replay')
    else:
        values = json.loads(args.config.read_text()) if args.config else {}
        if args.action=='prepare':
            if args.artifacts is None:
                parser.error('--artifacts is required for prepare')
            result = prepare(values, args.artifacts)
        else:
            result = preview(values)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
