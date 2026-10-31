# Can Old Tests Do New Tricks for Resolving SWE Issues?

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [Can Old Tests Do New Tricks for Resolving SWE Issues?](https://doi.org/10.1145/3808148)

Year/venue: 2026 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W4415967336

Discovery query: SWT-Bench; keyword hit is not dataset-use verification.


## Full-text/public-source audit — 2026-10-15

Read the complete 13,000-word arXiv v2 export. TestPrune (artifact name TestLoc) is a strong issue-level test-context/minimization approach: issue→suspicious functions→top-10 test files→coverage mapping→greedy set-cover of regression tests; downstream tests help Otter++ generate F→P BRTs and aid repair/patch selection. The experiments use Python SWE-Bench Lite (300) and Verified (500); TDD-Bench Verified’s harness is used for F→P scoring. SWT-Bench is only related work, and no Defects4J/BugsInPy experiment is reported. The author-linked [IBM artifact](https://github.com/IBM/Issue-Test-Localizer) is public Apache-2.0 and README directly identifies it as the FSE 2026 TestLoc artifact. Pinned HEAD `b9100eb6a4550486a26a07704d2d93560eaf751e`; substantial pipeline, data/results, README and source scripts inspected statically (no execution). It offers an exact-model route with GPT-4o/Claude API and a custom endpoint for separate model evaluation; precomputed outputs are in the repo. One-task quick start is 3–5 minutes; full Verified run ~2 days. Exact reproduction is conditional on Docker/SWE-bench plus paid, still-available model APIs. Main table gives F→P 31.2→34.0 (2.8 percentage points, 9% relative), not +9 pp. Candidate top choice for reproducing/evaluating issue-based test localization and a BRT pipeline add-on; not a root-cause taxonomy and not the user’s exact SWT-Bench/Defects4J/BugsInPy dataset. See `audit/reviews/047.json` and `public_evidence/source-audit.json`.
