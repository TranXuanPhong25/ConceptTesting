"""S1 (CONCEPT_WEAKNESS section 4): contribution of the fuzz witnesses alone, without any LLM.

witness-only = the bundle's `tool_inputs` (fuzz witnesses of the selected hints, the inputs toolinput shows the LLM),
each turned into an assertion whose expected value is the oracle's (ref / full). Compared with toolinput
(witness shown + LLM-written tests) and concept-hybrid on the v7 dev run, plus a split of toolinput's detections into
"on a witness call" vs "on a call the LLM added". CPU only: the ref programs are the cached ref_responses of
out/oracle_v7hyb, executed on the witness calls in a separate out dir (the original oracle dir is not touched).

    python -B trickcatcher_linefacts/analysis/witness_only.py
"""
import ast, json, shutil, sys
from math import comb
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob

RUN, ORACLE, OUT = H/'out/gen2_qwen7b_v7hyb_v4_r2', H/'out/oracle_v7hyb', H/'out/oracle_v7hyb_witness'
tasks, rows = ob.load_run(RUN)
R = {(r['task'], r['arm'], r['sample']): r for r in rows if r['split'] == 'dev'}
T = sorted({k[0] for k in R})


def norm(c):
    try:
        return ast.unparse(ast.parse(c, mode='eval').body)
    except SyntaxError:
        return None


wit = {t: [c for c in dict.fromkeys(norm(c) for c in tasks[t]['tool_inputs']) if c] for t in T}
OUT.mkdir(parents=True, exist_ok=True)
for f in ('ref_responses.json', 'b1_responses.json', 'post_responses.json'):
    if not (OUT/f).exists():
        shutil.copy(ORACLE/f, OUT/f)
calls_old = json.loads((ORACLE/'calls.json').read_text())
calls = {str(t): list(dict.fromkeys(calls_old.get(str(t), []) + wit[t])) for t in T}
(OUT/'calls.json').write_text(json.dumps(calls))
ex = ob.execute(RUN, OUT, 12)
jd = ob.judges(ex, RUN, ORACLE, use_llm=False)   # cached judge answers only; witness-only calls have none


def calls_of(r):
    e = tasks[r['task']]['entry']
    return list(dict.fromkeys(c for c in (ob.call_of(a['src'], e) for a in r['asserts']) if c))


def outcome(t, c, o):
    """1 = bug revealed (oracle emits, reference-correct, PUT wrong), -1 = false alarm, 0 = nothing."""
    rec = ex.get(str(t), {}).get('calls', {}).get(c)
    if rec is None:
        return 0
    emit, cok, pok = ob.decide(o, rec, jd.get((str(t), c)), None, None)
    if not emit:
        return 0
    if cok and rec.get('valid', True):
        return 1 if not pok else 0
    return -1


def det(t, cs, o):
    return int(any(outcome(t, c, o) == 1 for c in cs))


def sign(w, l):
    n = w + l; k = min(w, l)
    return min(1, 2*sum(comb(n, i) for i in range(k+1))/2**n) if n else 1


def cmp(x, y):
    w = sum(x[t] > y[t] for t in T); l = sum(x[t] < y[t] for t in T)
    return f'{w}/{l} p={sign(w, l):.3f}'


res = {}
missing = sum(str(t) not in ex for t in T)
lines = [f'v7 dev: {len(T)} tasks, K=3 (witness-only is deterministic: same score for each sample); '
         f'tasks without oracle execution: {missing}']
for o in ('ref', 'full'):
    W, TI, TIW, TIA, CH, PH = ({t: 0 for t in T} for _ in range(6))
    n = dict(w=0, ti=0, ch=0, ph=0); fa = dict(w=0, ti=0, ch=0, ph=0)
    for t in T:
        w = wit[t]
        for s in range(3):
            ti, ch, ph = calls_of(R[t, 'toolinput', s]), calls_of(R[t, 'concept-hybrid', s]), calls_of(R[t, 'plain-hybrid', s])
            W[t] += det(t, w, o); TI[t] += det(t, ti, o); CH[t] += det(t, ch, o); PH[t] += det(t, ph, o)
            TIW[t] += det(t, [c for c in ti if c in w], o); TIA[t] += det(t, [c for c in ti if c not in w], o)
            for k, cs in (('w', w), ('ti', ti), ('ch', ch), ('ph', ph)):
                n[k] += len(cs); fa[k] += sum(outcome(t, c, o) == -1 for c in cs)
    d = lambda x: sum(x.values())/3
    m = 3*len(T)
    res[o] = dict(witness_only=d(W), toolinput=d(TI), toolinput_on_witness_calls=d(TIW), toolinput_on_added_calls=d(TIA),
                  concept_hybrid=d(CH), plain_hybrid=d(PH), calls_per_sample={k: n[k]/m for k in n},
                  false_alarms_per_sample={k: fa[k]/m for k in fa},
                  sign={'toolinput_vs_witness': cmp(TI, W), 'concept_hybrid_vs_witness': cmp(CH, W),
                        'plain_hybrid_vs_witness': cmp(PH, W), 'concept_hybrid_vs_toolinput': cmp(CH, TI)})
    lines += [f'[{o}] bugs/run: witness-only {d(W):.1f} | toolinput {d(TI):.1f} (on witness calls {d(TIW):.1f}, '
              f'on LLM-added calls {d(TIA):.1f}) | concept-hybrid {d(CH):.1f} | plain-hybrid {d(PH):.1f}',
              f'   calls/sample: ' + ', '.join(f'{k} {v/m:.1f}' for k, v in n.items())
              + ' | false alarms/sample: ' + ', '.join(f'{k} {v/m:.2f}' for k, v in fa.items()),
              f'   per task (wins/losses): ' + ', '.join(f'{k} {v}' for k, v in res[o]['sign'].items())]
print('\n'.join(lines))
(H/'analysis/witness_only.txt').write_text('\n'.join(lines) + '\n')
(H/'analysis/witness_only.json').write_text(json.dumps(res, indent=1))
