"""v7_mutref registered analysis (PREREG "v7_mutref"): ODD dev tasks (even tasks fitted the rule), ref (and full).

Primary: concept-hybrid vs plain-hybrid and vs toolinput, per task sign test; on the strict construction (round 2 =
selected Hypothesis inputs only) and on the raw run. Secondary: matched test count by random subsets (RESULTS 11.38
method), placebo, and the same comparisons for v7 / v8-strict on the same odd tasks (old hint rule).
Strict rows are scored with the run's oracle execution (strict calls are a subset of the run's calls; calls without
an oracle record count as no detection and are reported).

    python -B trickcatcher_linefacts/analysis/mutref_compare.py
"""
import ast, json, random, sys
from math import comb
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob

SEED, DRAWS = 20261013, 100
MR = H/'pipelines/v7_mutref/out/humaneval'


def lit(v):
    return ast.literal_eval(v) if isinstance(v, str) else v


def load(run, oracle, gen=None):
    tasks, rows = ob.load_run(run); ex = ob.execute(run, oracle, 12); jd = ob.judges(ex, run, oracle, use_llm=False)
    if gen is not None:   # strict construction: assertions from gen.jsonl
        rows = []
        for l in open(gen):
            r = json.loads(l)
            rows.append(dict(task=int(r['task']), arm=r['arm'], sample=int(r['sample']), split=r['split'],
                             asserts=[dict(src=s) for s in lit(r['assertions'])]))
    R = {}
    for r in rows:
        t = int(r['task'])
        if r['split'] == 'dev' and t % 2 == 1:
            e = tasks[t]['entry']
            R[t, r['arm'], int(r['sample'])] = list(dict.fromkeys(c for c in (ob.call_of(a['src'], e) for a in r['asserts']) if c))
    return R, ex, jd


def make(R, ex, jd):
    miss = [0, 0]

    def hit(t, c, o):
        rec = ex.get(str(t), {}).get('calls', {}).get(c)
        miss[1] += 1
        if rec is None:
            miss[0] += 1; return False
        emit, cok, pok = ob.decide(o, rec, jd.get((str(t), c)), None, None)
        return bool(emit and cok and not pok and rec.get('valid', True))
    return hit, miss


def sign(w, l):
    n = w + l; k = min(w, l)
    return min(1, 2*sum(comb(n, i) for i in range(k+1))/2**n) if n else 1


def compare(name, R, hit, o, lines, res):
    T = sorted({k[0] for k in R})
    arms = sorted({k[1] for k in R})
    per = {a: {t: sum(any(hit(t, c, o) for c in R[t, a, s]) for s in range(3)) for t in T} for a in arms}
    ncalls = {a: sum(len(R[t, a, s]) for t in T for s in range(3)) / (3*len(T)) for a in arms}
    lines.append(f'[{name} | {o}] odd dev {len(T)} tasks: ' + ', '.join(
        f'{a} {sum(per[a].values())/3:.1f} ({ncalls[a]:.1f})' for a in sorted(arms, key=lambda a: -sum(per[a].values()))))
    res[name, o] = {'bug_per_run': {a: sum(per[a].values())/3 for a in arms}, 'calls_per_sample': ncalls}
    for a, b in [('concept-hybrid', 'plain-hybrid'), ('concept-hybrid', 'toolinput'), ('concept-hybrid', 'placebo-hybrid')]:
        w = sum(per[a][t] > per[b][t] for t in T); l = sum(per[a][t] < per[b][t] for t in T)
        rng = random.Random(f'{SEED}-{name}-{o}-{a}-{b}'); pa = {t: 0.0 for t in T}; pb = {t: 0.0 for t in T}
        for t in T:
            for s in range(3):
                ca, cb = R[t, a, s], R[t, b, s]; n = min(len(ca), len(cb))
                for cs, acc in ((ca, pa), (cb, pb)):
                    h = [hit(t, c, o) for c in cs]
                    if n >= len(cs) or not any(h):
                        acc[t] += float(any(h))
                    else:
                        acc[t] += sum(any(h[i] for i in rng.sample(range(len(cs)), n)) for _ in range(DRAWS)) / DRAWS
        mw = sum(pa[t] > pb[t] + 1e-9 for t in T); ml = sum(pa[t] + 1e-9 < pb[t] for t in T)
        lines.append(f'   {a} vs {b}: {w}/{l} p={sign(w, l):.3f} | matched (random) {sum(pa.values())/3:.1f} vs '
                     f'{sum(pb.values())/3:.1f}, {mw}/{ml} p={sign(mw, ml):.3f}')
        res[name, o][f'{a} vs {b}'] = dict(wins=w, losses=l, p=sign(w, l), matched=(sum(pa.values())/3, sum(pb.values())/3, mw, ml, sign(mw, ml)))
    return per


lines, res, pers = [], {}, {}
for name, args in [('mutref strict', (MR/'generation', MR/'oracle', MR/'strict/generation/gen.jsonl')),
                   ('mutref raw', (MR/'generation', MR/'oracle', None)),
                   ('v8-strict (old rule)', (H/'out/gen2_qwen7b_v8strict_est', H/'out/oracle_v8strict_est', None)),
                   ('v7 raw (old rule)', (H/'out/gen2_qwen7b_v7hyb_v4_r2', H/'out/oracle_v7hyb', None))]:
    R, ex, jd = load(*args); hit, miss = make(R, ex, jd)
    for o in ('ref', 'full'):
        pers[name, o] = compare(name, R, hit, o, lines, res)
    lines.append(f'   calls without oracle record: {miss[0]}/{miss[1]} lookups')
for o in ('ref', 'full'):
    for a in ('concept-hybrid', 'toolinput', 'plain-hybrid'):
        for new, old in (('mutref strict', 'v8-strict (old rule)'), ('mutref raw', 'v7 raw (old rule)')):
            x, y = pers[new, o][a], pers[old, o][a]; T = sorted(set(x) & set(y))
            w = sum(x[t] > y[t] for t in T); l = sum(x[t] < y[t] for t in T)
            lines.append(f'[{o}] {a}: {new} vs {old}: {sum(x[t] for t in T)/3:.1f} vs {sum(y[t] for t in T)/3:.1f}, {w}/{l} p={sign(w, l):.3f}')
print('\n'.join(lines))
(H/'analysis/mutref_compare.txt').write_text('\n'.join(lines) + '\n')
(H/'analysis/mutref_compare.json').write_text(json.dumps({f'{k[0]}|{k[1]}': v for k, v in res.items()}, indent=1, default=str))
