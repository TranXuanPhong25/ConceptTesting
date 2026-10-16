# Qwen chain controlled16 pilot — 2026-10-16

Actual Qwen endpoint run, not canned offline fixtures. Frozen source/generation verified by pilot.report. No prompts/validators/budgets repaired after first completion. Human semantic labels remain unadjudicated; no real20/canonical/ref/D_IO.

| Stage | Valid | Failed | Blocked | N/A |
|---|---:|---:|---:|---:|
| S1 | 0 | 16 | 0 | 0 |
| S2 | 0 | 16 | 0 | 0 |
| S3 | 0 | 0 | 16 | 0 |
| S4 | 0 | 0 | 16 | 0 |
| S5 | 0 | 0 | 16 | 0 |

Costs: {"scheduled_slots": 80, "physical_completion_attempts": 32, "received_completions": 32, "input_tokens": 35169, "output_tokens": 11946, "unknown_usage_attempts": 0, "tokenizer_metadata_calls": 32, "tokenizer_metadata_errors": 0}.

Mechanical gates: {"required_slots": 62, "optional_attempted_slots": 0, "valid_required_or_requested": 0, "stage_validity": 0.0, "stage_validity_passed": false, "probe_parseable": 0, "probe_admissible": 0, "probe_required": 7, "probe_parseable_passed": false, "probe_admissible_passed": false}.

## Observed interface failure forms

- S1: bare_item_missing_envelope = 12.
- S1: copied_contract_description = 4.
- S2: copied_contract_description = 16.

These are output-interface failures, not scores for semantic extraction/alignment. A bare obligation/behavior may contain substantive statements but has not passed the frozen envelope/quote/reference checks. Copying the contract/meta-schema shows ambiguity in the prompt interface; offline parser checks did not establish that Qwen would follow it. Blocked downstream stages cannot measure hypothesis/discriminator quality. Raw responses, alias maps where parsed, stage errors and model usage are preserved.

Next proposed change, if separately registered: simplify each stage prompt to one unambiguous JSON schema/response shape and validate the output interface on a fresh version before interpreting semantic accuracy. Do not silently wrap or extract exact_shape from these scored responses. A JSON-guided decoding interface could constrain syntax while leaving semantic claims open, but must be checked against the actual server and independently registered.
