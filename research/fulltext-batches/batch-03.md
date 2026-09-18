# Full-Text Reading Batch 03: Catalog #41-60

_Read on 2026-09-18. “Full text read” means an official PDF, an author-hosted manuscript, or an official open-access article was available. “Abstract-only” means the publisher record was found but no lawful full text was available during this pass. Numbers are omitted rather than inferred in those cases._

## 41. Mutation-Guided LLM-based Test Generation at Meta

**Method.** ACH creates privacy-relevant mutants, filters likely-equivalent ones, then asks an LLM to write a test that kills each survivor. Engineers review the resulting tests as ordinary diffs.

**Motivation.** Coverage can rise without detecting a changed behavior. A non-equivalent mutant gives the generator a concrete behavior to distinguish.

**Dataset + shape.** Deployment over 10,795 classes in seven Meta product/code areas. It created 31,677 mutants; 9,095 built and passed; 4,660 non-equivalent mutants became generation targets.

**Evaluation.** Engineers accepted 27/30 initial tests and 73% of test-a-thon submissions. ACH killed mutants in 15% of targeted classes versus 2.4% for the coverage-only baseline; 49% of its uniquely mutant-killing tests added no line coverage.

**Concept applicability.** Direct fit. Store mutant operator, changed expression, required distinguishing input, and buggy-versus-mutant oracle as the concept record. This supplies a semantic target missing from line coverage.

