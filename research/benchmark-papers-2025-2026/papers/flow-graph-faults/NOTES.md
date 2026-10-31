# An Anatomy of 488 Faults from Defects4J Based on the Control- and Data-Flow Graph Representations of Programs

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: A.

Paper/record: [An Anatomy of 488 Faults from Defects4J Based on the Control- and Data-Flow Graph Representations of Programs](https://arxiv.org/abs/2502.02299)

Year/venue: 2025 EASE; preprint title: Flow Graph-Based Classification of Defects4J Faults

Dataset: Defects4J; 488 faults / 7 projects

Input setting: post-hoc inspection of buggy/fixed code and failing tests

Model: No LLM required

Artifact: https://github.com/alexvdspuy/fcd4j

License: MIT

Concept hook (research judgment): 8 control/data-flow classes làm annotation framework để đánh giá generalization theo fault class.

Limitation: Artifact chủ yếu là manual classifications + query Makefile, không phải automatic concept extraction hoặc test generator. Đây là support paper.

Local reproduction: **not performed**. No author source modified.

## Full-text audit 2026-10-15

See ../../audit/reviews/006.json for primary-source evidence. Verdict: conditional. No author-model reproduction performed.
