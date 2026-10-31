# TestExplora: Benchmarking LLMs for Proactive Bug Discovery via Repository-Level Test Generation

Reviewed: 2026-10-15. Evidence: full text and official author source verified. Grade: C (conditional).

Paper: [arXiv:2602.10471 v2](https://arxiv.org/abs/2602.10471), 2026.

Dataset: TestExplora 1,552 PRs / 2,389 tasks / 482 Python repositories; TestExplora-Lite 330 PRs / 517 samples. SWT-Bench and TDD-Bench are comparators only. No Defects4J or BugsInPy experiment.

Task: proactive documentation-oracle test generation for hidden PR-linked defects; tests should pass after PR and fail before. White box, black box and repository-exploring agent modes. It is behavior-focused but does not produce a validated root-cause taxonomy.

Author artifact: [Microsoft/TestExplora](https://github.com/microsoft/TestExplora), explicitly linked by paper and README. Public MIT implementation at `11e6952261f58d3ceb9f4d2571e03aa35dad9523`; generation, local vLLM calling, Docker evaluator and benchmark construction scripts are present. Paper is CC BY-NC-ND 4.0; dataset license is not separately verified.

Reproduction is conditional: public repo lacks task JSONs, generated patches and result cache; README requires a user-supplied JSON without a download link; default subset selection reads an absolute author-local path. Public Qwen wrapper says Qwen2.5-Coder-32B while paper reports Qwen3-Coder-30B-A3B. Resolve the benchmark data and model identity before an exact run. No source execution or model/API call.

Full verdict and detailed evidence: `audit/reviews/063.json`; source inspection notes: `public_evidence/source_audit.md`.
