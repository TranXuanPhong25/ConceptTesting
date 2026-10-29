---
name: v83-reka-quarter
description: Two-arm HumanEval quarter run on Reka after DeepInfra pool failures
metadata:
  type: experiment
---

2026-10-27 v83 terminal partial: 2 arms (`concept-hybrid`, `concept-hybrid-ft`), K=1, frozen 28-task cohort; 26 paired tasks completed, 2 not completed. Stop reason was one unknown-accounting attempt (`missing_done`); 175 physical attempts, 166 received responses, 8 explicit 429s, 1 unknown. Known V83 bill $0.68198775; unresolved reserve $0.0642930; cumulative hard cap remained $4.20. No retry after unknown and terminal partial cannot resume per frozen PREREG_V83.

Post-freeze CPU scoring recovered from saved outputs. The scorer omitted tasks with no parseable assertions/calls; task 3 had no assertions in either arm. Representing such tasks as empty oracle-call maps yields descriptive partial results: o0 4 wins/4 losses/18 ties (FT FP9 vs control6); reference/full 3/4/19 (FT FP2 vs control0). Efficacy rule not evaluated. No paid scoring calls. See `trickcatcher_linefacts/analysis/v83_reka_fullquarter/RESULTS_V83.md` and frozen run `trickcatcher_linefacts/pipelines/v83_reka_fullquarter/out/reka_quarter_final2`.
