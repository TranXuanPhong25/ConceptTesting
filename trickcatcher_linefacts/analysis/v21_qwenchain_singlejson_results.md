# Qwen chain single-output-shape adaptation — 2026-10-16

Separate exploratory prompt-only adaptation after first pilot format failures. Same16 fixtures/validators/caps/gates. Source and generation snapshot verified by pilot.report. No response repair, pooled score, real20 or D_IO.

| Stage | Valid | Failed | Blocked | N/A |
|---|---:|---:|---:|---:|
| S1 | 13 | 3 | 0 | 0 |
| S2 | 3 | 13 | 0 | 0 |
| S3 | 3 | 0 | 13 | 0 |
| S4 | 0 | 0 | 13 | 3 |
| S5 | 0 | 0 | 13 | 3 |

Costs: {"scheduled_slots": 80, "physical_completion_attempts": 35, "received_completions": 35, "input_tokens": 33290, "output_tokens": 6412, "unknown_usage_attempts": 0, "tokenizer_metadata_calls": 35, "tokenizer_metadata_errors": 0}.

Mechanical gates: {"required_slots": 62, "optional_attempted_slots": 0, "valid_required_or_requested": 19, "stage_validity": 0.3064516129032258, "stage_validity_passed": false, "probe_parseable": 0, "probe_admissible": 0, "probe_required": 7, "probe_parseable_passed": false, "probe_admissible_passed": false}.

## Earliest failures

- S1: quote_mismatch = 3.
- S2: guard = 13.

Prediction checks: []. Unique native executions: {}.

## Interpretation limits

S1 full-spec quote and span were supplied in the prompt: passing these verifies provenance transport, not independent clause extraction/entailment. S4 includes the concrete format seed ([1,1],); 0 proposal slots copied that tuple, so these do not demonstrate novel discriminator discovery. Output predictions describe candidate runtime behavior; a native match does not establish specification correctness. Semantic accuracy remains unadjudicated; the independent human12/16 gate is pending. Operation-value observations remain unknown.

Post-run audit identified a prompt/validator contract gap: the prompt permits empty strings where needed, while S2 requires nonempty guard/effect. For unconditional code an empty guard is natural, so this rejection is not evidence of misunderstood flow. S3 condition/alternative and S5 condition have related latent gaps. The preflight review and74 offline checks missed this live negative case. Frozen rejections are retained.

Qualitative independent review: f02 describes sorted(set(xs)) as sorted unique output; f04 distinguishes spec >=limit from implementation >limit in raw claims. Both S2 replies are rejected for an empty guard, so these plausible descriptions do not reach alignment. Conversely f13 passes S1/S2/S3 but overclaims consistency: suitable is undefined in the spec, S1 leaves ambiguity empty and S3 treats first-element behavior as correct based on the empty-list example. A mechanically valid abstention is not a justified semantic conclusion.

All three valid S3 artifacts abstain (f11/f12/f13). f12 exposes a semantic alignment miss: S2 correctly describes len(xs)>2 returning False, whereas the spec explicitly allows any length; S3 nevertheless says no clear mismatch. The preregistered evaluator marks f12 probe-applicable. This is a qualitative missed mismatch, not a measured D_IO score. f11 is the corresponding correct implementation; f13 remains ambiguous.

Failed response samples and valid S3 claims are preserved in the JSON report for review. No further prompt changes or generation continuation are implied by this report.
