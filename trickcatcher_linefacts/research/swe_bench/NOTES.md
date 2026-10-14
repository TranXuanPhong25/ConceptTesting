# SWE-bench fit for LineFacts

Reviewed 2026-10-14. Feasibility research only; no benchmark experiment started.

SWE-bench evaluates issue-solving code patches on repositories. Dataset fields include
base_commit, problem_statement, the gold code patch, test_patch, FAIL_TO_PASS and PASS_TO_PASS.
Its standard resolved score measures repair, while LineFacts currently generates tests.

Primary sources:
- [Original paper](https://arxiv.org/abs/2310.06770)
- [Official dataset schema](https://www.swebench.com/SWE-bench/guides/datasets/)
- [Official evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/)

Our assessment: the buggy/fixed repository pairs can support a repository-level external
evaluation, but a test-generation harness and repository adapter are required. Use the
test-generation formulation documented separately in [SWT-Bench](../swt_bench/NOTES.md).

The setting changes: an explicit issue describes a reported defect, whereas current
LineFacts searches for defects from function specification/code/base tests. Keep this
evaluation separate from HumanEval numbers. Issue text is generation input; gold code/test
patches and evaluator-only failure metadata are withheld from generation and retrieval.
Any oracle localization using gold changed files must be labelled as a separate diagnostic.
