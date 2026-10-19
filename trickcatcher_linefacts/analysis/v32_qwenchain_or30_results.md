# Qwen3.5 OpenRouter30dev feasibility — 2026-10-19

State: complete. Frozen source verified; generation snapshot verified=True. Exact model qwen/qwen3.5-35b-a3b, same v22 prompts/validators; larger visible caps, reasoning requested disabled.30fixed dev tasks, seed20261019. Real secret env only sourced; never read/printed.

| Stage | Valid | Failed | Blocked | Other |
|---|---:|---:|---:|---:|
| S1 | 29 | 1 | 0 | 0 |
| S2 | 28 | 2 | 0 | 0 |
| S3 | 7 | 20 | 3 | 0 |
| S4 | 3 | 0 | 23 | 4 |
| S5 | 0 | 3 | 23 | 4 |

Costs: {"calls": 93, "received": 93, "unknown": 0, "input_tokens": 276850, "output_tokens": 44330, "cost_usd": 0.051242750000000004, "reserved_unknown_usd": 0}. Reasoning tokens=0.

Interface failures: [{"stage": "S3", "error": "status", "count": 5}, {"stage": "S3", "error": "comparison_coverage", "count": 2}, {"stage": "S3", "error": "empty_ok", "count": 11}, {"stage": "S5", "error": "local_id", "count": 1}, {"stage": "S2", "error": "source_refs", "count": 1}, {"stage": "S2", "error": "local_id", "count": 1}, {"stage": "S5", "error": "unknown_reference_alias", "count": 2}, {"stage": "S3", "error": "unique_json_object_required", "count": 1}, {"stage": "S1", "error": "quote_mismatch", "count": 1}, {"stage": "S3", "error": "comparison_terminal_status", "count": 1}].

Accepted selected-concept tasks=3; tasks with any parsed inputs=3; tasks with final proposals=0. Proposals={"S4": 18}. Native inputs={"unique": 18, "ok": 16, "native_checked": 17, "filtered": 1, "exception": 1}. S5 decisions={}. S4 prediction checks={"observed_contradiction": 10, "observed_match": 7, "unverified": 1}.

Post-generation canonical comparison: any-stage discrepancy tasks=3/30; final-S5 discrepancy tasks=0/30. Canonical normal native result and matched admissible inputs required for decisive comparison; all unresolved cases remain explicit. This is conditional on mined-filter/spec-domain validity, not a certified semantic success score.

Qualitative examples: task58 requires sorted common elements but code returns set iteration order; ([10,2,5],[5,2,10]) produces [2,10,5] vs canonical [2,5,10]. Task137 compares normalized numeric strings lexicographically: ("10","2") returns "2" vs canonical "10". Task79 adds a0..255 bound absent from the described conversion domain:256 raises ValueError while canonical returns db100000000db. These selected cases are promising candidate reasoning/input evidence; no aggregate semantic accuracy is inferred.

No baseline arms or human semantic adjudication in this small feasibility run. No claim concepts improve over plain/toolinput/placebo; no causal model comparison with earlier runs. Dev tasks have prior exposure; not held-out. Schema-valid claims can still be wrong, and invalid raw claims remain rejected rather than repaired. No model/spend expansion or retry is implied. Detailed raw rejects/claims and task-level IO evidence in JSON.
