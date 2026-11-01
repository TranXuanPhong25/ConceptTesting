"""One-shot input generation per arm/task, followed by a frozen reference evaluation."""
from __future__ import annotations

import ast
import hashlib
import json
import random
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, permutation_test

from final.pipeline import Pipeline, Settings, digest, save
from .analysis import analyze_task
from .execution import execute
from .pools import candidate_pool, select_witnesses
from .prompts import ARMS, common_prompt, messages
from .cohort import call_usage

BUDGET=20


def parsed_input(record):
    if not isinstance(record,dict):
        raise ValueError('Input record must be an object')
    for key in ('args','kwargs'):
        if not isinstance(record.get(key),str) or len(record[key])>16000:
            raise ValueError('Invalid or oversized literal')
    args,kwargs=ast.literal_eval(record['args']),ast.literal_eval(record['kwargs'])
    if not isinstance(args,(list,tuple)) or not isinstance(kwargs,dict) or not all(isinstance(k,str) for k in kwargs):
        raise ValueError('Invalid args/kwargs')
    return dict(args=record['args'],kwargs=record['kwargs'],concept_id=record.get('concept_id'))


def prepare(task,cohort_task,metadata,model,directory):
    path=directory/'packet.json'
    if path.exists():
        return json.loads(path.read_text())
    passing=[p for p in cohort_task['programs'] if p['base']['status']=='pass']
    if cohort_task['generated']!=10 or not passing:
        result=dict(task_id=task['task_id'],skip='generation_shortfall' if cohort_task['generated']!=10 else 'no_base_pass')
        save(path,result)
        return result
    task_number=int(task['task_id'].split('/')[1])
    # Visibility is chosen before any new-input/oracle outcome, identically across arms.
    visible=sorted(passing,key=lambda p:hashlib.sha256(f"{task_number}:{p['id']}".encode()).hexdigest())
    while visible:
        common=common_prompt(task,visible,metadata['contract'],BUDGET)
        analysis=analyze_task(dict(cohort_task,programs=visible))
        for arm in ('classical','contrastive','placebo'):
            for card in analysis[arm]:
                card['text']=card['text'][:800]
        # Largest registered hint envelope must leave the same 2048-token output budget.
        sizes={arm:model.tokens(messages(common,arm,analysis,[])) for arm in ARMS if arm!='toolinput'}
        if max(sizes.values())<=model.context-2048-128:
            break
        visible.pop()
    if not visible:
        result=dict(task_id=task['task_id'],skip='prompt_too_large')
        save(path,result)
        return result
    pool=candidate_pool(visible,task_number)
    checks=execute(dict(mode='validate',context=task['prompt'],source='',entry=task['entry_point'],
                        contract=metadata['contract'],tests=pool,timeout=3))['tests']
    witnesses=select_witnesses(pool,checks,set(cohort_task['base_input_keys']),task_number)
    while witnesses and model.tokens(messages(common,'toolinput',analysis,witnesses))>model.context-2048-128:
        witnesses.pop()
    result=dict(task_id=task['task_id'],visible_put_ids=[p['id'] for p in visible],common=common,
                analysis=analysis,witnesses=witnesses,pool=pool,pool_validation=checks,prompt_tokens=sizes)
    save(path,result)
    return result


