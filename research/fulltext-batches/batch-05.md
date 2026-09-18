# Full-text notes: catalog #81-100

Reviewed 2026-09-18. “Full text” means an author manuscript, arXiv PDF, ACL PDF, or openly hosted paper was read. “Abstract-only” means the publisher page or record was accessible but not a full paper; no unreported dataset size or result is inferred.

## 81. Efficient Fairness Testing in Large Language Models: Prioritizing Metamorphic Relations for Bias Detection (2025)

**Method.** The paper ranks fairness metamorphic relations (MRs) by sentence diversity before executing them. The aim is to run the MRs most likely to expose a demographic-output inconsistency before the budget is exhausted.

**Motivation.** Fairness MRs combine quickly; testing all of them is impractical.

**Dataset and shape.** The accessible manuscript evaluates two language models with fairness MRs. I did not find a stable public count of prompts, relation instances, or protected-attribute groups in the source inspected.

**Evaluation.** Diversity ranking improves fault detection by 22% over random and 12% over distance-based ranking; it reduces time to first failure by 15% and 8%, respectively, and stays within 5% of fault-based prioritization.

**Concept applicability.** High. Treat a concept as an MR plus its source-to-follow-up transformation and rank concepts by predicted fault yield. This is a direct route from a symbolic concept to a test budget policy.

