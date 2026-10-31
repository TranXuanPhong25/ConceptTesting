# Reproduction Test Generation for Java SWE Issues

Reviewed: 2026-10-15. Full text and public benchmark/evaluator verified. Grade: B for own-model evaluation; exact paper-method reproduction is conditional.

Paper: [arXiv:2605.04320 v2](https://arxiv.org/abs/2605.04320), 7 May 2026; CC BY 4.0.

TDD-Bench-Java has 250 issue-conditioned Java tasks from 13 repositories and tests the fail-before-fix / pass-after-fix oracle. SWT-Bench and TDD-Bench-Verified are related Python benchmarks; Defects4J is related work, not an experiment dataset. A second 150-issue IBM dataset is private.

Public artifact: [IBM/TDD-Bench-Verified](https://github.com/IBM/TDD-Bench-Verified/tree/3df8be066e486789d0b8e0d2865a3a4422b4560f/TDD-Bench-Java), Apache-2.0. The public CSV has 250 rows and matches all 250 IDs; all rows include issue text, base commit, code/test patches, test command and Dockerfile metadata. Java setup pins SWE-PolyBench commit `1963184`, applies `tdd_java.diff`, then uses Docker evaluation on model prediction JSON patches.

This is the strongest practical candidate so far for evaluating a local model on Java issue-to-reproducing-test generation. It does not reproduce the authors' e-Otter++ pipeline: the paper explicitly says generator code is proprietary. The paper reports Claude-Sonnet-4.5 and GPT-5.2, with 43.6% and 46.4% F2P; exact API revisions are not pinned. There is no root-cause taxonomy. No source or model was run.

Detailed verdict: `audit/reviews/098.json`; source evidence: `public_evidence/source_audit.md`.
