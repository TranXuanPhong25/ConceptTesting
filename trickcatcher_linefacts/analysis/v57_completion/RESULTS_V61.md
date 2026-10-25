# v61 terminal pilot audit — 2026-10-25

The registered six-case ngrok pilot and post-freeze scoring completed. **The concept treatment did not instantiate:** all 18 writer hypotheses were rejected, leaving no constructed inputs, supplied concept witnesses, or final hypothesis-realization checks. This is a failed writer-to-tool interface in the tested implementation; these scores cannot establish whether executable concepts help testing.

## Lifecycle and integrity

- Generation: `out/pipelines/v61_pathfault_integrated/pilot6_20261025/generation_v2/` (relative to `trickcatcher_linefacts/`). All 108 physical slots completed, all six case results exist.
- Independent scoring: `analysis/v57_completion/out_integrated_v61_reviewed/score.json`; supervisor exited successfully. One tokenizer connection timeout was resumed from checkpoints; no duplicate chat attempts were needed.
- Read-only reviewer `v57_review` independently verified all 775 frozen artifacts, readiness approval/source/config/request/author-prompt identities, scorer/worker/core provenance, and 209 worker-result receipts. No mismatches. The audit made no model calls and executed no PUT/reference programs.
- Generation freeze SHA256: `5fb20d6d9eef77c623a566f588ece8377abed7a85c34b8a6186ca3f46d1b6c1a`.
- Score SHA256: `3f3d91474d2cd03d1a2e2047290c0e1b5fcca02984e1e20c49658257ac722bc9`.
- Evaluation manifest SHA256: `5d740ff037d1f575f3140747b44fc44e24dc4b4d8f4d39f230aa6589b4288f31`.
- Observer queued this terminal check once and exited. Both generation controllers, supervisor, and observer are no longer active. No follow-on run was launched.

## Five-arm scores

Each arm has 36 raw final slots, including malformed and absent slots. A confirmed label requires a valid input that exposes a PUT/reference discrepancy with the correct expected output under the reviewed scorer. False alarms and revealing inputs with wrong expected outputs are separate categories.

| Arm | Confirmed cases / 6 | Confirmed slots | Passing | Revealing input, wrong expected | False alarm | Invalid input | Unresolved parse/absent |
|---|---:|---:|---:|---:|---:|---:|---:|
| Plain | 0 | 0 | 23 | 5 | 2 | 0 | 6 |
| Explicit pattern | 1 | 1 | 7 | 12 | 10 | 6 | 0 |
| Concept | 0 | 0 | 21 | 5 | 2 | 2 | 6 |
| Equal-evidence raw | 0 | 0 | 26 | 4 | 6 | 0 | 0 |
| Inputs-only | 0 | 0 | 26 | 4 | 4 | 2 | 0 |

The sole confirmed label is explicit-pattern case131, problem3696, final slot5. Six PUTs cover only five distinct problems: cases61 and66 share problem3701. At problem level, explicit pattern detects1/5 and other arms0/5. Concept has zero paired wins against every control and one paired loss against explicit pattern. This small, previously examined dev cohort is not a held-out effectiveness evaluation.

Plain's six unresolved slots are case58: `expected` was a JSON number instead of the required Python-literal string. Concept's six unresolved slots are case66: the final completion reached the token limit. Neither output is retrospectively normalized or recovered for these metrics. There are no duplicate/conflicting-expected annotations in the scored slots.

The scorer retains `provisional=true` and `review_required=true`: evaluator implementation and artifact integrity were reviewed, but this audit did not independently re-adjudicate every private reference/validity judgment. Report the labels with this qualification. The explicit-pattern arm uses the author's prompt with the documented common-JSON adaptation; it is not trained UTGen.

## Writer admission and actual mechanism execution

All six writer completions parsed as JSON and each proposed three hypotheses. First rejection reasons were **11 `spec_quote_binding` and 7 `hypothesis_priority`**. These are first-failure counts, not mutually exclusive underlying defects:

- All18 priorities are strings (`high`, `medium`, `low`), while admission requires integers0–3.
- All18 triggers and all18 event predicates are strings, while the tool requires nested predicate dictionaries.
- The writer prompt names operators but omits their precise field schema and examples, and omits the integer priority range. That is an implementation/interface deficiency; it was not caught by the prior code-readiness review or authored transport fixtures.
- Fourteen of18 proposals have identical `required_relation` and `observed_relation` strings; twelve supply no alternative. Therefore a mechanical serialization repair would not itself establish meaningful fault hypotheses or semantic correctness.

Every case has0 admitted hypotheses,0 construction records,0 candidate inputs,0 construction native executions, and0 final realization checks. Concept/raw evidence arrays and the supplied inputs-only witness pools are empty. Native construction and compositional predicates therefore received no actual model hypothesis in this run. The final audit had nothing to verify; this is not evidence that final inputs satisfied a concept.

Generation still used ordinary PUT probe feedback:402 feedback entries,287 normal observations and115 `ValueError:branch_cap` errors. The branch cap is an instrumentation limit, not a demonstrated program defect. This restricts the useful feedback available to every arm. The score's19 `public_witness_only` entries are the original supplied public examples, all labeled passing; they are not newly constructed fault witnesses.

## Usage and errors

| Component | Received chat completions | Input tokens | Output tokens |
|---|---:|---:|---:|
| Shared writer | 6 | 30,551 | 2,264 |
| Plain | 24 | 75,505 | 8,282 |
| Explicit pattern | 24 | 87,658 | 12,878 |
| Concept generation | 18 | 54,048 | 6,818 |
| Equal-evidence raw generation | 18 | 54,273 | 4,189 |
| Inputs-only generation | 18 | 54,522 | 4,552 |
| **Fresh pilot total** | **108** | **356,557** | **38,983** |

Total395,540 tokens;102 completions finished with `stop`,6 with `length`. The six truncated slots are61/pattern/plan,66/plain/probe1,66/plain/probe2,66/concept/probe2,66/concept/final,131/pattern/plan. All108 dispatched chat attempts have received-result receipts; no unknown chat usage in this run. Tokenizer preflight matches actual input-token usage108/108. The earlier tokenizer timeout consumed no recorded chat dispatch.

The shared writer is physically charged once and logically allocated to each concept/raw/inputs package. Plain/pattern receive four useful calls per case; other arms receive one shared writer plus three generation calls. This matches logical calls, not token counts or successful semantic work.

Archived instrumentation trial `generation/` is separate: two received completions,7,751 input+525 output tokens; three further saved slot records failed context preflight without a chat dispatch. Earlier progress notes described an interrupted unknown attempt; the terminal receipts now establish both archived attempts were received. Combined trial+fresh pilot:110 received completions and403,816 known tokens. The trial is not included in the five-arm comparison.

## Decision

Do not promote v61 or interpret its zero concept score as a test of the concept idea. The integrated workflow reached terminal scoring, but its writer contract prevented the intended mechanism from running. A future isolated revision would first need an explicit writer schema and a model-facing admission diagnostic, plus a deliberate policy for trace-cap feedback and literal serialization. Such a revision has not been run, and no frozen output has been repaired retrospectively.
