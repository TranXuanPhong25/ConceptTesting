# Agentic Bug Reproduction for Effective Automated Program Repair at Google

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [Agentic Bug Reproduction for Effective Automated Program Repair at Google](https://doi.org/10.48550/arxiv.2502.01821)

Year/venue: 2025 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W4407184967

Discovery query: Defects4J, SWT-Bench; keyword hit is not dataset-use verification.


## Full-text/public-source audit — 2026-10-15

Read all 10,291 extracted words of arXiv v2. This is a direct BRT-generation paper, but it evaluates 80 private Google GITS bugs, not Defects4J/SWT-Bench (those are related work only). BRT Agent gets issue + buggy file, uses internal Google code search/Bazel, and edits test files via Gemini fine-tuned on Google code; plausible BRT is checked against an internal ground-truth fix/oracle. Candidate/plausible rates are 85%/28% vs adapted LIBRO 41%/10%. On 23 selected cases, Passerine gets 17 plausible fixes with BRT vs 13 without, but paper says this is an upper bound because generated tests were selected for plausibility using the known ground-truth fix. No public implementation/data or exact model IDs were found; code, data, main fine-tuned model and APR environment are proprietary. Therefore not reproducible; use as a task/evaluation comparator, not a runnable baseline. It discusses root-cause value but offers no explicit root-cause taxonomy. Review: `audit/reviews/046.json`.
