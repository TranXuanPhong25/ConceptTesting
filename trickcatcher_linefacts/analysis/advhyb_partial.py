"""Provisional advdoc-hybrid scoring without the one unfinished sample (endpoint died 23:05)."""
import json, shutil, sys
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts.evalmitigate import run_advhyb as A
from trickcatcher_linefacts import evaluate as evaluator, oracle_b01, v4_runtime
src = H/'out/gen2_qwen7b_advhyb_v4'; run = H/'out/gen2_qwen7b_advhyb_v4_partial'; ora = H/'out/oracle_advhyb_partial'
step = sys.argv[1]
if step == 'gen':
    run.mkdir(exist_ok=True)
    for f in ('tasks.json', 'manifest.json'): shutil.copy(src/f, run/f)
    bundle = json.loads((src/'tasks.json').read_text()); k = json.loads((src/'manifest.json').read_text())['k']
    rows, missing = [], []
    for t in bundle['tasks']:
        for s in range(k):
            for a in A.ARMS:
                p = src/'artifacts'/str(t['task'])/str(s)/a/'result.json'
                if p.exists(): rows.append(json.loads(p.read_text()))
                else: missing.append((t['task'], s, a))
    (run/'gen.jsonl').write_text(''.join(json.dumps(A.scrub(r), ensure_ascii=False)+'\n' for r in rows))
    print('rows', len(rows), 'missing', missing)
elif step == 'eval':
    m = json.loads((run/'manifest.json').read_text())
    evaluator.evaluate(run/'tasks.json', run/'gen.jsonl', run/'eval.jsonl', python=v4_runtime.interpreter(m['python']))
elif step == 'oracle':
    (ora/'cache').mkdir(parents=True, exist_ok=True)
    for f in A.ORACLE_CACHE.glob('*.json'):
        if not (ora/'cache'/f.name).exists(): shutil.copy(f, ora/'cache'/f.name)
    oracle_b01.collect(run, ora)
    oracle_b01.llm(run, ora, workers=16, stages=('ref', 'post'))
    oracle_b01.score(run, ora, workers=12, use_llm=False)
