# Full-Text Notes, Batch 06 (Catalog #101-#122)

_Read on 2026-09-18. “Full text read” means an open paper or author manuscript was available. “Abstract-only” means the data/result fields deliberately stop at what the primary abstract or official artifact states._

## 101. LLMs in the Heart of Differential Testing: A Case Study on a Medical Rule Engine

**Method.** LLMeDiff asks an LLM to write tests from medical-rule knowledge, then runs each test against two GURI rule-engine implementations; any output disagreement is the oracle.

**Motivation.** Medical rules encode standards and regulations in two independently maintained implementations. Manual agreement testing does not scale, while a public-knowledge model can propose medically meaningful cases.

**Dataset + shape.** 58 real medical rules in the Cancer Registry of Norway's GURI system; two implementations; four LLMs.

**Evaluation results.** Differential execution found inconsistencies in 22 rules, including version-handling differences. GPT-3.5 hallucinated least and produced the highest reported usable-test rate, but took the longest.

**Concept applicability.** Strong. The concept should be a semantic relation between implementations: rule version, input condition, expected equivalence, and the minimal divergent case. This is a clean fault-exposure oracle without needing a hand-written expected result.

**Evidence.** Full text read. Primary source: <https://arxiv.org/abs/2404.03664>

## 102. AutoOracle: High-Quality C++ Test Oracle Generation via Data Quality-Driven and Filtering-Enabled LLMs

**Method.** AutoOracle constructs C++ test-assert pairs by code de-differentiation, scores and filters noisy examples, fine-tunes a C++ oracle model, then filters suspicious generated assertions.

**Motivation.** Tests without trustworthy assertions do not detect faults. Existing oracle generators inherit noisy training pairs and emit plausible-looking but wrong expected values.

**Dataset + shape.** The released AutoOracleDataset has 79,496 prompt/label/quality-score samples from 666 open-source C++ projects. A prompt contains a test prefix plus focal-method definition; the label is an assertion.

**Evaluation results.** The paper abstract reports 2.13x higher oracle accuracy and 52.3% lower error rate than its stated SOTA baseline; it also reports better compile/runtime success in a Samsung embedded SSD-firmware study and a survey of 19 practitioners. Exact split and per-project table values were not accessible.

**Concept applicability.** Strong. A concept record can produce the assertion target: postcondition, invariant, relation between inputs and outputs, and forbidden state. The suspicious-oracle filter is worth copying as a post-generation critic.

**Evidence.** Abstract plus official dataset artifact; publisher full text unavailable. Primary sources: <https://doi.org/10.1145/3786583.3786868>, <https://github.com/SamsungDS/AutoOracleDataset>

## 103. Leveraging Retrieval-augmented LLMs for Automated Test Case Generation from Software Requirements Specification

**Method.** The system retrieves semantically related SRS chunks using MiniLM embeddings, adds few-shot examples, and asks proprietary or open models to produce structured test cases; a Streamlit interface exposes the pipeline.

**Motivation.** Requirements are broad and domain-specific. A prompt containing the whole SRS mixes irrelevant material with the target requirement.

**Dataset + shape.** 50 SRS-to-test-case pairs across eight domains: education, aerospace, automotive, telecom, e-commerce, government, hotel management, and healthcare. Documents are chunked into 100-200 words; each chunk maps to 2-5 tests. Evaluation uses leave-one-domain-out retrieval/examples.

**Evaluation results.** GPT-4o reached BLEU 0.72 and a 4.8/5 human score. Removing few-shot examples reduced these to 0.45 and 3.6. The paper reports six evaluated models.

**Concept applicability.** Moderate to strong. Retrieve a target-specific concept card, rather than raw document fragments: preconditions, business rule, state transition, boundary, and expected result. The small mixed public/synthetic corpus makes it a method example, not a strong bug-finding benchmark.

**Evidence.** Full text read. Primary source: <https://oaji.net/articles/2025/3603-1766026568.pdf>

## 104. Software Testing with Large Language Models: An Interview Study with Practitioners

**Method.** Qualitative interviews, analyzed with grounded-theory-style thematic analysis, yield a five-step workflow: define objective, prompt, refine, evaluate output, learn from use.

