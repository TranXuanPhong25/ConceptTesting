"""Wait for owned original worker, restore exact-cache arm slots, grade once."""
import hashlib,json,os,time
from pathlib import Path
from ..client import atomic,digest
from ..run import tasks,HERE as ROOT
from ..prompts import utility
from ..grade_utility import grade
from .render import render
HERE=Path(__file__).resolve().parent
OUT=ROOT/'out/run_20261026'

def fill_from_cache():
    lookup={}
    for p in (OUT/'calls').glob('*/request.json'):
        request=json.loads(p.read_text())
        if request['stage']!='utility':continue
        body=request['body']
        assert digest({'stage':'utility','request':body}) == p.parent.name
        assert body['model']=='qwen3.5-27b-awq' and body['max_tokens']==800
        assert body['temperature']==0.1 and body['top_p']==0.95
        assert body['chat_template_kwargs']=={'enable_thinking':False}
        assert body['response_format']=={'type':'json_object'} and body['stream'] is False
        key=digest({'messages':body['messages'],'seed':body['seed']})
        terminal=p.with_name('response.json')
        if terminal.exists():
            response=json.loads(terminal.read_text())
            assert response['request_sha256']==p.parent.name
            lookup[key]=response
    cohort=set(json.loads((ROOT/'data/utility_cohort.json').read_text())['tasks'])
    restored=[];missing=[]
    for task in tasks():
        tid=task['task_id']
        if tid not in cohort:continue
        stem=tid.replace('/','_')
        original=json.loads((OUT/'retrieved'/f'{stem}.json').read_text())
        for arm,hints in [('plain',[]),('v2',original['baseline']),('v3',original['selected'])]:
            path=OUT/'utility'/f'{stem}__{arm}.json'
            if path.exists():continue
            key=digest({'messages':utility(task,hints),'seed':314300+int(tid.split('/')[1])})
            response=lookup.get(key)
            if response is None:
                missing.append({'task_id':tid,'arm':arm});continue
            atomic(path,{'task_id':tid,'split':task['split'],'arm':arm,'response':response,'restored_from_exact_terminal_cache':True})
            restored.append({'task_id':tid,'arm':arm,'request_sha256':response['request_sha256']})
    result={'restored':restored,'missing':missing,'new_inference_attempts':0,'unique_utility_requests':len(lookup),'planned_arm_slots':120}
    atomic(HERE/'CACHE_RESTORATION.json',result)
    return result

def main():
    if (HERE/'FINALIZED.json').exists():
        return
    pid=int((HERE/'OWNER.pid').read_text())
    # A /proc check handles zombies as terminal. The task process cannot restart.
    while True:
        try:
            stat=Path(f'/proc/{pid}/stat').read_text().split()
            if stat[2]=='Z':break
        except FileNotFoundError:break
        time.sleep(10)
    restored=fill_from_cache()
    grade(OUT)
    summary=render()
    atomic(HERE/'FINALIZED.json',{'finished':time.time(),'utility_completeness':summary['utility_completeness'],'cache_restoration':restored})
    print(json.dumps(summary['utility_completeness']),flush=True)

if __name__=='__main__':main()
