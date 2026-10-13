"""oracle-score for pipelines/v11_fair without the B4 judge (PREREG dev sanity run amendment 1: ref only).
    python -B trickcatcher_linefacts/analysis/v11_score_refonly.py [dataset]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from trickcatcher_linefacts.pipelines.v11_fair import paths
ds = sys.argv[1] if len(sys.argv) > 1 else 'humaneval'
paths.set_dataset(ds)
from trickcatcher_linefacts.pipelines.v11_fair import oracle_b01 as ob
from trickcatcher_linefacts.pipelines.v11_fair.run import Layout
L = Layout(ds)
ob.score(L.generation, L.oracle, workers=12, use_llm=False)
