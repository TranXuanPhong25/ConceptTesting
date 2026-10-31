# LLM-Based Invariant Testing for Software Functional Bugs

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: X.

Paper/record: [LLM-Based Invariant Testing for Software Functional Bugs](https://arxiv.org/abs/2607.18711)

Year/venue: 2026 ISSRE

Dataset: C/C++ libraries + historical bugs; not Defects4J/BugsInPy

Input setting: library APIs + LLM invariants

Model: Not audited

Artifact: https://github.com/SecurityLab-UCD/CNTG

License: Not verified

Concept hook (research judgment): Invariant discovery và validity controls useful concept prior work.

Limitation: Không thuộc requested benchmark; không tính là exact-dataset base.

Local reproduction: **not performed**. No author source modified.


## Full-text and artifact audit — 2026-10-15

Đã đọc toàn bộ arXiv v1 (14,691 words, gồm Appendix A–E). Lisa là C/C++ library functional-bug detection: feedback-guided API-sequence generation + documentation/Daikon-grounded chunk invariants. Lisa-Bench 7 libraries; 25 historical bugs trên 5 libs, 12 phát hiện (48%) vs CITYWALK 3 và OSS-Fuzz 2. Dataset hoàn toàn khác Defects4J/BugsInPy/SWT; TECO-derived 500 prefixes used for oracle metrics, mutation-valid N=362.

Full author Zenodo artifact `21357436` (latest version of concept DOI `19238006`) contains 18,134 entries, DCAware source, MIT LICENSE, data, prompts, Docker/PIT evaluator and cached results; CC BY 4.0 record. ZIP manifest inspected by HTTP Range only (1.26GB compressed/1.69GB expanded; not fully downloaded/extracted); 500 DCAware outputs/model present. GitHub CNTG is invariant-generation component, CGNTG is PromptFuzz component. Model setup Qwen3-Coder-30B-A3B-Instruct-FP8 (vLLM/A100 40GB) or GPT-5-mini/Azure; paper says $0.87 total for 500 GPT requests. No code run/API calls.

Very high oracle-concept relevance, but test prefix/current code are given (regression-oracle completion), not issue-to-reproduction; must distinguish. Candidate invariant violations are developer-confirmed high-confidence reports, not proofs. Full reproduction is conditional on toolchain and hardware/API. See `audit/reviews/034.json` and `public_evidence/source-audit.json`.
