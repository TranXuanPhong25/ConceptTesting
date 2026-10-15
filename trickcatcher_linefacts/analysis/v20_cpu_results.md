# v20 CPU mechanism and independent audit — 2026-10-15

User requested plan → subagent audit → implementation. Plan was written before two independent read-only reviews; all must-fix resolutions were recorded before code. Both reviewers rechecked later corrections. See PLAN_GROUNDED_FLOW_V20.md and v20_plan_review.md.

## Scope

Initial active family is multiplicity only. Tool checks an explicit candidate count relation, links the original argument to an exact set-call source ID, records before/committed per-value losses, follows an approved transparent collection transport to return, and checks that the same eligible value has the same count loss in the final output. Source activation is operation-specific, not a line hit. Native/instrumented signatures include post-input and alias information. Candidate model truth, causality and independent bug confirmation remain separate.

No symbolic execution, complete FSM, general branch/loop reasoning, arbitrary90-day predicates or automatic spec entailment. Unsupported source/alias/provenance gets an abstention; no coverage threshold.

## Independent audit history

| Version | Authored fixture expectations | Independent/integration disposition |
|---|---:|---|
| v20_groundedflow | 21/21 | failed_semantic_audit |
| v20_groundedflow_checked | 28/28 | failed_cycle_audit |
| v20_groundedflow_bounded | 32/32 | failed_size_audit |
| v20_groundedflow_strict | 33/33 | failed_validator_integration |
| v20_groundedflow_domainfix | 35/35 | accepted_cpu_increment_with_limited_scope |

Passing finite fixtures did not override reviewer counterexamples. Lambda lexical scope, builtin entry shadowing, concrete argument provenance, wrong eligible-value losses, masked return flows, cyclic definitions and oversized AST failure were corrected in new copies. All earlier source/protocol/results preserved. cpu_v4 inventory found a validator invocation bug despite fixture success; cpu_v5 adds accepted/rejected validator integration cases and corrects only the calling convention.

## Final CPU evidence

-14 static/helper tests and35/35 authored fixture expectations pass. Both reviewers accept the narrow CPU inventory only.
-All20 known dev tasks retained; source subset supports1/20 (task149, already a known design example).19 explicitly unsupported; do not call this unseen validation.
-Task149:12 worker results/native signature checks;3 inputs have a complete candidate count-loss chain,0 reviewed-grounded real-task instances. All confirmed_bug fields remain null.
-No model requests, canonical/reference execution, GPU or D_IO. Costs are CPU-only; inventory PUT upper bound24, plus38 original/instrumented fixture executions. Inventory elapsed time is measured per task; total engineering/review/test time is not.

Example evidence:

Task 149 input `(['aa', 'b', 'aa'],)`

```json
{
  "bindings": [
    {
      "operation": "Call:18:23:18:31",
      "occurrence": 1,
      "requirement": "eligible_multiplicity",
      "matched_losses": [
        {
          "value_type": "str",
          "value": "aa",
          "before_count": 2,
          "after_count": 1
        }
      ],
      "kind": "observed_required_value_loss_transported_to_return"
    }
  ],
  "relation": {
    "domain": true,
    "holds": false,
    "violations": [
      {
        "value": "aa",
        "expected_count": 2,
        "actual_count": 1
      }
    ],
    "trigger": true,
    "relation": "eligible occurrence counts only; no invented full output"
  },
  "requirement_review_status": "unreviewed",
  "confirmed_bug": null
}
```

## Remaining work

The mechanism now has checkable operation-to-output evidence for a deliberately narrow direct-input collection subset. Real-task requirement remains an unreviewed v18 proposal; original-argument identity excludes derived collections, conditions/loops are unsupported, and a matching count-loss association does not prove a unique cause. Next changes need a new audited scope: review normative obligations independently, then extend selected branch/loop semantics with their own negative cases. Do not start a generation comparison merely because these fixtures pass. Any GPU pilot needs its own frozen protocol and fair shared-discovery controls.
