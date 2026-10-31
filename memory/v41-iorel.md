---
name: v41-iorel
description: v41 2026-10-21 observed I/O relations (Hypothesis sampling + metamorphic minorities) CPU ceiling — no-go (C2 11/33, lift 0.38) but sampling alone reaches bugs in 22/33
metadata:
  type: project
---

2026-10-21 (Claude): `trickcatcher_linefacts/analysis/v41_iorel/` (PREREG + amendment, iorel.py, RESULTS.md).
User wanted relations the model cannot get by reading code; chosen: PUT input→output relations measured by
execution (metamorphic transforms of Hypothesis samples), minority categories as anomalies. Two independent Opus
review passes before the run (user rule: review impl for practicality / tricky code / library use / plan adherence).

- C1 22/33 (sampling reaches a bug-revealing input; template pool 17, plain Qwen3.5 19), C2 11/33 vs random-k 8.94,
  median lift 0.38, 8/22 C1 tasks with no relation → **no-go**. Strong enrichment only in 87/124/161/141.
- Lesson: input reachability is solvable by cheap sampling; the binding problem is recognising which executed input is
  wrong (oracle/selection). Review caught a package-size bug and a missing random-k baseline that would have favoured GO.

**Why:** closes the "observed relation selects bug inputs" idea on VibePass. **How to apply:** next concept work should
target oracle/selection over a sampled pool, not input reach; reuse iorel.py sampling (frozen Hypothesis constants,
in_domain filter, official re-check). Related: [[v36-llm-localize]], [[v34-ftplacebo]], [[signal-not-more-data]].
