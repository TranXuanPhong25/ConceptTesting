"""v8-strict (CPU construction from the v7 run): round 2 adds exactly the selected Hypothesis inputs, nothing else.

  python3 -B trickcatcher_linefacts/v8_strict_est.py build     # out/gen2_qwen7b_v8strict_est/gen.jsonl
  python3 -B trickcatcher_linefacts/v8_strict_est.py eval      # eval.jsonl (rebuilt arms evaluated; others copied)
  QWEN_BASE_URL=<cached only> python3 -B trickcatcher_linefacts/v8_strict_est.py oracle   # out/oracle_v8strict_est
Exact for ref/full (they ignore the written expected value); o0 of the rebuilt arms is not meaningful.
"""
import json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts import evaluate as evaluator, oracle_b01 as ob, v4_runtime

SRC, SRC_ORACLE = HERE/'out/gen2_qwen7b_v7hyb_v4_r2', HERE/'out/oracle_v7hyb'
RUN, ORACLE = HERE/'out/gen2_qwen7b_v8strict_est', HERE/'out/oracle_v8strict_est'
REBUILT = ('concept-hybrid', 'plain-hybrid', 'placebo-hybrid')


def strict(row, entry):
    r1 = list(row['round1_assertions'])
    added = [a for a in row['assertions'] if a not in set(r1)]
    by_call = {}
    for a in added:
        c = ob.call_of(a, entry)
        if c and c not in by_call: by_call[c] = a
    seen = {ob.call_of(a, entry) for a in r1}
    out, placeholders = list(r1), 0
    for s in row['selected_inputs']:
        c = s['call']
        if c in seen: continue
        seen.add(c)
        if c in by_call: out.append(by_call[c])
        else: out.append(f'assert {c} == None'); placeholders += 1
    return out, placeholders


def build():
    RUN.mkdir(exist_ok=True)
    for f in ('tasks.json', 'manifest.json'): shutil.copy(SRC/f, RUN/f)
    tasks = {t['task']: t for t in json.loads((SRC/'tasks.json').read_text())['tasks']}
    rows, stats = [], {a: [0, 0, 0, 0] for a in REBUILT}
    for line in open(SRC/'gen.jsonl'):
        r = json.loads(line)
        if r['arm'] in REBUILT:
            new, ph = strict(r, tasks[r['task']]['entry'])
            st = stats[r['arm']]; st[0] += 1; st[1] += len(r['assertions']) - len(new); st[2] += len(new) - len(r['round1_assertions']); st[3] += ph
            r = dict(r, assertions=new, n_assertions=len(new), text='```python\n' + '\n'.join(new) + '\n```', v8_strict=True)
        rows.append(r)
    (RUN/'gen.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    for a, (n, dropped, kept, ph) in stats.items():
        print(f'{a}: {n} samples; dropped {dropped/n:.1f} self-added assertions/sample; kept {kept/n:.2f} selected inputs/sample ({ph} placeholders)')


def evaluate():
    m = json.loads((RUN/'manifest.json').read_text())
    sub = RUN/'rebuilt'; sub.mkdir(exist_ok=True)
    shutil.copy(RUN/'tasks.json', sub/'tasks.json')
    (sub/'gen.jsonl').write_text(''.join(l for l in open(RUN/'gen.jsonl') if json.loads(l)['arm'] in REBUILT))
    evaluator.evaluate(sub/'tasks.json', sub/'gen.jsonl', sub/'eval.jsonl', python=v4_runtime.interpreter(m['python']))
    kept = [l for l in open(SRC/'eval.jsonl') if json.loads(l)['arm'] not in REBUILT]
    (RUN/'eval.jsonl').write_text(''.join(kept) + open(sub/'eval.jsonl').read())


def oracle():
    (ORACLE/'cache').mkdir(parents=True, exist_ok=True)
    for f in (SRC_ORACLE/'cache').glob('*.json'):
        if not (ORACLE/'cache'/f.name).exists(): shutil.copy(f, ORACLE/'cache'/f.name)
    ob.collect(RUN, ORACLE)
    ob.llm(RUN, ORACLE, workers=16, stages=('ref', 'post'))
    ob.score(RUN, ORACLE, workers=12, use_llm=False)


if __name__ == '__main__':
    dict(build=build, eval=evaluate, oracle=oracle)[sys.argv[1]]()
