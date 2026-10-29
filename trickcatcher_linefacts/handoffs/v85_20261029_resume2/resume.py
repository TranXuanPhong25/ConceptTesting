"""Resume only missing shared references, then grade the frozen113paired tasks."""
import argparse
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import sys
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
RUN_REL = Path('trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/handoff_resume2_20261029')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unpack(work):
    manifest = json.loads((HERE/'MANIFEST.json').read_text())
    archive = HERE/'checkpoint.tar.gz'
    if sha(archive) != manifest['archive_sha256']:
        raise ValueError('checkpoint_archive_changed')
    snapshot = work/'snapshot'
    if not snapshot.exists():
        work.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive,'r:gz') as bundle:
            for member in bundle.getmembers():
                p = Path(member.name)
                if p.is_absolute() or '..' in p.parts or not member.isfile():
                    raise ValueError('unsafe_archive_member')
            bundle.extractall(work,filter='data')
    for name,digest in manifest['files'].items():
        data = (work/name).read_bytes()
        # The ledger may grow; the imported history must remain byte-for-byte intact.
        if name == manifest['ledger']['path']:
            data = data[:manifest['ledger']['bytes']]
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('imported_source_or_checkpoint_changed: '+name)
    return snapshot


def check_ledger(root):
    attempts = [json.loads(line) for line in (root/'transport/attempts.jsonl').read_text().splitlines()]
    keys = [row['key'] for row in attempts]
    history = json.loads((root/'HISTORY.json').read_text())
    if len(keys) != len(set(keys)) or len(keys)+len(history) > 3503 or len(history) != 18:
        raise ValueError('cumulative_attempt_inventory_invalid')
    for key in keys:
        folder = root/'transport/calls'/key
        if not (folder/'response.json').exists():
            raise ValueError('unresolved_attempt_do_not_retry: '+key)
        response = json.loads((folder/'response.json').read_text())
        body = json.loads((folder/'request.json').read_text())['body']
        digest = hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if response.get('status') != 'received' or response.get('key') != key or digest != key:
            raise ValueError('failed_or_changed_attempt_do_not_retry: '+key)
    return len(keys),history


def missing_oracles(root,jobs):
    missing = []
    for job in jobs:
        path = root/'oracles'/str(job['task'])/f'{job["sample"]}.json'
        if not path.exists():
            missing.append(job)
            continue
        record = json.loads(path.read_text())
        response = record['response']
        folder = root/'transport/calls'/response['key']
        request = json.loads((folder/'request.json').read_text())['body']
        if (record['task'] != job['task'] or record['sample'] != job['sample']
                or response != json.loads((folder/'response.json').read_text())
                or request['messages'] != job['messages'] or request['seed'] != job['seed']
                or request['model'] != 'qwen3.5-27b-awq' or request['temperature'] != .8
                or request['top_p'] != .95 or request['max_tokens'] != 1024):
            raise ValueError('saved_oracle_identity_mismatch')
    return missing


def cumulative_results(results,history):
    historical = len(history)
    unknown = sum(bool(r["response"].get("unknown_completion_usage")) for r in history)
    if 'completion_attempts_current_ledger' in results:
        raise ValueError('historical_attempts_already_counted')
    results = dict(results)
    results['completion_attempts_current_ledger'] = results['completion_attempts']
    results['completion_attempts'] += historical
    results['unknown_completion_usage'] += unknown
    results['inherited_unknown_completion_usage'] = unknown
    results['historical_physical_attempts'] = historical
    results['duplicate_received_attempts'] = sum(r.get('duplicate',False) for r in history)
    results['usage'] = {key:value+sum(r['response'].get('usage',{}).get(key,0) for r in history) for key,value in results.get('usage',{}).items()}
    if results['completion_attempts'] > 3503:
        raise ValueError('cumulative_attempt_cap_exceeded')
    return results


