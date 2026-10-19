"""Run unchanged native diagnostic engines at explicit new roots with Luna CLI stages."""
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
sys.path[:0] = [str(REPO), str(HERE)]
from client import Client, ProtocolViolation, MODEL, costs, immutable, now, read, write

ROOT = REPO / 'trickcatcher_linefacts/out/model_probes/luna_versions_20261018'
VERSIONS = {'v23': ('v23_concepthyp.diagnostic',160),
            'v24': ('v24_obligations.experiment',90), 'v25': ('v25_interface_gate.gate',30)}


def module(version):
    return importlib.import_module('trickcatcher_linefacts.pipelines.' + VERSIONS[version][0])


def source(version, m):
    return m.source_snapshot() if version=='v23' else m.files() if version=='v24' else m.source_files()


def old_integrity(version, m):
    protocol = read(m.ROOT / 'protocol.json')
    original_sources = protocol['sources' if version=='v25' else 'source']
    assert source(version,m) == original_sources, 'original_source_drift'
    names = ('generation_frozen.json',) if version=='v23' else ('preparation_frozen.json','generation_frozen.json') if version=='v24' else ('run_frozen.json',)
    evidence = {}
    for name in names:
        snapshot = read(m.ROOT/name)
        assert all(hashlib.sha256((m.ROOT/p).read_bytes()).hexdigest()==sha for p,sha in snapshot.items()), 'original_artifact_drift'
        evidence[name] = hashlib.sha256((m.ROOT/name).read_bytes()).hexdigest()
    return {'sources':original_sources, 'original_snapshots':evidence}


def suite_files():
    return {n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('client.py','runner.py','PREREG.md','test_client.py')}


def prepare():
    catalog = read(Path.home()/'.codex/models_cache.json')
    requested = next(x for x in catalog['models'] if x.get('slug')==MODEL)
    versions={}
    for version in VERSIONS:
        m=module(version); root=ROOT/version; old=old_integrity(version,m)
        prepared_name = 'prepared_packets.json' if version=='v24' else 'prepared.json' if version=='v25' else None
        if prepared_name:
            immutable(root/prepared_name,read(m.ROOT/prepared_name))
        cpu=m.preflight(root); assert cpu['passed']
        m.freeze(root); m.verify_preflight(root)
        if prepared_name:
            assert read(root/prepared_name)==read(m.ROOT/prepared_name)
        versions[version]=dict(old, cpu_passed=True, case_count=len(read(root/prepared_name)) if prepared_name else 16,
                              call_cap=VERSIONS[version][1])
    data={'model':MODEL,'reasoning_effort':'low','versions':versions,'suite_sources':suite_files(),
          'CLI_version':subprocess.check_output(['codex','--version'],text=True).strip(),
          'catalog_model':{k:requested.get(k) for k in ('slug','visibility','supported_reasoning_levels')},
          'scope':'native16/9/5 diagnostics only; different CLI harness, unmatched sampling budgets',
          'max_task_CLI_invocations':280,'max_canary_model_turns':1,'source_and_raw_model_origins_separate':True}
    immutable(ROOT/'protocol_v4.json',data)
    print(json.dumps({'prepared':True,'cases':{k:v['case_count'] for k,v in versions.items()},'model':MODEL}))


def verify():
    protocol=read(ROOT/'protocol_v4.json'); assert protocol['suite_sources']==suite_files(),'adapter_drift'
    for version in VERSIONS:
        assert old_integrity(version,module(version))['sources']==protocol['versions'][version]['sources']
    return protocol


def canary():
    """Qualify existing failed-exposure canary as host-denial evidence; NO new model call."""
    verify()
    from client import inspect_events
    path=ROOT/'canary_v3/transport/calls/tools_availability'
    attempt=read(path/'attempts.json')[0]
    events=inspect_events((path/'stdout.jsonl').read_text())
    value=json.loads((path/'last.txt').read_text())
    assert attempt['state']=='protocol_violation' and attempt['usage_known']
    assert events['completed_turns']==1 and not events['forbidden_items']
    assert len(events['configuration_warnings'])==2
    assert value=={'callable_tools':['functions.exec','functions.wait','functions.request_user_input'],'result':5}
    assert 'error=code-mode host is disabled' in (path/'stderr.txt').read_text()
    immutable(ROOT/'readiness_v4.json',{
        'status':'host_disabled_fail_closed_with_schemas_exposed','actual_canary_model_turns':1,
        'exposure_gate_passed':False,'reported_callable_tools':value['callable_tools'],
        'canary_denied_tool_attempts_at_least':1,'observed_external_tool_results':0,
        'original_failed_canary_preserved':True,'canary_costs':costs(ROOT/'canary_v3/transport'),
        'source_evidence':'canary_v3/transport/calls/tools_availability',
        'authority':'post-canary operational qualification before any scientific task outputs; not passed no-tools exposure gate'})
    print('existing canary qualified as host-denial evidence; schemas exposed, no new model turn')


def run(version):
    verify(); assert read(ROOT/'readiness_v4.json')['status']=='host_disabled_fail_closed_with_schemas_exposed'
    m=module(version); root=ROOT/version
    sf=importlib.import_module('trickcatcher_linefacts.pipelines.'+VERSIONS[version][0].rsplit('.',1)[0]+'.diagnostic_client').SlotFailure
    with (root/'luna_controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'luna_status.json').exists():
            raise RuntimeError('version_already_started_no_duplicate_launch')
        status={'state':'running','started_at':now(),'model':MODEL,'reasoning_effort':'low'}
        write(root/'luna_status.json',status)
        try:
            client=Client(root/'transport',sf,VERSIONS[version][1])
            if version=='v25':
                m.run(client,root,backend={'mode':'plain','authority':'CLI adapter; no vLLM enforcement/echo'})
            else:
                m.run(client,root)
            result=m.report(root)
            status.update(state='complete',native_report='report.json',gates=result.get('gates'))
        except BaseException as exc:
            status.update(state='incomplete',error_type=type(exc).__name__,error=str(exc)[:200])
        finally:
            status.update(finished_at=now(),adapter_costs=costs(root/'transport'))
            write(root/'luna_status.json',status)
            print(version,json.dumps(status),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('prepare','canary','run','verify'))
    parser.add_argument('--version',choices=tuple(VERSIONS));args=parser.parse_args()
    if args.command=='prepare':prepare()
    elif args.command=='verify':verify();print('verified')
    elif args.command=='canary':canary()
    else:
        if args.version is None:parser.error('--version required')
        run(args.version)


if __name__=='__main__':main()
