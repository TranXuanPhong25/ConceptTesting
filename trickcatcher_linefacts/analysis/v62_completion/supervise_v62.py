"""Detached bounded continuation for an already authorized, reviewed v62 pilot.

Uses inherited private endpoint environment. Never prints endpoint/credential values.
Waits for the exact recorded process, resumes only transport failures under the
per-slot attempt cap, and invokes the independent scorer only after full freeze.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def process_identity(pid,out,requests):
    try:
        cmd=[x.decode()for x in Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')if x]
        if 'trickcatcher_linefacts.pipelines.v62_pathfault_contractfix.pipeline'not in cmd:return None
        cwd=Path(f'/proc/{pid}/cwd').resolve()
        resolve=lambda flag:(cwd/cmd[cmd.index(flag)+1]).resolve()
        if resolve('--out')!=out.resolve()or resolve('--requests')!=requests.resolve():return None
        start=Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split()[19]
        return {'pid':pid,'starttime':start,'out':str(out.resolve()),'requests':str(requests.resolve())}
    except (OSError,ValueError,IndexError):return None


def status(out,value):
    # Monitoring status is intentionally mutable; scientific artifacts are immutable.
    (out.parent/'monitor_v2'/'status.json').write_text(json.dumps(value,sort_keys=True)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--generation',type=Path,required=True);p.add_argument('--requests',type=Path,required=True)
    p.add_argument('--approval',type=Path,required=True);p.add_argument('--score-out',type=Path,required=True)
    a=p.parse_args();out=a.generation
    import fcntl
    monitor=out.parent/'monitor_v2';monitor.mkdir(exist_ok=True)
    lock=(monitor/'.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    pid=int((out/'runner.pid').read_text());restarts=0;deadline=time.monotonic()+24*3600;log_offset=0
    expected=process_identity(pid,out,a.requests)
    (monitor/'process_identity.json').write_text(json.dumps(expected)+'\n')
    while time.monotonic()<deadline:
        actual=process_identity(pid,out,a.requests)
        if actual is not None and expected is not None and actual==expected:
            status(out,{'state':'generation_active','pid':pid,'restarts':restarts});time.sleep(30);continue
        if (out/'generation_frozen.json').exists():
            status(out,{'state':'generation_frozen_scoring','restarts':restarts})
            if (a.score_out/'score.json').exists():
                status(out,{'state':'complete_existing_score','score_out':str(a.score_out)});return
            scorer=Path(__file__).with_name('score_frozen.py')
            with (monitor/'scoring.log').open('a')as log:
                code=subprocess.call([sys.executable,str(scorer),'--integrated-v62','--generation',str(out),
                                      '--requests',str(a.requests),'--out',str(a.score_out)],stdout=log,stderr=subprocess.STDOUT)
            status(out,{'state':'complete'if code==0 else 'scoring_failed','exit_code':code,'score_out':str(a.score_out)});return
        tail=(out/'run.log').read_bytes()[log_offset:].decode(errors='replace')[-6000:]
        terminal=next((line.strip()for line in reversed(tail.splitlines())if line.strip()),'')
        fatal=('transport_attempt_budget_exhausted','protocol_drift','integrity','schema','cohort','readiness','checkpoint')
        if any(word in terminal for word in fatal):
            status(out,{'state':'stopped_attempt_budget','restarts':restarts});return
        transient=any(terminal.endswith('EndpointError: '+reason)for reason in
                      ('endpoint_connection_failed','http_status:500','http_status:502','http_status:503','http_status:504'))
        if not transient or restarts>=12:
            status(out,{'state':'stopped_requires_review','restarts':restarts});return
        time.sleep(30);restarts+=1
        log_offset=(out/'run.log').stat().st_size
        with (out/'run.log').open('a')as log:
            child=subprocess.Popen([sys.executable,'-B','-m','trickcatcher_linefacts.pipelines.v62_pathfault_contractfix.pipeline',
                                    '--online','--requests',str(a.requests),'--out',str(out),'--approval',str(a.approval)],
                                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        pid=child.pid;(out/'runner.pid').write_text(str(pid)+'\n')
        # Exec of module can lag process creation briefly; do not monitor an unrelated PID.
        expected=None
        for _ in range(20):
            expected=process_identity(pid,out,a.requests)
            if expected is not None or child.poll()is not None:break
            time.sleep(.1)
        (monitor/'process_identity.json').write_text(json.dumps(expected)+'\n')
    status(out,{'state':'monitor_deadline','restarts':restarts})


if __name__=='__main__':main()