**Evidence.** Abstract-only; [primary arXiv record](https://arxiv.org/abs/2505.07870).

## 82. ASSURE: Metamorphic Testing for AI-powered Browser Extensions (2025)

**Method.** ASSURE combines a modular test generator, isolated browser execution, and validation rules for consistency, metamorphic relations, security boundaries, content alignment, and performance. It uses both metamorphic and adversarial generation strategies.

**Motivation.** AI browser extensions are stateful and nondeterministic, and their behavior depends on both page content and browser context. Exact-output oracles are often unavailable.

**Dataset and shape.** Six widely used AI browser extensions; the paper reports 1,000 metamorphic tests per extension.

**Evaluation.** ASSURE reports 531 distinct issues, 6.4x the testing throughput of manual testing, and a mean 12.4 minutes to detect critical security vulnerabilities.

**Concept applicability.** High for browser/security work. Encode a page transformation, security-boundary hypothesis, and invariant as the concept; generate the paired pages and let the validation pipeline act as the oracle.

**Evidence.** Full text; [primary arXiv PDF](https://arxiv.org/pdf/2507.05307).

## 83. FLAG: Finding Line Anomalies in RTL Code with Generative AI (2025)

**Method.** FLAG regenerates each RTL source line with an LLM, compares the original and generated lines, then ranks deviations using lexical and contextual features. It localizes likely defects without simulation, synthesis, test benches, or manually specified properties.

**Motivation.** RTL defect localization is expensive when a design is incomplete or lacks a working test environment.

**Dataset and shape.** 120 real-world RTL bugs and 81 synthetic bugs are reported for the 2025 RTL version.

**Evaluation.** The paper reports 38/120 real-world bugs and 32/81 synthetic bugs found. These are localization/detection results, not generated-test coverage.

**Concept applicability.** Indirect but useful. FLAG can propose an anomaly concept, such as an unexpected assignment or missing condition; a downstream generator could turn that concept into a property, assertion, or directed testbench.

**Evidence.** Full text; [primary author manuscript](https://arxiv.org/pdf/2306.12643) and [2025 journal record](https://doi.org/10.1145/3736411). The manuscript is an earlier version, so the 2025 counts above are cross-checked against the journal abstract/record.

## 84. CKGFuzzer: LLM-Based Fuzz Driver Generation Enhanced By Code Knowledge Graph (2025)

**Method.** CKGFuzzer builds an interprocedural code knowledge graph over repository entities and API relations. An LLM agent queries that graph to generate, compile-repair, and refine fuzz drivers and seeds; crash reports are also fed into analysis.

**Motivation.** Manual fuzz-driver construction and API understanding limit fuzzing of large libraries.

**Dataset and shape.** Eight open-source software projects.

**Evaluation.** It reports 8.73% average coverage improvement over the stated baselines, 84.4% less manual crash-review work, and 11 real bugs, nine previously unreported.

**Concept applicability.** Very high. A concept can be a graph-grounded API path: entry API, required object state, argument constraints, and target sink. This is closer to usable fuzz-driver context than flat AST tags.

**Evidence.** Full text; [primary arXiv PDF](https://arxiv.org/pdf/2411.11532) and [official artifact](https://github.com/security-pride/CKGFuzzer).

## 85. Your Fix Is My Exploit: Enabling Comprehensive DL Library API Fuzzing with Large Language Models (2025)

**Method.** DFUZZ gives the LLM a white-box view of deep-learning APIs, asks it to infer error-triggering edge cases, transfers those cases to related APIs, and synthesizes executable API test programs.

**Motivation.** TensorFlow and PyTorch expose thousands of APIs with complex input constraints; generic fuzzers miss API-specific edge cases.

**Dataset and shape.** The evaluation targets TensorFlow and PyTorch APIs. The accessible source describes libraries with more than 1,000 APIs but I did not recover a defensible exact number of evaluated APIs from the full text during this batch.

**Evaluation.** DFUZZ found 37 bugs; eight were fixed and 19 were under developer investigation when reported. It also reports higher API coverage than its named baselines.

**Concept applicability.** Very high. The reusable concept is an API edge-case schema: dtype, shape, rank, boundary value, parameter interaction, and expected failure mode. This is a strong template for concept-guided input generation.

**Evidence.** Full text; [primary arXiv PDF](https://arxiv.org/pdf/2501.04312).

## 86. The Seeds of the FUTURE Sprout from History: Fuzzing for Unveiling Vulnerabilities in Prospective Deep-Learning Libraries (2025)

**Method.** FUTURE mines historical bug-reproduction code from established DL libraries, learns mappings between old and prospective-library APIs, then converts the old bug seeds into tests for the new library. It also transfers discoveries back toward the established library.

**Motivation.** New DL libraries have sparse documentation, few existing tests, and little historical bug knowledge, while their APIs borrow ideas from mature libraries.

**Dataset and shape.** Three prospective DL libraries, 452 targeted APIs, and historical bug code from established libraries. The evaluated targets include Apple MLX, MindSpore, and OneFlow.

**Evaluation.** FUTURE reports 148 bugs across the 452 APIs, 142 previously unknown; 10 received CVE IDs. It also found seven PyTorch bugs.

**Concept applicability.** Very high. “Historical vulnerability pattern + cross-library API mapping” is a concept representation with a natural oracle: transferred seed should trigger the analogous erroneous behavior. It is more fault-directed than line coverage.

**Evidence.** Full text; [primary arXiv PDF](https://arxiv.org/pdf/2412.01317) and [official artifact](https://github.com/Redempt1onzzZZ/FUTURE).

## 87. Towards Leveraging LLMs to Generate Abstract Penetration Test Cases from Software Architecture (2026)

**Method.** The authors define an Abstract Penetration Test Case (APTC) metamodel, derive fields that are available in architecture models, and compare prompting strategies for generating APTCs from those models.

**Motivation.** Security feedback often arrives after design decisions harden into implementation. Architecture models can expose attack surfaces earlier, but architects rarely receive testable security guidance.

**Dataset and shape.** Architecture-model evaluation cases are used, but the accessible paper does not state a single dataset cardinality in the abstract. I did not infer one.

**Evaluation.** The best setting reaches 93% usefulness and 86% correctness, assessed for the generated APTCs.

**Concept applicability.** High, but upstream of executable test generation. The APTC fields can become concepts: asset, trust boundary, entry point, threat, precondition, and test action. Implementation-level generators still need code and environment context.

**Evidence.** Full text; [primary arXiv PDF](https://arxiv.org/pdf/2603.23698).

## 88. Test Case Generation Using Large Language Models: A Systematic Literature Review (2026)

**Method.** Systematic literature review of LLM-based test-case generation.

**Motivation.** The field has fragmented across unit testing, fuzzing, prompt engineering, repair, and evaluation.

**Dataset and shape.** The review corpus and screening counts were not available in an open full text during this batch.

**Evaluation.** A review, not a test-generation evaluation. No performance claim is recorded here.

**Concept applicability.** Background only. Use it to trace taxonomies and primary papers, not as evidence that a concept design works.

**Evidence.** Abstract-only; [primary DOI](https://doi.org/10.1007/s10586-026-06021-z). Full text was inaccessible from the publisher at review time.

## 89. MultiFileTest: A Multi-File-Level LLM Unit Test Generation Benchmark and Impact of Error Fixing Mechanisms (2026)

**Method.** MultiFileTest packages repository context into multi-file unit-test tasks and evaluates generation together with mechanisms for fixing generated-test errors.

**Motivation.** Single-function benchmarks hide dependency resolution, imports, configuration, and cross-file behavior that determine whether a repository test runs.

**Dataset and shape.** 60 real repositories: 20 Python, 20 Java, and 20 JavaScript projects; 2,389 tasks are stated in the paper’s benchmark description.

**Evaluation.** The paper compares multi-file context and repair mechanisms. Exact aggregate result numbers need table-level extraction from the ACL PDF; this batch does not quote them because the accessible text extraction was incomplete.

**Concept applicability.** High. Concepts should include dependency paths, construction protocol, imported symbols, and cross-file state, not only local path constraints. This benchmark is a better stress test than TestEval for a repository-aware concept representation.

**Evidence.** Full text; [primary ACL PDF](https://aclanthology.org/2026.findings-acl.1403.pdf).

## 90. BenjiTest: An Agentic Framework for Evaluating LLM-Based Unit Test Generation and Correction (2026)

**Method.** BenjiTest frames test generation and correction as an agentic workflow that evaluates generated unit tests and applies correction steps.

**Motivation.** A generated test is only useful after it compiles, executes, and has a defensible oracle; one-shot outputs leave too many failures untreated.

**Dataset and shape.** The SSRN record exposes a 50-page manuscript, but the accessible metadata did not expose the benchmark composition or counts without downloading through the SSRN gated flow.

**Evaluation.** Result tables were not available in the accessible source. No numbers are asserted here.

**Concept applicability.** Plausibly high. A concept state can persist across generator, executor, and repair agents, but this needs verification from the manuscript before citing it as a specific design precedent.

**Evidence.** Abstract-only; [primary SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6843084). Full PDF was inaccessible in this environment.

## 91. Retry and Refine: A Multi-agent Framework for LLM Based Reliable Unit Test Generation (2025)

**Method.** Multi-agent generation with structured retries, validation, and feedback-guided regeneration; the accessible abstract also mentions an ablation on expected-output feedback.

**Motivation.** LLM-produced unit tests need a developer-like refinement cycle rather than an accept-or-discard decision.

**Dataset and shape.** Not recoverable from the publisher metadata available in this batch.

**Evaluation.** The accessible source says expected-output feedback reduced retry depth and improved convergence, but did not expose numeric tables.

**Concept applicability.** High in design terms. Persist the concept and update only the evidence layer after each failure: compiler error, runtime error, unmet path, or failed oracle. This avoids re-prompting from scratch.

**Evidence.** Abstract-only; [primary Springer chapter record](https://doi.org/10.1007/978-3-032-11402-0_7). Full chapter required publisher access.

## 92. Intelligent Test Case Generation Method for Fuzzing IoT Protocols Based on LLM (2025)

**Method.** LIPFuzzer asks an LLM to parse protocol knowledge, classify message fields, choose mutation fields, and mutate real protocol messages. It targets Modbus-TCP, MQTT, and CoAP implementations.

**Motivation.** Protocol fuzzing usually demands detailed manual format knowledge and struggles to make targeted mutations in stateful message formats.

**Dataset and shape.** Several implementations of Modbus-TCP, MQTT, and CoAP. The accessible full text did not yield a reliable total implementation/message count in this pass.

**Evaluation.** It reports more convenient and efficient test generation and better vulnerability discovery than Peach, but I did not extract a result table whose counts can be quoted safely.

**Concept applicability.** Very high. A concept can be protocol state plus field semantics, mutation legality, checksum/length dependencies, and target behavior. This is nearly the same representation problem as structured test-input synthesis.

**Evidence.** Full text; [primary open manuscript PDF](https://assets-eu.researchsquare.com/files/rs-6331846/v1_covered_cd29b2d6-2a8a-468e-b159-411b48c9313d.pdf). The catalog DOI points to the later journal version.

## 93. CITYWALK: Enhancing LLM-Based C++ Unit Test Generation via Project-Dependency Awareness and Language-Specific Knowledge (2025)

**Method.** CITYWALK uses program dependence analysis to retrieve project dependencies and augments GPT-4o with C++-specific knowledge drawn from documentation and observed failure patterns.

**Motivation.** C++ tests fail for reasons local-method prompts omit: pointers, templates, virtual dispatch, builds, mocks, and nonlocal dependencies.

**Dataset and shape.** Eight popular C++ projects in the arXiv version. The later journal page describes ten, so the final-version count should be verified before paper citation.

**Evaluation.** The accessible full paper states that CITYWALK outperforms prior methods, but this note does not quote deltas until the journal tables are reconciled with the arXiv version.

**Concept applicability.** High. A usable concept representation must include dependency closure, ownership/lifetime assumptions, build/framework requirements, and language-specific hazards. CITYWALK is a direct precedent for expanding concepts beyond control flow.

**Evidence.** Full text; [primary author PDF](https://zhangyw.work/file/papers/Zhang2025TOSEM_B.pdf) and [primary arXiv record](https://arxiv.org/abs/2501.16155).

## 94. YATE: The Role of Test Repair in LLM-Based Unit Test Generation (2025)

**Method.** YATE repairs initially invalid LLM-generated Java tests using rule-based static analysis and re-prompting. Repaired tests become retained tests and potential seeds for further generation.

**Motivation.** Discarding an invalid test wastes a candidate that may already exercise valuable program logic.

**Dataset and shape.** Six open-source projects.

**Evaluation.** Versus a plain LLM method, YATE covers 32.06% more lines and kills 21.77% more mutants. Against HITS, SYMPROMPT, TestSpark, and CoverUp it reports 22% higher line coverage, 20% higher branch coverage, and 20% more mutants killed at comparable LLM-call cost.

**Concept applicability.** High. Preserve the original reachability/fault concept through repair. Feed the repair agent the failed test plus the concept and error evidence, rather than asking it to make a generic test pass.

**Evidence.** Full text; [primary arXiv PDF](https://arxiv.org/pdf/2507.18316).

## 95. TestLoter: A Logic-Driven Framework for Automated Unit Test Generation and Error Repair Using LLMs (2025)

**Method.** TestLoter extracts Java AST metadata, prompts with a five-stage logic-driven chain that combines white-box path/condition criteria with boundary-value and equivalence-partition testing, then applies a three-level repair process for syntax, dependencies/compilation, and semantic assertion errors.

**Motivation.** LLM tests often have both low coverage and high error rates; prompt-only generation does not systematically cover control logic or repair dependencies.

**Dataset and shape.** Nine open-source Java projects from data-processing and utility-library domains.

**Evaluation.** 83.6% line coverage, 78.0% branch coverage, and 2.3% failing generated tests. It improves line/branch coverage over ChatUniTest by 8.5%/10.9%; the paper reports more than 10% line and 15% branch coverage gains over EvoSuite.

**Concept applicability.** Very high. Its white-box/black-box prompt fields map cleanly to target-specific concepts: branch condition, boundary relation, equivalence class, and repair status. Our symbolic concept block can replace its generic reasoning stages with program-derived constraints.

**Evidence.** Full text; [primary publisher article](https://doi.org/10.1016/j.cola.2025.101348).

## 96. Mokav: Execution-driven Differential Testing with LLMs (2025 journal version)

**Method.** Mokav receives two program versions and one equal-output example input. It generates candidate inputs, executes both versions, feeds output and internal execution differences back to the LLM, and stops when it finds a difference-exposing test (DET).

**Motivation.** A coverage-reaching test does not establish a behavioral difference. Program repair, mutation testing, and refactoring validation need inputs that distinguish two implementations.

**Dataset and shape.** 1,535 Python program pairs from Codeforces and 32 pairs from QuixBugs.

**Evaluation.** Mokav finds DETs for 1,255/1,535 Codeforces pairs (81.7%), versus 4.9% for Pynguin and 37.3% for Differential Prompting. The paper attributes the result to iterative, execution-driven feedback.

**Concept applicability.** Extremely high. This is the closest direct template for semantic concept testing: concept = hypothesized behavioral difference; oracle = unequal outputs on buggy/mutant and correct/fixed versions. It can replace structural coverage as the feedback signal.

**Evidence.** Full text; [primary author manuscript PDF](https://www.diva-portal.org/smash/get/diva2%3A1907143/FULLTEXT01.pdf), [official artifact](https://github.com/ASSERT-KTH/mokav), and [journal DOI](https://doi.org/10.1016/j.jss.2025.112571).

## 97. LSPAI: An IDE Plugin for LLM-Powered Multi-Language Unit Test Generation with Language Server Protocol (2025)

**Method.** LSPAI plugs language-server static analysis into an IDE workflow and passes the resulting semantic context to an LLM for on-demand tests in Java, Go, and Python.

**Motivation.** Per-language test-generation integrations are expensive to build and do not fit developer workflows that need immediate, project-aware tests.

**Dataset and shape.** Evaluation spans Java, Go, and Python projects. The accessible paper excerpt did not expose the number of projects or target methods.

**Evaluation.** Compared with Copilot, it reports line-coverage improvements of 145% for Java, 931% for Go, and 95.62% for Python. These are relative gains, so they should not be compared directly with absolute TestEval coverage.

**Concept applicability.** High for deployment. The language server can supply symbol/type/call-site concepts automatically; combine that with path and fault concepts in the prompt, rather than building language-specific extractors from scratch.

**Evidence.** Full text; [primary author PDF](https://gwihwan-go.github.io/files/papers/FSE-Industry25-LSPAI.pdf) and [official artifact](https://zenodo.org/records/15206535).

## 98. A System for Automated Unit Test Generation Using Large Language Models and Assessment of Generated Test Suites (2025)

**Method.** AgoneTest automates class-level Java test generation and assessment. It starts from Methods2Test and creates a paired dataset for comparing human and LLM-generated tests, then runs an end-to-end quality assessment workflow.

**Motivation.** Method-level toy evaluations and manual integration do not represent the dependency and scale problems of real test-suite generation.

**Dataset and shape.** A new dataset derived from Methods2Test for human-vs-LLM test comparison. The accessible full text did not provide a safely extractable final count in this batch.

**Evaluation.** The contribution is an automated system, dataset, and assessment methodology. No aggregate result is quoted here because the paper’s tables were not extracted reliably enough for an exact claim.

**Concept applicability.** Moderate to high. It supplies an evaluation framework for whether concept-guided generation produces tests that survive project-level integration, which is more useful than syntax-only measures.

**Evidence.** Full text; [primary arXiv PDF](https://arxiv.org/pdf/2408.07846) and [ICSTW DOI](https://doi.org/10.1109/ICSTW64639.2025.10962454).

## 99. AgentTester: An LLM-Based Tool for Unit Test Generation with Automatically Generated Prompts (2025)

**Method.** AgentTester automatically generates prompts for an LLM-based unit-test tool.

**Motivation.** Prompt construction is a bottleneck for reproducible LLM test generation.

**Dataset and shape.** Not available in the accessible bibliographic record.

**Evaluation.** Not available in the accessible bibliographic record.

**Concept applicability.** Potentially useful as a prompt-construction layer: symbolic concepts could become structured prompt fields. The paper needs full-text inspection before using it as evidence for any claimed effect.

**Evidence.** Abstract-only; [primary Springer DOI](https://doi.org/10.1007/978-981-95-0011-6_10). Full chapter was inaccessible.

## 100. QTRAN: Extending Metamorphic-Oracle Based Logical Bug Detection Techniques for Multiple-DBMS Dialect Support (2025)

**Method.** QTRAN transfers metamorphic-oracle SQL query pairs from one DBMS dialect to another. It identifies dialect-specific features with parsing, queries a feature knowledge base through retrieval, uses an LLM to translate the pair, and mutates transferred queries for further testing.

**Motivation.** Metamorphic DBMS testers depend on manually engineered dialect grammars, so they cover only a few popular systems.

**Dataset and shape.** Eight DBMS dialects are represented in its feature inventory: MySQL, MariaDB, TiDB, PostgreSQL, SQLite, MonetDB, DuckDB, and ClickHouse. The paper evaluates transferred statement pairs and fuzzing outcomes across those dialects.

**Evaluation.** QTRAN found 24 previously unknown logical bugs; 16 were confirmed. The authors also report that most transferred pairs were suitable for metamorphic testing.

**Concept applicability.** Very high. A metamorphic concept can encode the original SQL, relation-preserving transformation, dialect-specific feature mapping, and expected output relation. This is a concrete design for concepts that survive translation across contexts.

**Evidence.** Full text; [primary paper PDF](https://matafeiyanll.github.io/paper/Issta25.pdf) and [official artifact](https://github.com/QTRANll/QTRAN).

## Inaccessible full texts

- #88, *Test Case Generation Using Large Language Models: A Systematic Literature Review*: publisher full text inaccessible.
- #90, *BenjiTest*: SSRN PDF download was gated in this environment.
- #91, *Retry and Refine*: Springer chapter requires publisher access.
- #99, *AgentTester*: Springer chapter requires publisher access.

For #81, #83, #85, #92, #93, and #98, an open manuscript was accessible but some table-level dataset/result details could not be extracted reliably. Those entries deliberately omit those numbers.
