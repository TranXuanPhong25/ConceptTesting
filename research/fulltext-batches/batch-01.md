# Full-text notes: catalog entries 1-20

Reviewed 2026-09-18. “Full text” means an official open-access PDF, author manuscript, or conference preprint was available and read. “Abstract-only” means a primary landing page exposed an abstract but no accessible full text was found; those entries deliberately omit unreported dataset sizes and results.

## 1. A Logic-Guided and Explainable Approach to LLM-Based Unit Test Generation (Logic-CoT, 2026)

- **Method.** Logic-CoT converts the CUT's control-flow graph into condition/state vectors and paths, derives satisfying inputs and expected outputs, then fills an Arrange-Act-Assert template. A two-level repair loop fixes syntax locally; assertion failure sends the process back to logical inference.
- **Motivation.** Direct code-to-test prompting has poor branch reasoning, weak assertions, and unreadable intent. The authors want the model to externalize the route from input constraint to expected outcome.
- **Dataset + shape.** Java experiments use QuixBugs, Apache Commons Math, Apache Commons Lang, HumanEval-X, and SV-COMP. The accessible article names the corpora but the exact sampled counts should be taken from its experiment tables before reuse.
- **Evaluation.** The paper compares Logic-CoT with a native LLM and ChatUniTest on effectiveness, repair efficiency, and interpretability. The article reports significant paired improvements but this note does not quote table values not independently transcribed.
- **Concept applicability.** Very high. Its condition-state table is almost the same object as a target-specific symbolic concept. Keep the explicit guard, alias, path polarity, input relation, and oracle separate so the LLM can inspect them.
- **Evidence.** Full text, official open-access article: <https://www.mdpi.com/2076-3417/16/5/2542>

## 2. Test Wars: A Comparative Study of SBST, Symbolic Execution, and LLM-Based Approaches to Unit Test Generation (2025)

- **Method.** An empirical comparison of EvoSuite (search-based testing), Kex (symbolic execution), and TestSpark (LLM generation).
- **Motivation.** Claims that LLMs replace established generators need a direct, controlled comparison on the same Java bugs and metrics.
- **Dataset + shape.** GitBug Java benchmark. The paper evaluates the three tools against bug-containing real-world Java projects; consult its dataset table for project/method counts before reproducing.
- **Evaluation.** Coverage, mutation/fault detection, execution, and cost are compared. The study frames LLM generation as complementary rather than universally dominant: classical tools retain strengths on systematic exploration.
- **Concept applicability.** Medium. Use concept synthesis as the LLM arm, then compare against symbolic constraints and SBST. This paper is a good ablation template, not a concept-extraction method.
- **Evidence.** Full author PDF: <https://research.tudelft.nl/files/235086533/tga_pipeline_paper.pdf>

## 3. Benchmarking LLMs for Unit Test Generation from Real-World Functions (ULT, 2026)

- **Method.** ULT is a function-level Python benchmark curated for high cyclomatic complexity and reduced test leakage; PLT is its deliberately pre-leaked paired control.
- **Motivation.** Existing benchmarks can reward memorization and structurally simple code, inflating apparent test-generation ability.
- **Dataset + shape.** ULT has 3,909 real-world Python functions. Functions were selected through multi-stage curation with a complexity filter; PLT provides leaked counterparts for controlled memorization analysis.
- **Evaluation.** Across evaluated LLMs on ULT, average test accuracy was 41.32%, statement coverage 45.10%, branch coverage 30.22%, and mutation score 40.21%. The paired TestEval averages reported are 91.79%, 92.18%, 82.04%, and 49.69%, respectively.
- **Concept applicability.** High. ULT is the right stress test after TestEval: concept blocks need to handle realistic dependencies and semantic difficulty, not only clean LeetCode control flow.
- **Evidence.** Full accepted manuscript: <https://discovery.ucl.ac.uk/id/eprint/10223971/1/3805043.pdf>

## 4. LLM-Powered Fuzz Testing of Automotive Diagnostic Protocols (2025)

