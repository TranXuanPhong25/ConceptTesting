---
name: check-version-tree-before-proposing
description: User rule 2026-10-20 — before proposing or building any new direction, compare it against the version tree (v7…v35) and say what is already tried
metadata:
  type: feedback
---

Before proposing, planning or implementing a new direction/variant, check it against the existing version tree
(artifact https://claude.ai/artifact/7a6yvf5bhiVmZVyt9UvTC8, `trickcatcher_linefacts/PIPELINES.md`, pipelines/*/CHANGELOG.md,
the memory index). State explicitly: which earlier version already tried the same core idea, its result, and what is
genuinely new. If the core idea was tried and failed, say so before spending effort or budget.

**Why:** v31–v35 (fault-type mutant concepts + templates) turned out to repeat v7's MUTANT line fact (and v7_mutref
ranking); the overlap was not flagged when the user proposed it, so a paid run re-found a known small, n.s. effect.
User (2026-10-20): "thế pipeline này khác gì với v7, v11 thế" → "có lưu, thành rule trong memory đi".
**How to apply:** every new idea gets a one-line "prior art in this repo" check (v-number, result) in the first reply
and in the plan/PREREG. Related: [[signal-not-more-data]], [[v34-ftplacebo]], [[version-tree-diagram]].
