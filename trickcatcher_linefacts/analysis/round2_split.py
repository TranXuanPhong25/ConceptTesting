"""v7 dev, ref: what round 2 adds -- the Hypothesis-selected inputs vs the tests Qwen adds on its own."""
import json, sys
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob
run, out = H/'out/gen2_qwen7b_v7hyb_v4_r2', H/'out/oracle_v7hyb'
tasks, _ = ob.load_run(run); ex = ob.execute(run, out, 12); jd = ob.judges(ex, run, out, use_llm=False)
rows = [json.loads(l) for l in open(run/'gen.jsonl')]
def det(t, cs, o='ref'):
    for c in cs:
        rec = ex[str(t)]['calls'].get(c, {}); emit, cok, pok = ob.decide(o, rec, jd.get((str(t), c)), None, None)
        if emit and cok and not pok and rec.get('valid', True): return 1
    return 0
for arm in ('concept-hybrid', 'plain-hybrid'):
    n = r1d = alld = gain = gain_sel = gain_own = gain_both = nsel = nown = 0
    for r in rows:
        if r['arm'] != arm or r['split'] != 'dev' or str(r['task']) not in ex: continue
        e = tasks[r['task']]['entry']; n += 1
        r1 = [ob.call_of(a, e) for a in r['round1_assertions']]; r1 = [c for c in r1 if c]
        al = [ob.call_of(a, e) for a in r['assertions']]; al = [c for c in al if c]
        sel = {s['call'] for s in r['selected_inputs']}
        added = [c for c in dict.fromkeys(al) if c not in set(r1)]
        s_calls = [c for c in added if c in sel]; o_calls = [c for c in added if c not in sel]
        nsel += len(s_calls); nown += len(o_calls)
        a, b = det(r['task'], r1), det(r['task'], al); r1d += a; alld += b
        if b and not a:
            gain += 1; ds, do = det(r['task'], s_calls), det(r['task'], o_calls)
            gain_sel += ds and not do; gain_own += do and not ds; gain_both += ds and do
    print(f'{arm}: samples {n}; ref bug/run round1 {r1d/3:.1f} -> all {alld/3:.1f} (+{gain/3:.1f}); '
          f'round-2 tests/sample: Hypothesis-selected {nsel/n:.1f}, Qwen own {nown/n:.1f}; '
          f'new detections from selected only {gain_sel/3:.1f}, own only {gain_own/3:.1f}, both {gain_both/3:.1f}')