- **Method.** An LLM is taught Unified Diagnostic Services (UDS) structure and constraints, then used to construct a protocol fuzzer that emits semantically valid diagnostic messages. The authors compare it with a commercial fuzzer under different prompts and network configurations.
- **Motivation.** Automotive fuzzers require protocol and deployment expertise, and generic byte mutation wastes effort on invalid UDS messages.
- **Dataset + shape.** UDS diagnostic protocol traffic and automotive ECU/network configurations. The accessible paper does not expose a public corpus cardinality in the material reviewed.
- **Evaluation.** It studies fault/vulnerability detection and generated-byte/action distributions, including chi-square and Shannon entropy analyses, against a commercial fuzzer. Do not claim a bug count without the result tables.
- **Concept applicability.** High for fuzzing. Protocol fields, session state, service/subfunction constraints, and ECU configuration are precisely the kind of structured concepts that should guide seed generation.
- **Evidence.** Full author-hosted PDF: <https://mpese.com/publication/mcshane-2025-llm/2025-01-8091.pdf>

## 5. AI-Powered Unit Test Generation via Multi-LLM Chaining (2025)

- **Method.** Gemini generates JUnit tests; GPT-4o refines them for compilation, boundary inputs, assertions, and coverage. Other single-model and chained configurations, including Claude-3.5, are compared.
- **Motivation.** One-shot tests often compile poorly or miss edge cases. The second model acts as a targeted test editor rather than generating from scratch.
- **Dataset + shape.** HumanEval tasks translated into JUnit tests. The full paper should be consulted for the exact retained-task count.
- **Evaluation.** The best reported chain reaches 99.05% branch coverage, 90.48% line coverage, and 94.32% mutation coverage. Randoop reports 68.64% branch and 78.84% line coverage in the same study.
- **Concept applicability.** High. Put symbolic concepts in both stages: generation receives reachability constraints; refinement receives uncovered constraints and weak-oracle evidence. This is closer to the current feedback loop than a one-shot prompt.
- **Evidence.** Full open-access IEEE article: <https://ieeexplore.ieee.org/document/11269709/>

## 6. GEM: A Framework for Strengthening LLM-Generated Unit Tests Using Mutation Feedback (2026)

- **Method.** GEM expands to Generate-Execute-Mutate: it uses surviving mutants to strengthen LLM-generated assertions.
- **Motivation.** Tests that run and cover code can still accept mutant behavior because their oracles are weak.
- **Dataset + shape.** Abstract-only; no dataset size is recorded here.
- **Evaluation.** Abstract-only; the public conference record does not provide the experiment table in the accessible material.
- **Concept applicability.** Very high. Treat the mutant operator, changed expression, behavioral difference, and required distinguishing input as the concept. This is a direct semantic extension of the current TestEval loop.
- **Evidence.** Abstract-only, official conference page: <https://conf.researchr.org/details/cibse-2026/cibse-2026-cibse-2026--main-track-/27/GEM-A-Framework-for-Strengthening-LLM-Generated-Unit-Tests-Using-Mutation-Feedback->

## 7. OBsmith: LLM-Powered JavaScript Obfuscator Testing (2026)

- **Method.** The framework creates JavaScript sketches with LLMs, fills placeholders with concrete values, instruments a baseline, obfuscates programs under several settings, and differentially compares observable behavior. It also extracts sketches from real programs.
- **Motivation.** Obfuscators are expected to preserve semantics, but conventional JavaScript fuzzers do not target obfuscation-specific transformations or silent miscompilations.
- **Dataset + shape.** Generated LLM sketches plus sketches extracted from real JavaScript programs; evaluation covers JS-Confuser and Obfuscator.IO across low/medium/high configurations. The accessible artifact does not give a single total-program count in its README.
- **Evaluation.** OBsmith found 11 previously unknown correctness bugs in the two obfuscators. Five general JavaScript fuzzers found none under the same program budget.
- **Concept applicability.** High. The concept should encode a JavaScript feature, an obfuscation transform, and the semantic relation expected to survive it. This is a clean route to metamorphic/differential test generation.
- **Evidence.** Full arXiv preprint: <https://arxiv.org/pdf/2510.10066>; artifact and bug corpus: <https://github.com/shanjiang98/obsmith>

## 8. Req2Test: An Approach for the Automatic Generation of Unit Tests from User Stories Using LLMs (2026)

- **Method.** Abstract-only in this review. The title and venue identify requirements/user stories as the input to LLM unit-test generation.
- **Motivation.** Move test generation earlier, from natural-language user stories rather than only code.
- **Dataset + shape.** Abstract-only; unavailable.
- **Evaluation.** Abstract-only; unavailable.
- **Concept applicability.** Medium. Requirement-level concepts could seed a test-intent layer, but they need grounding against implementation-level paths or contracts before driving fault exposure.
- **Evidence.** Abstract-only, official metadata record: <https://doi.org/10.5281/zenodo.17917984>

