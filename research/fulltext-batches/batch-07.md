# Full-Text Notes, Batch 07 (Catalog #123-#131): Bug-Finding Additions

_Read on 2026-09-26. Added after the TrickyBugs pilot showed that ConceptCoder's static VD concepts (tree-sitter syntax labels) did not improve fault exposure (7/26 vs 7/26). These papers use concepts tied to a specific fault, constraint, or runtime state instead. Same evidence policy as earlier batches._

## 123. KITE: Knowledge-Guided Synthetic Bug Feedback for LLM-Based Unit Test Generation

**Method.** Four stages. (1) Offline, each real-bug record becomes a *semantic mechanism* (what constraint is violated, where it applies, how to inject it) plus a *structural unit* (normalized AST fingerprint with anchor roles `control_header | expression_center | statement_center` and relations `condition_of | expr_in_stmt | guard_to_body | adjacent_stmt | same_block`). (2) A repository knowledge graph supplies calling context, type constraints, and related tests. (3) Dual semantic and structural recall selects mechanisms for the focal method; an injection plan produces a before/after diff that must pass locality, compilation, compatibility, and non-triviality gates. (4) Tests are iteratively improved until they pass the correct method and fail the injected ones.

**Motivation.** Coverage and mutation score are proxies; they carry no information about how real bugs behave.

**Dataset + shape.** 172 method-level Defects4J tasks (Cli 24, Compress 32, Csv 11, JacksonDatabind 51, Jsoup 54). Knowledge base: 2,069 of 2,083 records from Defects4J, Bears, Bugs.jar, GitBug-Java, GHRB (benchmark projects excluded), giving 1,686 unit-structure records and 1,325 reviewed mechanisms. Model: gpt-5.4, temperature 0.1.

**Evaluation results.** Real-bug detection rate 72.67% vs MutGen 52.33%, CoverUp 48.26%, KTester 47.09%, ChatUniTest 45.35%, EvoSuite 29.07%, direct LLM 23.26%. Removing synthetic-bug feedback drops it to 52.91% (-19.76 pp). Synthetic kill rate 81.85%; 19 bugs found only by KITE; 0.177M tokens per task.

**Concept applicability.** Direct fit. The concept is a retrieved bug mechanism turned into an executable synthetic bug. For TrickyBugs, the knowledge base would be built from competitive-programming bug records instead of Java repositories.

**Evidence.** Full text read (arXiv HTML). Code not stated. Primary source: <https://arxiv.org/abs/2607.11573>

## 124. CodeHacker: Automated Test Case Generation for Detecting Vulnerabilities in Competitive Programming Solutions

**Method.** Phase I calibrates the evaluation tools. The validator is attacked with invalid inputs (bypass) and valid edge cases (rejection) and patched until it matches the statement. The checker is attacked with deceptive and alternative-valid outputs, backed by an anti-hallucination pipeline (small inputs, explicit reasoning, independent LLM judge); humans intervened in under 5% of cases. Phase II has a code analyst that uses static reading plus a C++ sandbox and a Python calculator. It drives three cascading generators: stress (size and structure extremes), LLM-targeted (WA/RE/TLE/MLE for the identified weakness), and anti-hash (lattice reduction or birthday attack).

**Motivation.** Benchmarks miss corner cases, so wrong solutions pass. Tests must target the logic weaknesses of one concrete implementation.

**Dataset + shape.** 2,000 CodeContest+ problems (1,000 standard judge, 1,000 special judge; C++). CodeHackerBench has about 6,000 human-verified problem–submission pairs. The RL study uses 287 AtCoder problems from LiveCodeBench. Models: DeepSeek V3.2, GPT-5-Mini, Qwen3-Next-80B-A3B, **Gemini-3.0-Flash**, Qwen3-32B; RL on Qwen3-4B.

**Evaluation results.** TNR on standard-judge problems rises to 96.31%, vs 85.72% for CodeContest+ and 76.33% for CodeContests. Valid-input rate is 100%. Hack success rate: DeepSeek V3.2 64.83%, GPT-5-Mini 51.40%, Gemini-3.0-Flash 35.65%. RL on the new tests raises LiveCodeBench Medium pass@5 from 73.53% to 80.88%.

