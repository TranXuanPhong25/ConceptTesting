---
name: v68-symbolicgen
description: v57 4-arm Qwen protocol + v66 CrossHair evidence + spec-validity judge: NOT PROMISING (concept 1 = plain 1 = raw 1 > inputs_only 0 /6); oracle copies PUT output
metadata:
  type: project
---

2026-10-25 (Claude), user said "có" to running v66 evidence in the v57 protocol. [RESULTS_V68](../trickcatcher_linefacts/pipelines/v68_symbolicgen/RESULTS_V68.md).
Reused v57 generation_v2 writer (6) + plain (18) slots (identity-checked by Sonnet review); 59 new ngrok slots, 223,993 tokens.
Endpoint switched mid-run at user request (new URL only in scratchpad env file; one in-flight slot charged unknown, retried).

Tasks confirmed /6: concept 1, plain 1, raw 1, inputs_only 0 — all only case 85 (spec route). Concept lowered attack rate .16 vs .34.
Evidence: contract-valid but bug-revealing only on 131 (3 inputs); concept/inputs_only reused 2 shown witnesses but copied the displayed
PUT output as expected → input_discrepancy. Catalogue edit ≠ real fix (alternative output also wrong). Validity judge good except 124.

**Why:** tests whether completing v57's construction (v66 PASS 5/6) yields concept gain.
**How to apply:** do not enlarge this run (signal-not-more-data). Bottlenecks are fault-hypothesis relevance and oracle (model trusts
PUT observation), not input construction. Related: [[v66-symbolicpath]], [[v57-pathfault]], [[v41-iorel]], [[v48-v49-e2e-defn]], [[signal-not-more-data]].
