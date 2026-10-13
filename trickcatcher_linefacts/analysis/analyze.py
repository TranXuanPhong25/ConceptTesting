import json, sys, ast
from pathlib import Path
from collections import defaultdict
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
W = Path('/home/phong/.claude/jobs/08a7596f/tmp/why')
rows = json.load(open(W/'rows.json')); base = json.load(open(W/'base.json'))
res = {int(p.stem): json.load(open(p)) for p in (W/'res').glob('*.json')}
ex = {}
for d in ('oracle_v3m2hyb', 'oracle_advhyb_partial', 'oracle_evalmitigate'):
    for p in (H/'out'/d/'exec').glob('[0-9]*.json'):
        if p.name.endswith('.job.json'): continue
        ex.setdefault(d, {})[int(p.stem)] = json.load(open(p))['calls']
src = {'concept-hybrid': 'oracle_v3m2hyb', 'plain-hybrid': 'oracle_v3m2hyb', 'concept': 'oracle_v3m2hyb', 'plain': 'oracle_v3m2hyb',
       'toolinput': 'oracle_v3m2hyb', 'advdoc-hybrid': 'oracle_advhyb_partial', 'advdoc-plainhybrid': 'oracle_advhyb_partial',
       'advdoc': 'oracle_evalmitigate', 'onlydoc': 'oracle_evalmitigate'}
def norm(c):
    try: return ast.unparse(ast.parse(c, mode='eval'))
    except Exception: return c
def refdet(arm, t, c):
    rec = ex[src[arm]].get(t, {}).get(c, {}); d = rec.get('ref', {})
    return bool(d.get('emit') and d.get('canon_ok') and not d.get('put_ok') and rec.get('valid', True))
S = defaultdict(lambda: defaultdict(float)); per = defaultdict(dict)
for r in rows:
    if r['task'] == 160: continue
    a, t = r['arm'], r['task']; R = res[t]; B = {norm(c) for c in base[str(t)]}
    r1 = list(dict.fromkeys(r['r1'])); al = list(dict.fromkeys(r['all'])); r2 = [c for c in al if c not in set(r1)]
    st = S[a]; st['n'] += 1
    for lab, cs in (('r1', r1), ('r2', r2), ('all', al)):
        rev = any(R.get(c) == 'reveal' for c in cs); det = any(refdet(a, t, c) for c in cs)
        st[lab+'_reveal'] += rev; st[lab+'_ref'] += det; st[lab+'_calls'] += len(cs)
        st[lab+'_inv'] += sum(R.get(c) == 'invalid' for c in cs)
        st[lab+'_revcalls'] += sum(R.get(c) == 'reveal' for c in cs)
    st['r1_base'] += sum(norm(c) in B for c in r1)
    st['r2req'] += r['r2req']
    s1 = r.get('r1sum') or {}
    if s1.get('shown_hit_counts') is not None:
        st['shown'] += len(s1['shown_hit_counts']); st['shown_hit'] += sum(x > 0 for x in s1['shown_hit_counts'])
    per[a][t] = per[a].get(t, 0)
    per[a, 'ref'] = per.get((a, 'ref'), {}); per[a, 'ref'][t] = per[a, 'ref'].get(t, 0) + any(refdet(a, t, c) for c in al)
    per[a, 'rev'] = per.get((a, 'rev'), {}); per[a, 'rev'][t] = per[a, 'rev'].get(t, 0) + any(R.get(c) == 'reveal' for c in al)
    per[a, 'r1rev'] = per.get((a, 'r1rev'), {}); per[a, 'r1rev'][t] = per[a, 'r1rev'].get(t, 0) + any(R.get(c) == 'reveal' for c in r1)
    per[a, 'r1ref'] = per.get((a, 'r1ref'), {}); per[a, 'r1ref'][t] = per[a, 'r1ref'].get(t, 0) + any(refdet(a, t, c) for c in r1)
order = ['concept-hybrid', 'advdoc-hybrid', 'plain-hybrid', 'advdoc-plainhybrid', 'concept', 'plain', 'toolinput', 'advdoc', 'onlydoc']
print(f"{'arm':20s} {'R1 reveal':>9s} {'R1 ref':>7s} {'R2 +rev':>8s} {'ALL rev':>8s} {'ALL ref':>8s} {'ref/rev':>7s} {'r1 calls':>8s} {'r1 base%':>8s} {'r1 inv%':>7s} {'r1 rev-call%':>11s} {'r2 req':>6s} {'hint hit r1':>11s}")
for a in order:
    st = S[a]; n = st['n']; k = 3
    print(f"{a:20s} {st['r1_reveal']/k:9.1f} {st['r1_ref']/k:7.1f} {(st['all_reveal']-st['r1_reveal'])/k:8.1f} {st['all_reveal']/k:8.1f} {st['all_ref']/k:8.1f} "
          f"{st['all_ref']/max(1,st['all_reveal']):7.2f} {st['r1_calls']/n:8.1f} {100*st['r1_base']/max(1,st['r1_calls']):7.1f}% {100*st['r1_inv']/max(1,st['r1_calls']):6.1f}% "
          f"{100*st['r1_revcalls']/max(1,st['r1_calls']):10.1f}% {st['r2req']/n:6.2f} {(st['shown_hit']/st['shown'] if st['shown'] else float('nan')):11.2f}")
from math import comb
def sign(w, l):
    n = w + l; k = min(w, l); return min(1, 2*sum(comb(n, i) for i in range(k+1))/2**n) if n else 1
for key in ('r1rev', 'rev', 'r1ref', 'ref'):
    A, B = per['concept-hybrid', key], per['advdoc-hybrid', key]
    w = sum(A[t] > B[t] for t in A); l = sum(A[t] < B[t] for t in A)
    print(f'concept-hybrid vs advdoc-hybrid [{key}]: {w}/{l} p={sign(w,l):.3g}')
# the 20 tasks concept-hybrid wins under ref: where does the gap come from?
A, B = per['concept-hybrid', 'ref'], per['advdoc-hybrid', 'ref']
wins = [t for t in A if A[t] > B[t]]
cat = defaultdict(list)
for t in wins:
    if per['advdoc-hybrid', 'rev'][t] < per['concept-hybrid', 'rev'][t]: cat['advdoc inputs reveal less'].append(t)
    else: cat['same/more revealing inputs, ref fails to emit'].append(t)
print({k: (len(v), v) for k, v in cat.items()})
json.dump({k: v for k, v in cat.items()}, open(W/'wins.json', 'w'))