**Concept applicability.** Closest to TrickyBugs. The concept is an implementation-specific weakness hypothesis paired with a calibrated validator. This directly fixes the invalid-input failure seen in the pilot (declaring N=200000 but supplying 696 numbers).

**Evidence.** Full text read. Code not stated. Primary source: <https://arxiv.org/abs/2602.20213>

## 125. AutoCode: LLMs as Problem Setters for Competitive Programming

**Method.** Validator: the LLM writes 40 cases (10 valid, 30 near-valid illegal) and 3 candidate validators; the one that classifies the most cases correctly is kept. Generator: small-data exhaustion, randomized/extreme values (overflow, precision), and TLE-inducing structures; outputs are filtered by the validator, deduplicated, and balanced. Checker: 3 candidates scored on 40 labelled outputs. A problem counts only when every test's outputs are validated pairwise.

**Motivation.** High false-positive and false-negative rates in test suites mislead RL and evaluation.

**Dataset + shape.** 7,538 problems from the intersection of CodeContests+, CodeContests, HardTests, TACO; 720 recent rated Codeforces problems. Models: o3 (main), GPT-4o, GPT-5-High.

**Evaluation results.** Consistency 91.1% vs HardTests 81.0%; FPR 3.7% vs 12.1%; FNR 14.1% vs 25.8%. On the 720 Codeforces problems: consistency 98.7%, FPR 1.3%, FNR 1.2%.

**Concept applicability.** Supplies the constraint layer: a selected validator is the executable form of the input constraints. It is a prerequisite for any fault-hypothesis concept on TrickyBugs.

**Evidence.** Full text read. Project page: <https://livecodebenchpro.com/projects/autocode/overview>. Primary source: <https://arxiv.org/abs/2510.12803>

## 126. Specification Grounding Drives Test Effectiveness for LLM Code

**Method.** A controlled ablation. The tester prompt differs by one line: `spec` gets the specification enumerated into discrete rules (one test per rule); `free+` gets the ticket and is told to probe invalid inputs and edge cases. Both arms share the same repair loop and a hidden hand-written gold oracle.

**Motivation.** It separates the effect of test quantity from grounding in the specification.

**Dataset + shape.** 18 specification-completeness tasks (8 core, 4 held-out, 6 scale-up) plus 8 logic tasks; 48 core instances. Models: Claude Haiku 4.5, Sonnet 4.6, Opus 4.8, GPT-5.3-codex, Gemini 3.5 Flash.

**Evaluation results.** Core final correctness: spec 100% vs free+ 60%. Detection: 30/30 vs 18/30. False alarms: 0% vs 33%. Ablation: no spec 0/30, CoT plan 2/30, spec as prose 27/30, enumerated spec 30/30. Gemini 3.5 Flash gap +19 pp. Sign test p=0.002.

**Concept applicability.** Strong and cheap. It shows that *enumerated* rules beat both prose and "think about edge cases". A concept record should therefore be one atomic rule, one test.

**Evidence.** Full text read. Code not stated. Primary source: <https://arxiv.org/abs/2607.06636>

## 127. Extremal Testing for Network Software using LLMs

**Method.** The LLM lists input validity constraints (e.g. DNS name length), then generates tests that violate them. Filtering code rejects unusable extremal inputs. The method is extended with agentic automation and to shortest-path algorithms.

**Motivation.** Boundary value analysis needs hand-written constraints; LLMs can enumerate richer ones.

**Dataset + shape.** HTTP, BGP, and DNS implementations; shortest-path algorithms.

**Evaluation results.** The abstract reports new bugs in each subject; counts are not stated there.

**Concept applicability.** Moderate. The concept is constraint → violating input. For competitive programming, the variant that fits is inputs *at* the constraint boundary rather than beyond it.

**Evidence.** Abstract-only. Primary source: <https://arxiv.org/abs/2507.11898>

## 128. ReDig: Refining LLM-based Directed Test Input Generation via Runtime Value Feedback

**Method.** The LLM generates inputs for a target line from the function and its shortest call path, and coverage is measured with llvm-cov. On a miss, the LLM proposes up to 5 runtime value queries (location + gdb expression); a gdb script collects the values, and the generator revises the seed input. A controller schedules 5 trials and restarts when progress stalls. 4,343 LoC of Python.

**Motivation.** LLMs make plausible but wrong assumptions about runtime behavior; the process needs to be grounded in observed values.

