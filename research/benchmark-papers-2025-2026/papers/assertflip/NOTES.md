# AssertFlip: Reproducing Bugs via Inversion of LLM-Generated Passing Tests

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: A.

Paper/record: [AssertFlip: Reproducing Bugs via Inversion of LLM-Generated Passing Tests](https://arxiv.org/abs/2507.17542)

Year/venue: 2026 ICSE; preprint 2025

Dataset: SWT-Bench

Input setting: buggy repo + issue; generate passing test then invert assertion

Model: GPT-4o (original setting)

Artifact: https://github.com/uw-swag/AssertFlip

License: Apache-2.0

Concept hook (research judgment): Concept hướng assertion inversion và failure alignment.

Limitation: Docker repo evaluation + repeated generation tăng chi phí. Required context và retries phải matched across arms.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T10:38:47.071723+07:00

Strong SWT-Bench public code/data candidate, conditional on Azure API and Agentless localization; first choice for reproducible bug-reproduction workflow if exact model route is available. Report generation coverage/abstentions separately from conditional success.

Blockers: Noauthor inference/evaluator run; Closed Azure GPT4o accessneeded to regenerate;Azure deployment name notversion pin; Code defaultmodel/temperature aligns,but article usesconfiguration/state time-sensitive;model API updates/data leakage October2023 cutoff concern; Verified denominator433 but system intentionally generates326 issues;claimed43.6% all-instance vs58% amonggenerated;compare conditionalcoverage/abstentionbaselinefairly; UsesAgentless localizations external input;realistic vsperfect localization changes resolved issue sets; Per-instance cost~$1 at10 regen, not free; No initialstart-to-finish run;some cached datasets/output andprojectsetup Docker prebuiltimage versusreconstructcost

Sources: https://arxiv.org/html/2507.17542v2, https://github.com/uw-swag/AssertFlip/tree/a5cd61992e0791b6a167549b1e2eca13627eed3f, https://swtbench.com/
