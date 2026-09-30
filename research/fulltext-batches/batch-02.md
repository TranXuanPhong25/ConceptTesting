# Full-text notes, catalog entries 21-40

_Read on 2026-09-18. “Full text” means an official open PDF, author-accepted manuscript, or arXiv version was available and read. “Abstract-only” means the listed facts are restricted to the publisher or author abstract; missing fields are deliberately left missing._

## 21. METAMON: Finding Inconsistencies between Program Documentation and Behavior using Metamorphic LLM Queries

**Method.** METAMON uses EvoSuite regression tests to expose a Java method's observed behavior, then asks an LLM whether each generated oracle agrees with the method documentation. It adds metamorphic query transformations, chain-of-thought, and self-consistency to check the verdict.

**Motivation.** Documentation can drift from code. Reading code and comments alone lets an LLM hallucinate a mismatch; concrete executions give it behavior to judge.

**Dataset + shape.** 9,482 Java method/documentation pairs drawn from five Defects4J v2.0.1 projects.

**Evaluation results.** It reports precision 0.72 and recall 0.48 for documentation-behavior inconsistency classification.

**Concept applicability.** High. Treat a documented pre/postcondition as a concept, generate a source input, then generate a relation-preserving follow-up input. The oracle is whether code violates the relation promised by the documentation.

**Evidence.** Full text. Primary source: https://arxiv.org/abs/2502.02794

## 22. Evaluating the Effectiveness of Large Language Models in Automated Unit Test Generation

**Method.** Compares GPT-4, Claude 3.5, Command-R-08-2024, and Llama 3.1 as JavaScript unit-test generators, then evaluates generated tests with Jest coverage and Stryker mutation testing.

**Motivation.** Model choice for CI test generation should be measured with executable and mutation-based outcomes rather than prose quality.

**Dataset + shape.** 106 test cases in 23 test suites, selected with input from software experts and QA engineers.

**Evaluation results.** Claude 3.5 is reported at 93.33% test success, 98.01% statement coverage, and 89.23% mutation score.

**Concept applicability.** Moderate. This is primarily a model comparison, but the Stryker survivors can be turned into concepts for a targeted second pass.

**Evidence.** Abstract-only; publisher PDF was not openly retrievable. Primary source: https://doi.org/10.1109/icarc64760.2025.10962997

## 23. HPCAgentTester: a Multi-Agent LLM Approach for Enhanced HPC Unit Test Generation

**Method.** A Recipe Agent proposes an HPC-aware test recipe; a Test Agent writes tests; the pair iterates through critique for OpenMP and MPI code.

**Motivation.** HPC tests must account for parallel execution, communication, synchronization, and nondeterminism, which a single generic code-generation prompt often omits.

**Dataset + shape.** The accessible manuscript describes tests for OpenMP and MPI primitives. It does not state a reproducible corpus size in the accessible abstract.

**Evaluation results.** The paper claims higher compilation and functional-correctness rates than a standalone LLM, but the accessible abstract does not provide the numeric table.

**Concept applicability.** High for concurrent software. A concept record should carry communication topology, synchronization preconditions, data partitioning, and allowed nondeterminism. A separate recipe agent is a plausible place to synthesize that record.

**Evidence.** Full text, but the available manuscript leaves corpus/result counts unclear. Primary source: https://arxiv.org/abs/2511.10860

## 24. LLMs for Automated Unit Test Generation and Assessment in Java: The AgoneTest Framework

**Method.** AgoneTest is an end-to-end Java test-generation and assessment framework. It generates class-level suites and measures coverage, mutation coverage, and test smells against human tests.

**Motivation.** A test generator needs a common evaluation pipeline. Compilation alone does not tell whether a suite covers code, kills mutants, or accumulates poor test structure.

**Dataset + shape.** It introduces Classes2Test, a class-to-corresponding-test-class dataset derived from Methods2Test. The accessible paper does not give a corpus count in its abstract.

**Evaluation results.** The available abstract says that, among tests that compile, generated suites can match or exceed human suites on coverage and defect detection. It does not support a precise aggregate number.

**Concept applicability.** Moderate. Use class dependencies, constructors, fixture setup, and existing-test gaps as a concept context. AgoneTest is more useful here as an evaluator than as a concept-generation method.

**Evidence.** Full text for the framework paper; the catalog's 2025 title has a later arXiv version. Primary source: https://arxiv.org/abs/2408.07846

## 25. Evaluating LLM-Generated Unit Tests with Mutation Testing: ChatGPT vs DeepSeek

