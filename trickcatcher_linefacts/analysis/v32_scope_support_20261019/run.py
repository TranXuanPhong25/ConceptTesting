"""Single authorized seen5 run. Imports frozen CLI adapter, never an endpoint client."""
import argparse
import fcntl
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PRIOR = HERE.parent / 'luna_versions_20261018'
sys.path[:0] = [str(REPO), str(PRIOR)]
from client import Client, MODEL, costs, immutable, now, read, write
from trickcatcher_linefacts.pipelines.v32_scope_support import gate
from trickcatcher_linefacts.pipelines.v32_scope_support.diagnostic_client import SlotFailure

ROOT = REPO / 'trickcatcher_linefacts/out/model_probes/v32_luna_20261019'
OLD_SUITE = ROOT.parent / 'luna_versions_20261018'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def old_inventory():
    bases = [REPO / 'trickcatcher_linefacts/pipelines' / x for x in
             ('v7', 'v23_concepthyp', 'v24_obligations', 'v25_interface_gate')]
    bases += [ROOT.parent / x for x in ('luna_versions_20261018', 'luna_versions_continue_20261019')]
    bases += [REPO / 'trickcatcher_linefacts/out/transport_probes']
    for version, module in (('v23_concepthyp', 'diagnostic'), ('v24_obligations', 'experiment'),
                            ('v25_interface_gate', 'gate')):
        m = importlib.import_module('trickcatcher_linefacts.pipelines.' + version + '.' + module)
        bases.append(m.ROOT)
    return {str(p.relative_to(REPO)): sha(p) for base in bases for p in sorted(base.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts
            and p.suffix != '.pyc'}


def suite_files():
    return {'run.py': sha(HERE / 'run.py'), 'CLI_client': sha(PRIOR / 'client.py'),
            'prereg': sha(gate.HERE / 'PREREG.md'), 'plan_audit': sha(HERE / 'PLAN_AUDIT.md'),
            'code_audit': sha(HERE / 'CODE_AUDIT.md')}


def prepare():
    assert not (ROOT / 'status.json').exists(), 'already_started'
    assert read(HERE / 'audit_approval.json')['passed'] is True
    assert read(HERE / 'audit_approval.json')['sources'] == gate.source_files(), 'post_audit_source_drift'
    prior = read(OLD_SUITE / 'protocol_v4.json')
    assert prior['suite_sources']['client.py'] == sha(PRIOR / 'client.py')
    cli = subprocess.check_output(['codex', '--version'], text=True).strip()
    assert cli == prior['CLI_version'], 'CLI_changed_need_new_readiness'
    assert read(OLD_SUITE / 'readiness_v4.json')['status'] == 'host_disabled_fail_closed_with_schemas_exposed'
    import runner as original_runner
    original_checks = {v: original_runner.old_integrity(v, original_runner.module(v))
                       for v in ('v23', 'v24', 'v25')}
    cpu = gate.preflight(ROOT); assert cpu['passed']
    gate.freeze(ROOT); gate.verify_preflight(ROOT)
    # Same authored packets and entire witness pool as v25, fresh caches and responses.
    assert read(ROOT / 'prepared.json') == read(OLD_SUITE / 'v25/prepared.json')
    immutable(ROOT / 'old_inventory.json', old_inventory())
    immutable(ROOT / 'suite_frozen.json', {
        'sources': gate.source_files(), 'suite_sources': suite_files(), 'CLI_version': cli,
        'requested_model': MODEL, 'reasoning_effort': 'low', 'task_cap': 30,
        'readiness_source_sha256': sha(OLD_SUITE / 'readiness_v4.json'),
        'tool_policy': 'host disabled; schemas exposed; fail closed on recorded tool/router attempts',
        'old_inventory_sha256': sha(ROOT / 'old_inventory.json'), 'prepared_sha256': sha(ROOT / 'prepared.json')})
    immutable(ROOT / 'old_frozen_checks.json', original_checks)
    print('prepared and frozen: 5 cases, <=30 single attempts, no historical outputs imported', flush=True)


def verify():
    frozen = read(ROOT / 'suite_frozen.json')
    assert frozen['sources'] == gate.source_files(), 'source_drift'
    assert frozen['suite_sources'] == suite_files(), 'suite_drift'
    assert frozen['prepared_sha256'] == sha(ROOT / 'prepared.json'), 'prepared_drift'
    assert frozen['old_inventory_sha256'] == sha(ROOT / 'old_inventory.json'), 'inventory_file_drift'
    assert read(ROOT / 'old_inventory.json') == old_inventory(), 'old_source_or_artifact_drift'
    assert frozen['CLI_version'] == subprocess.check_output(['codex', '--version'], text=True).strip()
    gate.verify_preflight(ROOT)


def run():
    verify()
    with (ROOT / 'luna_controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / 'status.json').exists():
            raise RuntimeError('already_started_no_duplicate_launch_or_automatic_retry')
        status = {'state': 'running', 'started_at': now(), 'requested_model': MODEL, 'reasoning_effort': 'low'}
        write(ROOT / 'status.json', status)
        try:
            client = Client(ROOT / 'transport', SlotFailure, 30)
            gate.run(client, ROOT, backend={'mode': 'plain', 'authority': 'CLI; no endpoint/echo'})
            result = gate.report(ROOT)
            verify()
            status.update(state='complete', gates=result['gates'], report='report.json')
        except BaseException as exc:
            status.update(state='incomplete', error_type=type(exc).__name__, error=str(exc)[:200])
        finally:
            status.update(finished_at=now(), costs=costs(ROOT / 'transport'))
            write(ROOT / 'status.json', status)
            print(json.dumps(status), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('command', choices=('prepare', 'run', 'verify'))
    command = p.parse_args().command
    if command == 'prepare': prepare()
    elif command == 'run': run()
    else: verify(); print('integrity verified')
