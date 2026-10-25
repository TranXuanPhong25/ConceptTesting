---
name: v72-symdiff
description: CrossHair PUT-vs-Haiku-plain-impl differential gate STOP: 0/10 v64-unreachable tasks newly confirmed; solver reproduces 12/33 with ≤5 inputs, adds nothing to v64's 25/33
metadata:
  type: project
---

2026-10-25 (Claude). User approved my proposal after v68 + literature search (misguidance effect ISSTA'26, ConVerTest,
Konstantinou actual-vs-expected). [RESULTS](../trickcatcher_linefacts/analysis/v72_symdiff/RESULTS.md); PREREG 61e0763.
Search venv /tmp/concepttester-v64-venv; export/score venv = 2dddac78…/scratchpad/codex_v4/venv (has `hypothesis`).

Result: 0/10 unreachable newly confirmed (69/70 only FA from common-mode wrong Haiku programs; 171 env missing sortedcontainers);
crosshair pool alone 12/33 (prec .79), union_x = union = 25/33. Score harness needed v64 answers/plain copied into v72 out (S.OUT).

**Why:** test whether solver-directed disagreement with spec-only programs closes v64's reach gap.
**How to apply:** don't propose solver input search again for this dev cohort; remaining misses are search-space size or
common-mode spec programs. Related: [[v64-haiku-plainoracle]], [[v68-symbolicgen]], [[v66-symbolicpath]], [[check-version-tree-before-proposing]].