**Method.** Generates Java tests from structured prompts using GPT-4o and DeepSeek V3, repeats each model/class run five times, and evaluates PIT mutation coverage and mutation score plus compilation/runtime failures.

**Motivation.** Coverage misses weak tests. The study asks whether generated tests kill seeded faults and whether complexity predicts generation failure.

**Dataset + shape.** Six Java classes from Defects4J at different cyclomatic-complexity levels; two models; five runs per class/model. The released artifact includes prompts, generated suites, fixed mutant sets, PIT reports, and failure logs.

**Evaluation results.** DeepSeek V3 is reported as more stable and more effective at killing mutants; GPT-4o generated valid suites for more classes. The paper reports no significant correlation between cyclomatic complexity and compilation success. The accessible abstract does not provide the aggregate mutation scores.

**Concept applicability.** High. A live mutant's operator, changed expression, and required distinguishing behavior form a clean target concept. The artifact can support a direct mutation-guided ablation.

**Evidence.** Abstract plus official artifact; paper PDF was not openly retrievable. Primary sources: https://doi.org/10.5753/sbqs.2025.13792 and https://zenodo.org/records/17250744

## 26. STRUT: Structured Seed Case Guided Unit Test Generation for C Programs using LLMs

**Method.** STRUT statically extracts focal-function context and builds a structured seed case. GPT-4o expands it into structured cases, and rule-based code translates those cases into executable C tests.

**Motivation.** Directly asking an LLM for C test code fails on pointers, mocks, dependencies, and setup. A constrained intermediate representation narrows the generation task.

**Dataset + shape.** The paper evaluates diverse C programs and compares against a direct GPT-4o baseline and SunwiseAUnit. The accessible page did not expose the exact project/function count.

**Evaluation results.** STRUT achieves 96.01% execution pass rate, 77.67% line coverage, and 63.60% branch coverage. It reports 37% and 33% relative improvements in line and branch coverage over direct GPT-4o.

**Concept applicability.** Very high. The structured seed is already a concept carrier: types, interface facts, branch-relevant assignments, mock effects, and output constraints. The current Python annotator could emit a comparable structured input record rather than prose tags.

**Evidence.** Full text. Primary source: https://doi.org/10.1145/3728970

## 27. A Large-Scale Empirical Study on Fine-Tuning Large Language Models for Unit Testing

**Method.** Compares fine-tuning and prompting across three unit-testing tasks, five benchmarks, eight metrics, and 37 LLMs; it also analyzes architecture, size, leakage, and bug-detection implications.

**Motivation.** Earlier LLM unit-test studies were too narrow to distinguish model scale, architecture, fine-tuning, and prompting effects.

**Dataset + shape.** Three tasks, five benchmarks, 37 models, and more than 3,000 NVIDIA A100 GPU-hours. The test-generation result quoted in the paper uses Defects4J; the source code and data are released.

**Evaluation results.** On test generation, GPT-3.5 reaches 49.16% correct rate and 51.03% passing rate; the strongest fine-tuned model named in the paper, DeepSeek-Coder-6B, reaches 45.96% and 41.67%. Across tasks, the study reports LLMs outperforming prior methods on nearly all metrics, while warning about leakage and weak bug-detection evidence.

**Concept applicability.** Moderate. This paper does not propose concepts, but it supplies a useful warning: compare concept prompting against an equal model and prompt budget, and hold the benchmark split fixed.

**Evidence.** Full text. Primary source: https://arxiv.org/abs/2412.16620

## 28. PRIMG: Efficient LLM-driven Test Generation Using Mutant Prioritization

**Method.** PRIMG first runs mutation testing on Solidity smart contracts. A learned model over mutant subsumption graphs prioritizes surviving mutants; an LLM then generates and refines a test for the chosen mutant until syntax and behavior checks pass.

**Motivation.** Mutation-guided LLM generation becomes costly when real projects create many surviving mutants and a test per mutant bloats the suite.

**Dataset + shape.** Real-world Solidity projects from Code4Arena. The accessible manuscript does not provide the number of projects/contracts in the text retrieved here.

**Evaluation results.** PRIMG reports higher mutation coverage with a smaller suite and lower effort than random mutant selection. The accessible abstract does not expose exact aggregate numbers.

**Concept applicability.** Very high. Mutant selection is exactly concept selection: mutation operator, affected state transition, and expected behavioral distinction. Its subsumption graph suggests a principled way to prioritize concept targets.

**Evidence.** Full text. Primary source: https://arxiv.org/abs/2505.05584