**Motivation.** Teams use LLMs in testing through ad hoc trials; the study asks how testers actually integrate them and where human review remains necessary.

**Dataset + shape.** 15 software testers in diverse roles and domains, interviewed semi-structurally. There is no program/test benchmark.

**Evaluation results.** Participants described iterative prompt refinement and emphasized human validation because hallucination and inconsistent reasoning remain operational risks. The output is a preliminary practice guideline, not a comparative accuracy or coverage claim.

**Concept applicability.** Indirect. It supports exposing the concept record to a tester or critic and recording why a test was accepted, repaired, or rejected. It does not validate a concept extractor by itself.

**Evidence.** Full text read. Primary source: <https://arxiv.org/abs/2510.17164>

## 105. LLM-Based Property-Based Test Generation for Guardrailing Cyber-Physical Systems

**Method.** ChekProp first asks an LLM to extract properties from CPS code and documentation, then generates property-based tests that can run before deployment or monitor a deployed system.

**Motivation.** CPS safety needs checks across physical, computational, and communication components, but manually writing both safety properties and generators is expensive.

**Dataset + shape.** Preliminary experiments cover real-world and commonly studied CPS examples, including a pneumatic-control system and a line-following robot. The paper evaluates generated properties against manual ones, executability after minimal edits, and input-space partition coverage; it does not release a large numeric corpus in the manuscript.

**Evaluation results.** The authors conclude that generated properties were comparable to manual properties and that the generated PBTs were executable and covered relevant partitions. The paper presents this as preliminary evidence rather than a broad benchmark score.

**Concept applicability.** Very strong. The extracted property is already a concept: invariant, safe/unsafe state, controllable inputs, and follow-up relation. This points beyond line coverage toward property/fault oracles.

**Evidence.** Full text read. Primary source: <https://arxiv.org/abs/2505.23549>

## 106. A Review of Large Language Models for Automated Test Case Generation

**Method.** Systematic literature review using IEEE Xplore, seed papers, Litmaps, ACM DL, and Scopus; it groups approaches into prompt engineering, feedback-driven generation, fine-tuning/pre-training, and hybrid methods.

**Motivation.** Reported LLM test-generation outcomes are hard to compare because prompts, datasets, metrics, languages, and feedback mechanisms vary widely.

**Dataset + shape.** 84 primary studies published from 2022-2025, selected after screening. This is a review corpus, not executable test data.

**Evaluation results.** The review does not report a unified new model score. Its empirical conclusion is that coverage, mutation score, and compilability are measured inconsistently; many studies use small or narrow benchmarks, and feedback/context/program complexity strongly affect results.

**Concept applicability.** Useful as a taxonomy check. A concept-guided paper should separate extraction, prompting, feedback, and oracle evaluation so it can be compared to these four families. It supplies no direct fault-exposure result.

**Evidence.** Full text read. Primary source: <https://www.mdpi.com/2504-4990/7/3/97>

## 107. Can Generative AI Produce Test Cases? An Experience from the Automotive Domain

**Method.** RQM2Text uses retrieval-augmented few-shot prompting to convert informal Rational Quality Manager test steps into executable ecu.test instructions.

**Motivation.** Automotive test plans start as informal behavior descriptions but engineers must later translate them into tool-specific scripts, often with missing or inconsistent context.

**Dataset + shape.** An industrial partner supplied 36 test-specification/script pairs. After cleaning, the benchmark has 200 unique informal-step to executable-instruction pairs; scripts average 4.4 executable instructions. The industrial data remain confidential.

**Evaluation results.** The best configuration achieved 49.5% exact-match rate and 64.5% line-match rate; code-tuned models did better than counterparts, and inaccurate/unneeded context hurt results.

**Concept applicability.** Strong for requirements-driven generation. Convert retrieved context into explicit concepts such as signal, actuator state, CAN mapping, value constraint, and expected observation. The evaluation measures translation fidelity, not bug detection.

**Evidence.** Full text read. Primary source: <https://aisberg.unibg.it/retrieve/889f446d-9d3a-467f-87a7-7ad6a39ea240/2025_FSE_Industy.pdf>

## 108. CoverUp: Effective High Coverage Test Generation for Python

