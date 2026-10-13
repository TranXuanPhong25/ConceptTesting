import json, sys
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob
def dets(run, out, oracles=('ref', 'full')):
    run, out = H/'out'/run, H/'out'/out
    tasks, rows = ob.load_run(run); ex = ob.execute(run, out, 12); jd = ob.judges(ex, run, out, use_llm=False)
    D = {}
    for r in rows:
        t, entry = str(r['task']), tasks[r['task']]['entry']
        if t not in ex: continue
        seen = set(); det = {o: False for o in oracles}; n = 0
        for a in r['asserts']:
            c = ob.call_of(a['src'], entry)
            if c is None or c in seen: continue
            seen.add(c); rec = ex[t]['calls'].get(c, {}); valid = rec.get('valid', True)
            for o in oracles:
                emit, cok, pok = ob.decide(o, rec, jd.get((t, c)), ob.expected_of(a['src']), a)
                if emit and cok and not pok and valid: det[o] = True
        D[r['task'], r['arm'], r['sample']] = (det, r['split'])
    return D
A = dets('gen2_qwen7b_advhyb_v4_partial', 'oracle_advhyb_partial')
E = dets('gen2_qwen7b_evalmitigate', 'oracle_evalmitigate')
V = dets('gen2_qwen7b_v3m2hyb_v4', 'oracle_v3m2hyb')
allD = {**A, **E, **V}
def per_task(arm, o, split='dev', drop=(160,)):
    out = {}
    for (t, a, s), (d, sp) in allD.items():
        if a == arm and sp == split and t not in drop: out[t] = out.get(t, 0) + d[o]
    return out
from math import comb
def sign(w, l):
    n = w + l; k = min(w, l)
    return min(1, 2*sum(comb(n, i) for i in range(k+1))/2**n) if n else 1
arms = ['advdoc-hybrid', 'advdoc-plainhybrid', 'advdoc', 'onlydoc', 'concept-hybrid', 'plain-hybrid', 'toolinput', 'plain']
for o in ('ref', 'full'):
    print(f'== {o} (dev, task 160 dropped)')
    P = {a: per_task(a, o) for a in arms}
    print('  means/run:', {a: round(sum(P[a].values())/3, 1) for a in arms}, 'tasks', {a: len(P[a]) for a in arms})
    for a, b in [('advdoc-hybrid', 'advdoc-plainhybrid'), ('advdoc-hybrid', 'advdoc'), ('advdoc-plainhybrid', 'advdoc'),
                 ('advdoc-hybrid', 'concept-hybrid'), ('advdoc-hybrid', 'plain-hybrid'), ('advdoc-hybrid', 'toolinput'), ('advdoc-hybrid', 'plain'), ('advdoc-hybrid', 'onlydoc')]:
        ts = set(P[a]) & set(P[b]); w = sum(P[a][t] > P[b][t] for t in ts); l = sum(P[a][t] < P[b][t] for t in ts)
        print(f'  {a} vs {b}: {w}/{l} p={sign(w,l):.3g} (n={len(ts)})')
