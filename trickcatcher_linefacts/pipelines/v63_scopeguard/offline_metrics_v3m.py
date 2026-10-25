"""Frozen v3c reporting definitions, copied from codex_rank_v2/eval_v2.py and codex_v3c/analyze.py.\nNo selection or gate changes; evaluation only."""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

import random, statistics

from math import comb

from . import facts

P = dict(random_seed=20261010, random_draws=2000)

def pf(h):
    den = h['fail_hits'] + h['pass_hits']
    return h['fail_hits']/den if den else None

def sign_p(up, down):
    m, k = up+down, min(up, down)
    return min(1., 2*sum(comb(m, i) for i in range(k+1))/2**m) if m else 1.

def metrics(ts, tops, version='new'):
    allpf, bases, up, down, tie, no_score, strong, shown = [], [], 0, 0, 0, 0, 0, 0
    worse_ids, strong_ids, per = [], [], {}
    for t in ts:
        base=t.get(version+'_base',t['base'])
        pfs=[t[version+'_pf'][i] for i in tops[t['n']]]
        shown+=len(pfs)
        valid=[p for p in pfs if p is not None]
        allpf+=valid; bases += [base]*len(valid)
        has=any(p>=.5 for p in valid)
        strong+=has
        if has: strong_ids.append(t['n'])
        mean=statistics.mean(valid) if valid else None
        if mean is None: no_score+=1
        elif mean > base+1e-12: up+=1
        elif mean < base-1e-12: down+=1; worse_ids.append(t['n'])
        else: tie+=1
        per[t['n']]={'indices':tops[t['n']], 'mean_pf':mean, 'strong':has}
    return dict(n=len(ts), strong=strong, mean_pf=statistics.mean(allpf) if allpf else None,
                base=statistics.mean(bases) if bases else None,
                task_base=statistics.mean(t.get(version+'_base',t['base']) for t in ts), shown=shown, scored=len(allpf),
                better=up, worse=down, tie=tie, no_score=no_score, sign_p=sign_p(up,down),
                worse_tasks=worse_ids, strong_tasks=strong_ids), per

def selected(ts,k):return {t['n']:[t['fr']['facts'].index(f) for f in facts.pick(t['fr']['facts'],t['n'],k)] for t in ts}

def pool(ts):return {t['n']:[i for i,f in enumerate(t['fr']['facts']) if f['reached'] and facts.display_slot(f) in facts.RANK_SLOTS] for t in ts}

def enriched_metrics(ts,tp,version='new'):
    m,per=metrics(ts,tp,version)
    m['have_shown']=sum(bool(tp[t['n']]) for t in ts)
    m['strong_facts']=sum(t[version+'_pf'][i] is not None and t[version+'_pf'][i]>=.5 for t in ts for i in tp[t['n']])
    for t in ts:
        p=per[t['n']];base=t.get(version+'_base',t['base'])
        p.update(base=base,pfs=[t[version+'_pf'][i] for i in p['indices']],n_plus=t['nr']['n_plus'],n_fail=t['nr']['n_fail'],comparison='no_score' if p['mean_pf'] is None else 'better' if p['mean_pf']>base+1e-12 else 'worse' if p['mean_pf']<base-1e-12 else 'tie')
    return m,per

def kind_metrics(ts,shown=False):
    out={}
    for kind in facts.SLOTS:
        tp={t['n']:[i for i,f in enumerate(t['fr']['facts']) if f['reached'] and facts.slot(f)==kind and (not shown or i in t['fr']['top3'])] for t in ts}
        m,_=enriched_metrics(ts,tp);m['reached']=m.pop('shown');m['valid_reach']=m['scored']/m['reached'] if m['reached'] else None
        out[kind]=m
    return out

def analyze(ts):
    results={};per={};pools=pool(ts)
    for k in (3,5):
        tops={'selected':selected(ts,k),'ceiling':{t['n']:sorted(pools[t['n']],key=lambda i:-(t['new_pf'][i] if t['new_pf'][i] is not None else -1))[:k] for t in ts}}
        for name,tp in tops.items():
            m,pt=enriched_metrics(ts,tp);results[f'{name}@{k}']=m;per[f'{name}@{k}']=pt
        rng=random.Random(P['random_seed']+k);draws=P['random_draws'];keys=['strong','mean_pf','base','better','worse','tie','no_score','sign_p','shown','scored','have_shown','strong_facts']
        sums={key:0. for key in keys};counts={key:0 for key in keys};tm={t['n']:[] for t in ts}
        strong_counts=[]
        for _ in range(draws):
            tp={t['n']:rng.sample(pools[t['n']],min(k,len(pools[t['n']]))) for t in ts}
            m,pt=enriched_metrics(ts,tp);strong_counts.append(m['strong'])
            for key in keys:
                if m[key] is not None:sums[key]+=m[key];counts[key]+=1
            for n,p in pt.items():
                if p['mean_pf'] is not None:tm[n].append(p['mean_pf'])
        m={key:sums[key]/counts[key] if counts[key] else None for key in keys};up=down=tie=0;random_per={}
        for t in ts:
            n=t['n'];mean=statistics.mean(tm[n]) if tm[n] else None
            comparison='no_score' if mean is None else 'better' if mean>t['base']+1e-12 else 'worse' if mean<t['base']-1e-12 else 'tie'
            up+=comparison=='better';down+=comparison=='worse';tie+=comparison=='tie'
            random_per[n]=dict(mean_pf=mean,base=t['base'],comparison=comparison,scored_draws=len(tm[n]))
        m.update(n=len(ts),draws=draws,seed=P['random_seed']+k,task_base=statistics.mean(t['base'] for t in ts),expected_task_better=up,expected_task_worse=down,expected_task_tie=tie,expected_task_no_score=sum(not ms for ms in tm.values()),expected_task_sign_p=sign_p(up,down),strong_draw_min=min(strong_counts),strong_draw_max=max(strong_counts))
        results[f'random@{k}']=m;per[f'random@{k}']=random_per
    plc={t['n']:[t['fr']['placebo_all'].index(p) for p in t['fr']['placebo3']] for t in ts}
    results['placebo@3'],per['placebo@3']=enriched_metrics(ts,plc,'placebo')
    return dict(tasks=[t['n'] for t in ts],results=results,per_task=per,by_kind=kind_metrics(ts),shown_by_kind=kind_metrics(ts,True))