**Method.** CoverUp instruments Python with SlipCover, prompts an LLM using uncovered line/branch information, lets it request extra code context, executes the test, and continues the dialogue after a failure or no coverage improvement.

**Motivation.** A one-shot test prompt has no information about what execution is still missing. Coverage feedback can name the next concrete target.

**Dataset + shape.** Three Python benchmark suites derived from 35 open-source projects. The principal CodaMosa-derived suite contains 4,116 functions; the paper also evaluates a MuTAP-compatible suite.

**Evaluation results.** With GPT-4o, CoverUp achieved median per-module line+branch coverage of 80% versus CodaMosa's 47%; on the MuTAP comparison it reached 89% overall line+branch coverage versus 77%. Ablations attribute the gain to coverage context, code-context access, and continued dialogue, not only the LLM.

**Concept applicability.** Direct. Replace raw uncovered branch text with symbolic path constraints, aliases, state changes, and boundary cases; retain CoverUp's execution loop. This is the closest existing architecture to the current TestEval feedback runner.

**Evidence.** Full text read. Primary source: <https://doi.org/10.1145/3729398>

## 109. ScenarioFuzz-LLM: Enhancing Diversity in Autonomous Driving Scenario Fuzzing with LLMs

**Method.** The framework combines LLM guidance, RAG, and genetic scenario mutation to diversify autonomous-driving simulations; it measures path, event, traffic-condition, and behavior coverage.

**Motivation.** Traditional ADS scenario fuzzers repeatedly mutate close variants and miss rare combinations of traffic participants, weather, road layout, and timing.

**Dataset + shape.** The artifact includes initial scenarios, results, and detected violations for CARLA 0.9.13 with Autoware and a Behavior Agent. The accessible artifact does not state the paper's final seed count or experimental budget.

**Evaluation results.** The authors report a 35.62% improvement in scenario diversity over their stated SOTA baseline and release unique violation scenarios. Exact fault counts and confidence intervals need the paper PDF.

**Concept applicability.** Strong. A scenario concept should encode road topology, actor roles, event ordering, weather, ego-vehicle objective, and safety predicate. It is a natural extension of symbolic preconditions from scalar inputs to world-state constraints.

**Evidence.** Official artifact/abstract only; paper PDF was not accessible. Primary source: <https://github.com/ldegao/ScenarioFuzz-LLM>

## 110. Automatic High-Level Test Case Generation using Large Language Models

**Method.** The authors collect use-case to high-level-test-case pairs, evaluate GPT-4o/Gemini and fine-tuned LLaMA 3.1 8B/Mistral 7B, then use human review.

**Motivation.** Practitioners reported that aligning testing with business requirements is harder than writing the final test script. High-level cases make the requirement-to-test decision earlier.

**Dataset + shape.** A survey of 26 practitioners motivates a use-case-to-test-case dataset. The accessible full paper describes the task shape but does not expose a reliable dataset cardinality in its abstract/searchable text.

**Evaluation results.** Fine-tuning the two open models improves their generation quality, and a final human survey finds the cases useful. Exact automatic/human scores require table-level extraction from the PDF.

**Concept applicability.** Strong for a requirements setting: business goal, actors, preconditions, alternate flow, boundary, and expected result can be a concept record before executable-test synthesis.

**Evidence.** Full text read; quantitative tables were not machine-extractable from the accessible manuscript, so no values are asserted. Primary source: <https://arxiv.org/abs/2503.17998>

## 111. Automating a Complete Software Test Process Using LLMs: An Automotive Case Study

**Method.** SPAPI-Tester preserves an existing vehicle-API workflow and assigns LLMs the manual judgment steps: extract test objects, map API data to CAN signals, generate inputs, execute tests, and interpret results alongside conventional automation.

**Motivation.** In-vehicle API tests require reconciling specifications, communication protocols, simulation, and parameter dependencies. Partial automation leaves the human glue work intact.

**Dataset + shape.** More than 100 APIs of Volvo's in-vehicle SPAPI web server, tested in a vehicle-test rig with virtual-vehicle/CAN context.

**Evaluation results.** The paper reports test-case precision of 90% and says generated tests are comparable to manual testing in pass rate, coverage, and failure detection. It frames the system as replacing a workflow that previously consumed 2-3 FTEs; detailed raw counts are industrial/confidential.

