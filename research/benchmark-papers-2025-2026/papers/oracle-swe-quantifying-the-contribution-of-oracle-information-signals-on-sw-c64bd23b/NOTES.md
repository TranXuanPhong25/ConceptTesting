# ORACLE-SWE: Quantifying the Contribution of Oracle Information Signals on SWE Agents

Reviewed 2026-10-15. Full paper + appendices read; no author implementation found.

Paper: [arXiv:2604.07789v2](https://arxiv.org/abs/2604.07789), CC BY 4.0. Full-text extraction is 12,542 words (SHA-256 `23134f3b9aef46fef3c527ed4910b8221721ee5dd78712aeee7c497a4efc724f`).

The paper measures five injected information signals for SWE agents: F2P reproduction tests, P2P regression tests, gold edit locations, execution context and API usage. Datasets are SWE-bench Verified (459 filtered tasks), SWE-bench-Live (353) and SWE-bench-Pro Python/Go (220/211). It reports reproduction tests as the strongest individual signal and all five together at ≥97% on four model-benchmark settings. Its separate validation extracts signals with a stronger model and passes them to a weaker repair model. Defects4J is cited only as general background; BugsInPy/SWT-Bench are not evaluated. No root-cause taxonomy or diagnosis accuracy is measured.

**Fit for us:** useful conceptual support that a high-quality F2P test conveys strong actionable information. But its oracle conditions intentionally use gold F2P tests, patch locations and other gold patch-derived context to measure an upper bound. It is not a test-generation method and does not assess a concept-guided oracle. It also requires large SWE-bench infrastructure and hosted model APIs.

I found no paper-linked author code, extracted signal data or result cache; exact code reproduction is not feasible from public artifacts. SWE-agent is the cited baseline implementation, not Oracle-SWE source. Do not implement the method as part of this audit. For the user's immediate experiment planning, #74 is much more practical: its public Defects4J CSVs and analysis notebooks allow no-API reanalysis.

Structured evidence: [`audit/reviews/111.json`](../../audit/reviews/111.json); source search record: [`public_evidence/source_audit.md`](public_evidence/source_audit.md).
