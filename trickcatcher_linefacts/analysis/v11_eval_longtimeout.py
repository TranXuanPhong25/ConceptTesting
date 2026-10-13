"""Run v11_fair `evaluate` with a 3600 s per-task scoring sandbox instead of 600 s (same as v7_mutref, task 83).
Source files stay unchanged (their hashes are pinned); only the timeout argument of the evaluate sandbox is patched."""
import sys
sys.argv = [sys.argv[0], 'evaluate']
from trickcatcher_linefacts.pipelines.v11_fair import v4_runtime, run
_orig = v4_runtime.isolated
def isolated(mode, job, directory, python=None, timeout=900):
    return _orig(mode, job, directory, python, 3600 if mode == 'evaluate' else timeout)
v4_runtime.isolated = isolated
run.main()