**Concept applicability.** Strong. Build concepts from API parameter mapping, inter-parameter dependency, protocol state, simulator precondition, and response relation. The decomposed workflow is a good design for a concept extractor plus deterministic execution tools.

**Evidence.** Full text read. Primary source: <https://arxiv.org/abs/2502.04008>

## 112. LLMorpheus: Mutation Testing Using Large Language Models

**Method.** LLMorpheus replaces chosen JavaScript source expressions with placeholders, prompts an LLM for realistic replacements, and uses the resulting changes as mutants; it compares to StrykerJS operators.

**Motivation.** Fixed mutation operators miss realistic bug classes. An LLM can propose context-sensitive changes that resemble historical defects.

**Dataset + shape.** 13 JavaScript packages; several LLMs and prompt variants; the authors release experimental data. Exact corpus size and mutation counts were not accessible in the public abstract.

**Evaluation results.** The paper reports LLM mutants resembling bugs that StrykerJS cannot generate, with measurements of running time, cost, and mutant count. It does not claim a test-generator improvement; it creates better targets for mutation testing.

**Concept applicability.** Very strong. A surviving mutant is a ready-made behavioral concept: altered expression, expected behavioral difference, affected inputs, and kill oracle. It is a sensible bridge from TestEval coverage to semantic fault exposure.

**Evidence.** Full text read. Primary source: <https://arxiv.org/abs/2404.09952>

## 113. Evaluation of the Choice of LLM in a Multi-Agent Solution for GUI-Test Generation

**Method.** PathFinder uses four agents for GUI summarization, action decision, input extraction, and validation. The authors test all 27 assignments of Mistral-Nemo, Gemma2, and Llama 3.1 across three non-validation agents.

**Motivation.** Multi-agent GUI systems assume each role benefits from a different model, but model mismatch can cause inconsistent decisions and poor coordination.

**Dataset + shape.** Four e-commerce websites; a purchase scenario; 27 model constellations.

**Evaluation results.** LLM selection significantly changes efficacy measured with F1. The paper finds that using one model across agents can give the best balance, while an official project summary reports that hybrid assignments can help across diverse platforms. It does not provide a defect/fault-exposure benchmark.

**Concept applicability.** Moderate. Put scenario, intended state transition, candidate widget semantics, and validation predicate in shared context memory. The main transferable lesson is to keep concept extraction, planner, executor, and critic interfaces explicit.

**Evidence.** Full text read. Primary source: <https://www.diva-portal.org/smash/get/diva2%3A1974470/FULLTEXT01.pdf>

## 114. LLM-Based Automatic Metamorphic Test Case Generation for LLM Fairness Testing

**Method.** The study defines fairness metamorphic relations and compares LLM-generated follow-up cases with human-written cases; experts judge relation conformity and sensitive-attribute relevance with Cohen's kappa.

**Motivation.** Fairness has no ordinary reference output. Template-based follow-up generation and manually listed sensitive attributes limit coverage.

**Dataset + shape.** The accessible primary abstract names LLM and human-generated cases plus expert judgments, but does not disclose task count, models, relation count, or corpus size.

**Evaluation results.** The accessible abstract describes the planned comparative evaluation but gives no aggregate outcome. No numeric claim is available without the proceedings PDF.

**Concept applicability.** Strong in form: the concept is the metamorphic relation, protected attribute transformation, invariant output property, and source-to-follow-up mapping. It is less directly useful for ordinary program test generation unless a domain relation is known.

**Evidence.** Abstract-only; proceedings full text unavailable. Primary source: <https://doi.org/10.1109/aitest70988.2026.00012>

## 115. Multi-Agent LLM-Based Metamorphic Testing for REST APIs

**Method.** ARMeta uses agents to infer metamorphic scenarios from OpenAPI documentation, express them as Given-When-Then specifications, synthesize executable tests, and run them.

**Motivation.** REST APIs often lack a precise expected response for every request. Metamorphic relations check whether paired requests preserve or transform behavior as required.

**Dataset + shape.** Two public web applications exposing REST interfaces, compared with a scenario-based testing baseline. The paper's accessible manuscript does not give a larger task count in the abstract.

