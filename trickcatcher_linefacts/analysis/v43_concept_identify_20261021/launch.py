"""Detached owner launcher; quota-only continuation, no transport/content retries."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v43_concept_identify import identify as app


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wait_for_quota(state):
    while True:
        done=subprocess.run([sys.executable,str(app.QUOTA),'check'],capture_output=True,text=True,timeout=30,check=True)
        snapshot=app.strict_json(done.stdout)
        state['quota']=snapshot
        if not snapshot['should_stop']:
            return
        reset=snapshot.get('reset_unix')
        if type(reset) not in (int,float):
            raise RuntimeError('quota_reset_unknown')
        state.update(state='waiting_quota_reset',wake_unix=max(time.time()+60,reset+120))
        app.write_json(app.ROOT/'launch_state.json',state)
        while time.time()<state['wake_unix']:
            time.sleep(min(30,state['wake_unix']-time.time()))


def main():
    with (app.ROOT/'launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (app.ROOT/'launch_state.json').exists():
            raise SystemExit('launch_already_consumed_no_duplicate')
        registration=app.read(app.ROOT/'launch_registration.json')
        assert registration['launcher_sha256']==sha(__file__)
        state={'state':'checking','controller_pid':os.getpid(),'started_utc':datetime.now(timezone.utc).isoformat()}
        app.write_json(app.ROOT/'launch_state.json',state)
        try:
            while True:
                wait_for_quota(state);app.verify()
                approval=app.read(app.ROOT/'approval.json')
                assert approval['launcher_sha256']==sha(__file__)
                assert approval['readiness_script_sha256']==sha(HERE/'readiness2.py')
                ready=app.read(app.ROOT/'readiness2/status.json')
                assert ready['state']=='ready' and ready['script_sha256']==approval['readiness_script_sha256']
                assert sha(app.ROOT/'readiness2/status.json')==approval['readiness_result_sha256']
                state.update(state='launching',launched_utc=datetime.now(timezone.utc).isoformat())
                app.write_json(app.ROOT/'launch_state.json',state)
                previous_status_sha=sha(app.ROOT/'status.json') if (app.ROOT/'status.json').exists() else None
                done=subprocess.run([sys.executable,'-B','-m','trickcatcher_linefacts.pipelines.v43_concept_identify.identify','run'],
                                    cwd=REPO,stdin=subprocess.DEVNULL)
                state.update(state='controller_exited',returncode=done.returncode,
                             diagnostic_status=app.read(app.ROOT/'status.json') if (app.ROOT/'status.json').exists() else None)
                fresh_status=(app.ROOT/'status.json').exists() and sha(app.ROOT/'status.json')!=previous_status_sha
                state['child_status_fresh']=fresh_status
                if (done.returncode==0 and fresh_status and state['diagnostic_status']
                        and state['diagnostic_status'].get('state')=='stopped'
                        and state['diagnostic_status'].get('reason')=='quota_at_or_below15'):
                    continue
                break
            app.verify()
        except Exception as exc:
            state.update(state='launcher_stopped',error_type=type(exc).__name__)
        state['ended_utc']=datetime.now(timezone.utc).isoformat()
        app.write_json(app.ROOT/'launch_state.json',state)
        app.immutable(app.ROOT/'terminal_inventory.json',{
            str(p.relative_to(app.ROOT)):sha(p) for p in app.ROOT.rglob('*') if p.is_file()})
        print(json.dumps(state),flush=True)
        message=(
            'Owned user-authorized v43 concept-identification diagnostic finished/stopped. '
            'Read status, launch_state, freeze, approval and allartifacts under '
            '/home/phong/dev/ConceptTester/trickcatcher_linefacts/out/pipelines/v43_concept_identify/humaneval/binding8 '
            'and analysis/v43_concept_identify_20261021, pipelinePREREG. CheckCodex5hquota>15; stop<=15. '
            'No duplicate/retry/reset/repair/newcalls. Verify frozen60source/eightpools/deps, parentv40inventories '
            'and newterminal/generation inventories. Ifcomplete independently review actualALL8initialbindings '
            'and16pairedraw/toolfinals includinginvalid/blocked/unknowns, specquote/argument/labelquality, '
            'toolrequests/actualfeedback, relationtruthvsnormativecorrectness, correctE7/ambiguousE8, '
            'sameevidenceparity and prereg>=2tool-onlywins/0oppositelosses. Use clean-contextreviewer. '
            'Saved-data analysis only, no model-authoredexpected/assertion/discoveryclaim. Reused78saved '
            'observations are biasedpriorQwen/sharedpool, no newPUTworkers. ReportactualQwenusage/calls/unknowns '
            'andBOTHreadinessmetadata stages including failedsyntheticreadiness1 and READINESS_AMENDMENT.md separately; originalv40unknown stayshistorical separate. Ifincomplete report '
            'exactterminalcause/all24slotstatuses withoutrepair. UpdateownRESULTS/analysis/memory andcommitpush '
            'ownmain; preserveothersessions/endpointsecrecy. Vietnamese reply. Callbackalreadyhandled means '
            'reverifyonly, neverrelaunch.')
        done=subprocess.run(['codex','queue','--thread',registration['thread_id'],'--message',message],
                            cwd=REPO,capture_output=True,text=True,timeout=30)
        app.write_json(HERE/'callback.json',{'method':'codex_queue','returncode':done.returncode})


if __name__=='__main__':
    main()
