# AnyPoC: Universal Proof-of-Concept Test Generation for Scalable LLM-Based Bug Detection

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [AnyPoC: Universal Proof-of-Concept Test Generation for Scalable LLM-Based Bug Detection](https://doi.org/10.48550/arxiv.2604.11950)

Year/venue: 2026 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W7154526831

Discovery query: Defects4J; keyword hit is not dataset-use verification.


## Full paper and author-source audit — 2026-10-15 (#40)

Read full arXiv v2 (9,990 words). AnyPoC turns candidate bug reports into executable PoCs. Its analyzer checks mechanism, trigger, consequence and oracle; a generator iterates with execution traces/project knowledge; a separate checker reruns in a fresh workspace. It spans logic, robustness and security bugs across large systems, not only vulnerabilities. Paper reports 121 new bugs over 12 projects (108 confirmed, 92 fixed; 46 PoCs adopted) and a 192-report balanced evaluation.

The first author’s public repo `zzjas/anypoc` is Apache-2.0 and implements a related current CLI. It cites the paper but now advertises 130+ findings; no paper-version tag is present. The 192-report corpus, raw traces/results and table-reproduction runner were not found. Paper uses Claude Code/Opus and Codex/GPT-5 Codex, at $5.02/$2.61 per report. Strong conceptual fit, but exact paper metrics are not reproducible from current package without the frozen data. No run/API call.
