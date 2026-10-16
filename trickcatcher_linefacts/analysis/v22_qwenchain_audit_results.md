# Qwen chain contract/alignment diagnostic — 2026-10-16

Separate preregistered v22 adaptation after observing v21. Same16 seen diagnostic fixtures; S3 cap increased1024 to2048. No unseen generalization or matched-budget effect claim. Source/generation snapshot verified. No response repair or automatic real20/D_IO.

| Stage | Valid | Failed | Blocked | N/A |
|---|---:|---:|---:|---:|
| S1 | 16 | 0 | 0 | 0 |
| S2 | 5 | 11 | 0 | 0 |
| S3 | 1 | 4 | 11 | 0 |
| S4 | 1 | 0 | 15 | 0 |
| S5 | 1 | 0 | 15 | 0 |

Costs: {"scheduled_slots": 80, "physical_completion_attempts": 39, "received_completions": 39, "input_tokens": 46603, "output_tokens": 10909, "unknown_usage_attempts": 0, "tokenizer_metadata_calls": 39, "tokenizer_metadata_errors": 0}.

Mechanical gates: {"required_slots": 62, "optional_attempted_slots": 0, "valid_required_or_requested": 24, "stage_validity": 0.3870967741935484, "stage_validity_passed": false, "probe_parseable": 1, "probe_admissible": 1, "probe_required": 7, "probe_parseable_passed": false, "probe_admissible_passed": false}.

## Interface failures

- S2: items_cap = 2.
- S2: local_id = 9.
- S3: comparison_source_refs = 1.
- S3: empty_ok = 2.
- S3: status = 1.

Prediction checks: [{"stage": "S4", "result": "observed_contradiction", "count": 3}, {"stage": "S4", "result": "observed_match", "count": 3}]. Unique native execution statuses: {"ok": 6}.

## Model-authored comparisons

- f06: ok, selected hypotheses=1, verdicts=["mismatch"].

## Limits

Comparison verdicts, obligations and mismatch statements are Qwen claims, not trusted semantic certificates. Tools validate coverage, references and internal consistency only. Whole-spec quote/span supplied in S1 proves provenance transport, not clause-level entailment. Unknown source observation capabilities remain unknown. Native exact-output prediction matches establish runtime behavior on those inputs, not specification correctness. No canonical/reference scoring or D_IO; human semantic12/16 adjudication remains pending. Former duplicate format seed is absent from this version; tuple-copy tracking against the old seed is descriptive only. Raw failures and valid S3 comparisons are saved in JSON.

## Qualitative follow-up

Accepted f06 S3 distinguishes allowed extra container values from exact set equality. S4 supplies6 admissible unique inputs, including required=[1,2],container=[1,2,3], native result False. Three predictions match native outputs and3 contradict; native checks do not supply a trusted spec oracle. S5 marks unknown and emits0 final inputs.

f12 is blocked at S2 local_id, so its original alignment miss was not validated in this end-to-end run. A separate S3-only replay appears in v22_qwenchain_s3replay_results.md and must not be pooled into coverage. No empty-guard or quote-span failures remain. Main failures are N aliases used as behavior IDs, item caps, terminal status structure and source references.
