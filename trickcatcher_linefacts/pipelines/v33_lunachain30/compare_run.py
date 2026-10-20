"""Paired fixed-dev30 chain/direct experiment. No oracle read before generation freeze."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import copy,fcntl,hashlib,json,random,subprocess,threading
from pathlib import Path
from . import paths,schemas,prompt_aliases,source_view
from .chain import OfflineChain,sha
from .chain_inputs import parse_arguments,literal_for_transport,parse_literal,typed_value
from .execution_adapter import execute
from .llm_client import atomic_json
from .v4_runtime import immutable
from . import compare_interface as interface
from .luna_client import Client,costs
HERE=Path(__file__).resolve().parent;ROOT=paths.DATA_OUT/'comparison';LOG=paths.REPO/'trickcatcher_linefacts/out/runlogs_v33_lunachain30';C=paths.CONFIG['comparison']
class Incomplete(RuntimeError):pass

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze():immutable(ROOT/'protocol.json',{p.name:digest(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.json','.md','.jinja')})
def canon(value,task):return literal_for_transport(parse_arguments(value,task['arity']))

def retained(requests,inputs,task):
    rows=[]
    for value in requests:
        try:
            literal=canon(value,task)
            if literal not in {x['input_repr'] for x in inputs.values()}:raise ValueError('never_proposed')
            rows.append(dict(input_repr=literal,status='accepted'))
        except (ValueError,TypeError) as exc:rows.append(dict(input_repr=value,status='rejected',reason=str(exc)))
    return rows

def chain_stage(chain,name,client,ident):
    ready=chain.status(name)
    if ready in ('valid','failed'):return chain.data['stages'][name]
    if ready!='ready':return dict(state=ready)
    artifacts={s:r['artifact'] for s,r in chain.data['stages'].items() if r['state']=='valid'}
    messages=interface.messages(name,chain.task,artifacts,chain.data['feedback'] if name=='S5' else [])
    response=client.complete(dict(slot=f'{ident}_chain_{name}',messages=messages))
    row=dict(state='failed',raw=response['text'],origin=response['origin'],parents={s:sha(a) for s,a in artifacts.items()})
    try:
        raw,_=schemas.extract(response['text']);compiled=interface.compile_output(name,raw,artifacts)
        _,back=prompt_aliases.maps(chain.task,{} if name in ('S1','S2') else artifacts);expanded=prompt_aliases.expand(name,compiled,back)
        schemas.validate(name,expanded,chain.task,chain.data['registry'],chain.selected(),[r['id'] for r in chain.data['feedback']])
        registry=copy.deepcopy(chain.data['registry']);artifact=schemas.register(name,expanded,chain.task['task_hash'],registry)
        row.update(state='valid',raw_interface=raw,compiled=compiled,artifact=artifact);chain.data['registry']=registry
    except (ValueError,KeyError,TypeError) as exc:row['reason']=str(exc)
    chain.data['stages'][name]=row;chain.save();return row

def run_chain(item,client,stop):
    ident=item['task_id'];chain=OfflineChain(item['task'],ROOT/'cases'/str(ident)/'chain')
    for stage in schemas.STAGES:
        if stop.is_set():return
        row=chain_stage(chain,stage,client,ident)
        if row['state']=='valid' and stage in ('S4','S5'):chain.execute_fixture_slots(stage)
        if stage=='S5' and row['state']=='valid':
            chain.data['final_retention']=retained(row['raw_interface']['retain'],chain.data['inputs'],chain.task);chain.save()
        print(ident,'chain',stage,row['state'],row.get('reason',''),flush=True)

def direct_inputs(task,values,inputs,cache):
    rows=[]
    for value in values:
        row=dict(input_repr=value)
        try:
            literal=canon(value,task);key=sha(dict(source_hash=task['source_hash'],input_repr=literal))
            if key not in inputs:
                if len(inputs)>=12:raise ValueError('input_budget')
                result=execute(task,literal,[],cache);inputs[key]=dict(input_repr=literal,result=result)
            row.update(input_repr=literal,status=inputs[key]['result']['status'],execution={k:v for k,v in inputs[key]['result'].items() if k!='observations'})
        except (ValueError,TypeError,RecursionError) as exc:row.update(status='rejected',reason=str(exc))
        rows.append(row)
    return rows

def run_direct(item,client,stop):
    ident=item['task_id'];directory=ROOT/'cases'/str(ident)/'direct';directory.mkdir(parents=True,exist_ok=True);path=directory/'state.json'
    state=json.loads(path.read_text()) if path.exists() else dict(task_hash=item['task']['task_hash'],stages={},inputs={},feedback=[])
    immutable(directory/'context.json',dict(task=item['task'],comparison=C))
    for i,cap in enumerate(C['direct_new_input_slots'],1):
        if stop.is_set():return
        if str(i) in state['stages']:continue
        response=client.complete(dict(slot=f'{ident}_direct_{i}',messages=interface.direct_messages(item['task'],i,state['feedback'],cap)))
        record=dict(state='failed',raw=response['text'],origin=response['origin'])
        try:
            obj,_=schemas.extract(response['text'])
            if set(obj)!={'inputs','retain'} or type(obj['inputs']) is not list or len(obj['inputs'])>cap or not all(type(x) is str for x in obj['inputs']):raise ValueError('direct_inputs_schema_or_cap')
            if type(obj['retain']) is not list or len(obj['retain'])>12 or not all(type(x) is str for x in obj['retain']) or (i<5 and obj['retain']):raise ValueError('direct_retention_schema')
            rows=direct_inputs(item['task'],obj['inputs'],state['inputs'],directory/'native_executions');state['feedback'].extend(rows)
            record.update(state='valid',artifact=obj,attempts=rows)
            if i==5:state['final_retention']=retained(obj['retain'],state['inputs'],item['task'])
        except (ValueError,TypeError,KeyError) as exc:record['reason']=str(exc)
        state['stages'][str(i)]=record;atomic_json(path,state);print(ident,'direct',i,record['state'],record.get('reason',''),flush=True)

def report():
    summary={a:dict(stages={},tasks_with_inputs=0,inputs=0,final_tasks=0,selected_concept_tasks=0,errors=[]) for a in ('chain','direct')}
    for item in json.loads((HERE/'prepared.json').read_text()):
        for arm in summary:
            p=ROOT/'cases'/str(item['task_id'])/arm/'state.json'
            if not p.exists():continue
            state=json.loads(p.read_text());s=summary[arm];s['tasks_with_inputs']+=bool(state['inputs']);s['inputs']+=len(state['inputs']);s['final_tasks']+=any(r['status']=='accepted' for r in state.get('final_retention',[]))
            if arm=='chain':s['selected_concept_tasks']+=bool(state['stages'].get('S3',{}).get('artifact',{}).get('selected_ids'))
            for name in (schemas.STAGES if arm=='chain' else [str(i) for i in range(1,6)]):
                row=state['stages'].get(name)
                status=OfflineChain(item['task'],p.parent).status(name) if arm=='chain' else row['state'] if row else 'not_called'
                count=s['stages'].setdefault(name,{});count[status]=count.get(status,0)+1
                if row and row['state']=='failed':s['errors'].append(dict(task_id=item['task_id'],stage=name,reason=row.get('reason')))
    allcost=costs(ROOT/'transport');byarm={}
    for arm in summary:
        records=[]
        for p in (ROOT/'transport/calls').glob(f'*_{arm}_*/attempts.json'):records.extend(json.loads(p.read_text()))
        byarm[arm]=dict(calls=len(records),received=sum(r['state']=='received' for r in records),input_tokens=sum(r.get('input_tokens',0) for r in records),output_tokens=sum(r.get('output_tokens',0) for r in records),unknown=sum(not r.get('usage_known') for r in records))
    result=dict(tasks=30,arms=summary,costs=allcost,arm_costs=byarm,canary=costs(paths.DATA_OUT/'canary'),D_IO=None);atomic_json(ROOT/'report.json',result);return result

def score():
    snap=json.loads((ROOT/'generation_frozen.json').read_text());assert all(digest(ROOT/p)==h for p,h in snap.items())
    refs={int(x['task_id'].split('/')[1]):x for x in map(json.loads,paths.dataset_paths()['oracle_hep'].read_text().splitlines())};rows=[]
    for item in json.loads((HERE/'prepared.json').read_text()):
        n=item['task_id'];ref=refs[n];reference=source_view.prepare(ref['prompt']+ref['canonical_solution'],ref['entry_point'],valid_code=item['task']['valid_code']);arms={}
        for arm in ('chain','direct'):
            path=ROOT/'cases'/str(n)/arm/'state.json';state=json.loads(path.read_text()) if path.exists() else {'inputs':{}}
            kept={r['input_repr'] for r in state.get('final_retention',[]) if r['status']=='accepted'};out=[]
            for x in state['inputs'].values():
                actual=x.get('result') or {};expected=execute(reference,x['input_repr'],[],ROOT/'scoring'/str(n));row=dict(input_repr=x['input_repr'],decisive=False,different=False,final=x['input_repr'] in kept)
                if actual.get('native_checked') and expected.get('native_checked') and expected['status']=='ok':
                    try:
                        if actual['status']=='exception':different=True
                        elif actual['status']=='ok':different=typed_value(parse_literal(actual['output_repr'],output=True))!=typed_value(parse_literal(expected['output_repr'],output=True))
                        else:out.append(row);continue
                        row.update(decisive=True,different=different,put=actual.get('output_repr'),put_exception=actual.get('exception_type'),canonical=expected.get('output_repr'))
                    except (ValueError,KeyError):pass
                out.append(row)
            arms[arm]=dict(inputs=out,detected=any(x['different'] for x in out),final_detected=any(x['different'] and x['final'] for x in out),unresolved=sum(not x['decisive'] for x in out))
        rows.append(dict(task_id=n,arms=arms))
    wins=sum(r['arms']['chain']['detected'] and not r['arms']['direct']['detected'] for r in rows);losses=sum(r['arms']['direct']['detected'] and not r['arms']['chain']['detected'] for r in rows)
    rng=random.Random(C['seed']);matched=[]
    for _ in range(C['equal_input_resamples']):
        counts={a:0 for a in ('chain','direct')}
        for r in rows:
            m=min(len(r['arms'][a]['inputs']) for a in counts)
            for a in counts:counts[a]+=any(x['different'] for x in rng.sample(r['arms'][a]['inputs'],m))
        matched.append(counts)
    result=dict(scope='post-generation canonical IO conditional on mined/spec admissibility; same maximum calls/inputs, actual tokens unmatched',tasks=30,detection={a:sum(r['arms'][a]['detected'] for r in rows) for a in ('chain','direct')},final_detection={a:sum(r['arms'][a]['final_detected'] for r in rows) for a in ('chain','direct')},chain_only=wins,direct_only=losses,equal_input_mean={a:sum(x[a] for x in matched)/len(matched) for a in ('chain','direct')},rows=rows)
    atomic_json(ROOT/'io_score.json',result);return result

def main():
    LOG.mkdir(parents=True,exist_ok=True)
    with (LOG/'run.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);freeze();stop=threading.Event();client=Client(ROOT/'transport',Incomplete,C['max_task_calls']);items=json.loads((HERE/'prepared.json').read_text());rng=random.Random(C['seed']);rng.shuffle(items);order=[]
        for item in items:
            arms=['chain','direct'];rng.shuffle(arms);order.append(dict(task_id=item['task_id'],arms=arms))
        immutable(ROOT/'order.json',order);atomic_json(LOG/'status.json',dict(state='running',model='gpt-5.6-luna',effort='low',max_task_calls=300))
        def one(pair):
            item=next(x for x in items if x['task_id']==pair['task_id'])
            try:
                for arm in pair['arms']:
                    if stop.is_set():return
                    (run_chain if arm=='chain' else run_direct)(item,client,stop)
            except BaseException:stop.set();raise
        try:
            with ThreadPoolExecutor(C['workers']) as pool:list(pool.map(one,order))
            summary=report()
            if stop.is_set():raise Incomplete('run_stopped')
            immutable(ROOT/'generation_frozen.json',{str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'cases').rglob('*.json')})
            atomic_json(LOG/'status.json',dict(state='generation_complete_scoring',costs=summary['costs']));result=score();atomic_json(LOG/'status.json',dict(state='complete',summary={k:v for k,v in result.items() if k!='rows'},costs=summary['costs']))
        except BaseException as exc:atomic_json(LOG/'status.json',dict(state='incomplete_no_auto_retry',error_type=type(exc).__name__,report=report()))
        finally:
            try:subprocess.run(['/usr/bin/codex','queue','--thread','01a1387b-2603-7221-8fd0-b314052b1085','--message','Authorized v33_lunachain30 GPT-5.6 Luna low chain-vs-direct30 finished/stopped. Read out/runlogs_v33_lunachain30/status.json and out/pipelines/v33_lunachain30/humaneval/comparison. Verify frozen source/generation, CLI identity/effort/toolattempts/costs; report actual matched maximum call/input budgets, chain/direct any-stage/final canonical IO and random equal-input comparisons. Preserve admissibility and unmatched-token caveats. Do not auto-retry quota/unknown CLI attempts or switch model. Resume only unchanged missing scoring without model calls if needed; no paid env/API. Update own results/memory, preserve other sessions.','-C',str(paths.REPO)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
            except Exception:pass

if __name__=='__main__':main()
