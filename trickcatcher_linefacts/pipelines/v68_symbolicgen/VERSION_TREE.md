# Version relationship

```text
v7 (best packaged baseline)
└── v57_pathfault (new isolated copy; engineering only)
    ├── v31 fixed-transform module ported unchanged as legacy control
    ├── exact AST hypotheses + optional explicit semantic writer interface
    ├── joint Z3 path/infection/propagation construction
    └── network-isolated replay + equal-evidence prompt export
```

Historical mechanism lineage: v31 → v34 placebo → v35 fixed-pool ceiling.
V31 still reports 18 vs15 confirmed tasks on its original33 PUT cohort; v34 fails its FA gate.
V57 addresses the one-edit input pool and absent joint path solving; it does not change those historical scores.

Status: CPU engineering and independent review; no new benchmark score or promoted best pipeline.
Trade-off: richer jointly constrained inputs, explicit bounded Python support and solver cost; independent spec oracle still required.
Library: Z3 for constraint solving. No paper implementation or benchmark result was borrowed.
