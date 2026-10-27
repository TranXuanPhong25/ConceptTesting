# Read-only Qwen implementation review — 2026-10-26

Before task inference, a separate Qwen context reviewed protocol, prompts, parsing
and judge validation. Raw request/response is under `out/engineering_review/`.
It returned a FAIL verdict with the findings below. Findings were assessed
individually rather than accepted mechanically.

| Finding | Disposition |
| --- | --- |
| Reference/witness in the grader constitutes retrieval leakage | Rejected: the grader explicitly needs independent correctness evidence. The retrieval/utility messages never contain reference/witness; those are separate contexts and separate files. Grader evidence does not flow back into retrieval. |
| Lack of a fully formal actual-bug definition makes judge noisy | Accepted limitation: same-model grading is auxiliary; retain frozen-label metrics, native test utility and manual review of examples/conflicts. |
| SHA256-seeded shuffling is not stable between environments | Rejected: SHA256 has a standardized stable output; JSON mapping is also persisted for each exact prompt. Input drift is checked by hashes. |
| Short reason limit may invalidate schema | Not applicable as stated: reason length is a prompt brevity request, not a schema rejection rule. Native/schema completion failures are still reported as failures without retry. |
| Catalog changes could invalidate numeric IDs | Already handled: corpus hash and exact retrieval-job messages are frozen; all IDs resolve against that unchanged corpus. |
| Model may discard useful hints while following the spec | Recorded tradeoff: rejecting inconsistent hints is intended. Use the plain control and measured oracle correctness rather than assuming every hint helps. |
| Witness validity/correctness may be flawed | Retain official-contract native replay, display actual/reference results and grade examples from saved evidence. Judge scores alone cannot establish benefit. |

Additional self-review fixes: failed transport/parse is distinct from intentional
abstention; run verifies code and message freeze; exact score domains and all
judge keys required; consumed response caching prevents retries of unknown calls.

Method identity is masked and candidate order shuffled. Language/style can still
suggest which binding is more specifically instantiated. Therefore card-selection
scores (deduplicated shared cards) and binding-quality scores are reported
separately. Utility receives only the selected card definitions, not v3's extra
instantiation text, so its comparison isolates card selection more closely.

The utility arms match the **test-generation** call budget. V3 additionally pays
one retrieval completion per task; it is not a matched-total-inference pipeline
comparison. Costs/tokens are reported separately. Prior v2 positive labels are
incomplete and do not replace concept-by-concept quality assessment.