def native_checks(run,package):
    tests = unittest.defaultTestLoader.loadTestsFromName(package+'.test_retrievalhybrid.RetrievalHybridTests.test_native_shared_oracle_requires_agreement_and_three_survivors')
    if not unittest.TextTestRunner(verbosity=1).run(tests).wasSuccessful():
        raise RuntimeError('native_oracle_preflight_failed')
    # A reachable parent listener distinguishes network isolation from a closed port.
    with socket.socket() as listener, tempfile.TemporaryDirectory() as directory:
        listener.bind(('127.0.0.1',0))
        listener.listen()
        port = listener.getsockname()[1]
        with socket.create_connection(('127.0.0.1',port),timeout=2):
            pass
        root = Path(directory)
        script,job,output = root/'network.py',root/'job.json',root/'output.json'
        job.write_text('{}')
        script.write_text('import json,socket,sys\nfrom pathlib import Path\ntry:\n s=socket.create_connection(("127.0.0.1",'+str(port)+'),timeout=2)\n s.close()\n denied=False\nexcept OSError:\n denied=True\nPath(sys.argv[2]).write_text(json.dumps({"denied":denied}))\n')
        result = run.v4_runtime.gen_inputs.sandbox(run.v4_runtime.interpreter(),script,job,output,10)
        if result.get('denied') is not True:
            raise RuntimeError('native_network_isolation_failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true',help='offline integrity and native sandbox checks; no model calls')
    mode.add_argument('--run',action='store_true',help='generate only missing refs, then score both arms')
    parser.add_argument('--work-dir',type=Path,default=HERE/'work')
    args = parser.parse_args()
    if os.environ.get('LINEFACTS_FAIR_FLAGS') or os.environ.get('LINEFACTS_DATASET') not in (None,'humaneval'):
        raise ValueError('remove_pipeline_environment_overrides')
    os.environ['V4_PYTHON'] = str(Path(sys.executable).absolute())
    args.work_dir.mkdir(parents=True,exist_ok=True)
    work_lock = (args.work_dir/'handoff.lock').open('a')
    fcntl.flock(work_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    snapshot = unpack(args.work_dir.absolute())
    sys.path.insert(0,str(snapshot))
    package = 'trickcatcher_linefacts.pipelines.v85_retrievalhybrid'
    run = importlib.import_module(package+'.comparison')
    scoring = importlib.import_module(package+'.comparison_score')
    transport = importlib.import_module(package+'.transport')
    client_class = importlib.import_module('trickcatcher_linefacts.pipelines.v85_transport_longwait.transport').Client
    root = snapshot/RUN_REL
    run.ROOT = root
    # Relocate only the interpreter used by native workers; frozen config bytes stay intact.
    run.CONFIG['V4_PYTHON'] = str(Path(sys.executable).absolute())
    run.verify()
    run.v4_runtime.require_versions()
    run.v4_runtime.interpreter()
    prepared = [json.loads(p.read_text()) for p in (root/'prepared').glob('*.json')]
    expected = {t['task'] for t in json.loads((run.HERE/'assets/tasks.json').read_text())}
    if len(prepared) != 113 or {p['v11']['task'] for p in prepared} != expected:
        raise ValueError('prepared_cohort_mismatch')
    for arm in ('v11','retrieval'):
        found = {int(p.parts[-4]) for p in (root/'generation'/arm).glob('*/artifacts/*/0/concept-hybrid/result.json')}
        if found != expected:
            raise ValueError('paired_generation_incomplete')
    prepared.sort(key=lambda p:hashlib.sha256(str(p['v11']['task']).encode()).hexdigest())
    jobs = list(run.oracle_jobs(prepared))
    if len(jobs) != 1130:
        raise ValueError('oracle_job_inventory_mismatch')
    with (root/'RUN.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        received,history = check_ledger(root)
        historical = len(history)
        missing = missing_oracles(root,jobs)
        native_checks(run,package)
        print(json.dumps(dict(generation_pairs=113,received=received,historical_attempts=historical,historical_unknown=sum(bool(r["response"].get("unknown_completion_usage")) for r in history),
                              saved_oracles=1130-len(missing),missing_oracles=len(missing),output=str(root))),flush=True)
        if args.check or (root/'HANDOFF_COMPLETE.json').exists():
            return
        (root/'controller.pid').write_text(str(os.getpid())+'\n')
        transport.MAX_ATTEMPTS = 3503-historical
        client = client_class(root/'transport')
        def generate_oracle(job):
            response = client.chat(job['messages'],job['seed'],temperature=.8,top_p=.95,max_tokens=1024)
            run.atomic_json(root/'oracles'/str(job['task'])/f'{job["sample"]}.json',dict(task=job['task'],sample=job['sample'],response=response))
        try:
            client.preflight()
            run.run_pool('remaining_shared_spec_oracle',missing,generate_oracle)
            if missing_oracles(root,jobs):
                raise ValueError('oracle_inventory_incomplete')
            check_ledger(root)
            run.verify()
            files = [p for part in ('generation','oracles','transport','prepared') for p in (root/part).rglob('*')
                     if p.is_file() and p.suffix in ('.json','.jsonl','.py')]
            run.atomic_json(root/'GENERATION_FREEZE.json',dict(files={str(p.relative_to(root)):sha(p) for p in sorted(files)},target_reference_used=False))
            scoring.score(prepared)
            results = cumulative_results(json.loads((root/'RESULTS.json').read_text()),history)
            results['continuation'] = 'portable_handoff_resume2_20261029'
            run.atomic_json(root/'RESULTS.json',results)
            status = json.loads((root/'STATUS.json').read_text())
            status.update(completion_attempts=results['completion_attempts'],unknown_completion_usage=results['unknown_completion_usage'])
            run.atomic_json(root/'STATUS.json',status)
            run.atomic_json(root/'COMPLETE.json',status)
            run.atomic_json(root/'HANDOFF_COMPLETE.json',status)
        except Exception as exc:
            # Endpoint details never enter logs/status; transport already returns sanitized errors.
            run.atomic_json(root/'STATUS.json',dict(stage='blocked',error_type=type(exc).__name__))
            raise SystemExit('handoff_blocked: '+type(exc).__name__) from None


if __name__ == '__main__':
    main()
