# CHANGELOG v7 (base pipeline)

- 10f991c (2026-10-13): self-contained copy of the v7 pipeline (B5 preconditions + v4c Hypothesis strategies, v6 code
  facts, spec input-class facts, 7 arms, v4 evaluation, B1/ref/full oracle, optional strict construction).
  Verified: bundles equal, 0 cache misses, report reproduced (EQUIVALENCE.md).
- Status: current best on dev (v8-strict construction: concept-hybrid 61.0 vs plain-hybrid 55.7, per task 29/20 n.s.).
  Base for every new copy. Never edited in place.