## 9. LLM-based Dynamic Differential Testing for Database Connectors with Reinforcement Learning-Guided Prompt Selection (2025)

- **Method.** Parameterized prompts supply database-connector domain knowledge. The LLM generates tests, differential execution compares connector behavior, and reinforcement learning selects prompts using prior behavioral feedback to improve coverage and discrepancy discovery.
- **Motivation.** Connector defects are stateful and specification-sensitive; generic fuzzing and unguided LLM prompts miss interface/internal logic.
- **Dataset + shape.** Two production JDBC connectors: MySQL Connector/J and OceanBase Connector/J.
- **Evaluation.** The authors reported 16 issues: 10 confirmed bugs and 6 acknowledged unsafe implementations.
- **Concept applicability.** Very high. Connector API sequence, connection state, SQL feature, expected cross-connector relation, and known unsafe behavior form an actionable concept block. The differential oracle avoids needing a hand-written expected result.
- **Evidence.** Full arXiv manuscript: <https://arxiv.org/pdf/2506.11870>; official ASE record: <https://ieeexplore.ieee.org/document/11334652/>

## 10. A Cascaded Pipeline for Self-Directed, Model-Agnostic Unit Test Generation via LLMs (CasModaTest, 2025)

- **Method.** CasModaTest separately generates a test prefix and a semantically matched oracle, retrieves demonstrations from manually built prefix/oracle pools, assembles the test, executes it, and repairs compilation/runtime errors.
- **Motivation.** Prior work often generates only an oracle or fails to preserve the semantic connection between setup and assertion; closed-model dependence also limits use.
- **Dataset + shape.** Defects4J plus 1,625 focal methods from six real-world Java projects.
- **Evaluation.** On Defects4J it outperforms five prior approaches on accuracy and focal-method coverage. On the six projects it exceeds EvoSuite on method, line, and branch coverage; use the tables for exact deltas.
- **Concept applicability.** High. The relevant concept should bind input construction to the expected behavioral relation, not appear as loose annotations. This gives a design rule for symbolic concepts: every reachability concept needs an oracle counterpart.
- **Evidence.** Full author PDF: <https://vinci-grape.github.io/papers/A_Cascaded_Pipeline_for_Self_Directed__Model_Agnostic_Unit_Test_Generation_via_LLMs.pdf>

## 11. GenFair: Systematic Test Generation for Fairness Fault Detection in Large Language Models (2025)

- **Method.** Metamorphic fairness testing combines equivalence partitioning, mutation operators, and boundary-value analysis to create source prompts; metamorphic relations generate demographic follow-ups; tone comparisons flag violations.
- **Motivation.** Template and grammar approaches miss linguistically diverse, intersectional bias cases.
- **Dataset + shape.** Generated fairness prompts evaluated against GPT-4.0 and LLaMA-3.0. The accessible manuscript should be used for the exact prompt/mutation inventory.
- **Evaluation.** Fault-detection rate is 0.73 on GPT-4.0 and 0.69 on LLaMA-3.0, versus 0.54/0.51 for a template baseline and 0.39/0.36 for ASTRAEA. Reported syntactic and semantic diversity are 10.06 and 76.68.
- **Concept applicability.** High for semantic concepts. The concept is a protected-attribute transformation plus the response relation that should remain invariant. This transfers directly to metamorphic tests for conventional programs.
- **Evidence.** Full arXiv manuscript: <https://arxiv.org/pdf/2506.03024>

## 12. Prompt engineering in LLMs for automated unit test generation: A large-scale study (2026)

- **Method.** An empirical comparison of zero-shot, few-shot, chain-of-thought, tree-of-thought, and guided tree-of-thought prompts across GPT-3.5, GPT-4, Mistral 7B, and Mixtral 8x7B, with EvoSuite as a conventional baseline.
- **Motivation.** Existing test-generation evaluations are often small or omit execution-driven quality, hallucinations, smells, and class-level context.
- **Dataset + shape.** 216,300 generated tests over Defects4J, SF110, and CMD, a corpus intended to reduce LLM training-data leakage.
- **Evaluation.** Guided Tree-of-Thought improves reliability, compilability, and structural adherence for general models. Compilation failures from hallucinated APIs/dependencies reach as high as 86% in the study; generated tests are generally more readable than EvoSuite but retain smells such as magic numbers and assertion roulette.
- **Concept applicability.** High. Concept blocks can be injected as GToT branches: target path, required object state, and oracle premise. The scale and metrics make this an unusually good methodology reference for reporting failure modes.
- **Evidence.** Full accepted manuscript: <https://orbilu.uni.lu/bitstream/10993/68099/1/s10664-026-10840-4.pdf>

