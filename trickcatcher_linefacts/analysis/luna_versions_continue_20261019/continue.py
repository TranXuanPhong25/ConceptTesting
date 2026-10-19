"""Continue only missing native stages; accepted old outputs and quota ledgers stay intact."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
BASE=HERE.parent/'luna_versions_20261018'
sys.path[:0]=[str(BASE),str(REPO)]
import runner as old
from client import Client, costs, immutable, now, read, write

ROOT=REPO/'trickcatcher_linefacts/out/model_probes/luna_versions_continue_20261019'
EXCLUDE={'luna_status.json','luna_controller.pid','luna_controller.log','luna_controller.lock'}
FAILED={'v23':'f06__hyp_only__revision','v24':'f06__text_hyp__revision'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def inventory(path):
    return {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def prepare():
    old.verify()
    assert subprocess.check_output(['codex','--version'],text=True).strip()==read(old.ROOT/'protocol_v4.json')['CLI_version'],'CLI_changed'
    ROOT.mkdir(parents=True,exist_ok=False)
    versions={}
    for version,slot in FAILED.items():
        source=old.ROOT/version;status=read(source/'luna_status.json')
        assert status['state']=='incomplete'
        failure=source/'transport/calls'/slot
        assert not (failure/'response.json').exists()
        assert 'You’ve hit your usage limit.' in (failure/'stdout.jsonl').read_text()
        assert read(failure/'attempts.json')[0]['denied_router_attempt'] is False
        originals=inventory(source)
        dest=ROOT/version
        shutil.copytree(source,dest,ignore=shutil.ignore_patterns(*EXCLUDE))
        copied=inventory(dest)
        assert all(originals[k]==v for k,v in copied.items())
        accepted=len(list((source/'transport/calls').glob('*/response.json')))
        versions[version]={'original_inventory':originals,'imported_inventory':copied,
                           'accepted_imported_responses':accepted,'quota_failed_slot':slot,
                           'new_call_cap':old.VERSIONS[version][1]-accepted}
    protocol={'authorization':'user explicit continuation2026-10-19','created_at':now(),
              'wrapper_sha256':sha(Path(__file__)),'PREREG_sha256':sha(HERE/'PREREG.md'),
              'old_suite_protocol_sha256':sha(old.ROOT/'protocol_v4.json'),'versions':versions,
              'v25_original_inventory':inventory(old.ROOT/'v25'),
              'client_source_sha256':sha(BASE/'client.py'),'requested_model':'gpt-5.6-luna','effort':'low'}
    immutable(ROOT/'resume_protocol.json',protocol)
    print(json.dumps({v:{k:x[k] for k in ('accepted_imported_responses','new_call_cap','quota_failed_slot')} for v,x in versions.items()}))


def verify():
    p=read(ROOT/'resume_protocol.json')
    assert p['wrapper_sha256']==sha(Path(__file__)) and p['PREREG_sha256']==sha(HERE/'PREREG.md')
    assert p['client_source_sha256']==sha(BASE/'client.py')
    old.verify()
    for v in FAILED:assert inventory(old.ROOT/v)==p['versions'][v]['original_inventory']
    assert inventory(old.ROOT/'v25')==p['v25_original_inventory']
    return p


class ContinuationClient:
    def __init__(self,version,protocol):
        self.root=ROOT/version;self.previous=old.ROOT/version/'transport/calls'
        sf=__import__('importlib').import_module('trickcatcher_linefacts.pipelines.'+old.VERSIONS[version][0].rsplit('.',1)[0]+'.diagnostic_client').SlotFailure
        self.fresh=Client(self.root/'continuation_transport',sf,protocol['versions'][version]['new_call_cap'])
    def complete(self,request):
        previous=self.previous/request['slot']
        if (previous/'response.json').exists():
            assert request==read(previous/'request.json'),'imported_request_drift'
            immutable(self.root/'reused_transport'/request['slot']/'reuse.json',
                      {'original_response_sha256':sha(previous/'response.json'),'origin':'accepted_previous_stage_not_new_sample'})
            return read(previous/'response.json')
        if previous.exists():assert request==read(previous/'request.json'),'quota_request_drift'
        return self.fresh.complete(request)


def run(version):
    p=verify();root=ROOT/version
    with (root/'luna_controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert not (root/'luna_status.json').exists(),'already_started'
        status={'state':'running','started_at':now(),'requested_model':'gpt-5.6-luna','resumed':True}
        write(root/'luna_status.json',status)
        try:
            m=old.module(version);m.run(ContinuationClient(version,p),root)
            m.report(root);status.update(state='complete',native_report='report.json')
        except BaseException as exc:
            status.update(state='incomplete',error_type=type(exc).__name__,error=str(exc)[:200])
        finally:
            status.update(finished_at=now(),new_costs=costs(root/'continuation_transport'),
                          imported_old_costs=costs(root/'transport'))
            write(root/'luna_status.json',status);print(version,json.dumps(status),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('prepare','verify','run'));p.add_argument('--version',choices=tuple(FAILED));a=p.parse_args()
    if a.command=='prepare':prepare()
    elif a.command=='verify':verify();print('originals unchanged; continuation wrapper verified')
    else:
        if not a.version:p.error('--version required')
        run(a.version)


if __name__=='__main__':main()
