"""v8-strict (CPU) vs v7: per-task comparisons under ref/full, dev, all arms scored in out/oracle_v8strict_est."""
import json, sys
from math import comb
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob
def load(run, out):
    run, out = H/'out'/run, H/'out'/out
    tasks, rows = ob.load_run(run); ex = ob.execute(run, out, 12); jd = ob.judges(ex, run, out, use_llm=False)
    D = {}
    for r in rows:
        t = str(r['task'])
        if r['split'] != 'dev' or t not in ex: continue
        e = tasks[r['task']]['entry']; seen = set(); det = {'ref': 0, 'full': 0}; n = 0
        for a in r['asserts']:
            c = ob.call_of(a['src'], e)
            if not c or c in seen: continue
            seen.add(c); n += 1; rec = ex[t]['calls'].get(c, {})
            for o in det:
                emit, cok, pok = ob.decide(o, rec, jd.get((t, c)), None, None)
                if emit and cok and not pok and rec.get('valid', True): det[o] = 1
        D[r['task'], r['arm'], r['sample']] = (det, n)
    return D
V8 = load('gen2_qwen7b_v8strict_est', 'oracle_v8strict_est')
def sign(w, l):
    n = w + l; k = min(w, l); return min(1, 2*sum(comb(n, i) for i in range(k+1))/2**n) if n else 1
T = sorted({k[0] for k in V8})
for o in ('ref', 'full'):
    per = {}
    for (t, a, s), (d, n) in V8.items(): per.setdefault(a, {}); per[a][t] = per[a].get(t, 0) + d[o]
    calls = {a: sum(n for (t, b, s), (d, n) in V8.items() if b == a) / sum(1 for k in V8 if k[1] == a) for a in per}
    print(f'[{o}] ' + ', '.join(f'{a} {sum(per[a].values())/3:.1f} ({calls[a]:.1f} calls)' for a in sorted(per, key=lambda a: -sum(per[a].values()))))
    for a, b in [('concept-hybrid', 'plain-hybrid'), ('concept-hybrid', 'toolinput'), ('concept-hybrid', 'placebo-hybrid'),
                 ('concept-hybrid', 'concept'), ('plain-hybrid', 'plain')]:
        w = sum(per[a][t] > per[b][t] for t in T); l = sum(per[a][t] < per[b][t] for t in T)
        print(f'   {a} vs {b}: {w}/{l} p={sign(w, l):.3f}')

# matched test count (cut the arm with more calls to the other's count, per task/sample) and the 36 spec-hint tasks
run, out = H/'out/gen2_qwen7b_v8strict_est', H/'out/oracle_v8strict_est'
tasks, rows = ob.load_run(run); ex = ob.execute(run, out, 12); jd = ob.judges(ex, run, out, use_llm=False)
R = {(r['task'], r['arm'], r['sample']): r for r in rows if r['split'] == 'dev' and str(r['task']) in ex}
def calls(r):
    e = tasks[r['task']]['entry']; s = []
    for a in r['asserts']:
        c = ob.call_of(a['src'], e)
        if c and c not in s: s.append(c)
    return s
def det(t, cs, o='ref'):
    for c in cs:
        rec = ex[str(t)]['calls'].get(c, {}); emit, cok, pok = ob.decide(o, rec, jd.get((str(t), c)), None, None)
        if emit and cok and not pok and rec.get('valid', True): return 1
    return 0
spec36 = {t['task'] for t in json.loads((run/'tasks.json').read_text())['tasks'] if t.get('spec_facts') or any(f.get('kind') == 'SPEC' for f in t.get('concept_meta', []))}
print('spec-hint tasks in dev:', len([t for t in T if t in spec36]))
for a, b in [('concept-hybrid', 'plain-hybrid'), ('concept-hybrid', 'toolinput')]:
    pa, pb = {}, {}
    for t in T:
        for s in range(3):
            ca, cb = calls(R[t, a, s]), calls(R[t, b, s]); n = min(len(ca), len(cb))
            pa[t] = pa.get(t, 0) + det(t, ca[:n]); pb[t] = pb.get(t, 0) + det(t, cb[:n])
    w = sum(pa[t] > pb[t] for t in T); l = sum(pa[t] < pb[t] for t in T)
    print(f'matched calls {a} vs {b}: {sum(pa.values())/3:.1f} vs {sum(pb.values())/3:.1f}, {w}/{l} p={sign(w, l):.3f}')
    S = [t for t in T if t in spec36]
    fa = {t: sum(det(t, calls(R[t, a, s])) for s in range(3)) for t in S}; fb = {t: sum(det(t, calls(R[t, b, s])) for s in range(3)) for t in S}
    w = sum(fa[t] > fb[t] for t in S); l = sum(fa[t] < fb[t] for t in S)
    print(f'  36 spec tasks {a} vs {b}: {sum(fa.values())/3:.1f} vs {sum(fb.values())/3:.1f}, {w}/{l} p={sign(w, l):.3f}')
