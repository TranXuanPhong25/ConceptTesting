# GPT-5.6 Luna low: chain vs direct30 — 2026-10-20

State: complete. Source frozen verified; generation verified=True. Requested CLI identity gpt-5.6-luna/low; server identity not independently reported unless event metadata supplies it. Empty ephemeral cwd, execution host disabled, tool schemas may remain exposed. No paid endpoint/env access.

Same30dev tasks as v32, maximum5calls+12unique inputs per arm/task. Direct allocates3/3/2/2/2new-input slots; chain uses S1/S2/S3 then ≤6S4+≤6S5inputs. Actual calls/tokens may differ due upstream abstention/failure. IDs and orchestration status compiled mechanically; semantics remain model-authored.

| Arm | Tasks with inputs | Unique inputs | Tasks with final retained inputs | Selected concept tasks |
|---|---:|---:|---:|---:|
| chain | 9 | 27 | 9 | 9 |
| direct | 30 | 324 | 28 | 0 |

Stage outcomes: {"chain": {"S1": {"valid": 30}, "S2": {"valid": 25, "failed": 5}, "S3": {"valid": 23, "failed": 2, "blocked": 5}, "S4": {"not_applicable": 14, "valid": 9, "blocked": 7}, "S5": {"not_applicable": 14, "valid": 9, "blocked": 7}}, "direct": {"1": {"valid": 29, "failed": 1}, "2": {"valid": 30}, "3": {"valid": 30}, "4": {"valid": 30}, "5": {"valid": 30}}}.

Errors: {"chain": [{"task_id": 57, "stage": "S3", "reason": "comparison_source_refs"}, {"task_id": 68, "stage": "S2", "reason": "source_refs"}, {"task_id": 78, "stage": "S2", "reason": "source_refs"}, {"task_id": 83, "stage": "S2", "reason": "source_refs"}, {"task_id": 130, "stage": "S3", "reason": "comparison_source_refs"}, {"task_id": 135, "stage": "S2", "reason": "behavior_fields"}, {"task_id": 137, "stage": "S2", "reason": "source_refs"}], "direct": [{"task_id": 119, "stage": "1", "reason": "unique_json_object_required"}]}.

Task cost/accounting: {"CLI_invocations": 253, "received": 253, "known_usage_attempts": 253, "unknown_usage_attempts": 0, "input_tokens_known": 2225985, "output_tokens_known": 96074, "forbidden_item_count": 0, "denied_router_attempts": 0, "request_count_scope": "CLI invocations/turns, internal server HTTP retries unobserved"}. By arm: {"chain": {"calls": 103, "received": 103, "input_tokens": 1005737, "output_tokens": 61666, "unknown": 0}, "direct": {"calls": 150, "received": 150, "input_tokens": 1220248, "output_tokens": 34408, "unknown": 0}}. Canary separately: {"CLI_invocations": 1, "received": 1, "known_usage_attempts": 1, "unknown_usage_attempts": 0, "input_tokens_known": 6690, "output_tokens_known": 9, "forbidden_item_count": 0, "denied_router_attempts": 0, "request_count_scope": "CLI invocations/turns, internal server HTTP retries unobserved"}. Actual dollars/internal HTTP retries unobserved.

## Post-generation canonical IO

| Metric | Chain | Direct |
|---|---:|---:|
| Any-stage task detection /30 | 8 | 26 |
| Final-retained task detection /30 | 8 | 21 |
| Random equal-input mean /30 | 8.000 | 8.370 |

Paired outcomes: chain-only=0, direct-only=18. Shared nonempty-input cohort=9/30. Equal-input analysis uses200registered random subsets at per-task minimum counts, zero-count tasks stay in denominator; it is descriptive, not a new generation trial.

Post-hoc equality audit: 10 strict typed-signature differences have equal Python values. These are separately listed and cannot automatically be called semantic bugs; frozen primary scores are unchanged.

Python-value sensitivity (post-hoc): {"scope": "post-hoc Python-value equality sensitivity; frozen typed primary unchanged", "detection": {"chain": 8, "direct": 25}, "final_detection": {"chain": 8, "direct": 21}, "chain_only": 0, "direct_only": 17}. Direct-only losses by chain stage: {"S3_terminal_unknown": 10, "S3:comparison_source_refs": 1, "input_search_no_discriminator": 1, "S3_terminal_abstain": 1, "S2:source_refs": 3, "S2:behavior_fields": 1}.

Remaining interface defect: 6 rejects are due to >12 valid source references (legacy cap not clearly stated in the simplified prompt), not evidence of semantic misunderstanding. Another reject omits required uncertainty fields. Frozen outputs are not repaired. The7blocked tasks could add at most7detections if all were rescued; even that upper bound8+7=15 is below direct25. This bound only addresses those gates, not changes to14terminal decisions.

Recommendation: do not promote this hard-gated five-stage chain as the main method. Direct is stronger under the registered maximum budgets and chain has no unique discoveries. This does not disprove concepts generally; structured reasoning/input prioritization without stopping general generation would be a different method requiring a separate experiment.

Chain S5 decisions: {"keep": 8, "unknown": 2, "revise": 1}. Retention statuses: {"accepted": 23}.

Canonical comparisons require normal verified reference returns and verified candidate execution. Results remain conditional on spec-domain/mined-filter admissibility; unresolved/reference-exception cases are not counted as confirmed differences. No matched actual-token estimate, held-out generalization, human concept-accuracy certification or mechanism-only causal claim. This is a whole-workflow maximum-budget comparison with direct feedback/generation allocated differently. No additional model calls/retries/expansion are implied.
