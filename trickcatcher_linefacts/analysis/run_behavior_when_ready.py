"""Wait for the user's existing Qwen environment, then run a frozen behavior experiment.

Endpoint/key are inherited environment values only. Never log or persist them.
This wrapper changes scheduling only, not pipeline prompts, validators or budgets.
"""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.error
import urllib.request

REPO=Path(__file__).resolve().parents[2]
VERSION='v16_behavior_ready'
MODULE='trickcatcher_linefacts.pipelines.'+VERSION+'.behavior_experiment'
HERE=REPO/'trickcatcher_linefacts/pipelines'/VERSION
RUN=HERE/'out/humaneval/behavior_smoke'
MODEL='qwen2.5-coder-7b-instruct'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def available():
    base=os.environ.get('QWEN_BASE_URL','').rstrip('/')
    if not base:return False,'endpoint_env_missing'
    # Reuse the actual pipeline host/model policy without requesting a completion.
    from trickcatcher_linefacts.pipelines.v16_behavior_ready.llm_client import Client
    try:Client(RUN/'model_cache',offline=False,workers=2)
    except (ValueError,TypeError):return False,'endpoint_policy_rejected'
    headers={'ngrok-skip-browser-warning':'1'}
    token=os.environ.get('QWEN_API_KEY')
    if token:headers['Authorization']='Bearer '+token
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    try:
        with opener.open(urllib.request.Request(base+'/models',headers=headers),timeout=8) as response:
            data=json.load(response)
        live=any(row.get('id')==MODEL for row in data.get('data',[]) if isinstance(row,dict))
        return live,'model_ready' if live else 'pinned_model_missing'
    except urllib.error.HTTPError as exc:return False,'HTTP_'+str(exc.code)
    except Exception as exc:return False,type(exc).__name__

def save(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def notify(thread_id,directory):
    if not thread_id:return
    prompt=('User-authorized v16 GPU waiter finished or stopped. Read '+str(directory/'status.json')+
            ' and the frozen pipeline outputs under '+str(RUN)+
            '. Summarize the actual proposal gate, costs and results. If scoring is incomplete, '
            'resume only missing unchanged work; do not alter frozen prompts/validators/budgets. '
            'If concept gate failed, report rejections and stop generation. '
            'Update own results/memory; preserve other sessions. Never claim D_IO before scored.')
    result=subprocess.run(['/usr/bin/codex','queue','--thread',thread_id,'--message',prompt,'-C',str(REPO)],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
    save(directory/'notification.json',dict(queued=result.returncode==0,exit_code=result.returncode))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--not-before',required=True,help='timezone-aware ISO timestamp')
    ap.add_argument('--max-wait-minutes',type=int,default=40)
    ap.add_argument('--poll-seconds',type=int,default=60)
    ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--notify-thread')
    ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args();first=dt.datetime.fromisoformat(a.not_before)
    if first.tzinfo is None or a.poll_seconds<30 or a.max_wait_minutes<1:ap.error('invalid wait bounds')
    directory=a.directory.resolve();directory.mkdir(parents=True,exist_ok=True)
    with (directory/'waiter.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Waiter already running')
        # Exact frozen source/config/task match must pass before any possible model request.
        from trickcatcher_linefacts.pipelines.v16_behavior_ready import behavior_experiment as experiment
        experiment.verify()
        if not json.loads((RUN/'representation_gate.json').read_text())['passed']:
            raise SystemExit('Representation gate is not passed')
        config=json.loads((HERE/'config.json').read_text())
        if config['model']!=MODEL:raise SystemExit('Pinned model mismatch')
        python=config['V4_PYTHON']
        plan=dict(version=VERSION,not_before=first.isoformat(),max_wait_minutes=a.max_wait_minutes,
                  poll_seconds=a.poll_seconds,workers=2,max_logical_requests=400,
                  first_stage='two proposals/task then concept gate',
                  generation_condition='>=10/20 qualified concept tasks; otherwise stop',
                  endpoint_persisted=False,model=MODEL)
        save(directory/'plan.json',plan)
        if a.dry_run:print(json.dumps(plan));return
        status=dict(state='waiting_for_start',**plan);save(directory/'status.json',status)
        while time.time()<first.timestamp():time.sleep(min(30,first.timestamp()-time.time()))
        deadline=time.monotonic()+a.max_wait_minutes*60
        while time.monotonic()<deadline:
            live,reason=available();status.update(state='waiting_for_gpu',last_check=dt.datetime.now(dt.timezone.utc).isoformat(),check=reason)
            save(directory/'status.json',status)
            if live:break
            time.sleep(a.poll_seconds)
        else:
            status['state']='readiness_timeout';save(directory/'status.json',status)
            notify(a.notify_thread,directory);return
        stop=threading.Event()
        def keepalive():
            while not stop.wait(1200):available()
        keep=threading.Thread(target=keepalive,daemon=True);keep.start()
        status.update(state='running_frozen_pipeline',started_at=dt.datetime.now(dt.timezone.utc).isoformat())
        save(directory/'status.json',status)
        try:
            env=dict(os.environ,PYTHONPATH=str(REPO),PYTHONDONTWRITEBYTECODE='1')
            with (directory/'pipeline.log').open('a',buffering=1) as log:
                result=subprocess.run([python,'-B','-m',MODULE,'all','--online','--workers','2'],
                                      cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT)
            status.update(exit_code=result.returncode,finished_at=dt.datetime.now(dt.timezone.utc).isoformat())
            gate_path=RUN/'concept_gate.json'
            if result.returncode:status['state']='pipeline_error_resume_from_cache'
            elif gate_path.exists() and not json.loads(gate_path.read_text())['passed']:status['state']='concept_gate_failed_generation_stopped'
            elif (RUN/'report.json').exists():status['state']='scored_complete'
            else:status['state']='stopped_without_score'
        finally:
            stop.set();save(directory/'status.json',status)
        notify(a.notify_thread,directory)
if __name__=='__main__':main()
