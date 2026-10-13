# CHANGELOG v7_mutref (copy of v7)

Change vs v7: hint selection (rank 2). `pick()` replaced by a frozen logistic rule LR[noref+mutref]
(config.json `hint_rank`): every fact kind competes; features include covered site, boundary, crash, and the mutref
signal (mutant agrees with the majority of spec-only ref programs while the PUT does not).
Files: facts.py, hint_rank.py, refs.py, run.py, paths.py, config.json, v4_evaluation.py, verify.py, test_mutref.py.

- 5ecf6a1: folder created; offline reproduces odd-task good@3 37/35 (was 25 with the v7 rule).
- 1b67d00: v4_evaluation.py scores an assertion whose input raises MemoryError as a crash on both programs (task 87)
  instead of killing the task sandbox. Evaluate run with a 3600 s sandbox timeout wrapper
  (analysis/mutref_eval_longtimeout.py; task 83).
- Status: GPU run stopped at oracle-score (judge needs --online; endpoint down). Resume with
  out/runlogs_mutref/chain_from_score.sh. Primary analysis registered in PREREG "v7_mutref" (odd tasks).