**Evaluation results.** ARMeta explores behavior complementary to the baseline. The abstract does not give bug count, coverage, or statistical results.

**Concept applicability.** Very strong. Its Given-When-Then metamorphic scenario is an immediately usable concept schema: resource state, source request, transformation, follow-up request, and expected relation.

**Evidence.** Full text read. Primary source: <https://arxiv.org/abs/2605.28321>

## 116. Scenario-Guided LLM-based Mobile App GUI Testing

**Method.** ScenGen uses five agents: Observer, Decider, Executor, Supervisor, and Recorder. It combines visual widget extraction, multimodal semantic interpretation, context memory, state-transition checks, rollback/correction, and replayable JSON scripts.

**Motivation.** Coverage-driven GUI explorers create fragmented action sequences that miss business workflows such as purchase or email sending.

**Dataset + shape.** 99 app-scenario tasks across 92 mobile apps and ten representative scenarios.

**Evaluation results.** ScenGen reaches 86.87% scenario coverage and 84.85% completion, detects 106 scenario-related bugs, improves localization from 80.79% to about 98% after correction, and averages 4.71 minutes per generated test.

**Concept applicability.** Very strong. A scenario concept can persist across rounds as goal, preconditions, expected GUI state transition, widget role, and completion oracle. This offers a concrete multi-agent form for a feedback loop.

**Evidence.** Full text read. Primary sources: <https://arxiv.org/abs/2506.05079>, <https://doi.org/10.1145/3816025>

## 117. From Untestable to Testable: Metamorphic Testing in the Age of LLMs

**Method.** The paper addresses metamorphic testing with LLM workflows; the catalog entry identifies relation inference and follow-up-test generation as the central mechanism.

**Motivation.** Many systems have no conventional test oracle, so a test must establish a relation between outputs under controlled input transformations.

**Dataset + shape.** Not extracted: the arXiv PDF was unavailable through the accessible endpoint during this pass.

**Evaluation results.** Not asserted. The record requires full-text retrieval before quoting benchmark shape or results.

**Concept applicability.** Potentially strong. A concept becomes a relation template with source input, permitted transformation, expected output relation, and exceptions. This is only a design inference until the paper is read.

**Evidence.** Abstract-only/inaccessible PDF. Primary source: <https://arxiv.org/abs/2603.24774>

## 118. Less Is More: Failing Test Generation with Large Language Models

**Method.** MitGen decomposes a program into smaller constituent snippets and targets fault-triggering tests there rather than generating a failing test from the whole program at once.

**Motivation.** Failing-test generation must search jointly for a triggering input and a fault-revealing oracle. Whole-program prompts make both tasks too broad.

**Dataset + shape.** The accessible source identifies three LLMs (StarCoder2, Meta-Llama, CodeQwen), popular benchmarks, and real-world programs, but not their exact counts.

**Evaluation results.** MitGen reports recall 0.66, compared with 0.31 for the best baseline, a 112.7% relative increase. Remaining metric details need the TOSEM paper.

**Concept applicability.** Very strong. The current symbolic concept should be localized to a behaviorally coherent snippet, then include the fault hypothesis, trigger condition, and minimal distinguishing assertion. This is more semantic than a line target.

**Evidence.** Abstract-only; publisher full text unavailable. Primary source: <https://doi.org/10.1145/3793675>

## 119. TestExplora: Benchmarking LLMs for Proactive Bug Discovery via Repository-Level Test Generation

**Method.** TestExplora hides bug-revealing diff, commit message, and issue signals. Models inspect realistic repositories and documentation-derived intent, generate tests, and are judged by fail-on-buggy/pass-on-fixed behavior.

**Motivation.** Existing test benchmarks emphasize regression prevention or reproducing known reports. The target here is proactive bug discovery before a known manifestation exists.

**Dataset + shape.** 2,389 test-generation tasks from 1,552 pull requests across 482 repositories; TestExplora-Lite has 517 tasks from 330 pull requests. It supports black-box and white-box contexts.

**Evaluation results.** The paper's current arXiv version reports a maximum single-test F2P of 16.06%; SWE-agent with GPT-5-mini reaches 17.27% F2P and 29.7% F2P@5. The same manuscript notes assertion mismatch and mock configuration as dominant failure modes.

