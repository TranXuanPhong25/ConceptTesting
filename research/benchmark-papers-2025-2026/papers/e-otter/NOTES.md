# Heterogeneous Prompting and Execution Feedback for SWE Issue Test Generation and Selection

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Heterogeneous Prompting and Execution Feedback for SWE Issue Test Generation and Selection](https://arxiv.org/abs/2508.06365)

Year/venue: 2025 arXiv; earlier title Execution-Feedback Driven Test Generation from SWE Issues

Dataset: SWT-Bench Lite + TDD-Bench Verified

Input setting: heterogeneous prompts + execution feedback + candidate patch validation

Model: GPT-4o, Claude 3.7 Sonnet

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Failure alignment/candidate diversity controls; related SWT baseline.

Limitation: No exact usable artifact verified. TDD harness và SWT harness cho scores khác nhau; không gộp hai benchmarks.

Local reproduction: **not performed**. No author source modified.


## Full-text and artifact audit — 2026-10-15

Đã đọc toàn bộ arXiv v3 (11,665 words; §§1–8, RQ1–RQ6, threats, discussion và references). Paper proposes Otter candidate generation → execution-augmented repair (critic + retrieved code, tối đa 10 lần) → heterogeneous prompts (5 masks + 5 issue morphs) → rule-based selection trên 5 normalized Agentless surrogate patches. Dataset TDD-Bench Verified 449, SWT-Bench Lite 276, SWE-rebench subset 267. Headline: 63.0% Claude / 51.4% GPT-4o trên TDD; 52.5% Claude / 40.2% GPT-4o trên SWT Lite. Estimated costs $2.75/$1.80 per instance (Claude/GPT-4o) incl. Agentless patches.

Data Availability links [Zenodo record 18169083](https://zenodo.org/records/18169083), CC BY 4.0. Metadata has 10 large run ZIPs, four result JSONs, supplementary material. Downloaded/MD5 verified supplementary zip and GPT-4o TDD/SWT prediction JSONs. TDD file has 449 unique rows (match); SWT file has 272 vs 276 paper denominator (4 missing). IBM/TDD-Bench-Verified repo is public with benchmark harness/license and prior Otter predictions, not e-Otter++ implementation. No custom e-Otter/e-Otter++ source found in linked record; run outputs/logs public, method source is not.

Exact re-run needs closed-model APIs plus Otter/Agentless pipeline and surrogate patch artifacts; no API or source executed. Verdict: partial artifact / conditional reproduction. High related-work fit for execution feedback, test selection and oracle reliability, but do not reimplement without user authorization. See `audit/reviews/026.json` and `public_evidence/source-audit.json`.
