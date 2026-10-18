---
name: v26-proporacle
description: v26 2026-10-18 — concept as executable property/metamorphic oracle vs exact expected (Qwen 7B); negative, properties 17–19% unsound
metadata:
  type: project
---

2026-10-18 (Claude): `pipelines/v26_proporacle/` (copy of v21_flowtools), plan `trickcatcher_linefacts/PLAN_PROPERTY_ORACLE.md`,
report `trickcatcher_linefacts/analysis/v26_proporacle_results.md`. Fixed 12-input pools, 4 oracles, 1 call each.

- pilot20 precision: exact_spec 0.213, exact_code 0.197, property 0.148, metamorphic 0.179; tasks confirmed 8/8/6/4.
- diag16 precision: 0.473 / 0.429 / 0.307 / 0.225.
- 17–19% of model properties fail on the reference output → more false alarms. Consensus exact∧property is the
  most precise but halves recall.
- Format lesson: Qwen returns bare JSON arrays for array-only schemas; wrap identically for all arms.

**Why:** follow-up to [[linefacts-v21-flowtools]] (oracle bottleneck). **How to apply:** executable-property oracle
from a 7B model is not the fix; oracle precision ~0.2 on pilot20 is the open problem.
