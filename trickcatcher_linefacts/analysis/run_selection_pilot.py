"""Detached frozen v18 selection pilot, without generation, MCTS or persisted endpoints."""
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
from trickcatcher_linefacts.pipelines.v18_modelselect import selection_experiment as experiment,paths
from trickcatcher_linefacts.pipelines.v18_modelselect.llm_client import Client,NoRedirect,atomic_json


def main():
    directory=REPO/'trickcatcher_linefacts/out/runlogs_v18_modelselect';directory.mkdir(parents=True,exist_ok=True)
    with (directory/'controller.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Selection pilot already running')
        experiment.foundation.verify()
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
        status=dict(version='v18_modelselect',scope='selection-only; no generation or D_IO',state='running',started_at=dt.datetime.now(dt.timezone.utc).isoformat())
        atomic_json(directory/'status.json',status)
        try:
            with (directory/'pipeline.log').open('a') as log:
                p=subprocess.Popen([paths.CONFIG['V4_PYTHON'],'-B','-m',experiment.__name__,'all','--online','--workers','2'],cwd=REPO,
                    env=dict(os.environ,PYTHONPATH=str(REPO),PYTHONDONTWRITEBYTECODE='1'),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                (directory/'pipeline.pid').write_text(str(p.pid)+'\n');status['pipeline_pid']=p.pid;atomic_json(directory/'status.json',status)
                code=p.wait()
            gate=json.loads((experiment.ROOT/'candidate_gate.json').read_text())
            status.update(exit_code=code,finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),candidate_tasks=gate['candidate_tasks'])
            status['state']='audit_complete' if (experiment.ROOT/'report.json').exists() and not code else 'error_resume_unchanged' if code else 'candidate_gate_failed'
        finally:stop.set();atomic_json(directory/'status.json',status)
        prompt=('Authorized v18_modelselect SELECTION-ONLY pilot finished/stopped. Read '+str(directory/'status.json')+
                ' and outputs '+str(experiment.ROOT)+'. Report candidate-pool vs menu coverage, LLM vs rule-first/uniform selection, '
                'partial-scope/unknown rates, candidate discrepancy confirmation and costs. No D_IO or generation was run. '
                'Verify frozen snapshot; resume only unchanged missing work if necessary. Update own reports/memory; preserve other sessions.')
        q=subprocess.run(['/usr/bin/codex','queue','--thread','01a1387b-2603-7221-8fd0-b314052b1085','--message',prompt,'-C',str(REPO)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
        atomic_json(directory/'notification.json',dict(queued=q.returncode==0))
if __name__=='__main__':main()
