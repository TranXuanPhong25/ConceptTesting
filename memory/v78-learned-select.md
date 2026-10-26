---
name: v78-learned-select
description: 2026-10-26 cached-only grouped learned selection NO-GO; context18 vs random18.25/prior20.5, spec-only21 equals context-free; 33 PUTs/24 problems, $0 API
metadata:
  type: project
---

User authorizes direction1 ("làm cái 1 đi"), 2026-10-26. Registered/reviewed CPU diagnostic completed using frozen v47 menus and existing v41/v47 execution/reference caches. Read [report](../trickcatcher_linefacts/analysis/v78_learned_select/RESULTS.md), [protocol](../trickcatcher_linefacts/analysis/v78_learned_select/PREREG.md), and [saved outputs](../trickcatcher_linefacts/analysis/v78_learned_select/RESULTS.json).

Primary spec+code context selector18 vs random18.25, context-removed19, training-only subtype prior20.5. Secondary spec-only21 equals both context-removed and subtype prior on every PUT's reach. Registered NO-GO; no useful contextual benefit demonstrated. Exact boundary-tie expectations avoid arbitrary ordering. Primary uses ~10% more distinct inputs than random, with only +0.43 reach above its cost-conditioned random control. No tuning/data expansion/paid follow-up.

Important correction: 33 VibePass PUTs are **24 exact-specification problem groups**, not 33 independent problems. Initial run stopped before labels at duplicate-spec guard; prospective amendment plus fresh review then grouped holdout, balanced weights and bootstrap. Always exclude every PUT variant of a held-out specification; v44/v47 are overlapping cohorts, not independent training data. Full details and all earlier artifacts preserved.

**Why:** oracle upper bounds and beating a weak LLM picker do not establish learnable, context-dependent concept value. **How to apply:** do not repeat this feature/menu/estimator package or escalate model/data to salvage it. This result does not rule out all training or evaluate CASCADE online learning. 0 API calls/$0 API, 0 new program execution, no GPU; 11 synthetic tests and historical metric replay passed.