def generate_inputs(task,cohort_task,metadata,model,out):
    directory=out/'tasks'/task['task_id'].split('/')[1]
    packet=prepare(task,cohort_task,metadata,model,directory)
    if packet.get('skip'):
        save(directory/'inputs.json',dict(task_id=task['task_id'],skip=packet['skip']))
        return
    final=directory/'inputs.json'
    if final.exists():
        return
    client=Pipeline(model,out,Settings())
    arms={}
    for arm in ARMS:
        response=client.query(directory,arm,messages(packet['common'],arm,packet['analysis'],packet['witnesses']),
                              temperature=.7,max_tokens=2048,
                              seed=314159+int(task['task_id'].split('/')[1]))
        rejected=[]
        try:
            data=json.loads(response.text.strip().removeprefix('```json').removesuffix('```').strip())
            records=data['inputs']
            if not isinstance(records,list):
                raise ValueError()
        except (KeyError,TypeError,ValueError):
            records=[]
            rejected.append(dict(reason='invalid_response'))
        accepted=[]
        for index,record in enumerate(records[:BUDGET]):
            try:
                accepted.append(parsed_input(record))
            except (ValueError,SyntaxError,TypeError,RecursionError):
                rejected.append(dict(index=index,reason='invalid_literal'))
        arms[arm]=dict(inputs=accepted,rejected=rejected,finish_reason=response.finish_reason)
    arms['witness_only']=dict(inputs=packet['witnesses'],rejected=[])
    save(final,dict(task_id=task['task_id'],arms=arms))


def score_task(task,cohort_task,metadata,out):
    directory=out/'tasks'/task['task_id'].split('/')[1]
    result_path=directory/'result.json'
    if result_path.exists():
        return json.loads(result_path.read_text())
    generated=json.loads((directory/'inputs.json').read_text())
    if generated.get('skip'):
        result=dict(task_id=task['task_id'],skip=generated['skip'])
        save(result_path,result)
        return result
    raw,origin=[],{}
    for arm,record in generated['arms'].items():
        origin[arm]=[]
        for candidate in record['inputs']:
            origin[arm].append(len(raw))
            raw.append(candidate)
    reference=task['prompt']+task['canonical_solution']
    job=dict(mode='oracle',context=task['prompt'],source=reference,entry=task['entry_point'],
             contract=metadata['contract'],tests=raw,timeout=3,
             seed=271828+int(task['task_id'].split('/')[1]))
    reference_runs=[]
    for repeat in range(2):
        path=directory/f'oracle_{repeat}.json'
        if path.exists():
            checks=json.loads(path.read_text())
        else:
            checks=execute(job)
            save(path,checks)
        reference_runs.append(checks['tests'])
    valid,raw_to_index,by_key,rejected=[],{}, {}, []
    base_keys=set(cohort_task['base_input_keys'])
    for index,record in enumerate(raw):
        a,b=(run[index] for run in reference_runs)
        if a['status']!='ok' or b['status']!='ok':
            rejected.append(dict(index=index,reason='domain_or_reference_rejects',outcomes=[a,b]))
            continue
        if a['expected']!=b['expected'] or a['input_key']!=b['input_key']:
            rejected.append(dict(index=index,reason='unstable_reference'))
            continue
        key=a['input_key']
        if key in base_keys:
            rejected.append(dict(index=index,reason='base_duplicate'))
            continue
        if key not in by_key:
            by_key[key]=len(valid)
            valid.append(dict(args=record['args'],kwargs=record['kwargs'],expected=a['expected'],input_key=key))
        raw_to_index[index]=by_key[key]
    arm_indices={arm:list(dict.fromkeys(raw_to_index[i] for i in indices if i in raw_to_index))
                 for arm,indices in origin.items()}
    save(directory/'oracle_valid.json',dict(tests=valid,rejected=rejected,arm_indices=arm_indices))
    passing=[p for p in cohort_task['programs'] if p['base']['status']=='pass']
    outcomes={}
    for program in passing:
        runs=[]
        for repeat in range(2):
            path=directory/'evaluation'/f"{program['id']}_{repeat}.json"
            if path.exists():
                checks=json.loads(path.read_text())
            else:
                checks=execute(dict(mode='evaluate',context=task['prompt'],source=program['code'],
                        entry=task['entry_point'],tests=valid,atol=metadata['atol'],timeout=3,seed=job['seed']))
                save(path,checks)
            runs.append(checks['tests'])
        outcomes[str(program['id'])]=dict(
            failing=[i for i in range(len(valid)) if all(r[i]['status'] in ('fail','error','timeout') for r in runs)],
            unstable=[i for i in range(len(valid)) if runs[0][i]['status']!=runs[1][i]['status']])
    per_arm={}
    for arm,indices in arm_indices.items():
        chosen=set(indices)
        detected=[pid for pid,row in outcomes.items() if chosen.intersection(row['failing'])]
        per_arm[arm]=dict(valid_inputs=len(indices),detected_put_ids=detected,detected=len(detected))
    result=dict(task_id=task['task_id'],base_pass=len(passing),arms=per_arm,
                arm_indices=arm_indices,outcomes=outcomes,oracle_rejected=len(rejected),valid_union=len(valid))
    save(result_path,result)
    return result


