"""Detached user-authorized controlled16 contract/alignment-audit Qwen pilot; endpoint remains env-only."""
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v22_qwenchain_audit import pilot
from trickcatcher_linefacts.pipelines.v22_qwenchain_audit.online_transport import Connection
from trickcatcher_linefacts.pipelines.v22_qwenchain_audit.llm_client import atomic_json


def main():
    directory=REPO/'trickcatcher_linefacts/out/runlogs_v22_qwenchain_audit';directory.mkdir(parents=True,exist_ok=True)
    with (directory/'controller.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('pilot already running')
        pilot.freeze();connection=Connection();stop=threading.Event()
        def keepalive():
            while not stop.wait(1200):
                try:connection.call('/models',timeout=8);ok=True
                except Exception:ok=False
                with (directory/'keepalive.jsonl').open('a') as f:f.write(json.dumps(dict(at=dt.datetime.now(dt.timezone.utc).isoformat(),ok=ok))+'\n')
        threading.Thread(target=keepalive,daemon=True).start()
        status=dict(version='v22_qwenchain_audit',scope='controlled16 only; no real20/D_IO',state='running',started_at=dt.datetime.now(dt.timezone.utc).isoformat(),controller_pid=os.getpid())
        atomic_json(directory/'status.json',status)
        try:
            child=subprocess.Popen([sys.executable,'-B','-m',pilot.__name__,'all','--workers','2'],cwd=REPO,env=dict(os.environ,PYTHONPATH=str(REPO),PYTHONDONTWRITEBYTECODE='1'),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            (directory/'pipeline.pid').write_text(str(child.pid)+'\n');status['pipeline_pid']=child.pid;atomic_json(directory/'status.json',status)
            with (directory/'pipeline.log').open('a') as log:
                for line in child.stdout:
                    line=connection.redact(line);line=re.sub(r'https://[a-z0-9.-]+ngrok[a-z.-]*','<redacted>',line)
                    log.write(line);log.flush()
            code=child.wait();status.update(exit_code=code,finished_at=dt.datetime.now(dt.timezone.utc).isoformat())
            if not code and (pilot.ROOT/'report.json').exists():
                result=json.loads((pilot.ROOT/'report.json').read_text());status.update(state='pilot_complete_semantic_review_pending',costs=result['costs'],mechanical_gates=result['mechanical_gates'])
            else:status['state']='incomplete_resume_unchanged'
        except BaseException as exc:status.update(state='controller_error',error_type=type(exc).__name__)
        finally:stop.set();atomic_json(directory/'status.json',status)
        prompt=('User-authorized v22_qwenchain_audit controlled16 run finished/stopped. Read '+str(directory/'status.json')+' and '+str(pilot.ROOT)+'. Verify frozen source/generation, report actual per-stage/interface failures and S3 comparison verdicts, especially prior f12 alignment miss and ambiguity handling; probe/input coverage, prediction checks and costs. Same16 adapted fixtures are diagnostic, not unseen validation. Read selected real Qwen artifacts to explain earliest errors; any model-assisted semantic labels remain provisional. No D_IO or automatic real20; human semantic gate remains pending. If incomplete transport, resume only unchanged missing work from exact caches, never reset attempts or accept quarantined protocol failures. Preserve frozen prompts/validators/budgets, no paid fallback. Update own reports/memory; preserve other sessions.')
        try:
            done=subprocess.run(['/usr/bin/codex','queue','--thread','01a1387b-2603-7221-8fd0-b314052b1085','--message',prompt,'-C',str(REPO)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=60)
            atomic_json(directory/'notification.json',dict(queued=done.returncode==0))
        except Exception:atomic_json(directory/'notification.json',dict(queued=False))


if __name__=='__main__':main()