## 13. PALM: Synergizing Program Analysis and LLMs to Enhance Rust Unit Test Coverage (2025)

- **Method.** PALM extracts branch conditions from Rust functions, combines them into path constraints with context, and prompts the LLM separately for each scenario.
- **Motivation.** SBST/concolic methods struggle with complex branches and dependencies; fixed LLM prompts yield low compile rates and coverage.
- **Dataset + shape.** Fifteen open-source Rust crates. The authors also submitted 91 generated tests targeting new code.
- **Evaluation.** PALM-generated tests average 72.30% coverage, compared with 70.94% for human tests. Project coverage rises by over 50% in some cases within two to three hours. Of 91 submitted tests, 80 were accepted, 5 rejected, and 6 pending.
- **Concept applicability.** Very high. PALM is closest to this repo's symbolic approach: retain its path constraint as the hard core, but add alias resolution, state transition, and minimal boundary strategy to reduce LLM search.
- **Evidence.** Full arXiv manuscript: <https://arxiv.org/pdf/2506.09002>

## 14. Static Analysis and LLM for Comprehensive Java Unit Test Generation (SAGEN, 2025)

- **Method.** SAGEN uses AST static analysis to identify literal values and ranges before asking an LLM for Java tests.
- **Motivation.** Manual generation is costly; generic generators miss useful value boundaries.
- **Dataset + shape.** Abstract-only; not reported in accessible primary material.
- **Evaluation.** The available abstract reports 10% higher code coverage and 13% higher test quality than EvoSuite/Randoop, with an 89.7% compile-pass rate. It does not provide the underlying corpus size in the accessible material.
- **Concept applicability.** High but basic. Literal/range extraction is a useful component, yet it needs path polarity and data-flow context to avoid producing merely local boundary tests.
- **Evidence.** Abstract-only, IEEE metadata: <https://doi.org/10.1109/AEMCSE65292.2025.11042526>

## 15. Reinforcement Learning from Automatic Feedback for High-Quality Unit Test Generation (RLSQM, 2025)

- **Method.** RLSQM trains a Codex-family generator with lightweight static-analysis reward models for five test-quality metrics, individually and combined, using PPO.
- **Motivation.** Pretrained models reproduce low-quality tests and test smells. The paper finds undesirable smells in generated tests up to 37% of the time.
- **Dataset + shape.** The accompanying data are released on Figshare. The reviewed abstract does not establish a safe exact train/test split count for this note.
- **Evaluation.** RL improves quality metrics by up to 23%, yields nearly 100% syntactically correct tests, and outperforms GPT-4 on the reported static-quality metrics despite using a cheaper Codex model.
- **Concept applicability.** Medium-high. Treat concept adherence as an extra reward, but do not reward only textual mention of a concept. Reward observable facts: target reached, mutant killed, or metamorphic relation preserved/violated.
- **Evidence.** Full author PDF: <https://www.microsoft.com/en-us/research/wp-content/uploads/2024/12/2412.14308v1.pdf>

## 16. Harnessing Large Language Models for Automated Software Testing: A Leap Towards Scalable Test Case Generation (2025)

- **Method.** Fine-tunes Llama-2-7b-chat-hf with QLoRA for Java focal-method test generation.
- **Motivation.** General prompting lacks project-specific test behavior; focal methods focus the model on the unit under test.
- **Dataset + shape.** 25,000 curated records, tokenized for QLoRA training.
- **Evaluation.** The article evaluates generated tests against baseline approaches, but the accessible abstract does not provide a single result table value suitable for quotation here.
- **Concept applicability.** Medium. Fine-tuning could teach a compact concept vocabulary, but the current route is cheaper: externalize concepts in the prompt and evaluate causal compliance before committing to training.
- **Evidence.** Full open-access article: <https://www.mdpi.com/2079-9292/14/7/1463>

## 17. Mutation Testing via Iterative Large Language Model-Driven Scientific Debugging (2025)

