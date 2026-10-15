"""Resume frozen v16 after importing signal-registering modules on the main thread.

No pipeline source/prompt/config edits. Original source hashes are verified before work.
"""
import sys
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
# tracer registers SIGALRM at import. Import before ThreadPoolExecutor creates workers.
from trickcatcher_linefacts.pipelines.v16_behavior_ready import behavior,behavior_experiment

if __name__=='__main__':
    behavior_experiment.verify()
    behavior_experiment.main()