def detected(row,indices):
    chosen=set(indices)
    return sum(bool(chosen.intersection(program['failing'])) for program in row['outcomes'].values())


def matched_pair(rows,left,right):
    left_fracs,right_fracs=[],[]
    matched_rows=[]
    for row in rows:
        if row.get('skip'):
            continue
        a,b=row['arm_indices'][left],row['arm_indices'][right]
        count=min(len(a),len(b))
        seed_value=int(hashlib.sha256(f"{row['task_id']}:{left}:{right}".encode()).hexdigest()[:16],16)
        rng=random.Random(seed_value)
        da,db=detected(row,rng.sample(a,count)),detected(row,rng.sample(b,count))
        left_fracs.append(da/row['base_pass'])
        right_fracs.append(db/row['base_pass'])
        robustness=[]
        for _ in range(100):
            robustness.append((detected(row,rng.sample(a,count)),detected(row,rng.sample(b,count))))
        matched_rows.append(dict(task_id=row['task_id'],inputs_each=count,left=da,right=db,
            mean_left_100=sum(x for x,y in robustness)/100,mean_right_100=sum(y for x,y in robustness)/100))
    a,b=np.array(left_fracs),np.array(right_fracs)
    if len(a)>=2 and np.any(a!=b):
        pvalue=float(permutation_test((a,b),lambda x,y,axis:np.mean(x-y,axis=axis),
            permutation_type='samples',vectorized=True,n_resamples=10000,alternative='two-sided',rng=np.random.default_rng(20261030)).pvalue)
    else:
        pvalue=1.
    wins=sum(r['left']>r['right'] for r in matched_rows)
    losses=sum(r['left']<r['right'] for r in matched_rows)
    return dict(left=left,right=right,task_count=len(a),left_macro_fraction=float(a.mean()) if len(a) else None,
                right_macro_fraction=float(b.mean()) if len(b) else None,paired_permutation_pvalue=pvalue,
                tasks_left_more=wins,tasks_right_more=losses,
                directional_sign_pvalue=float(binomtest(wins,wins+losses).pvalue) if wins+losses else 1.,rows=matched_rows)


