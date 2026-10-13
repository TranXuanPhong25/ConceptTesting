# Analysis scripts (CPU only; read run/oracle outputs under out/, which is gitignored)

| Script | RESULTS | What it does |
|---|---|---|
| advhyb_partial.py, advhyb_paired.py | §11.23 | provisional advdoc-hybrid scoring (797/798 samples) and per-task comparisons |
| build.py, worker.py, analyze.py, examples.py, wins.json | §11.24 | why concept-hybrid beats advdoc-hybrid: PUT vs canonical on every generated input (input vs oracle split) |
| v7_vs_toolinput.py | §11.25 | v7 concept-hybrid vs toolinput: raw, matched test count, unions |
| round2_split.py | §11.26 | what round 2 adds: Hypothesis-selected inputs vs Qwen's self-added tests |
| v8_compare.py | §11.27 | v8-strict comparisons (../v8_strict_est.py builds the run) |

build.py / analyze.py / examples.py were run from a scratch dir (W = job tmp); set W to this folder to rerun.