- **Method.** Given a Python mutant and its module, the LLM forms a behavioral hypothesis, writes an experiment/test, receives execution feedback, and repeats until it kills the mutant or explains it as equivalent. It is compared with direct prompting, blind retry, and Pynguin.
- **Motivation.** A mutation-killing test must distinguish original and mutant semantics; plausible test imitation alone does not supply that reasoning.
- **Dataset + shape.** Python programs and generated mutants; the full paper's experiment tables should be consulted for subject and mutant counts.
- **Evaluation.** Iterative scientific debugging improves fault detection and coverage over Pynguin, at higher compute cost; iterative refinement is necessary for the strongest suites. Metrics include mutation score, coverage, kill success, and equivalent-mutant identification.
- **Concept applicability.** Very high. A mutant is a ready-made concept: changed operator, original-vs-mutant divergence hypothesis, necessary input relation, and expected assertion. This is the strongest near-term semantic loop to add after TestEval.
- **Evidence.** Full arXiv manuscript: <https://arxiv.org/pdf/2503.08182>

## 18. A Systematic Approach for Assessing Large Language Models’ Test Case Generation Capability (GBCV, 2025)

- **Method.** GBCV generates benchmark programs bottom-up from control-flow structures and variable-usage compositions, then asks models to produce input/output test cases.
- **Motivation.** Existing benchmarks do not systematically span control-flow and data-use difficulty, making it hard to attribute model failures.
- **Dataset + shape.** A configurable generated-program benchmark rather than a fixed mined corpus; it can target different languages and complexity levels.
- **Evaluation.** GPT-4o performs better on complex structures than GPT-3-Turbo. Both identify boundary values in simple conditions but struggle with arithmetic computations. A valid test requires both input and expected output; correctness is checked by execution.
- **Concept applicability.** High for controlled ablations. Generate paired tasks that differ in one concept, such as aliasing, arithmetic, or path conjunction, and measure whether the concept block fixes that exact failure.
- **Evidence.** Full open-access article: <https://www.mdpi.com/2674-113X/4/1/5>

## 19. LLM Driven Unit Test Case Generation Using Agentic AI (2025)

- **Method.** An AutoGen-based agent workflow prompts for Python unit tests, executes and repairs failed tests, analyses results, and aims to improve coverage and mutation score.
- **Motivation.** One-pass LLM tests often omit imports, invalid-input behavior, and boundary conditions.
- **Dataset + shape.** The accessible full-text landing page does not establish a reproducible dataset size in the material reviewed.
- **Evaluation.** The study reports coverage and mutation-testing evaluation, but this note leaves out exact values until the PDF tables are transcribed and checked.
- **Concept applicability.** Medium-high. Concepts belong in the planner/critic state, not only the generator prompt: the critic should check whether a proposed test realizes the target relation.
- **Evidence.** Full publisher PDF: <https://irojournals.com/jucct/article/pdf/7/4/3>

## 20. CrossProbe: LLM-Empowered Cross-Project Bug Detection for Deep Learning Frameworks (2025)

- **Method.** CrossProbe learns bug knowledge from issue/test material in one deep-learning framework and prompts an LLM to create tests for mirrored bugs in another framework.
- **Motivation.** Deep-learning framework fuzzers face huge model/API/hardware spaces; prompting from only one framework loses transferable bug patterns.
- **Dataset + shape.** Cross-project deep-learning framework issues and tests. The released repository contains the code and data, but the accessible project page should be paired with the paper PDF to quote corpus and framework counts.
- **Evaluation.** The available primary metadata establishes cross-project bug detection but does not expose a checked numeric result table in the reviewed material.
- **Concept applicability.** Very high. This treats the concept as a portable fault schema: API pattern, model/operator shape, triggering conditions, and expected crash or semantic discrepancy. That is an attractive extension beyond within-project AST concepts.
- **Evidence.** Official project page and artifact: <https://hguandl.github.io/publications/crossprobe/> and <https://github.com/CrossProbe2024/CrossProbe>

## Papers without accessible full text in this batch

- #6 GEM: only official abstract/conference record found.
- #8 Req2Test: official metadata available; no paper/manuscript retrieved.
- #14 SAGEN: IEEE metadata/abstract available; no paper/manuscript retrieved.

For #2, #7, #11, #17, and #20, a preprint/artifact was available; use the linked primary source rather than secondary summaries when turning these notes into paper claims.
