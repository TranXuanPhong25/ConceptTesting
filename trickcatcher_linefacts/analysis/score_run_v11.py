"""Score any single-arm run dir (baseline gen.jsonl + tasks.json) with the v11_fair evaluator and oracle.

Same ref programs as the v11_fair run: its oracle cache is copied in first (PREREG "Dev sanity run").
    python -B trickcatcher_linefacts/analysis/score_run_v11.py <run_dir> [--online]
"""
import shutil, sys
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts.pipelines.v11_fair import evaluate, oracle_b01 as ob, v4_runtime, paths
from trickcatcher_linefacts.pipelines.v11_fair.llm_client import Client

D = Path(sys.argv[1]).resolve(); online = '--online' in sys.argv
V11_CACHE = H/'pipelines/v11_fair/out/humaneval/oracle/cache'
ob.Client = lambda directory, **kw: Client(directory, offline=not online, model=paths.CONFIG['model'], **kw)
if not (D/'eval.jsonl').exists():
    evaluate.evaluate(D/'tasks.json', D/'gen.jsonl', D/'eval.jsonl', v4_runtime.interpreter(None))
O = D/'oracle'; (O/'cache').mkdir(parents=True, exist_ok=True)
for f in V11_CACHE.glob('*.json'):
    if not (O/'cache'/f.name).exists(): shutil.copy(f, O/'cache'/f.name)
ob.collect(D, O)
ob.llm(D, O, workers=12, stages=('ref',))   # PREREG dev sanity run amendment 1: ref only
ob.score(D, O, workers=12, use_llm=False)