**Evidence.** Full text read. [Primary source](https://arxiv.org/abs/2501.12862).

## 42. MORTAR: Multi-turn Metamorphic Testing for LLM-based Dialogue Systems

**Method.** MORTAR builds multi-turn dialogue tests from metamorphic relations. It transforms an earlier turn or dialogue context, then treats a violated relation between the two responses as the oracle.

**Motivation.** Single-turn tests miss failures caused by dialogue history, while exact expected answers are difficult to specify for open-ended LLM systems.

**Dataset + shape.** The paper evaluates dialogue-system testing scenarios with multi-turn prompts and metamorphic follow-up cases. The accessible manuscript describes the evaluation design but this pass did not extract a stable dataset-count table.

**Evaluation.** It reports that multi-turn metamorphic testing exposes unexpected dialogue behavior that single-turn testing misses. No headline aggregate is repeated here because the available source version was revised after publication and its result tables differ across versions.

**Concept applicability.** High for stateful systems. A concept becomes: source dialogue state, allowed transformation, expected relation, and the turn at which the relation must hold. This is useful for API workflows and agents, less directly for isolated TestEval functions.

**Evidence.** Full text read. [Primary source](https://arxiv.org/abs/2412.15557).

## 43. RUG: Turbo LLM for Rust Unit Test Generation

**Method.** RUG decomposes Rust test-context construction bottom-up: resolve dependent types and setup pieces with LLM calls, verify each piece, merge them into a test context, then use coverage-guided fuzzing to build harnesses and add tests.

**Motivation.** Rust ownership, borrowing, and type dependencies make naive generated tests fail to compile; existing generators also leave coverage low.

**Dataset + shape.** 17 real Rust projects, averaging 24,937 lines of code. The authors also submitted 113 generated tests upstream.

**Evaluation.** RUG reaches up to 71.37% coverage, near the reported 73.18% human-test coverage. Of the 113 submitted tests, 53 were accepted, 17 rejected, and 43 pending at reporting time.

**Concept applicability.** High. Concepts should include constructor/type obligations, ownership and lifetime constraints, dependency setup, and an uncovered target path. This supports the current idea of target-specific constraints but requires a language-aware context builder.

**Evidence.** Full text read. [Author PDF](https://mainarke.github.io/assets/papers/icse25_cheng.pdf); [artifact](https://github.com/CXWorks/rug).

## 44. Understanding LLM-Driven Test Oracle Generation

**Method.** An empirical study varies prompt strategy and supplied context for LLM-generated test oracles, then measures whether the generated assertions expose failures rather than merely encode current behavior.

**Motivation.** Regression oracles from tools such as Randoop and EvoSuite assume the implementation is correct. The study asks whether LLMs can write assertions about intended behavior instead.

**Dataset + shape.** The paper evaluates generated oracles across multiple prompt/context configurations. The author manuscript available in this pass does not make a compact public dataset summary easy to verify, so no count is asserted here.

**Evaluation.** The study compares oracle quality under different context levels and prompting strategies. It is an empirical characterization paper; do not cite a fault-detection percentage from this note without consulting its tables.

**Concept applicability.** Very high. A concept can act as assertion evidence: invariant/postcondition, authority for it, relevant state transition, and counterexample condition. It is a better place to put concepts than a generic list of AST tags.

**Evidence.** Full text read. [Author manuscript](https://valerio-terragni.github.io/assets/pdf/bodicoat-aiware-2025.pdf).

## 45. Knowledge Matters: Injecting Project and Testing Knowledge into LLM-based Unit Test Generation

**Method.** KTester extracts project structure and usage knowledge through static analysis, separates test-case design from test-method generation, and injects testing-domain knowledge into both stages.

**Motivation.** Repository tests need valid setup, dependencies, mocks, and project conventions. Source-only prompting often writes tests that compile poorly or do not fit the repository.

**Dataset + shape.** The manuscript evaluates repository-level Java unit-test generation. It includes project code plus extracted structure/usage knowledge rather than isolated functions; consult the paper tables for the project list and counts.

**Evaluation.** KTester is evaluated against prior LLM-based approaches on correctness, coverage, and maintainability-oriented measures. This note avoids quoting a number because the accessible version is an ICSE 2026 manuscript whose final table values may change.

**Concept applicability.** Direct fit. Extend the current concept schema with dependency graph facts, valid object-construction paths, collaborator usage, mock boundaries, and existing test conventions. This paper is the cleanest precedent for calling that material “knowledge,” not merely prompt decoration.

**Evidence.** Full text read. [Author PDF](https://mingwei-liu.github.io/assets/pdf/ICSE26KTester.pdf); [official artifact](https://github.com/SYSUSELab/KTester).

## 46. Acceptance Test Generation with Large Language Models: An Industrial Case Study

**Method.** A two-stage workflow first generates Gherkin acceptance scenarios from user stories, then converts scenarios into Cypress scripts using page HTML. The work integrates AutoUAT and Test Flow into an industrial workflow.

**Motivation.** Unit-test generation is common, while executable acceptance tests remain expensive and underexplored. Separating scenario design from script creation gives testers a review point before automation.

**Dataset + shape.** Real web-application projects from an industry partner, using user stories, pages, generated Gherkin scenarios, and Cypress tests.

**Evaluation.** Users rated 95% of generated scenarios helpful. For generated Cypress tests, 92% were helpful: 60% usable unchanged, 8% needing minor fixes, 24% needing regeneration with more input, and 8% discarded.

**Concept applicability.** Medium-high. A concept can carry acceptance criterion, user role, state precondition, UI elements, and expected observable outcome. It transfers well to workflow testing but not directly to algorithmic fault exposure.

**Evidence.** Full text read. [Primary source](https://arxiv.org/abs/2504.07244).

## 47. ASTER: Natural and Multi-Language Unit Test Generation with LLMs

**Method.** ASTER uses lightweight static analysis to build prompts, validates and refines generated tests, and issues additional prompts for uncovered code paths. It supports Java and Python and handles external dependencies through mocking.

**Motivation.** Few generators work across languages or produce tests developers find readable; naive prompts also struggle with environment setup.

**Dataset + shape.** Standard and enterprise Java applications, plus a large Python benchmark. The study includes a user study with 161 professional developers to judge naturalness.

**Evaluation.** The paper reports coverage competitive with or above the compared generators and substantially more natural tests. The available primary summary does not expose a single aggregate coverage number, so this note keeps the result qualitative.

**Concept applicability.** High. ASTER validates the static-analysis-to-prompt route already used here. Improve it by giving analysis output an explicit semantic form: guard, feasible setup, dependency/mocking plan, target behavior, and oracle.

**Evidence.** Full text read. [Primary source](https://arxiv.org/abs/2409.03093); [IBM technical note](https://research.ibm.com/blog/aster-llm-unit-testing).

## 48. Test Intention Guided LLM-Based Unit Test Generation

**Method.** IntUT supplies an explicit test intention: test inputs, mock behavior, and expected result. The LLM writes the concrete Java test from that intention.

**Motivation.** Direct LLM test generation tends to produce low coverage and weak mocking because it has to infer all three design decisions from source alone.

**Dataset + shape.** Three industrial Java projects, followed by a live study on three new Java projects.

**Evaluation.** The accessible abstract reports up to 94% branch-coverage and 49% line-coverage improvement, over 80% line coverage in the live study, and 30% less unit-test writing effort. The full ICSE paper was not publicly accessible in this pass.

**Concept applicability.** Direct fit. The current symbolic concept must become a full test intention: feasible input relation, mock/stub requirements, expected result, and target path. This is a close precedent for the proposed method.

**Evidence.** Abstract-only. [Publisher record](https://doi.org/10.1109/ICSE55347.2025.00243).

## 49. LWDIFF: an LLM-Assisted Differential Testing Framework for WebAssembly Runtimes

**Method.** LWDIFF uses an LLM to generate and mutate WebAssembly programs, then runs them on multiple runtimes. It uses differential outcomes as the oracle and a multi-armed-bandit selector to choose productive mutation operators.

**Motivation.** Existing Wasm testing does not cover decoding, validation, and execution well enough, while writing diverse valid Wasm programs by hand is hard.

**Dataset + shape.** Eight WebAssembly runtimes; generated tests span binary/text programs and three runtime phases.

**Evaluation.** LWDIFF found 31 bugs, 25 previously unknown; all were confirmed and fixed by runtime developers. It outperformed the compared Wasm testing tools in the reported experiments.

**Concept applicability.** High. Use a concept as a divergence hypothesis: runtime feature, phase, valid/invalid encoding constraint, expected cross-runtime agreement, and mutation family. Differential testing removes the need for a manually written assertion.

**Evidence.** Full text read. [Accepted manuscript](https://discovery.ucl.ac.uk/id/eprint/10222953); [author PDF](https://www4.comp.polyu.edu.hk/~csxluo/LWDIFF.pdf).

## 50. DrWASI: LLM-assisted Differential Testing for WebAssembly System Interface Implementations

**Method.** The catalog identifies DrWASI as LLM-assisted differential testing of WASI implementations. It generates tests and uses behavioral disagreement between implementations as the oracle.

**Motivation.** WASI has multiple implementations and platform-dependent behavior, making a single hand-written expected output insufficient for broad compatibility testing.

**Dataset + shape.** Not verified from full text in this pass.

**Evaluation.** Not asserted. The publisher landing page was available, but no author manuscript or open full text was found during this pass.

**Concept applicability.** Plausibly high: API contract, filesystem/process state, environment setup, and expected cross-implementation relation form a useful concept. Treat this as a hypothesis until the paper is read.

**Evidence.** Abstract-only. [Primary source](https://doi.org/10.1145/3716379).

## 51. LLAMAFUZZ: Large Language Model Enhanced Greybox Fuzzing

**Method.** LLAMAFUZZ fine-tunes an LLM on paired mutation seeds, asks it to produce structure-preserving mutations for complex inputs, and feeds the seeds into a greybox fuzzing loop.

**Motivation.** Byte-level mutation breaks structured formats; grammar fuzzers require hand-written grammar support and can be slow.

**Dataset + shape.** Magma plus 15 real-world structured-data fuzz targets. The model trains on AFL++ and FuzzBench-derived seed/mutation data.

**Evaluation.** Across trials it reached 85 unique bugs, triggered 47 unique bugs, and outperformed the top competitor by 41 bugs on average. On real programs it achieved 27.19% more branch coverage than AFL++ on average.

**Concept applicability.** High. Use concepts as grammar fragments, required field dependencies, parser state, and mutation-preservation rules. The generator should propose structured mutations, while the fuzzer supplies coverage feedback.

**Evidence.** Full text read. [Primary source](https://arxiv.org/abs/2406.07714); [open manuscript](https://escholarship.org/content/qt3pj1v61n/qt3pj1v61n_noSplash_983dd4b5c940be2f93bebf8a450edc38.pdf).

## 52. Automated Test Generation Using Large Language Models

**Method.** A general LLM unit-test-generation study comparing prompting and model choices.

**Motivation.** The paper studies whether LLMs can reduce unit-test authoring effort and where generated tests fail in practice.

**Dataset + shape.** Not verified in a full paper during this pass.

**Evaluation.** Not asserted. The accessible publisher record was insufficient to responsibly recover the dataset or result table.

**Concept applicability.** Unclear until full text is read. It appears to be a broad baseline study rather than a concept-guided method.

**Evidence.** Abstract-only. [Primary source](https://doi.org/10.3390/data10100156).

## 53. Unlocking Low Frequency Syscalls in Kernel Fuzzing with Dependency-Based RAG

**Method.** SyzGPT identifies rarely or never covered syscalls, retrieves dependency evidence for them, and prompts an LLM to generate valid Syzkaller seed programs. Conventional fuzzing then mutates those seeds.

**Motivation.** Syzkaller leaves low-frequency syscalls untouched when their resource and call-order dependencies are too hard to synthesize through mutation.

**Dataset + shape.** Linux kernel fuzzing over more than 360 syscalls and more than 4,400 Syzkaller specialized calls; the paper evaluates a set of low-frequency syscall targets.

**Evaluation.** The paper reports average gains of 17.73% code coverage, 58.00% low-frequency-syscall coverage, and 323.22% vulnerability detection over its baselines.

**Concept applicability.** Very high. Dependency chains, required resources, syscall ordering, and target reachability form an executable concept. This is a concrete template for turning static facts into structured seed generators.

**Evidence.** Full text read. [Author PDF](https://zhiyu.netlify.app/files/ISSTA25_SyzGPT_Zhiyu_Camera_Ready.pdf); [code index](https://github.com/google/syzkaller/blob/master/docs/research.md).

## 54. Leveraging Large Language Models in Software Testing: A Review of Applications and Challenges

**Method.** Literature review, not a new generator.

**Motivation.** Maps uses of LLMs in software testing and their practical limitations.

**Dataset + shape.** Reviewed-paper corpus; full extraction unavailable in this pass.

**Evaluation.** No test-generation metric. Do not use this paper as evidence that a concept method improves coverage or fault detection.

**Concept applicability.** Useful only for positioning: it can help classify the proposed method under analysis-guided generation, oracle construction, fuzzing, and feedback loops.

**Evidence.** Abstract-only. [Primary source](https://doi.org/10.1109/ISDFS65363.2025.11011986).

## 55. TestEval: Benchmarking Large Language Models for Test Case Generation

**Method.** TestEval supplies target lines, branches, and paths for LeetCode-style programs, asks an LLM for targeted tests, and executes them under instrumentation.

**Motivation.** Whole-suite coverage hides whether a generated test reaches the specific control-flow target it was asked to cover.

**Dataset + shape.** 210 Python/Java programs; 1,340 target lines, 983 target branches, and 854 target paths. It provides instrumented programs, prompts, and evaluators.

**Evaluation.** The paper reports targeted line, branch, and path coverage alongside syntax, execution, and assertion correctness. GPT-4o reaches 80.97% target-line coverage with the basic prompt and 84.85% with two-step CoT.

**Concept applicability.** High as a controlled structural ablation, limited as a fault-detection claim. The repo's symbolic concept and feedback-loop runs fit here, but need TestCase-Eval, mutants, or red/green revisions for semantic validation.

**Evidence.** Full text read. [ACL paper](https://aclanthology.org/2025.findings-naacl.197/); [official code](https://github.com/LLM4SoftwareTesting/TestEval).

## 56. Large Language Models for C Test Case Generation: A Comparative Analysis

**Method.** Compares several LLMs and prompt contexts for program-level C tests, measuring Pass@1 and line coverage. Prompts vary whether they include a statement, C solution, Python solution, and example tests.

**Motivation.** Most LLM test-generation studies focus on Python or Java; this study asks how context changes C test quality on non-public tasks.

**Dataset + shape.** Original, non-public C programming problems created to reduce training contamination. The benchmark uses HumanEval-ranked models and corresponding problem descriptions/solutions.

**Evaluation.** `GPT-4o Preview` reaches 98.7% line coverage when given both statement and C implementation. Llama 3.3 and Qwen 2.5 remain around 96.1-98.4% and 97-98% coverage respectively across several C-context prompts. Example tests help some models more than others.

**Concept applicability.** Medium. It supports supplying structured context, but it evaluates solution verification on small programs rather than fault exposure. A concept ablation here should separate raw source context from explicit guard/boundary/oracle facts.

**Evidence.** Full text read. [Open-access article](https://www.mdpi.com/2079-9292/14/11/2284).

## 57. Unify and Triumph: Polyglot, Diverse, and Self-Consistent Generation of Unit Tests with LLMs

**Method.** PolyTest generates tests in multiple programming languages at zero temperature and unifies them; it also samples diverse tests within a language at higher temperature before unification.

**Motivation.** A single test-generation trace has limited diversity. Different language realizations and samples expose complementary test ideas.

**Dataset + shape.** The paper evaluates polyglot unit-test generation across multiple language settings. Exact project/task counts were not extracted in this pass.

**Evaluation.** It reports that cross-language and within-language diversity produce complementary tests. No aggregate percentage is quoted here without the paper tables.

**Concept applicability.** Medium-high. Keep the same semantic concept fixed while sampling several test implementations or language front-ends, then merge candidates by coverage, mutation kill, or fault exposure. The main value is diversity after analysis, not analysis itself.

**Evidence.** Full text read. [Primary source](https://arxiv.org/abs/2503.16144).

## 58. Towards Large Language Model Guided Kernel Direct Fuzzing

**Method.** SyzAgent combines Syzkaller with static call-graph analysis and real-time LLM guidance. Given a target kernel function, it finds relevant paths from syscalls and feeds code plus fuzzing state back to the LLM for seed generation and mutation guidance.

**Motivation.** Direct kernel fuzzing needs to reach a specific region despite rapidly changing code and deep syscall/resource dependencies.

**Dataset + shape.** A benchmark of targeted kernel-fuzzing cases. The paper describes LLVM IR preprocessing, kernel call graphs, syscall-to-target paths, and dynamic fuzzing feedback; it does not present a large public defect corpus.

**Evaluation.** Preliminary experiments find the approach effective in about 67% of benchmark cases. The authors present it as an exploratory framework rather than a finished large-scale evaluation.

**Concept applicability.** Very high. Target function, syscall-to-target call path, prerequisite resource, blocked condition, and current fuzzing feedback are exactly the fields a concept record needs for directed fuzzing.

**Evidence.** Full text read. [Open-access chapter](https://link.springer.com/chapter/10.1007/978-3-031-90900-9_2); [preprint](https://arxiv.org/abs/2503.02301).

## 59. LLM-Powered Security Test Generation: Oracles, Vulnerability Probes, and Adversarial Inputs

**Method.** A security-testing overview of LLM-generated oracles, vulnerability probes, and adversarial inputs.

**Motivation.** Security testing needs tests that trigger and detect risky behavior, not only valid inputs or code coverage.

**Dataset + shape.** Not a benchmark paper; no new evaluation dataset verified in this pass.

**Evaluation.** No original aggregate result is asserted from this overview.

**Concept applicability.** Strong for framing: model a security concept as CWE/fault hypothesis, entry point, source-to-sink path, guard/trigger condition, exploit input constraints, and a red/green oracle. Use primary evaluation papers such as VulEUT for empirical claims.

**Evidence.** Abstract-only. [Primary source](https://doi.org/10.1109/MC.2025.3625694).

## 60. Do LLMs Generate Useful Test Oracles? An Empirical Study with an Unbiased Dataset

**Method.** Generates concrete assertions for existing test prefixes under four prompt configurations, using 10 LLMs from Llama, Phi, and Qwen families. It compares generated assertions with programmer-written ones and measures mutation score.

**Motivation.** Earlier oracle studies often use public benchmarks that may sit in model training data. The authors build a post-cutoff corpus to measure semantic oracle quality with lower leakage risk.

**Dataset + shape.** 13,866 test oracles from 135 Java projects, all created after 2024-09-01. The study generates 610,104 LLM oracles across model/prompt combinations.

**Evaluation.** LLM-generated oracles average 43% mutation score, close to 45% for human-written oracles. Test prefix plus invoked methods gives enough context for good results; extra code context did not materially improve them.

**Concept applicability.** High, with a useful restraint: concepts should explain the intended postcondition and relevant state, but dumping more source may not help. Put the concept into an oracle-design stage after the input prefix is known, then score it with mutation testing.

**Evidence.** Full text read. [Author PDF](https://homes.cs.washington.edu/~mernst/pubs/neurosymbolic-oracles-ase2025.pdf); [replication package](https://github.com/darthdaver/llm-prompts-empirical-study).

## Inaccessible or abstract-only in this batch

- #48 Test Intention Guided LLM-Based Unit Test Generation
- #50 DrWASI: LLM-assisted Differential Testing for WebAssembly System Interface Implementations
- #52 Automated Test Generation Using Large Language Models
- #54 Leveraging Large Language Models in Software Testing: A Review of Applications and Challenges
- #59 LLM-Powered Security Test Generation: Oracles, Vulnerability Probes, and Adversarial Inputs
