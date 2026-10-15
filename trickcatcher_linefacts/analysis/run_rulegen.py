"""Detached v19 generation comparison with metadata keepalive; no persisted endpoint."""
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import urllib.request
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v19_rulegen import behavior_experiment as experiment,paths
from trickcatcher_linefacts.pipelines.v19_rulegen.llm_client import Client,NoRedirect,atomic_json


def main():
    directory=REPO/'trickcatcher_linefacts/out/runlogs_v19_rulegen';directory.mkdir(parents=True,exist_ok=True)
    with (directory/'controller.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Generation comparison already running')
        experiment.verify()
        Client(experiment.ROOT/'model_cache',offline=False,workers=2)
        stop=threading.Event()
        def keepalive():
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
            while not stop.wait(1200):
                try:
                    headers={'ngrok-skip-browser-warning':'1'}
                    if os.environ.get('QWEN_API_KEY'):headers['Authorization']='Bearer '+os.environ['QWEN_API_KEY']
                    with opener.open(urllib.request.Request(os.environ['QWEN_BASE_URL'].rstrip('/')+'/models',headers=headers),timeout=8) as r:r.read(100000)
                except Exception:pass
        threading.Thread(target=keepalive,daemon=True).start()
        status=dict(version='v19_rulegen',scope='20 dev, K=1, rule-first generation comparison',state='running',started_at=dt.datetime.now(dt.timezone.utc).isoformat())
        atomic_json(directory/'status.json',status)
        try:
            with (directory/'pipeline.log').open('a') as log:
                p=subprocess.Popen([paths.CONFIG['V4_PYTHON'],'-B','-m',experiment.__name__,'all','--online','--workers','2'],cwd=REPO,
                    env=dict(os.environ,PYTHONPATH=str(REPO),PYTHONDONTWRITEBYTECODE='1'),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                (directory/'pipeline.pid').write_text(str(p.pid)+'\n');status['pipeline_pid']=p.pid;atomic_json(directory/'status.json',status)
                code=p.wait()
            gate=json.loads((experiment.ROOT/'concept_gate.json').read_text())
            status.update(exit_code=code,finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),candidate_tasks=gate['qualified'])
            status['state']='scored_complete' if (experiment.ROOT/'report.json').exists() and not code else 'error_resume_unchanged' if code else 'candidate_gate_failed'
        finally:stop.set();atomic_json(directory/'status.json',status)
        prompt=('Authorized v19_rulegen generation comparison finished/stopped. Read '+str(directory/'status.json')+
                ' and outputs '+str(experiment.ROOT)+'. Verify frozen protocol/generation. Report rule-first concept coverage, '
                'behavior+concept vs behavior and plain/placebo/toolinput/witness-only D_IO task detection, equal-input comparisons, '
                'candidate-property false alarms and costs. If scoring/transport incomplete, resume only unchanged missing work from exact caches. '
                'If gate failed stop generation. Never claim D_IO before scored. Update own reports/memory; preserve other sessions.')
        q=subprocess.run(['/usr/bin/codex','queue','--thread','01a1387b-2603-7221-8fd0-b314052b1085','--message',prompt,'-C',str(REPO)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
        atomic_json(directory/'notification.json',dict(queued=q.returncode==0))
if __name__=='__main__':main()
