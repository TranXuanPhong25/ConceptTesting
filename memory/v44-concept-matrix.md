---
name: v44-concept-matrix
description: v44 2026-10-21 concept taxonomy × tool method matrix (class/boundary/MR/property/coverage/mutants) CPU — no-go (union 21 vs random 21.4); 11 tasks unreachable by any method
metadata:
  type: project
---

2026-10-21 (Claude): `trickcatcher_linefacts/analysis/v44_concept_matrix/` (renumbered from v42; v42_mutoracle /
v43 are parallel work, mutant outcomes reused from v42_mutoracle). User diagnosis: missing tool-method coverage and
concept accuracy/taxonomy. Two Opus review passes caught an oracle-favouring baseline and by-construction precision.

- Input kinds, best instance by reference: class 20, boundary 14, coverage 9, mutants 19; each ≈ matched random by
  reach; union 21 vs 21.36 → **no-go**. Perfect pick vs random instance: class 20 vs 10, boundary 14 vs 6.6.
- Oracle kinds mined from PUT: MR 145/260 accurate, property 50/66, thousands of false-alarm inputs; accurate ones flag
  bugs in 1–3 tasks.
- 11/33 tasks unreachable by every method (6, 39, 48, 56, 58, 69, 70, 73, 74, 168, 171).

**Why:** generic tool methods partition inputs but do not concentrate bugs; generic relations are not what these bugs
violate. **How to apply:** do not add more generic kinds; next work must target the 11 unreachable tasks' input
structures or task-specific (spec-derived) concepts, and measure concept accuracy first. Related: [[v41-iorel]],
[[signal-not-more-data]], [[check-version-tree-before-proposing]].
