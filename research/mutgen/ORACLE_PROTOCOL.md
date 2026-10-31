# MUTGEN: oracle assumptions and comparison scope

Source audit: 2026-10-12. No paper reimplementation or experimental run.

Primary source: Guancheng Wang, Qinghua Xu, Lionel Briand, Kui Liu, [Mutation-Guided Unit Test Generation with a Large Language Model, arXiv:2506.02954v8](https://arxiv.org/html/2506.02954v8), revised 2026-04-15. The v1 title was Towards More Effective Fault Detection in LLM-Based Unit Test Generation; the oracle assumption is present in both versions.

- Sections II-C–II-F describe code summarization, mutation-feedback prompting, assertion/compilation repair and iterative generation.
- Section II-F retains successfully executing tests after filtering and fixes.
- Section III-A evaluates 104 HumanEval-Java subjects and 100 Leetcode-Java subjects. The primary metric is mutation score; the original program is the reference against which synthetic mutants are distinguished.
- Section III-C explicitly assumes original code correctness in its Oracle Problem discussion and acknowledges incorrect-oracle risk. It leaves evaluation on Defects4J real-world defects to future work.

Interpretation: this protocol does not establish an independent oracle for unknown bugs already present in the original program. A test can preserve an existing original-program bug while distinguishing additional synthetic mutants. A gain in mutation score consequently does not refute the buggy-input misguidance finding of EvalAndMitigate.

Related primary sources:

- [KITE, arXiv:2607.11573v1](https://arxiv.org/html/2607.11573v1), Section III-A1: all evaluated methods access correct-version code during generation/enhancement; actual historical buggy versions are reserved for final evaluation. Section II-D3 validates tests on the correct method and requires detection of injected defects.
- [EvalAndMitigate, arXiv:2607.22883v1](https://arxiv.org/html/2607.22883v1): studies buggy versus fixed input and classifies misguided tests as buggy-pass/fixed-fail.

These are different generation-time information assumptions. The comparison is about protocol scope, not a claim that the papers' reported empirical results are invalid.
