# Full-Text Notes: Concept-Guided LLM Testing

_Evidence rule: every number below comes from the linked full paper. These are the eight P0 papers whose full PDFs were downloaded and read on 2026-09-18. The broader 122-paper catalog remains in [the literature map](llm-test-generation-2025-2026.md)._

## 1. Mutation-Guided LLM-based Test Generation at Meta

Source: [paper](https://arxiv.org/abs/2501.12862), FSE Companion 2025.

**Motivation.** Line coverage misses tests that detect a new fault without executing a new line. Meta's ACH system uses mutants as the target because a killed non-equivalent mutant is a concrete fault signal.

**Method.** ACH asks an LLM to create a small number of privacy-relevant mutants, filters likely-equivalent mutants with a separate agent, then prompts an LLM to generate a test that kills the remaining mutant. Engineers review the generated test as a normal code diff.

**Evaluation shape.** The deployment spans 10,795 classes across Facebook Feed, Messenger, Instagram, Aloha, Wearables, cross-app code, Oculus, and WhatsApp. ACH generated 31,677 mutants; 9,095 built and passed; 4,660 were considered non-equivalent and became test-generation targets. The initial trial submitted 30 generated tests. The later test-a-thons reviewed 191 tests for usefulness.

**Results.** Engineers accepted 27 of 30 initial-trial tests. The test-a-thons accepted 73% of reviewed tests. ACH killed mutants in 15% of targeted classes, versus 2.4% for the coverage-only TestGen-LLM baseline. Of ACH tests that uniquely killed a mutant, 49% added no line coverage. Those tests disappear if selection optimizes only coverage.

**Concept fit.** Very high. A mutant already gives a compact concept: changed behavior, affected expression, expected distinguishability, and a red/green oracle. The missing component in the current repo is mutant generation and survivor selection, not prompt wording.

## 2. TestExplora

Source: [paper](https://arxiv.org/abs/2602.10471), 2026.

**Motivation.** Regression tests assume the current implementation is correct. Bug-reproduction benchmarks start after a failure report exists. TestExplora asks whether a model can discover a defect before either condition holds.

**Method.** The benchmark hides defect-related signals from real pull requests. Models receive black-box or white-box context and must write tests from documentation-derived intent. A test succeeds only when it fails on the buggy pre-fix revision and passes on the repaired revision.

**Evaluation shape.** The full benchmark has 2,389 tasks from 1,552 pull requests in 482 repositories. TestExplora-Lite contains 517 samples from 330 pull requests. The paper evaluates six models and repeats baseline experiments three times. Metrics are Head Pass, Fail-to-Pass, Entry Coverage, Change-focused Coverage, and number of generated tests.

**Results.** On the full benchmark, GPT-5-mini reaches 5.17% Fail-to-Pass in black-box mode and 7.54% in white-box mode. On TestExplora-Lite, it reaches 7.67% and 11.84%. GPT-4o reaches 1.47% and 1.79% on the full benchmark. Gemini 2.5 Pro produces more tests but has lower suite-level F2P because a larger suite makes one invalid test more likely.

**Concept fit.** Very high, but expensive. Documentation intent, changed behavior, relevant entry path, and expected pre-fix/post-fix difference map directly to a concept record. This is the best final benchmark for the repo's red/green claim after smaller semantic experiments work.

## 3. TestCase-Eval

Source: [ACL 2025 paper](https://aclanthology.org/2025.acl-short.82/).

**Motivation.** Structural coverage can execute a line while missing the incorrect behavior. TestCase-Eval measures whether tests distinguish accepted and incorrect competitive-programming solutions.

**Method.** Task 1 measures Fault Coverage across a broad set of wrong solutions. Task 2 gives a particular wrong solution and measures Fault Exposure: generate a valid input that makes it diverge from accepted solutions or fail at runtime.

**Evaluation shape.** The benchmark covers 500 Codeforces problems and roughly 100,000 human-written solutions. The released Task 1 corpus uses 118,611 wrong solutions; Task 2 uses a proportional 10,000-solution subset. It includes C++, Java, and Python. The paper also uses two high-rated Codeforces experts on 20 sampled problems as a human reference.

**Results.** For Task 2, GPT-4o reaches 31.7% fault exposure; GPT-4.1 reaches 36.5%; Qwen3-32B reaches 43.8%; human experts reach 93.3%. Qwen3-32B reaches 50.8% Fault Coverage@1 and 95.7% at 20 generated inputs. CoT outperforms direct output for the targeted fault-exposure task.

**Concept fit.** High and immediately runnable. The wrong implementation, error type, input constraints, and divergence oracle form a target concept. The repo now has a Python/PyPy Task 2 adapter, but it needs a larger run before reporting a score.

## 4. TestGenEval

Source: [ICLR 2025 paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/26ded5c8ee8ec1bc4caced4e1c9b1584-Paper-Conference.pdf).

**Motivation.** Small standalone functions make unit-test generation look easier than it is in repositories with long files, fixtures, mocks, and existing test suites.

**Method.** TestGenEval adapts SWE-bench repository snapshots into full-file test generation and first/last/extra test-completion tasks. Docker images install each repository version with coverage and mutation tooling.

**Evaluation shape.** The full set contains 1,210 code/test-file pairs from 11 Python repositories and 68,647 human tests. Average code files have 782 lines; average test files have 677 lines; median gold coverage is 60.4%. TestGenEvalLite has 160 pairs. Metrics include pass@1, pass@5, coverage, coverage improvement, and mutation score.

**Results.** GPT-4o gives the highest full-suite coverage at 35.2% and mutation score at 18.8%. Models solve roughly 60-70% of first/last completion tasks, but adding a final test to an already-covered suite usually adds less than 1% coverage.

**Concept fit.** High for project-aware concepts. A useful concept here must include dependency and fixture facts, target behavior, existing-test gaps, and mutation survivors. A line-level concept alone will not survive this benchmark.

## 5. VulEUT

Source: [FORGE 2025 paper](https://doi.org/10.1109/forge66646.2025.00021), [author manuscript](https://arxiv.org/abs/2409.16701).

**Motivation.** A disclosed third-party-library vulnerability matters to a client only when attacker-controlled data can reach the vulnerable code and satisfy its trigger condition.

**Method.** VulEUT builds a client call graph, analyzes parameter propagation along the call path, decides whether the vulnerability condition is reachable from a user-facing entry point, and asks an LLM for a JUnit test. Its oracle checks target-code reachability, trigger-condition satisfaction, and expected vulnerable behavior.

**Evaluation shape.** The study uses 32 third-party-library vulnerabilities across 70 Java client projects. It compares VulEUT against TRANSFER and VESTA and evaluates 292 generated unit tests.

**Results.** 229 of 292 generated tests confirm vulnerability exploitation, a 24% improvement over the reported baselines.

**Concept fit.** Direct match. The existing C/C++ concept work can borrow this shape: focal entry point, call path, parameter transfer type, vulnerability guard, and oracle. The benchmark is small enough to become the first security red/green experiment after the TestCase-Eval subset.

## 6. Directed Greybox Fuzzing via Large Language Model (HGFuzzer)

Source: [paper](https://arxiv.org/abs/2505.03425).

**Motivation.** Coverage-guided fuzzers spend most mutations away from a known risky location. Directed fuzzing needs a valid input that reaches a target path, not another random edge.

**Method.** HGFuzzer collects call chains to a target function, uses static analysis to recover constraints, asks an LLM to repair/complete target-reaching seeds, and combines those seeds with directed greybox fuzzing.

**Evaluation shape.** The paper builds a 20-vulnerability benchmark from real C/C++ libraries and CVE reports, repeats experiments five times, and also runs 24-hour campaigns on two libraries for new-bug discovery.

**Results.** HGFuzzer triggers 17 of 20 target vulnerabilities. The paper reports the highest target-function hit rate among the compared tools and finds new vulnerabilities in the extended campaigns.

**Concept fit.** Very high. The useful concept is not a generic bug label. It is the target call chain, input field constraints, parameter propagation, and the specific guard that must be violated. This is the fuzzing analogue of the current Python symbolic record.

## 7. G2FUZZ: Low-Cost and Comprehensive Non-textual Input Fuzzing with LLM-Synthesized Input Generators

Source: [paper](https://arxiv.org/abs/2501.19282).

**Motivation.** Text-trained LLMs struggle to emit valid binary/document/media inputs. Existing fuzzers often have no grammar for these formats.

**Method.** G2FUZZ asks an LLM to write input generators, debugs the generators, creates structured initial seeds, and then lets a conventional fuzzer mutate them. It targets non-textual formats such as TIFF, MP4, PDF, and image files.

**Evaluation shape.** It evaluates on 10 UNIFUZZ programs, 11 FuzzBench programs, and non-textual MAGMA targets. Experiments run across three systems and repeat key measurements five times.

**Results.** On UNIFUZZ, GPT-4-backed G2FUZZ finds 143 unique bugs, 32 more than the strongest compared fuzzer. Across current program versions it finds 10 unique bugs, four unique to G2FUZZ; developers confirmed three. On MAGMA it finds the most bugs across the selected non-textual targets.

**Concept fit.** High for structured inputs. A concept should name the file grammar, required chunks/fields, cross-field constraints, parser state, and mutation-safe generator operations. This is more useful than handing an LLM a format name and asking for bytes.

## 8. YATE

Source: [paper](https://arxiv.org/abs/2507.18316).

**Motivation.** Raw LLM unit-test generation often stops at a compiling test. Passing assertions and coverage feedback matter more than a one-shot prompt.

**Method.** YATE combines chain-of-thought prompting, compilation repair, assertion repair, and coverage-based augmentation. It generates method-level and class-level Java tests, then repairs or augments them with execution feedback.

**Evaluation shape.** The study uses six Java projects drawn from GitBug Java and other repositories, compares against HITS, SymPrompt, TestSpark, and CoverUp, and evaluates line coverage, branch coverage, mutation score, compilation/pass rate, and request cost.

**Results.** Relative to its plain LLM baseline, YATE reports 32.06 percentage points more line coverage, 28.69 more branch coverage, and 21.77 more mutation score on average. The abstract reports a lower-cost summary of roughly 22% more line coverage, 20% more branch coverage, and 20% more mutants killed. Ablation shows assertion repair affects mutation score more than coverage-only augmentation.

**Concept fit.** High. The current feedback loop should carry concepts across rounds and feed back separate statuses for syntax, assertion, coverage, and semantic fault exposure. YATE argues that coverage feedback alone is too weak; that matches the gap between the current TestEval loop and TestCase-Eval.
