# Do Coverage and Mutation Scores of LLM-Generated Test Suites Correlate with Their Effectiveness? (Replicability Study)

Reviewed: 2026-10-15. Full paper read; author source verified. Reproduction verdict: conditional.

Paper: [arXiv:2607.22880](https://arxiv.org/abs/2607.22880), PACMSE/ISSTA 2026, DOI [10.1145/3832093](https://doi.org/10.1145/3832093). Full HTML article (13,276 words) was read; text SHA-256 `d8c3e54703c453ed79ed1eeb830d4c6e6166329143c6bf1611c99c4c31712453`.

The study directly uses 318 buggy focal methods from all 17 Defects4J v3 projects, with fixed versions as the oracle. It generates 8,268 test suites / 101,123 test cases with 11 LLMs (13 configurations), then examines coverage, PIT mutation scores and real bug detection pooled, within-model and across-model, with and without size controls. BugsInPy appears only in related work; it is not used experimentally. No root-cause labels or taxonomy are provided.

Main result relevant to our evaluation: coverage and mutation sometimes track bug detection when models generate regression tests from fixed code, but coverage is weakly related to detecting a bug when the input method itself is buggy; mutation analysis is inapplicable in that setting. This is strong evidence to measure real F2P bug detection directly instead of assuming proxy improvement means better tests.

The paper-linked [author GitHub artifact](https://github.com/drixs2050/Cov_mut_bug_detect_correlation/tree/4bc2ed63917557a8c879e6c733b8fa41c15b9871) is public at commit `4bc2ed63917557a8c879e6c733b8fa41c15b9871`, MIT-licensed with third-party notices. Static inspection verified prompts, generation/evaluation notebooks, Defects4J harness and processed data. README says the per-method CSVs and analysis notebooks let one rerun the statistical analysis without Defects4J or API calls; 1,000 seeded samples of 100 focal methods, and sizes 3/5/10/all, are configurable. Some camera-ready boxplot cells use values transcribed from paper tables, so those plots are not independently recomputed by those cells. The full original-model generation route is much heavier: Java 11, Defects4J checkout/build, API key, test generation for both buggy and fixed versions, plus JaCoCo/CodeCover/PIT runs. Original provider model snapshots are not pinned. The notebook's generation call uses o4-mini; adapting it to local Qwen is plausible for a new independent evaluation, not exact replication.

Use this paper as a high-priority evaluation-method foundation. Reanalyzing its public statistics is easy; an exact end-to-end original model rerun is conditional and expensive. A bounded Qwen evaluation on selected Defects4J bugs could test a concept-guided method against direct fixed-vs-buggy detection. That would be a new-model study, not a reproduction. No source was run or modified.

Artifact record caveat: article/README references differ between Zenodo DOI suffixes; the verified public GitHub repository is the stable source. Zenodo record [21429529](https://zenodo.org/records/21429529) matches the title, author list and package and links back to the repository.

Full structured evidence: [`audit/reviews/074.json`](../../audit/reviews/074.json); static public-source details: [`public_evidence/source_audit.md`](public_evidence/source_audit.md).
