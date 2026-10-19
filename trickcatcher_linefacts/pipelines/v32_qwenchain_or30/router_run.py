"""Frozen 30-dev feasibility run, native feedback then post-generation canonical scoring."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from . import paths,schemas,chain_prompts,prompt_aliases,source_view
from .chain import OfflineChain,sha
from .router_transport import Router,StopRun
from .llm_client import atomic_json
from .v4_runtime import immutable
from .chain_inputs import parse_literal,typed_value
HERE=Path(__file__).resolve().parent;ROOT=paths.DATA_OUT/'dev30';LOG=paths.REPO/'trickcatcher_linefacts/out/runlogs_v32_qwenchain_or30'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze():
    immutable(ROOT/'protocol.json',{p.name:digest(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.json','.md','.jinja')})

def stage(chain,name,client):
    status=chain.status(name)
    if status in ('valid','failed'):return chain.data['stages'][name]
    if status!='ready':return dict(state=status)
    artifacts={s:r['artifact'] for s,r in chain.data['stages'].items() if r['state']=='valid'}
    messages=chain_prompts.messages(name,chain.task,artifacts,chain.data['feedback'] if name=='S5' else [])
    seed=paths.CONFIG['chain']['seed']+int(chain.task['task_hash'][:8],16)%1000000+int(name[1])
    try:response=client.complete(name,messages,seed)
    except ValueError as exc:
        record=dict(state='failed',reason=str(exc));chain.data['stages'][name]=record;chain.save();return record
    record=dict(state='failed',origin='openrouter',raw=response['text'],finish_reason=response['finish_reason'],cost_usd=response['cost_usd'],parents={s:sha(a) for s,a in artifacts.items()},model=response['model'])
    try:
        obj,_=schemas.extract(response['text'],response['finish_reason']);_,back=prompt_aliases.maps(chain.task,{} if name in ('S1','S2') else artifacts)
        record['parsed_alias_response']=copy.deepcopy(obj);expanded=prompt_aliases.expand(name,obj,back)
        schemas.validate(name,expanded,chain.task,chain.data['registry'],chain.selected(),[x['id'] for x in chain.data['feedback']])
        registry=copy.deepcopy(chain.data['registry']);record.update(state='valid',artifact=schemas.register(name,expanded,chain.task['task_hash'],registry));chain.data['registry']=registry
    except (ValueError,KeyError,TypeError) as exc:record['reason']=str(exc)
    chain.data['stages'][name]=record;chain.save();return record

def report():
    ledger=json.loads((ROOT/'transport/ledger.json').read_text()) if (ROOT/'transport/ledger.json').exists() else {};counts={s:Counter() for s in schemas.STAGES};errors=Counter();rows=[]
    for item in json.loads((HERE/'prepared.json').read_text()):
        path=ROOT/'cases'/str(item['task_id']);chain=OfflineChain(item['task'],path)
        for s in schemas.STAGES:
            status=chain.status(s);counts[s][status]+=1
            if status=='failed':errors[s,chain.data['stages'][s].get('reason','unknown')]+=1
        rows.append(dict(task_id=item['task_id'],**chain.report()))
    output=dict(tasks=30,stage_counts={s:dict(c) for s,c in counts.items()},errors=[dict(stage=s,error=e,count=n) for (s,e),n in errors.items()],rows=rows,calls=len(ledger),received=sum(x['status']=='received' for x in ledger.values()),unknown=sum(x['status']!='received' for x in ledger.values()),input_tokens=sum(x.get('input_tokens',0) for x in ledger.values()),output_tokens=sum(x.get('output_tokens',0) for x in ledger.values()),cost_usd=sum(x.get('cost_usd',0) for x in ledger.values()),reserved_unknown_usd=sum(x['reserved_usd'] for x in ledger.values() if x['status']!='received'),D_IO=None)
    atomic_json(ROOT/'report.json',output);return output

def score():
    from .execution_adapter import execute
    snapshot=json.loads((ROOT/'generation_frozen.json').read_text());assert all(digest(ROOT/p)==h for p,h in snapshot.items())
    refs={int(x['task_id'].split('/')[1]):x for x in map(json.loads,paths.dataset_paths()['oracle_hep'].read_text().splitlines())};rows=[]
    for item in json.loads((HERE/'prepared.json').read_text()):
        ident=item['task_id'];directory=ROOT/'cases'/str(ident);state=json.loads((directory/'state.json').read_text());r=refs[ident]
        canonical=source_view.prepare(r['prompt']+r['canonical_solution'],r['entry_point'],valid_code=item['task']['valid_code']);final=set()
        stage5=state['stages'].get('S5',{})
        if stage5.get('state')=='valid':
            from .chain_inputs import parse_arguments,literal_for_transport
            for p in stage5['artifact']['items']:
                try:final.add(literal_for_transport(parse_arguments(p['input_repr'],item['task']['arity'])))
                except ValueError:pass
        diffs=[];unresolved=0;decisive=0
        for v in state['inputs'].values():
            actual=v.get('result') or {};reference=execute(canonical,v['input_repr'],[],ROOT/'scoring'/str(ident));different=False
            if not actual.get('native_checked') or reference.get('status')!='ok' or not reference.get('native_checked'):unresolved+=1;continue
            try:
                if actual['status']=='exception':different=True
                elif actual['status']=='ok':different=typed_value(parse_literal(actual['output_repr'],output=True))!=typed_value(parse_literal(reference['output_repr'],output=True))
                else:unresolved+=1;continue
            except (ValueError,KeyError):unresolved+=1;continue
            decisive+=1
            if different:diffs.append(dict(input_repr=v['input_repr'],put=actual.get('output_repr'),put_status=actual.get('status'),put_exception=actual.get('exception_type'),canonical=reference.get('output_repr'),in_S5_final=v['input_repr'] in final))
        rows.append(dict(task_id=ident,inputs=len(state['inputs']),decisive=decisive,unresolved=unresolved,differences=diffs))
    result=dict(scope='post-generation canonical IO differences conditional on input admissibility; dev feasibility, no baseline comparison',tasks=30,any_stage_tasks=sum(bool(x['differences']) for x in rows),final_S5_tasks=sum(any(d['in_S5_final'] for d in x['differences']) for x in rows),rows=rows)
    atomic_json(ROOT/'io_score.json',result);return result

def main():
    LOG.mkdir(parents=True,exist_ok=True)
    with (LOG/'run.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);freeze();client=Router(ROOT/'transport');atomic_json(LOG/'status.json',dict(state='running',model=paths.CONFIG['chain']['model'],cap_usd=client.cap))
        def one(item):
            if client.stop.is_set():return
            try:
                chain=OfflineChain(item['task'],ROOT/'cases'/str(item['task_id']))
                for name in schemas.STAGES:
                    if client.stop.is_set():return
                    result=stage(chain,name,client)
                    if name in ('S4','S5') and result['state']=='valid':chain.execute_fixture_slots(name)
                    print(item['task_id'],name,result['state'],result.get('reason',''),flush=True)
            except BaseException:
                client.stop.set();raise
        try:
            with ThreadPoolExecutor(2) as pool:list(pool.map(one,json.loads((HERE/'prepared.json').read_text())))
            result=report()
            if client.stop.is_set():atomic_json(LOG/'status.json',dict(state='stopped_no_retry',report=result));return
            immutable(ROOT/'generation_frozen.json',{str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'cases').rglob('*.json')})
            atomic_json(LOG/'status.json',dict(state='generation_complete_scoring',cost_usd=result['cost_usd']));scored=score()
            atomic_json(LOG/'status.json',dict(state='complete',calls=result['calls'],cost_usd=result['cost_usd'],io_summary={k:v for k,v in scored.items() if k!='rows'}))
        except BaseException as exc:
            client.stop.set();atomic_json(LOG/'status.json',dict(state='incomplete_no_auto_retry',error_type=type(exc).__name__,error=str(exc) if isinstance(exc,StopRun) else None,report=report()))
        finally:
            client.http.close()
            try:subprocess.run(['/usr/bin/codex','queue','--thread','01a1387b-2603-7221-8fd0-b314052b1085','--message','User-authorized v32_qwenchain_or30 OpenRouter30dev run finished/stopped. Read out/runlogs_v32_qwenchain_or30/status.json and out/pipelines/v32_qwenchain_or30/humaneval/dev30. Verify frozen protocol/generation, costs/unknowns and stage/schema/concept/input coverage; distinguish canonical any-stage vs final-S5 IO and admissibility caveats. Never read scripts/openrouter_env.sh; only source if unchanged missing scoring/work is necessary. Do not retry ambiguous paid attempts or auto-expand/spend. Preserve other sessions; update own results/memory.','-C',str(paths.REPO)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
            except Exception:pass

if __name__=='__main__':main()
