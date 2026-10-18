# Luna vs Qwen chain probes — 2026-10-18

User-authorized fresh gpt-6-luna subagents with no parent history, one response per packet,6 attempts. Exact saved Qwen system/user messages verified byte-content-equivalent; no Qwen answers/evaluator labels supplied to agents. Frozen parent source/generation verified, same v22 alias expansion/validators applied without repair.

| Probe | Qwen prior | Luna | Qualitative observation |
|---|---|---|---|
| S2 any/even | Reject: local_id | Valid | Describes any/even, uses B1 and actual N references |
| S2 dedup/sort | Reject: items_cap | Valid | Sorted distinct output summarized in one behavior |
| S2 early length exit | Reject: local_id | Valid | Describes len>2 early False and else sum<=limit |
| S3 correct sum | Reject: empty_ok | Valid abstain | Consistent relation; no spurious hypothesis |
| S3 extra length guard | Reject: status | Valid mismatch | Divergence requires len(xs)>2 AND sum(xs)<=limit |
| S3 undefined suitable | Reject: status | Valid unknown | Explicitly keeps undefined eligibility unresolved |

Mechanical validity: Luna6/6 vs prior Qwen0/6 on these targeted failures. No content retries, output repairs, new Qwen/GPU/API calls, native execution/generation or D_IO. Six independent agents requested model gpt-6-luna. Token/cost accounting unavailable through this subagent harness; do not infer zero cost.

The S3 mismatch condition is more precise than Qwen replay, which only named len>2. Luna also distinguishes uncertainty from a confirmed mismatch in the ambiguous spec. These observations support a model-capability contribution to the bottleneck: the existing prompt/contract is executable by a stronger model on these packets. They do not clear all prompt/interface design problems.

Limits: failure-targeted6 seen cases, one sample, no cap/decoding/temperature/reasoning-budget equivalence, agent wrapper/tool context differs from bare Qwen endpoint. No strict causal model isolation, generalization/accuracy benchmark, full16 end-to-end comparison, S4/S5 quality or matched-budget concept gain established. Qualitative semantic judgments are provisional, not human gate certification.

Operational implication: test a stronger model over the full frozen chain before spending further effort tuning Qwen7B prompts. This probe alone does not authorize a new full experiment or paid fallback.