def report(out,cohort,expected_tasks):
    rows=[json.loads(p.read_text()) for p in (out/'tasks').glob('*/result.json')]
    rows.sort(key=lambda r:int(r['task_id'].split('/')[1]))
    totals={arm:dict(valid_inputs=sum(r['arms'][arm]['valid_inputs'] for r in rows if not r.get('skip')),
                    detected=sum(r['arms'][arm]['detected'] for r in rows if not r.get('skip')),
                    tasks_detected=sum(r['arms'][arm]['detected']>0 for r in rows if not r.get('skip')))
            for arm in (*ARMS,'witness_only')}
    comparisons=[matched_pair(rows,a,b) for a,b in [('classical','plain'),('contrastive','plain'),
                   ('classical','placebo'),('classical','toolinput')]]
    diagnostics=dict(card_kinds={},unsupported_graphs=0,visible_puts=0,tasks_with_contrast=0,
                     generation_rejections={},oracle_rejections={})
    for path in (out/'tasks').glob('*/packet.json'):
        packet=json.loads(path.read_text())
        if packet.get('skip'):
            continue
        diagnostics['visible_puts']+=len(packet['visible_put_ids'])
        diagnostics['unsupported_graphs']+=sum(a['graph_error'] is not None for a in packet['analysis']['analyses'])
        diagnostics['tasks_with_contrast']+=packet['analysis']['contrastive_available']
        for card in packet['analysis']['classical']:
            key=card['kind']
            diagnostics['card_kinds'][key]=diagnostics['card_kinds'].get(key,0)+1
    for path in (out/'tasks').glob('*/inputs.json'):
        data=json.loads(path.read_text())
        for arm,record in data.get('arms',{}).items():
            for rejection in record.get('rejected',[]):
                key=f"{arm}:{rejection['reason']}"
                diagnostics['generation_rejections'][key]=diagnostics['generation_rejections'].get(key,0)+1
    for path in (out/'tasks').glob('*/oracle_valid.json'):
        for rejection in json.loads(path.read_text())['rejected']:
            key=rejection['reason']
            diagnostics['oracle_rejections'][key]=diagnostics['oracle_rejections'].get(key,0)+1
    result=dict(cohort_sha256=cohort['cohort_sha256'],expected_tasks=expected_tasks,scored_tasks=len(rows),
        generated=sum(t['generated'] for t in cohort['tasks']),base_pass=sum(t['base_pass'] for t in cohort['tasks']),
        evaluated_base_pass=sum(r['base_pass'] for r in rows if not r.get('skip')),arms=totals,comparisons=comparisons,
        skips=[dict(task_id=r['task_id'],reason=r['skip']) for r in rows if r.get('skip')],
        writer_calls=cohort.get('generation_usage',{}),tester_calls=call_usage(out),diagnostics=diagnostics)
    observers=[json.loads(p.read_text()) for p in (out/'keepalive').glob('*.json')]
    result['keepalive_calls']=dict(attempts=len(observers),received=sum(x['state']=='received' for x in observers),
        unknown=sum(x['state']!='received' for x in observers),
        known_total_tokens=sum(x.get('usage',{}).get('total_tokens',0) for x in observers))
    for comparison in comparisons:
        comparison['zero_valid_budget_tasks']=sum(r['inputs_each']==0 for r in comparison['rows'])
    save(out/'summary.json',result)
    lines=['# Fixed-PUT concept benchmark, reference-program oracle','',
           f"Tasks scored: {len(rows)}/{expected_tasks}; frozen generated PUTs: {result['generated']}; base passes: {result['base_pass']}.",'',
           '| Arm | Valid novel inputs | Detected PUTs | Tasks with detection |','|---|---:|---:|---:|']
    for arm,total in totals.items():
        lines.append(f"| {arm} | {total['valid_inputs']} | {total['detected']} | {total['tasks_detected']} |")
    lines += ['','Raw counts above use each arm\'s valid yield. Primary comparison below matches valid input counts',
              'per task by prespecified random subsets, with tasks as statistical units. No failing-output filtering.', '']
    for c in comparisons:
        lines.append(f"- {c['left']} vs {c['right']}: macro detected fraction {c['left_macro_fraction']} vs {c['right_macro_fraction']}; paired p={c['paired_permutation_pvalue']:.5g}; tasks with more detections {c['tasks_left_more']}–{c['tasks_right_more']}.")
    lines += ['',f"Writer accounting (shared frozen-cohort cost): {result['writer_calls']}.",
              f"Tester accounting: {result['tester_calls']}.",f"Diagnostics: {diagnostics}.",
              f"Explicit skips: {result['skips']}."]
    lines += ['','Expected outputs come exclusively from the reference program after all arm inputs freeze.',
              'EvalPlus input contracts filter the domain; EvalPlus floating tolerances and polynomial-root property',
              'handle accepted non-unique roots. Reference oracle limitations remain; this is detection on this',
              'fixed LLM-generated cohort, not generalization to every real-world bug. Structural code diversity',
              'does not prove algorithmic independence. CFG edges/static def-use edges are may-relations, not',
              'proven paths. See per-task evidence and PREREG for shortfalls and visibility limits.','']
    (out/'REPORT.md').write_text('\n'.join(lines))
    return result