## 29. Towards metamorphic testing with LLM-based workflows: Metamorphic relation inference and follow-up test case generation

**Method.** The catalog identifies this as an LLM workflow for inferring metamorphic relations and generating follow-up tests. A primary open manuscript was not found during this batch.

**Motivation.** Metamorphic testing supplies an oracle when exact expected outputs are unavailable.

**Dataset + shape.** Not recoverable from an official full text in this batch.

**Evaluation results.** Not recoverable from an official full text in this batch.

**Concept applicability.** High in principle: each inferred relation becomes a concept comprising input transformation, required output relation, and validity preconditions. Exact feasibility remains unassessed until the paper is obtained.

**Evidence.** Abstract-only metadata. Primary source: https://doi.org/10.1016/j.infsof.2026.108150

## 30. An LLM-Driven Fuzzing Framework for Detecting Logic Instruction Bugs in PLCs

**Method.** LogicFuzz builds a semantic dependency graph for PLC instructions, uses enable signals to synthesize valid seed programs, mutates invocation contexts for control-triggered faults, and applies constrained parameter mutation for data-triggered faults. Its oracle combines logs, LEDs, and communication state.

**Motivation.** Proprietary PLC firmware prevents reliable static recovery of code boundaries, layouts, and calling conventions, but instruction faults still need valid, stateful trigger programs.

**Dataset + shape.** Six production PLCs from three vendors; 338 logic instructions evaluated; the paper also reports 1,743 bug clues attached to its semantic dependency graphs.

**Evaluation results.** It finds 19 instruction-level bugs, including four previously unknown vulnerabilities.

**Concept applicability.** Very high. The semantic dependency graph is an explicit concept representation. For test generation, retain instruction semantics, enable condition, predecessor instructions, parameter constraints, and physical/runtime oracle as separate fields.

**Evidence.** Full text. Primary source: https://www.ndss-symposium.org/wp-content/uploads/2026-f1081-paper.pdf

## 31. Search+LLM-Based Testing for ARM Simulators

**Method.** SearchSYS asks an LLM for initial C programs, compiles them, fuzzes the binaries, then differentially executes them on real ARM hardware and the gem5 simulator.

**Motivation.** A simulator can execute a vast program space yet subtly disagree with hardware; hand-written tests cannot cover the ISA/program combinations.

**Dataset + shape.** One target simulator, gem5, checked against actual ARM hardware. The released artifact contains the experiment material; the paper does not frame this as a conventional fixed benchmark count.

**Evaluation results.** It identifies 624 bug-activating cases from LLM-generated tests and 126 from fuzzed inputs; developers acknowledged four unique bugs.

**Concept applicability.** High. An ISA instruction family, operand types/ranges, memory mode, and expected hardware/simulator equivalence give a precise differential-testing concept.

**Evidence.** Full author-accepted manuscript. Primary source: https://discovery.ucl.ac.uk/10203327/1/main.pdf

## 32. Clozemaster: Fuzzing Rust Compiler by Harnessing LLMs for Infilling Masked Real Programs

**Method.** ClozeMaster mines historical Rust compiler bug-triggering programs, masks structurally meaningful regions with `clozeMask`, and asks an LLM to infill them. The retained context preserves enough syntax and semantic structure for valid compiler tests.

**Motivation.** Generating Rust compiler inputs from scratch produces too many invalid programs; mutation can also destroy the delicate structure that reaches deep compiler behavior.

**Dataset + shape.** Historical Rust issue-report test code is the seed corpus; tests run against rustc and mrustc. The accessible abstract does not give the seed-corpus count.

**Evaluation results.** The currently accessible preprint reports 27 confirmed bugs, 10 fixed by developers, and better coverage/effectiveness than compared fuzzers.

**Concept applicability.** Very high. The masked AST/grammar role, surrounding type context, and bug-history feature form a structured concept for an infilling model. This is stronger than prompt-only “write a weird Rust program.”

**Evidence.** Full text for the accessible preprint. Catalog year/DOI and the current arXiv version conflict: the catalog lists ICSE 2025, while the accessible arXiv record is dated 2026. Verify the bibliographic version before citation. Primary source: https://arxiv.org/abs/2605.00413

## 33. When Software Security Meets Large Language Models: A Survey

**Method.** Survey of LLM use in software security, including vulnerability discovery, fuzzing, code analysis, and repair.

**Motivation.** Security tasks expose both the potential and reliability limits of LLM-based program reasoning.

**Dataset + shape.** A survey, not a primary test-generation benchmark.

**Evaluation results.** No single experimental result should be used as evidence for the concept method.

