"""v7 (dev): concept-hybrid vs toolinput under ref/full: plain, matched test count, union of both."""
import json, sys
from math import comb
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob
run, out = H/'out/gen2_qwen7b_v7hyb_v4_r2', H/'out/oracle_v7hyb'
tasks, rows = ob.load_run(run); ex = ob.execute(run, out, 12); jd = ob.judges(ex, run, out, use_llm=False)
def calls(r):
    e = tasks[r['task']]['entry']; seen = []
    for a in r['asserts']:
        c = ob.call_of(a['src'], e)
        if c and c not in seen: seen.append(c)
    return seen
def det(t, cs, o):
    for c in cs:
        rec = ex[str(t)]['calls'].get(c, {})
        emit, cok, pok = ob.decide(o, rec, jd.get((str(t), c)), None, None)
        if emit and cok and not pok and rec.get('valid', True): return 1
    return 0
R = {(r['task'], r['arm'], r['sample']): r for r in rows if r['split'] == 'dev' and str(r['task']) in ex}
T = sorted({k[0] for k in R})
def sign(w, l):
    n = w + l; k = min(w, l); return min(1, 2*sum(comb(n, i) for i in range(k+1))/2**n) if n else 1
for o in ('ref', 'full'):
    ch, ti, chm, un, nch, nti = {}, {}, {}, {}, 0, 0
    for t in T:
        for s in range(3):
            a, b = calls(R[t, 'concept-hybrid', s]), calls(R[t, 'toolinput', s])
            nch += len(a); nti += len(b)
            ch[t] = ch.get(t, 0) + det(t, a, o); ti[t] = ti.get(t, 0) + det(t, b, o)
            chm[t] = chm.get(t, 0) + det(t, a[:len(b)], o)
            un[t] = un.get(t, 0) + det(t, list(dict.fromkeys(a + b)), o)
    def cmp(x, y):
        w = sum(x[t] > y[t] for t in T); l = sum(x[t] < y[t] for t in T); return f'{w}/{l} p={sign(w, l):.3f}'
    print(f'[{o}] concept-hybrid {sum(ch.values())/3:.1f} ({nch/len(T)/3:.1f} calls/sample) | toolinput {sum(ti.values())/3:.1f} ({nti/len(T)/3:.1f}) | '
          f'concept-hybrid cut to toolinput count {sum(chm.values())/3:.1f} | union {sum(un.values())/3:.1f}')
    print(f'   ch vs ti {cmp(ch, ti)} | ch-cut vs ti {cmp(chm, ti)} | union vs ch {cmp(un, ch)} | union vs ti {cmp(un, ti)}')

# budget controls for the union (ref): same-size unions from other pairs; false alarms / flag-correct-program
def stats(pairs, o='ref'):
    d, n, fa, flag, cnt = {}, 0, 0, 0, 0
    for t in T:
        for s in range(3):
            cs = []
            for arm, ds in pairs: cs += calls(R[t, arm, (s + ds) % 3])
            cs = list(dict.fromkeys(cs)); n += len(cs); cnt += 1
            d[t] = d.get(t, 0) + det(t, cs, o)
            bad = 0
            for c in cs:
                rec = ex[str(t)]['calls'].get(c, {})
                emit, cok, pok = ob.decide(o, rec, jd.get((str(t), c)), None, None)
                if emit and (not cok or not rec.get('valid', True)): bad += 1
            fa += bad; flag += bad > 0
    return d, n / cnt, 100 * flag / cnt
base_ch, _, _ = stats([('concept-hybrid', 0)])
for name, pairs in [('concept-hybrid + toolinput', [('concept-hybrid', 0), ('toolinput', 0)]),
                    ('concept-hybrid x2 (two samples)', [('concept-hybrid', 0), ('concept-hybrid', 1)]),
                    ('plain-hybrid + toolinput', [('plain-hybrid', 0), ('toolinput', 0)]),
                    ('toolinput x2', [('toolinput', 0), ('toolinput', 1)]),
                    ('concept-hybrid + plain-hybrid', [('concept-hybrid', 0), ('plain-hybrid', 0)])]:
    d, nc, fl = stats(pairs)
    print(f'{name:34s} ref {sum(d.values())/3:5.1f}  calls/sample {nc:5.1f}  flag-correct-program {fl:4.0f}%')
u, _, _ = stats([('concept-hybrid', 0), ('toolinput', 0)]); v, _, _ = stats([('concept-hybrid', 0), ('concept-hybrid', 1)])
p, _, _ = stats([('plain-hybrid', 0), ('toolinput', 0)])
for a, b, x, y in [('ch+ti', 'ch x2', u, v), ('ch+ti', 'ph+ti', u, p)]:
    w = sum(x[t] > y[t] for t in T); l = sum(x[t] < y[t] for t in T); print(f'{a} vs {b}: {w}/{l} p={sign(w, l):.3f}')
