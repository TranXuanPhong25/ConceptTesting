---
name: v82-deepinfra-quarter
description: Fresh full28/2arm/K1 DeepInfra attempt terminal before a paired task;2responses/3pool429s,$.00453354 known,$.01941660 reserved
metadata:
  type: project
---

2026-10-27 (Codex): User requests full28 HumanEval, two arms/K1 after v81 partial.
V82 fresh outputs on same fixed random cohort, no v81 output splicing, DeepInfra/fp8,
output cap32768, new cap$3.47684946 after preserving old v81 known/reserves.
Terminal before any paired task:5 physical attempts,2 received,3 upstream shared-pool
429. Known bill$.00453354, unresolved reserve$.01941660. No efficacy result.
See [report](../trickcatcher_linefacts/analysis/v82_deepinfra_quarter/RESULTS.md).

**How to apply:** shared-pool throttling is provider availability, not model failure.
For a full attempt, prereg and separately reserve a fresh protocol/cap/provider;
do not reuse previous incomplete responses or count 429s as known-free.
