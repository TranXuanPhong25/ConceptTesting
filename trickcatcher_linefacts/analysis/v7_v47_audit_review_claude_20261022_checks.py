"""Read-only tool-side checks of v47 (no reference, no model): prompt digests of cached calls, menu order-dedupe,
per-argument range blocking by pool_max."""
import hashlib, json, ast, sys
from pathlib import Path
from trickcatcher_linefacts.analysis.v47_concept_select import select_run as S
from trickcatcher_linefacts.analysis.v44_concept_matrix import matrix as M
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.hypothesis_replay import freeze_local_constants
freeze_local_constants()
run = ft_run.FTRun('vibepass_half')
prep = json.loads((S.OUT / 'prepared.json').read_text())
stale, ok, order_dups, blocked = [], 0, [], []
for case in run.cases:
    cid = case['case_id']; p = prep[cid]
    if 'error' in p:
        continue
    task = run.task(case)
    for arm in S.ARMS:
        f = S.OUT / 'calls' / cid / f'{arm}.json'
        items = p['menus'][arm]['items']
        if f.exists():
            rec = json.loads(f.read_text())
            sha = hashlib.sha256(json.dumps(S.prompt(task, case, items, arm), sort_keys=True).encode()).hexdigest()
            (ok := ok + 1) if sha == rec.get('prompt_sha256') else stale.append((cid, arm))
        sets = {}
        for it in items:
            sh = tuple(p['kinds'][it['kind']][it['instance']])
            sets.setdefault(frozenset(sh), []).append(it['id'])
        order_dups += [(cid, arm, v) for v in sets.values() if len(v) > 1]
    # per-argument: would arg i expand if compared with its own max instead of the global pool max?
    params = M.param_names(task['signature']); cons = M.constraints(task['spec'], params)
    seeds = ft_run.base_inputs(case, 'vibepass_half')
    for (i, kind), (lo, hi) in sorted(cons.items()):
        own = max((S._maxabs(repr(s[i]))['maxabs'] for s in seeds if i < len(s)), default=0)
        if hi > own and hi <= p['pool_max']:
            blocked.append((cid, i, kind, hi, own, p['pool_max']))
print('cached calls digest ok', ok, 'stale', stale)
print('same-set different-order menu items', order_dups)
print('constraints blocked by another arg (vs public max of own arg)', blocked)
