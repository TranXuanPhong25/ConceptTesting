# Beyond Fail-to-Pass: Iterative Hardening of Co-Generated Bug Reproduction Tests and Fixes

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [Beyond Fail-to-Pass: Iterative Hardening of Co-Generated Bug Reproduction Tests and Fixes](https://doi.org/10.48550/arxiv.2607.19843)

Year/venue: 2026 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W7170139577

Discovery query: SWT-Bench; keyword hit is not dataset-use verification.


## Full-text/public-source audit — 2026-10-15

Read the full 15,387-word paper including Appendices A–D. CoHarden exposes an important weakness in F→P-only evaluation: a Lax test may accept both a correct fix and plausible-but-wrong patch, whereas a Rigorous test constrains repair. Their MPE study finds +8.5 pp Resolved from injected Rigorous tests, 0.0 pp from Lax, and −3.6 pp from Misaligned. CoHarden generates a symptom witness before any fix, then hardens test+fix against semantic mutation patches using a Temporal Matrix. On 433 tasks in SWE-bench Verified ∩ SWT-Bench Verified it reaches 69.4% Resolved / 78.9% F→P vs OpenHands+Cogen 61.4% / 72.7%; Lite intersection is 276. GPT-5-mini main cost $0.84/instance; GPT-5.4 $6.69 and Opus 4.5 $18.07. Very high relevance to oracle rigor/root-cause constraints.

Artifact check: official [project page](https://yhtan777.github.io/CoHarden-project-page/) has a disabled GitHub button labelled “Code under review”; no source, result bundle or stable snapshot available. Exact reproduction is currently not feasible, and no implementation/API run was done. See `audit/reviews/049.json` and `public_evidence/source-audit.json`.
