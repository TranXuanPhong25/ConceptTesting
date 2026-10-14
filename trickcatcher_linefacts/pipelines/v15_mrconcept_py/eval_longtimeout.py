"""Run v13_hyp `evaluate` with a 3600 s per-task scoring sandbox instead of 600 s (as v11_fair amendment 2 and the
v12_rel run). Source files stay unchanged (their hashes are pinned); only the evaluate sandbox timeout is patched.
Usage (repository root, PYTHONPATH=$PWD): python3 -B -m trickcatcher_linefacts.pipelines.v13_hyp.eval_longtimeout"""
import sys
sys.argv = [sys.argv[0], 'evaluate']
from trickcatcher_linefacts.pipelines.v13_hyp import v4_runtime, run
_orig = v4_runtime.isolated


def isolated(mode, job, directory, python=None, timeout=900):
    return _orig(mode, job, directory, python, 3600 if mode == 'evaluate' else timeout)


v4_runtime.isolated = isolated
if __name__ == '__main__':
    run.main()
