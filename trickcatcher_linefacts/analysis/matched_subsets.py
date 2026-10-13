"""S2 (CONCEPT_WEAKNESS section 4; protocol fix 4, secondary analysis): matched test count by random subsets.

For each pair of arms and each task/sample, the arm with more distinct calls is cut to the other's count by a random
subset (seed 20261013, 100 draws, mean detection) instead of a prefix (prefix favours whatever an arm writes first).
Data: v8-strict construction on dev (out/gen2_qwen7b_v8strict_est, out/oracle_v8strict_est), ref and full.

    python -B trickcatcher_linefacts/analysis/matched_subsets.py
"""
import json, random, sys
from math import comb
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob

SEED, DRAWS = 20261013, 100
run, out = H/'out/gen2_qwen7b_v8strict_est', H/'out/oracle_v8strict_est'
tasks, rows = ob.load_run(run); ex = ob.execute(run, out, 12); jd = ob.judges(ex, run, out, use_llm=False)
R = {(r['task'], r['arm'], r['sample']): r for r in rows if r['split'] == 'dev' and str(r['task']) in ex}
T = sorted({k[0] for k in R})


def calls(r):
    e = tasks[r['task']]['entry']
    return list(dict.fromkeys(c for c in (ob.call_of(a['src'], e) for a in r['asserts']) if c))


def hit(t, c, o):
    rec = ex[str(t)]['calls'].get(c, {})
    emit, cok, pok = ob.decide(o, rec, jd.get((str(t), c)), None, None)
    return bool(emit and cok and not pok and rec.get('valid', True))


def cut(t, cs, n, o, rng, prefix):
    """Mean detection of an n-call subset of cs."""
    h = [hit(t, c, o) for c in cs]
    if n >= len(cs):
        return float(any(h))
    if prefix:
        return float(any(h[:n]))
    if not any(h):
        return 0.0
    idx = range(len(cs))
    return sum(any(h[i] for i in rng.sample(idx, n)) for _ in range(DRAWS)) / DRAWS


def sign(w, l):
    n = w + l; k = min(w, l)
    return min(1, 2*sum(comb(n, i) for i in range(k+1))/2**n) if n else 1


PAIRS = [('concept-hybrid', 'plain-hybrid'), ('concept-hybrid', 'placebo-hybrid'), ('concept-hybrid', 'toolinput'),
         ('concept-hybrid', 'concept'), ('plain-hybrid', 'toolinput'), ('concept', 'plain')]
lines, res = [f'v8-strict construction, dev {len(T)} tasks, K=3; random subsets: seed {SEED}, {DRAWS} draws'], {}
for o in ('ref', 'full'):
    for a, b in PAIRS:
        out_ = {}
        for mode in ('random', 'prefix'):
            rng = random.Random(f'{SEED}-{o}-{a}-{b}')
            pa, pb, n_sum = {t: 0.0 for t in T}, {t: 0.0 for t in T}, 0
            for t in T:
                for s in range(3):
                    ca, cb = calls(R[t, a, s]), calls(R[t, b, s]); n = min(len(ca), len(cb)); n_sum += n
                    pa[t] += cut(t, ca, n, o, rng, mode == 'prefix'); pb[t] += cut(t, cb, n, o, rng, mode == 'prefix')
            eps = 1e-9
            w = sum(pa[t] > pb[t] + eps for t in T); l = sum(pa[t] + eps < pb[t] for t in T)
            out_[mode] = dict(a=sum(pa.values())/3, b=sum(pb.values())/3, wins=w, losses=l, p=sign(w, l),
                              matched_calls_per_sample=n_sum/(3*len(T)))
        res[f'{o}:{a} vs {b}'] = out_
        r_, p_ = out_['random'], out_['prefix']
        lines.append(f"[{o}] {a} vs {b} @ {r_['matched_calls_per_sample']:.1f} calls: random {r_['a']:.1f} vs {r_['b']:.1f}, "
                     f"{r_['wins']}/{r_['losses']} p={r_['p']:.3f} | prefix {p_['a']:.1f} vs {p_['b']:.1f}, "
                     f"{p_['wins']}/{p_['losses']} p={p_['p']:.3f}")
print('\n'.join(lines))
(H/'analysis/matched_subsets.txt').write_text('\n'.join(lines) + '\n')
(H/'analysis/matched_subsets.json').write_text(json.dumps(res, indent=1))