**Dataset + shape.** Case studies on Poppler and libsndfile (2 target lines each); pilot on 120 functions per project. Model: gpt-5.4, temperature 0.

**Evaluation results.** 3 of 4 case studies succeed in 2 turns (91K–122K tokens); one fails after 7 turns (344K tokens). Work in progress; no baseline comparison.

**Concept applicability.** It is the online version of ConceptCoder's BP concepts (branch direction and quantized values): only the runtime values that explain a miss are collected, on demand.

**Evidence.** Full text read. Code not stated. Primary source: <https://arxiv.org/abs/2608.07926>

## 129. AnyPoC: Universal Proof-of-Concept Test Generation for Scalable LLM-Based Bug Detection

**Method.** An analyzer subagent checks the bug mechanism (root cause, consequence, required oracle) and filters false reports. A generator iterates a PoC until it triggers the bug, then re-runs it and saves traces as evidence. A checker defines the expected signals, re-executes the PoC in a fresh workspace, and verifies the signals and realism. A self-evolving knowledge base stores entries by project and category, each with keywords, a usefulness rating, and a version.

**Motivation.** Verifying LLM bug reports by hand is the bottleneck.

**Dataset + shape.** 12 systems (Chromium, Firefox, LLVM, OpenSSL, FFmpeg, SQLite, Wasmtime, Redis, FreeType, QuickJS, Hermes, Memcached); about 2,700 candidate reports; a 192-report validation set. Models: Claude Sonnet/Opus 4.5–4.6, GPT-5.2/5.3-Codex.

**Evaluation results.** 37% more valid PoCs than Claude Code or Codex, and 9.7× more false-positive rejections. 121 new bugs found, 108 confirmed, 92 fixed, 46 PoCs adopted as regression tests.

**Concept applicability.** The concept is a bug hypothesis with an explicit required oracle, and the independent re-execution check guards against hallucinated wins. That check is the missing step behind the pilot's false 8/26.

**Evidence.** Full text read. Code not stated. Primary source: <https://arxiv.org/abs/2604.11950>

## 130. MutGen: Mutation-Guided Unit Test Generation with a Large Language Model

**Method.** Mutation feedback goes into the prompt and generation repeats to kill surviving mutants. The paper also analyzes why mutants survive, per operator.

**Motivation.** A suite can reach 100% coverage with only a 4% mutation score.

**Dataset + shape.** 204 subjects from two benchmarks; compared with EvoSuite and vanilla prompting.

**Evaluation results.** The abstract reports a significantly higher mutation score than both baselines. KITE (#123) reports MutGen at 52.33% RBDR on Defects4J.

**Concept applicability.** The concept is a surviving mutant. Already partly covered by `testeval_py/mutation_loop.py` in this repo.

**Evidence.** Abstract-only. Primary source: <https://arxiv.org/abs/2506.02954>

## 131. TrickCatcher: LLM-Powered Test Case Generation for Detecting Bugs in Plausible Programs

**Method.** (1) PUT-guided variant generation: the LLM sees the spec and the PUT and writes repaired variants. (2) The LLM writes a Python input generator from the constraints instead of writing inputs directly. (3) Diversity-driven differential testing: when a variant disagrees with the PUT, the variant's output (the most frequent one if several disagree) becomes the oracle.

**Motivation.** Variant correctness is low on hard tasks, and 40.10% of directly generated inputs are invalid.

**Dataset + shape.** TrickyBugs: 366 human-written plausible programs (251 C++, 115 Python). EvalPlus: 151 AI-generated buggy programs. Models: gpt-3.5-turbo-0125 (main), deepseek-v3.

**Evaluation results.** Best F1: TrickyBugs C++ 41.31% vs DPP 24.95%; Python 42.35% vs 36.20%; EvalPlus 51.34% vs 35.76%. Recall up to 1.80× and precision up to 2.65× over DPP.

**Concept applicability.** This is the baseline already used in `trickcatcher_pilot`. Concepts can enter at every stage: variant generation (which fault to repair), the generator (which constraint boundary to hit), and oracle selection.

**Evidence.** Full text read. Code: <https://github.com/RinCloud/TrickCatcher>. Primary source: <https://aclanthology.org/2025.acl-long.20/>
