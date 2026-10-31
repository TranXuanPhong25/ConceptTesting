# TATG: Tracking-Aware Testing Objective for LLM-based Test Generation

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [TATG: Tracking-Aware Testing Objective for LLM-based Test Generation](https://doi.org/10.48550/arxiv.2607.03194)

Year/venue: 2026 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W7167639987

Discovery query: Defects4J; keyword hit is not dataset-use verification.

## Full-text/public-source audit 2026-10-15

Evidence and model/evaluation verdict: [review ledger](../../audit/reviews/044.json). Public source status: not_found. Reproduction feasibility: unknown. No author-code/model reproduction run.


## Full-text/public-source audit correction — 2026-10-15

Read the complete 9,403-word arXiv v1 text. TATG is a high-fit tracked-objective prior: each card contains source evidence, setup, action, oracle form, acceptance predicate, status and de-duplication key; structural objectives precede mutation-guided oracle hardening. Dataset use is verified: 110 KTester methods plus 31 additional fixed-code focal methods. Nine additional methods are from fixed Defects4J project revisions, not historical bug IDs or buggy/fixed pairs. Section IV-D says implementation and benchmark subjects will be released, but provides no repository URL. Checked arXiv source, exact-title public search and first-author GitHub profile/listing; no TATG package or stable source snapshot found. Models are Qwen3.6-35B-A3B via vLLM (temperature 0.2) and DeepSeek-V4-Flash-284B via Fireworks; exact immutable revisions are not pinned. Conclusion: high novelty relevance, not currently reproducible; do not select as a ready benchmark/base until the promised source/manifest appear. See `audit/reviews/044.json`.