**Concept applicability.** Indirect. Use it to map security concepts such as CWE, source/sink, sanitizer, guard, and exploit precondition; do not use it as an experimental baseline.

**Evidence.** Abstract-only for this batch. Primary source: https://doi.org/10.1109/jas.2024.124971

## 34. Kaizen: Metamorphic Fuzzing and Differential Testing for LLM-Translated HPC Applications

**Method.** Kaizen mutates source code into semantically equivalent variants, fuzzes inputs with a grammar, and differentially compares CUDA originals with LLM-generated OpenMP translations.

**Motivation.** Compilation, token similarity, and static benchmark tests can all accept an HPC translation that computes scientifically wrong results on particular inputs.

**Dataset + shape.** 16 CUDA scientific applications from seven domains, translated to OpenMP by three fine-tuned models at kernel and full-program granularities.

**Evaluation results.** The study finds nine recurring compile-error categories for kernel translation and 27 for full-program translation. It shows that semantic errors remain after compilation and developer tests, but the accessible abstract does not state a total confirmed-bug count.

**Concept applicability.** High. The concept is a semantic-preserving source transformation, input-domain relation, and cross-version equality/tolerance oracle. This shape translates cleanly to Python numerical code or API differential tests.

**Evidence.** Full text. Primary source: https://arxiv.org/abs/2607.04058

## 35. Hallucination to Consensus: Multi-Agent LLMs for End-to-End JUnit Test Generation

**Method.** CANDOR uses specialized agents to construct test prefixes and generate assertions, then applies a consensus mechanism among reasoning agents to decide oracles.

**Motivation.** High coverage with regression assertions can encode current bugs. Java needs correct setup, compileable tests, and intended-behavior oracles.

**Dataset + shape.** The accessible paper compares end-to-end Java unit-test generation against EvoSuite and oracle generation against TOGLL. Exact project/dataset counts were not retrieved in this batch.

**Evaluation results.** CANDOR reports coverage comparable to EvoSuite and at least 21.1 percentage points higher oracle correctness than TOGLL on both correct and faulty source code.

**Concept applicability.** High. Give the planner a concept record, but require independent agents to challenge the implied postcondition. Consensus is useful when a static concept is uncertain or underspecified.

**Evidence.** Full text. Primary source: https://arxiv.org/abs/2506.02943

## 36. Understanding the Characteristics of LLM-Generated Property-Based Tests in Exploring Edge Cases

**Method.** Uses Claude-4-Sonnet to generate property-based tests (PBT) and example-based tests (EBT), then compares the edge-case faults each catches.

**Motivation.** Example tests tend to miss large input spaces; properties explore broadly but can miss particular boundary patterns.

**Dataset + shape.** 16 HumanEval problems whose standard solutions fail extended tests. The model generates roughly three to five PBTs or 10 to 20 EBT cases per problem.

**Evaluation results.** PBT and EBT each detect bugs in 68.75% of the 16 problems; combining them reaches 81.25%. PBT catches performance and broad input-space issues, while EBT catches specific boundaries and special patterns.

**Concept applicability.** Very high. A concept can generate both a property and a minimal boundary witness. Run both because they expose different failures.

**Evidence.** Full text. Primary source: https://arxiv.org/abs/2510.25297

## 37. Mutant-Driven Test Generation for Ethereum Smart Contracts via LLMs

**Method.** Alchemist generates tests from live Solidity mutants and follows a scientific-method loop: form a hypothesis about the mutant, generate a test, execute it, and refine the hypothesis/test.

**Motivation.** Mutation testing identifies weak contract tests but developers need help converting live mutants into behaviorally meaningful test cases.

**Dataset + shape.** Solidity projects; exact corpus size was not available in an official accessible PDF during this batch.

**Evaluation results.** The available official abstract says Alchemist improves test quality over direct prompting and reduces developer effort; it does not provide numeric results.

**Concept applicability.** Very high. The mutation is the concept and the hypothesis loop is a natural implementation of concept-guided feedback. It is closely aligned with the current symbolic-plus-feedback design.

**Evidence.** Abstract-only. Primary source: https://doi.org/10.1109/aitest66680.2025.00033

## 38. Enhancing Search-Based Testing with LLMs for Finding Bugs in System Simulators

**Method.** SearchSYS generates parameterized input programs with six LLMs, mutates the compiled programs and parameters using AFL++, and uses hardware-vs-simulator differential execution as the oracle.

**Motivation.** Architecture simulators receive less fuzzing attention than ordinary software despite incorrect simulation affecting hardware design decisions.

