from datetime import datetime,timezone
import json,subprocess,time,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PATH=HERE/'resume_schedule.json'
state=json.loads(PATH.read_text())
while True:
    while time.time()<state['wake_unix']:
        time.sleep(min(30,state['wake_unix']-time.time()))
    guard=REPO/'trickcatcher_linefacts/analysis/astra_concept_design_20261020/quota_guard.py'
    checked=subprocess.run([sys.executable,str(guard),'check'],capture_output=True,text=True,timeout=30)
    if checked.returncode:
        state.update(state='quota_check_failed_no_continuation');break
    quota=json.loads(checked.stdout);state['wake_quota']=quota
    if quota['should_stop']:
        state.update(state='waiting_next_quota_reset',wake_unix=max(time.time()+120,quota.get('reset_unix') or time.time())+120)
        PATH.write_text(json.dumps(state,indent=2)+'\n');continue
    prompt=('Resume explicitly user-authorized v43 concept-identification tools implementation then Qwen run in /home/phong/dev/ConceptTester. Read AGENTS.md/memory and analysis/v43_concept_identify_20261021/CHECKPOINT.md,CODE_REVIEW.md, pipelines/v43_concept_identify/PREREG.md. Quota stopped at15%; fresh check must be>15. No Qwen/PUTcalls or diagnosticoutcomes have occurred. Finish mustfixes/CPUtests/independentcleancontext re-review BEFORE prepare/outcomes, freeze source/pools/deps/approval. Then user-authorized diagnostic8seen,8initial+16pairedfinal=max24singleattemptQwen32B calls, existing endpoint onlyfromconversation/env; no paidfallback, benchmark/training, parentedits or unknownattemptreset. Build detached guardedlauncher/callback with correctnewroot, record blockedslots/raworigins/allcosts; postfreezesemanticreview with independent reviewer, updateownRESULTS/analysis/memory andcommitpushownmain. Preserve other sessions and endpoint secrecy. This is continuation of same explicituser task, not newexperiment expansion.')
    done=subprocess.run(['codex','queue','--thread',state['thread_id'],'--message',prompt],cwd=REPO,capture_output=True,text=True,timeout=30)
    state.update(state='continuation_queued' if done.returncode==0 else 'queue_failed',queue_returncode=done.returncode);break
PATH.write_text(json.dumps(state,indent=2)+'\n')
