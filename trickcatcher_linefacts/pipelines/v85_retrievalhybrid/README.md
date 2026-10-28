# V85 retrieval-hybrid

New child of v11_fair, replacing concept selection and wording with v2 compact
retrieval while preserving the hybrid generation and spec-program oracle.

Current status:RUNNING. User restored endpoint; comparison_live_1 launched
2026-10-28 09:46UTC,PID51658,exact Qwen27B/context8192 preflight passed. First
checkpoint:6prepared tasks,31received preprocessing responses,0transport errors.
No efficacy result yet.27CPUtests passed;226current source/input hashes verified.
The initial08:36UTC HTTP404/zero-completion receipt remains preserved.

The treatment retrieves up to three cards from public buggy source, binds each
card to a measured v11 target at its source span when possible, and retains that
target's executable gate. A fallback measures only source-line reachability;
it never claims to verify the semantic bug mechanism. This is a package change,
not merely renaming v11 facts or adding card text to the standalone v2 runner.

The paired run uses all113 HumanEval dev PUTs, K1, Qwen3.5-27B-AWQ and fresh shared
B5 validity/domain preparation. Baseline: original v11 concept-hybrid. Treatment:
retrieval-hybrid. Both have8-call/20-assertion caps, strict round2, and the same
10spec-only generated oracle programs per task. Primary score uses v11 ref
consensus (at least3base-passing programs and unanimous successful outputs);
o0 is secondary. Target references/contracts are loaded only in final scoring.

Run from repository root after sourcing the private endpoint environment:

```sh
/tmp/pytoy-v84-venv/bin/python -m unittest trickcatcher_linefacts.pipelines.v85_retrievalhybrid.test_fair trickcatcher_linefacts.pipelines.v85_retrievalhybrid.test_retrievalhybrid
/tmp/pytoy-v84-venv/bin/python -m trickcatcher_linefacts.pipelines.v85_retrievalhybrid.prepare_comparison
/tmp/pytoy-v84-venv/bin/python -m trickcatcher_linefacts.pipelines.v85_retrievalhybrid.comparison
```

Preparation and controller each refuse a duplicate launch. Actual experiment
status now lives in `out/humaneval/comparison_contextfit_1/STATUS.json`; do not infer completion
from this README. Final output is `RESULTS.json` plus per-task scored records.
A full comparison needs up to3503completion attempts; these include shared
preparation and oracle work. Transport never retries. Algorithmic strategy
correction remains bounded by v11's original two-attempt rule.

Mac workers use sandbox-exec with network denied and a clean environment, wall
timeouts and a sampled3GiB process-group RSS cap. Linux keeps unshare/RLIMIT_AS.
Existing v11 sources and the frozen standalone v2 result are untouched.

See [registration](PREREG_V85.md), [changes](CHANGELOG.md), [parent hashes](PARENT.json).

The initial output root and live_1 are terminal and must not be reset. The original
live_1 controller used the frozen code and public inputs with this root override:

```python
from trickcatcher_linefacts.pipelines.v85_retrievalhybrid import comparison
comparison.ROOT = comparison.DATA_OUT / 'comparison_live_1'
comparison.main()
```

This original run is terminal; do not launch it again. Endpoint is supplied
only through the private environment. The registered3503attempt budget includes
all live_1 calls; the earlier404preflight used zero completions.

Version-number correction before any completion: remote main already contains
`v84_reka_completion`, discovered during push. This retrieval package is renamed
to v85; algorithm, cohort, seeds and budgets are unchanged. Initial v84-named
source snapshot is preserved in commit7bf6d3c and PREFLIGHT_FREEZE_V84.json;
its zero-completion HTTP404 receipt is retained. The existing dedicated venv
keeps its original temporary path; no environment/tool versions changed.

2026-10-28 10:38UTC: live_1 stopped on task125 strategy-correction context overflow
(4964input+4096output>8192), with113prepared/6paired tasks and509received calls.
No oracle/grading result. Original outputs stay frozen. The amended continuation
[v85_contextfit](../v85_contextfit/README.md) reuses verified checkpoints and runs
under `out/humaneval/comparison_contextfit_1`; inspect its status instead.
