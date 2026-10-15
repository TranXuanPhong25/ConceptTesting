"""Detached controller for an authorized frozen concept run; endpoints remain in environment."""
import argparse
import datetime as dt
import fcntl
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import urllib.request

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))


def save(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--version',required=True);ap.add_argument('--notify-thread');ap.add_argument('--workers',type=int,default=2)
    a=ap.parse_args()
    if not re.fullmatch(r'v[0-9]+_[a-z_]+',a.version) or a.workers<1:ap.error('invalid version/workers')
    here=REPO/'trickcatcher_linefacts/pipelines'/a.version;root=here/'out/humaneval/behavior_smoke'
    directory=REPO/'trickcatcher_linefacts/out'/('runlogs_'+a.version);directory.mkdir(parents=True,exist_ok=True)
    with (directory/'controller.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Run already controlled')
        experiment=importlib.import_module('trickcatcher_linefacts.pipelines.'+a.version+'.behavior_experiment')
        experiment.verify()
        config=json.loads((here/'config.json').read_text())
        if config['model']!='qwen2.5-coder-7b-instruct':raise SystemExit('Pinned model changed')
        from trickcatcher_linefacts.pipelines.v17_templates.llm_client import Client,NoRedirect
        Client(root/'model_cache',offline=False,workers=a.workers)
        stop=threading.Event()
        def keepalive():
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
            while not stop.wait(1200):
                try:
                    headers={'ngrok-skip-browser-warning':'1'}
                    if os.environ.get('QWEN_API_KEY'):headers['Authorization']='Bearer '+os.environ['QWEN_API_KEY']
                    req=urllib.request.Request(os.environ['QWEN_BASE_URL'].rstrip('/')+'/models',headers=headers)
                    with opener.open(req,timeout=8) as r:r.read(100000)
                except Exception:pass
        threading.Thread(target=keepalive,daemon=True).start()
        status=dict(version=a.version,state='running',started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    workers=a.workers,source_protocol_verified=True,endpoint_persisted=False)
        save(directory/'status.json',status)
        try:
            with (directory/'pipeline.log').open('a') as log:
                p=subprocess.Popen([config['V4_PYTHON'],'-B','-m',experiment.__name__,'all','--online','--workers',str(a.workers)],
                    cwd=REPO,env=dict(os.environ,PYTHONPATH=str(REPO),PYTHONDONTWRITEBYTECODE='1'),
                    stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
                (directory/'pipeline.pid').write_text(str(p.pid)+'\n');status['pipeline_pid']=p.pid;save(directory/'status.json',status)
                result=p.wait()
            gate_path=root/'concept_gate.json';gate=json.loads(gate_path.read_text()) if gate_path.exists() else None
            status.update(exit_code=result,finished_at=dt.datetime.now(dt.timezone.utc).isoformat())
            if gate:status['gate']={k:gate[k] for k in ('tasks','qualified','required','passed')}
            if result:status['state']='error_resume_from_exact_caches'
            elif gate and not gate['passed']:status['state']='concept_gate_failed_generation_stopped'
            elif (root/'report.json').exists():status['state']='scored_complete'
            else:status['state']='stopped_without_score'
        finally:stop.set();save(directory/'status.json',status)
        if a.notify_thread:
            prompt=('Authorized '+a.version+' run finished/stopped. Read '+str(directory/'status.json')+
                    ' and outputs under '+str(root)+'. Report actual gates, accepted concepts, request/token costs and scores. '
                    'If gate failed, stop generation; do not relax or edit frozen treatment. If incomplete score or transport '
                    'error, resume only unchanged missing work from exact caches. Never claim D_IO before scored. '
                    'Audit candidate-property false alarms separately from D_IO. Update own reports/memory; preserve other sessions.')
            q=subprocess.run(['/usr/bin/codex','queue','--thread',a.notify_thread,'--message',prompt,'-C',str(REPO)],
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
            save(directory/'notification.json',dict(queued=q.returncode==0))
if __name__=='__main__':main()