**Dataset + shape.** gem5 is the program under test; the experiment spans six LLMs and compares its behavior with real hardware.

**Evaluation results.** SearchSYS finds 21 new gem5 bugs: 14 hardware/simulator prediction mismatches and seven crashes. Every one of the six LLMs contributed new defects.

**Concept applicability.** High. Seed-generation concepts should name instruction syntax, operand and parameter types, and the intended differential relation. Fuzzing then mutates within that concept's grammar.

**Evidence.** Full text. Primary source: https://discovery.ucl.ac.uk/id/eprint/10209206/

## 39. Metamorphic Testing for Fairness Evaluation in Large Language Models: Identifying Intersectional Bias in LLaMA and GPT

**Method.** Defines fairness-focused metamorphic relations over sensitive attributes, generates source/follow-up prompts, and flags output changes in tone or sentiment that violate the relation.

**Motivation.** A fixed expected answer is rarely available for fairness. Varying a protected attribute while preserving task meaning gives an executable fairness oracle.

**Dataset + shape.** Tests GPT-4.0 and LLaMA 3.0 across demographic combinations including race, gender, age, marital status, and socioeconomic background. The accessible thesis reports a broad set of add/remove/substitute/paraphrase/permutation relations but not a single fixed corpus count.

**Evaluation results.** Tone-based relations detected up to 2,200 fairness violations; sentiment-based relations detected fewer than 500.

**Concept applicability.** High for metamorphic tests. Record the semantic invariant, allowed input transformation, sensitive dimensions, and comparison function. This is directly reusable for non-fairness APIs as well.

**Evidence.** Full author manuscript/thesis. Primary source: https://arxiv.org/abs/2504.07982

## 40. TOGLL: Correct and Strong Test Oracle Generation with LLMs

**Method.** Fine-tunes seven code LLMs with six prompt forms on oracle-generation data, selects the best model/prompt combination, and generates assertions and exception oracles for existing tests.

**Motivation.** A test input without a correct oracle cannot reliably detect a bug. Earlier neural oracle generators produced many false positives and weak assertions.

**Dataset + shape.** Training uses SF110. Generalization evaluation uses 25 large Java projects; the study also evaluates correctness, oracle diversity, mutation strength, and unique bug detection.

**Evaluation results.** TOGLL produces 3.8 times more correct assertion oracles and 4.9 times more correct exception oracles than the reported baselines. It finds 1,023 unique bugs not found by EvoSuite, about ten times the unique-bug count of TOGA.

**Concept applicability.** Very high. Feed a concept as an intended postcondition or invariant, then use an oracle generator/critic to decide the assertion. This directly addresses the main weakness of the current TestEval pipeline: a test that covers a target may still assert the wrong thing.

**Evidence.** Full text. Primary source: https://arxiv.org/abs/2405.03786

**Artifacts (checked 2026-09-29).** Code: verified source [doi.org/10.6084/m9.figshare.28282721.v3](https://doi.org/10.6084/m9.figshare.28282721.v3) (Figshare artifact, 7.2 GB zip: RQ1 fine-tune/inference .py (fine_tune_code_parrot.py etc.), RQ2-5 data+tests; no GitHub repo). Dataset: SF110-derived oracle dataset (fine-tune), OracleEval25 (25 Java projects), Defects4J — released by authors [doi.org/10.6084/m9.figshare.28282721.v3](https://doi.org/10.6084/m9.figshare.28282721.v3). Models: CodeGPT-small-java (110M), CodeParrot-small-multi (110M, selected), CodeGen-350M-multi, CodeGen-2B-multi, PolyCoder-0.4B, PolyCoder-2.7B, Phi-1 (1.3B).

## Inaccessible or incomplete full-text items

- #22 Evaluating the Effectiveness of Large Language Models in Automated Unit Test Generation: publisher PDF not open.
- #25 Evaluating LLM-Generated Unit Tests with Mutation Testing: ChatGPT vs DeepSeek: official artifact open, paper PDF not located.
- #29 Towards metamorphic testing with LLM-based workflows: Metamorphic relation inference and follow-up test case generation: official full text not located.
- #33 When Software Security Meets Large Language Models: A Survey: full text not retrieved in this batch.
- #37 Mutant-Driven Test Generation for Ethereum Smart Contracts via LLMs: full text not retrieved in this batch.

_Partial-detail caveat: #23, #24, #26, #28, and #35 had accessible manuscript text but the retrieved text did not expose every dataset count or aggregate result. Those fields stay qualified rather than inferred._
