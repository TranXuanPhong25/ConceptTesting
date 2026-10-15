"""Selection-only pilot. Gold code is loaded only after menus/choices/pools freeze."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from . import behavior_experiment as foundation,behavior,candidate_models as cm,paths,v4_runtime,gen_inputs
from .llm_client import Client,atomic_json
HERE=Path(__file__).resolve().parent
ROOT=foundation.ROOT/'selection_pilot'
CFG=paths.CONFIG['selection_pilot']


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def isolated(mode,job,directory):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    jp=directory/(mode+'_job.json');op=directory/(mode+'_result.json')
    v4_runtime.immutable(jp,dict(job,mode=mode))
    if op.exists():
        cached=json.loads(op.read_text())
        if 'worker_error' not in cached:return cached
        op.unlink()
    r=gen_inputs.sandbox(v4_runtime.interpreter(),HERE/'selection_worker.py',jp,op,1800)
    if 'worker_error' in r:op.unlink(missing_ok=True);raise RuntimeError(r['worker_error'])
    return r


def prepared(t):return foundation.prepared(t)


def menu_data(t):return json.loads((ROOT/'prepared'/str(t['task'])/'candidates_result.json').read_text())


def prepare(workers):
    representation=foundation.prepare(workers)
    if not representation['passed']:return dict(passed=False,reason='representation_gate')
    def one(t):
        r=isolated('candidates',dict(task=t,prepared=prepared(t)),ROOT/'prepared'/str(t['task']))
        row=dict(task=t['task'],enumerated=r.get('enumerated',0),survived=r.get('survived',0),retained=len(r['pool']),
                 displayed=len(r['menu']),inputs=len(r['inputs']),ambiguous=r.get('ambiguous_within_scope',False),reason=r['reason'])
        print('candidates',t['task'],row['retained'],'menu',row['displayed'],flush=True);return row
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,foundation.tasks()))
    count=sum(r['displayed']>0 for r in rows)
    gate=dict(tasks=len(rows),candidate_tasks=count,required=CFG['minimum_candidate_tasks'],passed=count>=CFG['minimum_candidate_tasks'],rows=rows)
    atomic_json(ROOT/'candidate_gate.json',gate);print('Candidate gate:',count,'/',len(rows),'passed',gate['passed'],flush=True)
    return gate


def freeze():
    value=dict(protocol_sha256=digest(foundation.ROOT/'protocol.json'),choices_sha256=digest(ROOT/'choices.json'),
        tasks={str(t['task']):dict(candidates=digest(ROOT/'prepared'/str(t['task'])/'candidates_result.json'),
                                  choice=digest(ROOT/'choices'/str(t['task'])/'summary.json'),
                                  explanation=digest(ROOT/'explanations'/str(t['task'])/'explain_result.json')) for t in foundation.tasks()},
        scope='All menus, choices, input pools and pre-gold evidence fixed before canonical audit')
    v4_runtime.immutable(ROOT/'selection_frozen.json',value)
    return value


def select(client,workers):
    if not json.loads((ROOT/'candidate_gate.json').read_text())['passed']:raise RuntimeError('candidate gate failed')
    def one(t):
        d=ROOT/'choices'/str(t['task']);out=d/'summary.json'
        if out.exists():return json.loads(out.read_text())
        p=prepared(t);data=menu_data(t);msgs=cm.choice_messages(p['ir']['docstring'],data['menu'])
        v4_runtime.immutable(d/'prompt.json',msgs)
        response=client.chat(msgs,CFG['seed']+t['task'],temperature=0,top_p=1,max_tokens=CFG['max_tokens'])
        atomic_json(d/'response.json',response)
        try:choice=cm.parse_choice(response['text'],data['menu']);valid=True;error=None
        except (ValueError,TypeError,KeyError) as exc:choice='NONE';valid=False;error=type(exc).__name__
        evidence=isolated('explain',dict(task=t,prepared=p,candidates=data,choice=choice),ROOT/'explanations'/str(t['task']))
        row=dict(task=t['task'],choice=choice,valid_choice=valid,error=error,selected_model=evidence['selected_model'],
                 logical_calls=1,input_tokens=response.get('n_in',0),output_tokens=response.get('n_out',0),
                 cache_hit=response.get('cache_hit',False),candidate_discrepancies=len(evidence['records']))
        atomic_json(out,row);print('choice',t['task'],choice,'valid',valid,flush=True);return row
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,foundation.tasks()))
    atomic_json(ROOT/'choices.json',rows);freeze()


def audit(workers):
    # Verify full immutable input/choice snapshot before any canonical material is read.
    if not (ROOT/'selection_frozen.json').exists():raise RuntimeError('freeze all choices first')
    freeze();foundation.verify()
    material={int(r['task_id'].split('/')[1]):{k:r[k] for k in ('prompt','canonical_solution','contract')}
              for r in map(json.loads,paths.dataset_paths()['oracle_hep'].read_text().splitlines())}
    choices={r['task']:r for r in json.loads((ROOT/'choices.json').read_text())}
    def one(t):
        h=material[t['task']]
        return isolated('audit',dict(task=t,candidates=menu_data(t),choice=choices[t['task']]['choice'],
            canon=h['prompt']+h['canonical_solution'],contract=h['prompt']+h['contract']+'\n    pass\n'),ROOT/'audit'/str(t['task']))
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,foundation.tasks()))
    eligible=[r for r in rows if r['displayed']];available=[r for r in rows if r['display_has_sampled_consistent']]
    ambiguous=[r for r in rows if r['ambiguous_within_scope']]
    def summary(rs):return dict(tasks=len(rs),pool_covered=sum(r['pool_has_sampled_consistent'] for r in rs),
        menu_covered=sum(r['display_has_sampled_consistent'] for r in rs),llm_consistent=sum(r['chosen_sampled_consistent'] for r in rs),
        rule_consistent=sum(r['rule_sampled_consistent'] for r in rs),uniform_expected=sum(r['uniform_expected_consistency'] for r in rs),
        partial_requirements_selected=sum(r['partial_requirement'] for r in rs),
        candidate_reports=sum(len(r['candidate_reports']) for r in rs),
        confirmed_candidate_reports=sum(x['confirmed'] for r in rs for x in r['candidate_reports']),
        false_alarms=sum(x['false_alarm'] for r in rs for x in r['candidate_reports']),
        tasks_with_confirmed_candidate=sum(any(x['confirmed'] for x in r['candidate_reports']) for r in rs))
    result=dict(scope='20 design dev selection-only pilot, finite frozen input audit; no D_IO comparison',
        totals=summary(rows),eligible=summary(eligible),conditional_on_menu_coverage=summary(available),
        ambiguous_within_scope=summary(ambiguous),choices=choices,rows=rows,
        paired_llm_vs_rule=dict(wins=sum(r['chosen_sampled_consistent'] and not r['rule_sampled_consistent'] for r in eligible),
            losses=sum(r['rule_sampled_consistent'] and not r['chosen_sampled_consistent'] for r in eligible)),
        misses=dict(pool_missing=sum(not r['pool_has_sampled_consistent'] for r in rows),
            lost_in_display=sum(r['pool_has_sampled_consistent'] and not r['display_has_sampled_consistent'] for r in rows),
            llm_missed_available=sum(r['display_has_sampled_consistent'] and not r['chosen_sampled_consistent'] for r in rows)),
        generation_run=False,D_IO=None,snapshot_sha256=digest(ROOT/'selection_frozen.json'))
    atomic_json(ROOT/'report.json',result);print(json.dumps(result['totals']),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('stage',choices=['prepare','select','audit','all']);ap.add_argument('--online',action='store_true');ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    if a.workers<1:ap.error('positive workers required')
    if a.stage in ('prepare','all'):
        if not prepare(a.workers)['passed']:return
    foundation.verify()
    if a.stage in ('select','all'):select(Client(ROOT/'model_cache',offline=not a.online,workers=a.workers),a.workers)
    if a.stage in ('audit','all'):audit(a.workers)
if __name__=='__main__':main()