**Concept applicability.** Best final semantic evaluation. Build concepts from API/docs intent, risky entry path, cross-module state, fault hypothesis, and pre-fix/post-fix oracle. It is expensive but exactly tests the red/green claim.

**Evidence.** Full text read. Primary source: <https://arxiv.org/abs/2602.10471>

## 120. TestGenEval: A Real World Unit Test Generation and Test Completion Benchmark

**Method.** TestGenEval derives file-level unit-test generation and completion tasks from SWE-bench Docker environments, then runs generated tests to measure pass rate, coverage, and mutation score.

**Motivation.** Function-level benchmarks hide repository context, fixtures, mocks, and long source/test files that make test generation difficult in practice.

**Dataset + shape.** 1,210 code/test-file pairs from 11 maintained Python repositories, containing 68,647 human tests. Average code files contain 1,157 LOC; average test files contain 943 LOC. TestGenEvalLite is a smaller fast-iteration version.

**Evaluation results.** GPT-4o achieves 35.2% average coverage, the best reported result in the paper; models struggle particularly with execution reasoning and assertions on complex paths. The benchmark provides pass@1/pass@5, coverage improvement, and mutation-score improvement against gold tests.

**Concept applicability.** Strong external evaluation. A useful concept must describe dependency/fixture facts, missing behavior relative to existing tests, state setup, and a mutation or fault target. It is a serious test for whether the current approach generalizes beyond isolated TestEval functions.

**Evidence.** Full text read. Primary sources: <https://proceedings.iclr.cc/paper_files/paper/2025/file/26ded5c8ee8ec1bc4caced4e1c9b1584-Paper-Conference.pdf>, <https://github.com/facebookresearch/testgeneval>

## 121. Can LLMs Generate High-Quality Test Cases for Algorithm Problems? TestCase-Eval: A Systematic Evaluation of Fault Coverage and Exposure

**Method.** TestCase-Eval measures broad Fault Coverage across wrong competitive-programming solutions and targeted Fault Exposure against a supplied wrong solution, using valid inputs that make it diverge from correct behavior or fail.

**Motivation.** Structural coverage can touch a path without exposing the wrong semantics. The benchmark asks whether a generated test actually distinguishes correct and faulty implementations.

**Dataset + shape.** 500 Codeforces problems and 100,000 human-written solutions; the released benchmark spans C++, Java, and Python. The paper evaluates 19 models. The target fault-exposure subset contains 10,000 wrong solutions.

**Evaluation results.** Qwen3-32B achieves 43.8% targeted Fault Exposure, while expert humans achieve 93.3%. The paper reports that CoT helps the targeted task. It demonstrates that fault exposure remains much harder than conventional coverage.

**Concept applicability.** Immediate. Use the faulty implementation to extract a difference concept: suspicious expression, input relation, invariant violated, expected correct behavior, and minimal counterexample. This is the smallest practical semantic benchmark for the current Python pipeline.

**Evidence.** Full text read. Primary source: <https://aclanthology.org/2025.acl-short.82.pdf>

## 122. Vulnerability-Triggering Test Case Generation from Third-Party Libraries

**Method.** VulEUT performs client-to-library reachability analysis for a disclosed vulnerability condition, tracks parameter propagation, and asks an LLM to write a unit test that confirms exploitation.

**Motivation.** A vulnerable dependency does not automatically make a client exploitable. The test must demonstrate that client-controlled data reaches the vulnerable condition.

**Dataset + shape.** 32 vulnerabilities across third-party libraries and 70 real client projects; 292 generated unit tests. It compares against TRANSFER and VESTA.

**Evaluation results.** 229 of 292 generated tests confirmed exploitation, reported as a 24% improvement over the compared baselines.

**Concept applicability.** Direct fit. The concept should preserve source entry point, call chain, parameter-transfer transformation, vulnerability guard, exploit condition, and red/green assertion. It is the strongest security-specific route after TestCase-Eval.

**Evidence.** Full text read. Primary sources: <https://arxiv.org/abs/2409.16701>, <https://doi.org/10.1109/forge66646.2025.00021>
