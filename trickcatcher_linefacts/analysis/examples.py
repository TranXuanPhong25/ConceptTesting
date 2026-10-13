import json, ast
from pathlib import Path
W = Path('/home/phong/.claude/jobs/08a7596f/tmp/why')
rows = json.load(open(W/'rows.json')); base = json.load(open(W/'base.json')); wins = json.load(open(W/'wins.json'))
res = {int(p.stem): json.load(open(p)) for p in (W/'res').glob('*.json')}
def norm(c):
    try: return ast.unparse(ast.parse(c, mode='eval'))
    except Exception: return c
from collections import Counter
src_of = Counter()
for t in sum(wins.values(), []):
    R = res[t]; B = {norm(c) for c in base[str(t)]}
    out = {}
    for arm in ('concept-hybrid', 'advdoc-hybrid'):
        rs = [r for r in rows if r['task'] == t and r['arm'] == arm]
        r1 = [c for r in rs for c in dict.fromkeys(r['r1'])]; al = [c for r in rs for c in dict.fromkeys(r['all'])]
        r2 = [c for r in rs for c in dict.fromkeys(r['all']) if c not in set(r['r1'])]
        out[arm] = dict(r1_rev=sum(R.get(c) == 'reveal' for c in r1), r2_rev=sum(R.get(c) == 'reveal' for c in r2),
                        r1=len(r1), base=sum(norm(c) in B for c in r1), inv=sum(R.get(c) == 'invalid' for c in r1),
                        ex_rev=[c for c in al if R.get(c) == 'reveal'][:2], ex_adv=[c for c in r1 if R.get(c) != 'reveal'][:3])
    c, a = out['concept-hybrid'], out['advdoc-hybrid']
    where = 'round1' if c['r1_rev'] > 0 and a['r1_rev'] == 0 else ('round2' if c['r2_rev'] > 0 and c['r1_rev'] == 0 else 'both/mixed')
    src_of[where] += 1
    print(f"task {t} [{where}] concept r1 rev {c['r1_rev']}/{c['r1']} r2 rev {c['r2_rev']} | advdoc r1 rev {a['r1_rev']}/{a['r1']} (base {a['base']}, inv {a['inv']}) r2 rev {a['r2_rev']}")
    print('   concept reveal:', c['ex_rev'][:2]); print('   advdoc r1:', a['ex_adv'])
print(src_of)
