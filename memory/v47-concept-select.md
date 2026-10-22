---
name: v47-concept-select
description: 2026-10-22 v47 LLM concept-instance selection from tool menus: no-go (picks below random); spec_range/value_biased add 2 tasks
metadata:
  type: project
---

v47 (`trickcatcher_linefacts/analysis/v47_concept_select/`): Qwen2.5-Coder-32B picks 3 of a frozen menu of concept
instances (class, boundary, spec_range, value_biased, coverage, mutation). covered@3 spec+code 16 / spec-only 15 vs
random3 18.25 / 17.96, first3 18, perfect menu 23 / 22 → registered **no-go**. Kind-matched random ≈ model, so the
LLM neither picks the right instance within a kind nor the right kind. Part A (exploratory): new methods reach only
tasks 56 and 89; 10 of 11 v44-unreachable tasks stay unreachable (union6 23, c1 23).

**Why:** v44 suggested concept accuracy is the lever; v47 shows this LLM cannot supply that accuracy from menus.
**How to apply:** do not re-propose "LLM selects among tool concepts" without a new information source; see
[[v44-concept-matrix]], [[signal-not-more-data]], [[check-version-tree-before-proposing]].
