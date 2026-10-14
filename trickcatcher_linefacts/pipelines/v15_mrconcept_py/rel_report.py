"""B3 ref-only reporting, including fixed-seed random-subset matched counts.

Witness-only assertions carry None as a collection placeholder: ref replaces
their oracle exactly as it replaces every other arm's expected values. Own
oracle metrics for witness-only placeholders must not be interpreted.
"""
import collections
import hashlib
import json
import random
from pathlib import Path
from . import oracle_b01 as ob, rel_prompts
from .llm_client import atomic_json
from .paths import CONFIG

DRAWS = 100


def metrics(records):
    result = dict(D_I=0,D_IO=0,D_I_samples=0,D_IO_samples=0,correct_failing=0,failing=0)
    for sample in records:
        seen = set()
        di = dio = 0
        for call,r in sample:
            if call in seen: continue
            seen.add(call)
            valid = r.get('valid',False)
            di += bool(valid and r.get('d_i'))
            ref = r.get('ref',{})
            hit = bool(valid and r.get('d_i') and ref.get('emit') and ref.get('canon_ok'))
            dio += hit
            if ref.get('emit') and not ref.get('put_ok'):
                result['failing'] += 1
                result['correct_failing'] += bool(valid and ref.get('canon_ok'))
        result['D_I'] += di; result['D_IO'] += dio
        result['D_I_samples'] += bool(di); result['D_IO_samples'] += bool(dio)
    result['precision'] = result['correct_failing']/result['failing'] if result['failing'] else None
    result['false_alarms'] = result['failing']-result['correct_failing']
    return result


def comparison(indexed,first,second,matched=False):
    per_task = collections.defaultdict(lambda:[0.,0.])
    budgets = []
    for task,sample in sorted({(t,s) for t,s,a in indexed}):
        a,b = indexed[task,sample,first],indexed[task,sample,second]
        m = min(len(a),len(b)); budgets.append(dict(task=task,sample=sample,m=m))
        scores = [0.,0.]
        for draw in range(DRAWS if matched else 1):
            for side,records in enumerate((a,b)):
                if matched:
                    seed = hashlib.sha256(f"{CONFIG['seeds']['arms']}|{first}|{second}|{task}|{sample}|{draw}|{side}".encode()).digest()
                    records = random.Random(int.from_bytes(seed,'big')).sample(records,m)
                scores[side] += bool(metrics([records])['D_IO_samples'])/(DRAWS if matched else 1)
        for side in (0,1): per_task[task][side] += scores[side]
    # Round floating means before ties so equal probabilities remain ties.
    win = sum(round(a-b,10)>0 for a,b in per_task.values())
    loss = sum(round(a-b,10)<0 for a,b in per_task.values())
    return dict(first=first,second=second,matched=matched,draws=DRAWS if matched else 1,
                wins=win,losses=loss,sign_p=ob.sign_p(win,loss),
                detecting_samples=[sum(v[i] for v in per_task.values()) for i in (0,1)],budgets=budgets)


def summarize(tasks,rows,executions):
    output = dict(oracle='ref',matched_seed=CONFIG['seeds']['arms'],matched_draws=DRAWS,cohorts={})
    arms = sorted({r['arm'] for r in rows})
    keys = {(r['task'],r['sample'],r['arm']) for r in rows}
    k = max(r['sample'] for r in rows)+1
    if len(keys)!=len(rows) or keys!={(t,s,a) for t in tasks for s in range(k) for a in arms}:
        raise ValueError('report requires complete selected task x arm x K cohort')
    if set(map(str,tasks))-set(executions): raise ValueError('incomplete ref executions')
    pairs = [('rel-hybrid','flat-hybrid'),('flat-hybrid','review-hybrid'),('rel-hybrid','rel-nospec-hybrid')]
    pairs += [(a,b) for a in rel_prompts.NEW_ARMS for b in rel_prompts.REFERENCES]
    # B4 (v13_hyp): primary hyp vs flat and vs toolinput; secondary vs rel, plain, witness-only.
    pairs += [('hyp-hybrid','flat-hybrid'),('hyp-hybrid','toolinput'),('hyp-hybrid','rel-hybrid'),
              ('hyp-hybrid','plain-hybrid'),('hyp-hybrid','witness-only'),('hyp-witness-only','witness-only')]
    for split in ('dev','pilot','heldout'):
        group = [r for r in rows if r['split']==split]
        if not group: continue
        indexed = {}
        for r in group:
            entry = tasks[r['task']]['entry']
            observations = executions[str(r['task'])]['calls']
            records = []
            for a in r['asserts']:
                call = ob.call_of(a['src'],entry)
                if call is not None:
                    if call not in observations: raise ValueError('missing ref call execution')
                    records.append((call,observations[call]))
            indexed[r['task'],r['sample'],r['arm']] = records
        arm_metrics = {a:metrics([records for (t,s,arm),records in indexed.items() if arm==a]) for a in arms}
        comparisons = [comparison(indexed,a,b,matched) for a,b in pairs if a in arms and b in arms
                       for matched in (False,True)]
        output['cohorts'][split] = dict(tasks=len({r['task'] for r in group}),k=k,arms=arm_metrics,comparisons=comparisons)
    return output


def report(run,out,workers=12):
    tasks,rows = ob.load_run(Path(run))
    executions = ob.execute(Path(run),Path(out),workers)
    result = summarize(tasks,rows,executions)
    atomic_json(Path(out)/'ref_metrics.json',result)
    text = json.dumps(result,indent=2)
    (Path(out)/'report.txt').write_text('B3 development report; ref only; witness-only None values are placeholders.\n'+text+'\n')
    print(text)
    return result
