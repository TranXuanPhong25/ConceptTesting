# Quét base paper 2025–2026 cho hướng concept-guided test generation (2026-10-10)

Nguồn: 4 agent (Claude B: cs.SE; Claude C: bug/oracle/PBT; Codex 1: danh sách accepted ICSE/FSE/ISSTA/ASE/ICST/ICLR/NeurIPS; Codex 2: arXiv + ACL Anthology). Agent Claude A (ACL/NeurIPS) bị dừng giữa chừng, không có kết quả.
Đã loại trước: mọi paper trong `research/llm-test-generation-2025-2026.md` + UTGen, SAGA, HardTests, CodeContests-O/+, ConVerTest, TCGBench, TestCase-Eval, TestEval, TestGenEval, TrickCatcher, MutGen, test-aware mutants, AdverTest, KITE, CodeHacker, UTRL, CoverUp.
Khả thi (F) 1–5 do agent chấm theo ràng buộc: CPU-only, ~$20 Gemini, ưu tiên Python, có code. Báo cáo gốc: `scratchpad/papers/{codex1,codex2}/REPORT.md` và tin nhắn agent B/C.

Tổng: **121 paper** sau khi bỏ trùng. A 21, B 23, C 16, D 13, E 16, F 23, G 9

## B. Lõi: test bắt bug trong code (buggy vs đúng) (23)

| F | Paper | ID | Venue / ngày | Ngôn ngữ, benchmark | Code, license | LLM | Agent |
|---|---|---|---|---|---|---|---|
| 5 | VIBEPASS: Can Vibe Coders Really Pass the Vibe Check? | 2603.15921 | arXiv Mar 2026 (Salesforce) | Python; 173 buggy LCB solutions | vibepass Apache/MIT | 12 LLMs incl Gemini 3 | Claude-C |
| 4 | RTED: Reflective Unit Test Generation for Type Error Detection | 2507.02318 | ASE 2025 | Python; BugsInPy, TypeBugs | RTED no/CC-BY badge | DeepSeek-V3, Qwen3-Coder | Claude-B,Codex-1 |
| 4 | PBT-Bench: Benchmarking AI Agents on Property-Based Testing | 2605.15229 | NeurIPS 2026 D&B | Python; 365 injected bugs | PBTbench NOASSERTION | 8 LLMs incl Gemini 3 | Claude-B |
| 4 | Incoherence as Oracle-less Measure of Error (DiffTrust) | 2507.00057 | AAAI 2026 | Python; HE, MBPP | difftrust NOASSERTION | 16 LLMs | Claude-C |
| 4 | Revisit Self-Debugging with Self-Generated Tests | 2501.12793 | ACL 2025 | Python; HE+, MBPP+, LCB | not found | GPT-4o, Claude | Claude-C |
| 4 | LLMutantKiller: Using Large Language Models to Generate Tests that Kill Mutants | Author paper https://www.franktip.org/pubs/issta2026.pdf; DO | ISSTA 2026, Oct | JavaScript/TypeScript, Jest; 13 projects with surviving muta | [Artifact]; author software MIT; other material has separate | Claude Sonnet 4.6, Devstral-2512, Llama-3.3-7 | Codex-1 |
| 3 | DISTINCT: Description-Guided Branch-Consistency for Non-Regressive Tests | 2506.07486 | arXiv Jun 2025 | Java; Defects4J-Desc, QuixBugs-Desc | DISTINCT MIT badge | Qianfan, DeepSeek | Claude-B |
| 3 | DeCon: Detecting Incorrect Assertions via LLM Postconditions | 2501.02901 | arXiv Jan 2025 | Python; HumanEval | DeCon no license | GPT-3.5/4 | Claude-B |
| 3 | LLM vs Human Unit Tests: Fault Detection on Real Python Bugs | 2606.08588 | arXiv Jun 2026 | Python; BugsInPy | no link | Gemini 2.5 Flash | Claude-B |
| 3 | X-PBT: Cross-Model Property-Based Testing of Code | ICML26-ws-77983 | ICML 2026 workshop | Python; HumanEval, MBPP+ | none | Claude, GPT | Claude-C |
| 3 | Nexus: Multi-Agent Test Oracle Synthesis | 2510.26423 | arXiv Oct 2025 | Python; HE, MBPP, LCB, ULT | none | GPT-4.1 | Claude-C |
| 3 | REFUTE: Can Language Models Falsify? | 2502.19414 | arXiv Feb 2025 | C++; Codeforces | REFUTE Apache-2.0 | DeepSeek, Gemini 2.0 | Claude-C |
| 3 | SWE-Mutation: Can LLMs Generate Reliable Test Suites in Software Engineering? | 2605.22175 | arXiv 21 May 2026; ACL venue claimed by  | Python core plus nine other languages; paper: 800 instances, | [SWE-Mutation]; MIT; Python harness; released variant counts | Claude Sonnet 3.7/4.5, DeepSeek-V3.1, Qwen3-C | Claude-C,Codex-2 |
| 3 | Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests | 2607.22883 https://arxiv.org/abs/2607.22883 | ISSTA 2026, Oct; arXiv 2026-07-24 | Java; Defects4J/LLM4UT-based evaluation | [EvalAndMitigate]; MIT, third-party terms retained | Models U; inference generation; internal-mode | Codex-1,Codex-2 |
| 3 | Real-World Fault Detection for C-Extended Python Projects with Automated Unit Test Generat | 2603.06107 https://arxiv.org/abs/2603.06107 | ICST 2026, May; arXiv 2026-03-06 | Python/C; 1,648 modules from 21 libraries | [Artifact DOI]; archive/license U | Core method does not require LLM; Pynguin als | Codex-1 |
| 3 | Beyond Superficial Tests: Adversarial Refinement for Reliable Property-Based Testing | https://aclanthology.org/2026.findings-acl.683/ | Findings ACL, Jul 2026 | Python; 256 functions from sympy, sortedcontainers, more-ite | [PROBE]; public; license not visible | DeepSeek-V3.2, GPT-5, Qwen3-Next-80B; no task | Codex-2 |
| 3 | Adversarial Test-Hardening for AI-Written Code: An Instrument Autopsy and a Pre-Registered | https://arxiv.org/abs/2607.23002 | arXiv 25 Jul 2026; unreviewed preprint | Python; five modules in experiment 1, four in experiment 2;  | [crucible]; MIT; Python; experimental receipts | Paper identifiers claude-sonnet-5 / gpt-5.6-t | Codex-2 |
| 2 | Traditional test criteria vs bugs in LLM-generated code | 2609.09315 | arXiv Sep 2026 | Python; HE+, MBPP, BCB | none | Llama, GPT | Claude-B |
| 2 | On the risk of coding before testing | 2607.05139 | arXiv Jul 2026 | Python; HE+, MBPP, BCB | none | GPT-5-mini | Claude-B |
| 2 | Auditing Feedback-Driven Evolution in LLM Test Gen under Oracle Problem | 2608.19626 | arXiv Aug 2026 | Python; CodeContests | anonymous | Qwen local | Claude-B |
| 2 | Class-level LLM test suites in Python (ClassEval + Cosmic Ray) | 2609.24341 | arXiv Sep 2026 | Python; ClassEval | none | LLM | Claude-B |
| 2 | Boundary Value Test Input Generation with LLMs | 2501.14465 | arXiv Jan 2025 | C/C++ small programs | none | GPT-4o | Claude-C,Codex-2 |
| 2 | Coding Agents as Test-Suite Auditors: Finding What Official Suites Miss While Approaching  | https://arxiv.org/abs/2608.01715 | arXiv 3 Aug 2026 | Competitive-programming stdin/stdout; AtCoder and post-cutof | [test-suite-auditors], [agentic-testgen]; artifact license n | GPT-5.4, Claude Opus 4.8, Gemini 3.1 Pro, Dee | Codex-2 |

## D. Patch / PR / regression (13)

| F | Paper | ID | Venue / ngày | Ngôn ngữ, benchmark | Code, license | LLM | Agent |
|---|---|---|---|---|---|---|---|
| 4 | TestWeaver: Execution-aware Feedback-driven Regression Test Generation | 2508.01255 | ICSE 2026 | Python; CodaMosa suite | TestWeaver Apache-2.0 | GPT-4o; no train | Claude-B,Codex-1 |
| 3 | Test4Py: Type-aware LLM Regression Test Generation for Python | 2503.14000 | arXiv Mar 2025 | Python; 183 modules | Test4Py no license | OpenAI-compat | Claude-B |
| 3 | Testora: Using NL Intent to Detect Behavioral Regressions | 2503.18597 | ICSE 2026 | Python; scipy/pandas PRs | Testora MIT | GPT-4o(-mini), R1 | Claude-B |
| 3 | DiffTestGen: Change-Directed LLM Testing for Behavioral Differences | 2607.16024 | arXiv Jul 2026 | Python; 463 PRs | DiffTestGen MIT | gpt-5-mini | Claude-B |
| 3 | PatchGuru: Patch Oracle Inference from NL Artifacts | 2602.05270 | arXiv Feb 2026 | Python; 400 PRs | PatchGuru Apache-2.0 | GPT-5-mini | Claude-B |
| 3 | UTBoost: Rigorous Evaluation of Coding Agents on SWE-Bench | 2506.09289 | ACL 2025 | Python; SWE-bench | UTBoost MIT | GPT-4o | Claude-C,Codex-2 |
| 3 | Change And Cover: Last-Mile, Pull Request-Based Regression Test Augmentation | 2601.10942 https://arxiv.org/abs/2601.10942 | ICSE 2026, Apr; arXiv 2026-01-16 | Python; SciPy, Qiskit, Pandas PRs | [ChaCo]; license U | GPT-4o-mini referenced; complete inventory U; | Codex-1 |
| 3 | Evaluating LLM-based Regression Test Generation | Official paper https://conf.researchr.org/details/fse-2026/f | FSE 2026, Jul | Structured inputs; 46 commits in MuJS, Libxml2, Poppler, Jer | [Cleverest]; MIT | Models U; zero-shot inference, no training | Codex-1 |
| 3 | Improving Automated Patch Correctness Assessment by Designing LLM-Based Oracles | Official paper https://conf.researchr.org/details/icst-2026/ | ICST 2026; presentation 2026-05-19 | Java; 109 incorrect Defects4J patches | [Artifact-track entry]; archive/license U | GPT-4o, GPT-4o-mini, Llama-3.2-3B; no trainin | Codex-1 |
| 2 | Cleverest: Evaluating LLM-Based Regression Test Generation | 2501.11086 | FSE 2025/26 | C structured inputs | cleverest MIT | GPT-4o, R1 | Claude-B,Codex-2 |
| 2 | On the Risks of LLM-Generated Tests for Regression Testing | 2610.11835 | arXiv Oct 2026 | Python; 145 PRs | figshare | Claude Haiku | Claude-B |
| 2 | Evaluating LLM Test Generation Under Software Evolution | 2603.23443 | arXiv Mar 2026 | Python; 22k variants | none | 8 LLMs | Claude-B |
| 2 | PR-Aware Automated Unit Test Generation | 2605.25285 | arXiv May 2026 | Java | ? | GPT-4o | Claude-C |

## C. Tái hiện bug từ issue (SWT-bench / TDD-bench) (16)

| F | Paper | ID | Venue / ngày | Ngôn ngữ, benchmark | Code, license | LLM | Agent |
|---|---|---|---|---|---|---|---|
| 3 | AssertFlip: Reproducing Bugs via Inversion of Passing Tests | 2507.17542 | ICSE 2026 | Python; SWT-bench | AssertFlip Apache-2.0 | GPT-4o | Claude-B,Codex-1,Codex-2 |
| 3 | Issue2Test: Reproducing Test Cases from Issue Reports | 2503.16320 | ICSE 2026 | Python; SWT-bench Lite | issue2test no license | GPT-4o-mini etc | Claude-B,Codex-1,Codex-2 |
| 3 | Echo: Graph Retrieval + Execution Feedback for Issue Reproduction | 2603.07326 | arXiv Mar 2026 | Python; SWT-bench Verified | Echo no license | GPT-4o, Gemini-2.5 | Claude-B,Codex-2 |
| 3 | TestPrune: Old Tests for Resolving SWE Issues | 2510.18270 | FSE 2026 | Python; SWE-bench | Issue-Test-Localizer Apache-2.0 | GPT-4o | Claude-B |
| 3 | PatchDiff: Are Solved Issues in SWE-bench Really Solved? | 2503.15223 | ICSE 2026 | Python; SWE-bench Verified | PatchDiff no license | gpt-4o-mini | Claude-C |
| 3 | Automated Generation of Issue-Reproducing Tests by Combining LLMs and Search-Based Testing | 2509.01616 https://arxiv.org/abs/2509.01616 | ASE 2025, Nov; arXiv 2025-09 | Python; curated 426 issue/patch pairs and live PR study | Public implementation/data link and license U | Models U; LLM + SBST; no training described | Codex-1,Codex-2 |
| 2 | iCoRe: Correlation-Aware Retriever for Bug Reproduction Tests | 2604.19224 | FSE 2026 | Python; SWT-bench, TDD-bench | iCoRe no license | GPT-4o, DS-V3 | Claude-B,Codex-1,Codex-2 |
| 2 | Otter: Generating Tests from Issues to Validate SWE Patches | 2502.05368 | ICML 2025 | Python; TDD-Bench-Verified | benchmark Apache-2.0 | GPT-4o | Claude-B,Codex-2 |
| 2 | e-Otter++: Heterogeneous Prompting for SWE Issue Test Generation | 2508.06365 | ICSE 2026 | Python; TDD-Bench-Verified | outputs only | GPT-4o, Claude-3.7 | Claude-B,Claude-C,Codex-1,Codex-2 |
| 2 | EvoOtter: Evolutionary Reproduction Test Generator | 2607.02854 | arXiv Jul 2026 | Python; TDD-Bench-V | none | Claude 4.5 | Claude-B |
| 2 | CoHarden: Iterative Hardening of Co-Generated BRTs and Fixes | 2607.19843 | arXiv Jul 2026 | Python; SWE-bench | none | GPT-5-mini | Claude-B,Codex-2 |
| 2 | ReProAgent: Multi-Stage Agentic Bug Reproduction Tests | 2607.09123 | arXiv Jul 2026 | Python; SWT-bench | ReProAgent (license?) | GPT-5-mini | Claude-B,Codex-2 |
| 2 | Enhancing LLM-based Bug Reproduction via Code Entity Retrieval and Test Case Repair | Official paper https://conf.researchr.org/details/issta-2026 | ISSTA 2026, Oct | Java; Defects4J, recent-bug GHRB | Public code/data/license U | Models U; inference/retrieval/repair, no trai | Codex-1 |
| 2 | Reproduction Test Generation for Java SWE Issues | https://arxiv.org/abs/2605.04320 | arXiv 5 May 2026; v2 7 May 2026 | Java; TDD-Bench-Java, 250 public instances; additional priva | [TDD-Bench-Java]; repository Apache-2.0; generator not verif | Claude Sonnet 4.5, GPT-5.2; no training | Codex-2 |
| 1 | DPIAgent: Agentic Reproduction Tests | 2608.23341 | arXiv Aug 2026 | Python; SWT-bench V | none | GPT-5 | Claude-B |
| 1 | Multi-SWT-Bench: Multilingual Reproduction Test Benchmark | 2609.34752 | arXiv Sep 2026 | 8 langs | none | agents | Claude-B |

## A. Sinh unit test (coverage / path / context) (21)

| F | Paper | ID | Venue / ngày | Ngôn ngữ, benchmark | Code, license | LLM | Agent |
|---|---|---|---|---|---|---|---|
| 3 | TestTailor: Generating High-Coverage Tests via Path-Proximal Tests with LLMs | Official paper https://conf.researchr.org/details/fse-2026/f | FSE 2026; presentation 2026-07-08 | Python; CodaMosa benchmark, 486 modules in this paper | Implementation link and license U | Multiple backbones, names U; no training desc | Codex-1 |
| 3 | LSPRAG: LSP-Guided RAG for Language-Agnostic Real-Time Unit Test Generation | 2510.22210 https://arxiv.org/abs/2510.22210 | ICSE 2026, Apr; arXiv 2025-10-25 | Java, Go, Python projects; artifact also supports C++ | [LSPRAG]; Apache-2.0 | DeepSeek-chat/OpenAI/Ollama providers; exact  | Codex-1 |
| 3 | Clarifying Semantics of In-Context Examples for Unit Test Generation | 2510.01994 https://arxiv.org/abs/2510.01994 | ASE 2025, Nov; arXiv 2025-10-02 | Java; Defects4J/open-source and industrial projects | [CLAST]; license U | DeepSeek-V2.5 rewriting; CodeLlama-7B/DeepSee | Codex-1 |
| 2 | Panta: Iterative Hybrid Program Analysis Test Generation | 2503.13580 | ICSE 2026 | Java | Panta no license | GPT-4o | Claude-B,Codex-1 |
| 2 | JUnitGenie: Path-Sensitive Unit Test Generation | 2509.23812 | ASE 2025 | Java | none | GPT-4o | Claude-B,Codex-1 |
| 2 | Seed&Steer: Compilable Prefix and Branch Signals | 2507.17271 | arXiv Jul 2025 | Java | 404 | GPT-4 | Claude-B |
| 2 | NEUROTESTGEN: Neuro-Symbolic Guided Test Generation | 2609.30178 | arXiv Sep 2026 | Java; Defects4J | anonymous | Claude, GPT-4o | Claude-B |
| 2 | PALM(UCLA): Path-aware LLM Test Generation | 2506.19287 | arXiv Jun 2025 | Java | PALM no license | o3-mini | Claude-B |
| 2 | TATG: Tracking-Aware Testing Objective | 2607.03194 | arXiv Jul 2026 | Java | none | Qwen3.6 | Claude-B |
| 2 | Do Coverage/Mutation Scores of LLM Test Suites Correlate with Effectiveness | 2607.22880 | ISSTA 2026 | Java; Defects4J | MIT | several | Claude-B,Codex-1 |
| 2 | TestForge: Feedback-Driven Agentic Test Suite Generation | 2503.14713 | arXiv Mar 2025 | Python; TestGenEval | anonymous | GPT-4o | Claude-B |
| 2 | TestGeneralizer: Generalizing Test Cases for Scenario Coverage | 2604.21771 | FSE 2026 | Java | no license | o4-mini | Claude-B,Codex-1 |
| 2 | MuMuTestUp: test update with surviving-mutant agent | 2605.19265 | arXiv May 2026 | Java | GitHub | LLM | Claude-B |
| 2 | ConUT: Condition-Aware Test Generation for Complex Java Code | Official paper https://conf.researchr.org/details/issta-2026 | ISSTA 2026, Oct | Java; eight projects with complex logic hotspots | Code/data/license U | Models U; static-analysis-guided inference, n | Codex-1 |
| 2 | SAINT: Service-level Integration Test Generation with Program Analysis and LLM-based Agent | 2511.13305 https://arxiv.org/abs/2511.13305 | ICSE 2026, Apr; arXiv 2025-11-17 | Java REST; eight applications, one proprietary | Public code/license U | Models U; inference agents, no training descr | Codex-1 |
| 2 | Context Matters: Improving the Practical Reliability of LLM-Based Unit Test Generation (Ex | 2607.19682 https://arxiv.org/abs/2607.19682 | ISSTA 2026, Oct; arXiv 2026-07-22 | Java; proprietary projects plus Defects4J | Public implementation/data/license U | Models U; no training described | Codex-1 |
| 2 | Uncovering Business Logic Bugs via Semantics-Driven Unit Test Generation (Experience Paper | 2604.23509 https://arxiv.org/abs/2604.23509 | ISSTA 2026, Oct; arXiv 2026-04-26 | Go; four industrial projects, 60 real bugs; six-repository d | Public code/requirements/data/license U | Models U; no training described | Codex-1 |
| 1 | EvoGPT: LLM-Driven Seed Diversity for SBST | 2505.12424 | arXiv May 2025 | Java; Defects4J | none | LLM+EA | Claude-B |
| 1 | LLM test-gen techniques with newer LLMs | 2601.09695 | arXiv Jan 2026 | Java | near-empty | DeepSeek-V3 | Claude-B |
| 1 | TestPrism: multi-implementation test evaluation benchmark | 2610.12289 | arXiv Oct 2026 | ? | none | LLM | Claude-B |
| 1 | LLM Unit Tests with Equivalence Partitions and Boundary Values | 2505.09830 | JCC 2025 | ? | ? | LLM | Claude-C |

## E. PBT / oracle / metamorphic / judge (16)

| F | Paper | ID | Venue / ngày | Ngôn ngữ, benchmark | Code, license | LLM | Agent |
|---|---|---|---|---|---|---|---|
| 3 | PGS: Property-Oriented Minimal Feedback for Code Refinement | 2506.18315 | ICML 2026 | Python; HE, MBPP, LCB | supplementary | DeepSeek, Qwen, Claude | Claude-C |
| 3 | CodeJudgeBench: LLM-as-a-Judge for Coding | 2507.10535 | arXiv Jul 2025 | Python; LCB | HF | 26 judges | Claude-C |
| 3 | MR-Coupler: Automated Metamorphic Test Generation via Functional Coupling Analysis | 2604.10126 https://arxiv.org/abs/2604.10126 | FSE 2026, Jul; arXiv 2026-04-11 | Java; 100 human metamorphic tests, 50 real bugs | [Artifact]; contents/license U | Models U; inference, amplification/mutation;  | Codex-1 |
| 3 | Improving Dynamic Specification Inference with LLM-Generated Counterexamples | 2604.10761 https://arxiv.org/abs/2604.10761 | ICST 2026, May; arXiv 2026-04-12 | Java; SpecFuzzer, GAssert/EvoSpex benchmarks | [Author artifact URL]; usable record/content/license U | GPT-5.1, Llama-3.3-70B, DeepSeek-R1; no train | Codex-1 |
| 3 | DebateCoder: Towards Collective Intelligence of LLMs via Test Case Driven LLM Debate for C | https://aclanthology.org/2025.acl-long.589/ | ACL, Jul 2025 | Code-generation tasks; Python-style execution; two benchmark | [DebateCoder]; public; license not visible | Claude 3.5 Sonnet + GPT-4o-mini; Qwen-32B/Lla | Codex-2 |
| 2 | Agentic Property-Based Testing across Python Ecosystem | 2510.09907 | NeurIPS25 DL4C ws | Python; 100 PyPI | agentic-pbt no license | Claude Code | Claude-B,Codex-1 |
| 2 | MCTS-Judge: Test-Time Scaling LLM-as-Judge | 2502.12468 | arXiv Feb 2025 | code benchmarks | ? | 5 LLMs | Claude-C |
| 2 | CodeMetaAgent: Metamorphic Specification Mutation | 2511.18249 | arXiv Nov 2025 | Python; HE-Pro, MBPP-Pro | none | GPT-4o | Claude-C |
| 2 | Grounding AI Agents in Contracts: Spec-Driven Test Generation | 2608.17177 | SpecOps 2026 ws | multi; Google internal | private | Gemini 3 Flash | Claude-C |
| 2 | From Business Requirements to Test Assertions | 2607.10277 | arXiv Jul 2026 | Java; Defects4J Lang | ? | 5 LLMs | Claude-C |
| 2 | LISA: LLM-Based Invariant Testing for Functional Bugs | 2607.18711 | ISSRE 2026 | C/C++ | CNTG no license | gpt-5-mini | Claude-C |
| 2 | SpecMind: Multi-Turn Postcondition Inference | 2602.20610 | ACL 2026 | ? | ? | LLM | Claude-C |
| 2 | Round-Trip Mutation Testing | 2607.03223 | ICSTW 2026 | 40 buggy methods | ? | LLM | Claude-C |
| 2 | Industrial Practice of LLM-based Test Case Carving and Assertion Generation (Experience Pa | 2607.24000 https://arxiv.org/abs/2607.24000 | ISSTA 2026, Oct; arXiv 2026-07-27 | Microservice API traffic; language/benchmark details U | Public code/captures/license U | Models U; inference plus deterministic algori | Codex-1 |
| 1 | ChatGPT generating Metamorphic Relations | 2503.22141 | arXiv Mar 2025 | 9 SUTs | none | GPT-4 | Claude-C |
| 1 | ClassInvGen: Class Invariant Synthesis | 2502.18917 | arXiv Feb 2025 | C++ | ? | LLM | Claude-C |

## G. Fuzzing / miền khác (9)

| F | Paper | ID | Venue / ngày | Ngôn ngữ, benchmark | Code, license | LLM | Agent |
|---|---|---|---|---|---|---|---|
| 3 | Cottontail: Large Language Model-Driven Concolic Execution for Highly Structured Test Inpu | https://arxiv.org/abs/2504.17542 | IEEE S&P 2026 (metadata); arXiv 24 Apr 2 | C/C++ parser targets; XML, SQL, JS, JSON; eight libraries on | [cottontail]; GPL-3.0; C++ and Python | GPT-4o-mini / GPT-4o; DeepSeek-V3 and GPT-4.1 | Codex-2 |
| 3 | LogicHunter: Testing LLM Agent Frameworks with an Agentic Oracle | https://arxiv.org/abs/2607.06195 | arXiv 7 Jul 2026 | Python; LangChain, LlamaIndex, CrewAI; public API tests and  | [LogicHunter]; MIT; Python 3.10 | DeepSeek-V3 generation + GPT-5-mini oracle; n | Codex-2 |
| 2 | OpDiffer: LLM-Assisted Opcode-Level Differential Testing of Ethereum Virtual Machine | 2504.12034 https://arxiv.org/abs/2504.12034 | ISSTA 2025, Jun; arXiv 2025-04-16 | EVM bytecode/Python seed generators; nine EVMs | Public code/data/license U | GPT-4 discussed; complete inventory U; no tra | Codex-1 |
| 2 | ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space | https://arxiv.org/abs/2506.10323 | USENIX Security 2025 (metadata); arXiv 1 | Python input generators; parser/solver targets including cvc | [Author archive]; paper-linked; archive fetch failed; code l | CodeLlama-13B; no task fine-tuning; original  | Codex-2 |
| 2 | SeedSmith: LLM-Driven Seed Synthesis for Directed Fuzzing | https://arxiv.org/abs/2607.08949 | arXiv 9 Jul 2026; v2 14 Jul 2026 | C/C++ structured-input targets; Magma, ARVO; AFL++/AFLGo | No author implementation endpoint verified; license unknown | Claude Sonnet 4 exploration + GPT-4.1-mini se | Codex-2 |
| 1 | VistaFuzz: Document-Guided Fuzzing of Python Libraries | 2608.11744 | arXiv Aug 2026 | Python; 12 libs | ? | local LLM GPU | Claude-C,Codex-2 |
| 1 | Clotho: Measuring Task-Specific Pre-Generation Test Adequacy for LLM Inputs | 2509.17314 https://arxiv.org/abs/2509.17314 | FSE 2026, Jul; arXiv 2025-09-22 | Eight LLM tasks, three open-weight LLMs; not a unit-test ben | [Clotho]; repo retrieved in search; contents/license U | Hidden-state access + GMM fitting; model name | Codex-1 |
| 1 | Mut4All: Fuzzing Compilers via LLM-Synthesized Mutators Learned from Bug Reports | https://arxiv.org/abs/2507.19275 | arXiv 25 Jul 2025; v3 5 Oct 2026 | Rust/C++; rustc, gccrs, GCC, Clang; bug-report-derived input | [Mut4All-Artifacts]; public; license not visible; synthesize | GPT-4o; custom fine-tuning on 20 human-writte | Codex-2 |
| 1 | From Documentation to Zero-day Vulnerabilities: LLM-Driven Fuzzing of JavaScript Engines i | https://arxiv.org/abs/2608.06641 | CCS 2026 accepted (metadata); arXiv 6 Au | JavaScript/PDF; Adobe Acrobat, Foxit, PDF-XChange; Windows e | [PDFuzzer]; public; license not visible; Python/PowerShell | GPT-4o, o3-mini, Claude 3.7 Sonnet; no traini | Codex-2 |

## F. Cần huấn luyện (RL / fine-tune) — loại vì không GPU (23)

| F | Paper | ID | Venue / ngày | Ngôn ngữ, benchmark | Code, license | LLM | Agent |
|---|---|---|---|---|---|---|---|
| 3 | CASCADE: Detecting Inconsistencies between Code and Documentation with Automatic Test Gene | 2604.19400 https://arxiv.org/abs/2604.19400 | FSE 2026, Jul; arXiv 2026-04-21 | Java: 71 inconsistent + 814 consistent pairs; C#/Rust follow | [CASCADE]; MIT; Python orchestration | GPT-4.1-mini; GPT-4o-mini real-world study; n | Codex-1 |
| 3 | Reference-Based Retrieval-Augmented Unit Test Generation | Official journal-first paper https://conf.researchr.org/deta | TOSEM / ASE 2025 journal-first, Nov; exa | Java; benchmark details U | [PAGTest]; license unresolved, U | LLM/retriever inventory and training requirem | Codex-1 |
| 3 | S*: Test Time Scaling for Code Generation | https://aclanthology.org/2025.findings-emnlp.865/ | Findings EMNLP, Nov 2025 | Python/code-generation tasks; LiveCodeBench and additional e | [SkyThought]; Apache-2.0; paper-specific S* path linked by R | GPT-4o-mini, Qwen2.5-Coder, QwQ, DeepSeek-R1- | Codex-2 |
| 2 | CodeRM-8B: Dynamic Scaling of Unit Tests for Reward Modeling | 2501.01054 | ACL 2025 | Python; HE+, MBPP+, LCB | CodeRM no license | Llama3.1-8B (train) | Claude-C |
| 2 | Measuring the Influence of Incorrect Code on Test Generation | Official paper https://conf.researchr.org/details/icse-2026/ | ICSE 2026, Apr | Three benchmarks + 41 repository examples; language/names U | Public package/license U | Five open and six closed models, names U; eva | Codex-1 |
| 2 | ReproCopilot: LLM-Driven Failure Reproduction with Dynamic Refinement | Author publication https://www.microsoft.com/en-us/research/ | FSE 2025, Jun | Code/input failure workloads; language/benchmark U | Public code/data/license U | Models and training requirement U | Codex-1 |
| 2 | Test Case Generation from Bug Reports via Large Language Models: A Cognitive Layered Evalu | https://arxiv.org/abs/2510.05365 | arXiv 6 Oct 2025 | Java / Defects4J and GHRB; report/identifier perturbations | No new replication-package link verified; LIBRO-derived stud | StarCoder-15.5B, GPT-4o; no new task training | Codex-2 |
| 1 | MIST-RL: mutation-reward RL test generator | 2603.01409 | arXiv Mar 2026 | Python; HE+, MBPP+ | supplementary | Qwen3-14B GRPO (train) | Claude-B |
| 1 | CURE: Co-Evolving Coder and Unit Tester via RL | 2506.03136 | NeurIPS 2025 | Python | CURE no license | RL Qwen (train) | Claude-C |
| 1 | Code-A1: Adversarial Evolving of Code and Test LLM | 2603.15611 | arXiv Mar 2026 | Python | Code-A1 no license | RL (train) | Claude-C |
| 1 | ATGen: Adversarial RL for Test Case Generation | 2510.14635 | ICLR 2026 | APPS, Codeforces | Apache-2.0? | GRPO (train) | Claude-C,Codex-1,Codex-2 |
| 1 | TCS: Two-Stage RL for Sound and Adversarial Test Generation | 2609.03955 | EMNLP 2026 Findings | TACO, LCB | tcs Apache-2.0 | RL (train) | Claude-C,Codex-2 |
| 1 | Sol-Ver: Learning to Solve and Verify | 2502.14948 | arXiv Feb 2025 | MBPP, LCB | ? | self-play (train) | Claude-C |
| 1 | Correct Tests Are Not Enough: Oracle Conversion | 2609.05879 | arXiv Sep 2026 | C/C++; TC-Bench | none | GRPO (train) | Claude-C |
| 1 | Agentic Bug Reproduction for Effective Automated Program Repair at Google | 2502.01821 | arXiv 3 Feb 2025; v2 11 Mar 2025 | Proprietary Google code; 80 human-reported bugs; language mi | Private code/data/model; no public generator verified | Gemini fine-tuned on internal Google code; tr | Claude-C,Codex-2 |
| 1 | Small Models Infer Postconditions | 2507.10182 | arXiv Jul 2025 | Java; Defects4J | ? | 7B FT (train) | Claude-C |
| 1 | Doc2OracLL: Investigating the Impact of Documentation on LLM-based Test Oracle Generation | 2412.09360 https://arxiv.org/abs/2412.09360; DOI 3729354 htt | FSE 2025, Jun; older 2024-12 preprint | Java/Javadoc; exact oracle dataset inventory U | Public code/data/license U | Fine-tunes 10 LLMs; GPT-3.5 generates documen | Codex-1 |
| 1 | Less is More: On the Importance of Data Quality for Unit Test Generation | 2502.14212 https://arxiv.org/abs/2502.14212 | FSE 2025, Jun; arXiv 2025-02-20 | Java; Methods2Test, ATLAS | CleanTest code/data/license U | CodeBERT, AthenaTest, StarCoder, CodeLlama-7B | Codex-1 |
| 1 | CUBETESTERAI: Automated JUnit Test Generation using the LLaMA Model | 2504.15286 https://arxiv.org/abs/2504.15286 | ICST 2025 Industry, Mar–Apr | Java/Spring Boot; industrial programs, benchmark names U | Public code/data/license U | LLaMA version U, served by RunPod GPU; traini | Codex-1 |
| 1 | WebGen-Bench: Evaluating LLMs on Generating Interactive and Functional Websites from Scrat | NeurIPS proceedings https://proceedings.neurips.cc/paper_fil | NeurIPS 2025 Datasets and Benchmarks, De | Generated websites; operation/outcome tests | [WebGen-Bench]; license U | Proprietary/open LLMs, Bolt.diy/OpenHands/Aid | Codex-1 |
| 1 | SWE-Tester: Training Open-Source LLMs for Issue Reproduction in Real-World Repositories | https://arxiv.org/abs/2601.13713 | arXiv 20 Jan 2026; v2 8 Sep 2026 | Python repository tasks; 41K training instances, 2.6K reposi | No author code/weight endpoint verified in this pass; licens | Qwen2.5-Coder 7B/14B/32B; supervised fine-tun | Codex-2 |
| 1 | Discovering 100+ Compiler Defects in 72 Hours via LLM-Driven Semantic Logic Recomposition | https://arxiv.org/abs/2601.12360 | arXiv 18 Jan 2026; v2 27 Jan 2026 | C/C++; GCC and LLVM compiler fuzzing | No author artifact endpoint verified; license unknown | Qwen2.5-max feature extraction, fine-tuned Qw | Codex-2 |
| 1 | LLMs are All You Need? Improving Fuzz Testing for MOJO with Large Language Models | https://arxiv.org/abs/2510.10179 | arXiv 11 Oct 2025 | Mojo language/API fuzzing; emerging-language corpus; 13 clai | No official implementation/checkpoint link verified; license | Fine-tuned LLaMA2 family in method text; exac | Codex-2 |

## Chọn ứng viên base paper

Tiêu chí (theo thứ tự quan trọng):
1. **Có method sinh test bằng LLM + code công khai** (hoặc benchmark có sẵn arm prompting làm baseline).
2. **Không cần huấn luyện / GPU.**
3. **Có ground truth bug**: bản lỗi vs bản đúng/fix (đo "fail trên bug, pass trên đúng").
4. **Có bộ test sẵn mà bản lỗi vẫn qua** → tính được concept "test hiện có chưa bao giờ …" (đây là chỗ concept khác thông tin paper đã có).
5. Python (dùng lại tracer/facts.py), venue peer-reviewed, chưa thử trong repo.

| Ứng viên | 1 | 2 | 3 | 4 | 5 | Ghi chú |
|---|---|---|---|---|---|---|
| **PBT-Bench** 2605.15229, NeurIPS 2026 D&B | benchmark + arm baseline/PBT-scaffold | ✓ | ✓ 365 bug tiêm, fail-buggy/pass-fixed | ✓ `existing_tests/` qua trên bản lỗi | Python ✓, peer-reviewed ✓ | Agent OpenHands + Docker → phải đo chi phí; concept tính trên code thư viện (lớn hơn hàm HumanEval); license NOASSERTION |
| **UTBoost** 2506.09289, ACL 2025 | method ✓ MIT | ✓ | ✓ patch sai đã gán nhãn vs gold | ✓ patch sai qua test có sẵn | Python ✓, ACL ✓ | SWE-bench Docker nặng; concept = fact trên vùng code patch mà test cũ không chạm |
| **VIBEPASS** 2603.15921, arXiv 2026 (Salesforce) | benchmark + prompt Bug-Aware/Discovery | ✓ | ✓ silver solution | ✓ lời giải lỗi qua một phần test | Python ✓, chưa peer-review ✗ | Gần pipeline hiện tại nhất (hàm LCB) → port facts.py nhanh, rẻ; n=173 nhỏ |
| **RTED** 2507.02318, ASE 2025 | method ✓ (badge CC-BY) | ✓ | ✓ BugsInPy/TypeBugs | một phần | Python ✓, ASE ✓ | Chỉ lỗi kiểu; cài env từng project BugsInPy |
| **TestWeaver** 2508.01255, ICSE 2026 | method ✓ Apache | ✓ | ✗ chỉ đo coverage → phải tự thêm BugsInPy/mutant | ✓ | Python ✓, ICSE ✓ | Slot prompt sẵn (slice + test gần + state); dễ bị chê "concept trùng execution feedback" |
| **AssertFlip** 2507.17542, ICSE 2026 | method ✓ Apache | ✓ | ✓ fail-to-pass | ✓ | Python ✓ | Issue text đã mô tả bug → concept ít giá trị thêm; 10+10 lần thử/instance, phải cắt |
| PatchDiff 2503.15223, ICSE 2026 | method, không license | ✓ | ✓ | ✓ | Python ✓ | Thay thế UTBoost |
| PROBE (Findings ACL 2026) | method, license? | ✓ | bug dev xác nhận + mutation | ✗ | Python ✓ | Nặng, nhiều lượt gọi |
| LLMutantKiller (ISSTA 2026) | method ✓ MIT, CPU | ✓ | mutant | ✓ mutant sống | JS/TS ✗ | Hợp nhất về ý tưởng (mutant → test) nhưng phải viết lại tracer cho JS |
| SWE-Mutation 2605.22175 | benchmark MIT | ✓ | mutant | ✓ | Python, venue chưa rõ | Đánh giá bộ test bằng mutant phức tạp |

## Đọc kỹ 2 ứng viên đầu (2026-10-10; repo clone ở vendor/PBTbench @cef1aa4, vendor/vibepass @4dd8a7e)

### PBT-Bench (2605.15229, NeurIPS 2026 D&B)
- 100 bài / 40 thư viện Python / 365 bug tiêm (L1 87, L2 184, L3 94). Mỗi bài: `lib/` (bản lỗi), `bug_N.patch`, `docs/`, `existing_tests/` (qua hết trên bản lỗi), `ground_truth/pbt_test.py`, `problem.yaml` (trigger_condition, ground_truth_strategy — chỉ để đánh giá).
- Chấm: per-function F→P, mỗi `test_*` chạy trên (buggy, fixed_bugN); metric bug recall.
- Harness: OpenHands SDK vendored + Docker (`python:3.12-slim`, tự chọn linux/amd64). Arm: baseline / pbt_hypothesis (+ 2 paraphrase mỗi arm). License: harness MIT, data CC-BY-4.0, lib/ theo upstream. Chỉ msgpack có `.so` aarch64 (bug nằm trong fallback.py thuần Python).
- Kết quả paper (3 run): Gemini 3 Flash baseline 56.2% → PBT 62.8%; Sonnet 4.6 83.4%. Phân tích lỗi PBT: **31% "wrong strategy range" (Gemini 3 Flash tới 50%)** = generator không chạm vùng trigger → đúng chỗ concept "test hiện có chưa bao giờ …" giải quyết.
- Ví dụ khớp concept: MSGP-001 bug_2 trigger "chuỗi UTF-8 dài đúng 32 byte" (`n <= 0x20` thay vì `<= 0x1F`) ↔ fact BOUND "ở fallback.py:890, độ dài chưa bao giờ = 31/32 trong test hiện có".
- Chi phí: paper $2,288 cho 8 model × 2 mode × 3 run (~$0.5/bài/run trung bình); Gemini 3 Flash < $250/3 run (≤ $0.83/bài/run), trung bình 34 tool call/bài. Với ~$20: 3 arm × 10–15 bài × 1 run (≈ 35–55 bug/arm) — mỏng; cần đo pilot 1–2 bài trước.
- Việc phải làm: port tracer từ "1 hàm" lên "module thư viện" (instrument các file trong `scope`, chạy existing_tests bằng pytest). Không dùng bug patch / problem.yaml khi tính concept (rò rỉ).
- Rủi ro: prompt PBT bảo agent không đọc source → concept rút từ source phải ở dạng trừu tượng (vùng input), không lộ code; agent đa lượt → phương sai lớn, 1 run/arm khó có ý nghĩa thống kê.

### VIBEPASS (2603.15921, arXiv, Salesforce)
- 173 instance / 76 bài LiveCodeBench (LeetCode hàm + AtCoder stdin). HF: question_content, starter_code, silver_solution, buggy_solution, test_checker (kiểm input hợp lệ). Buggy qua 10–90% test chính thức (lỗi wrong-answer).
- Task FT-Test: 1 lần gọi → 1 test (input + output); metric VI/VIO/DI/DIO (DIO = fail buggy, pass gold, input hợp lệ). Gemini 3 Flash DIO 63.0%, Opus 4.6 79.8%. Paper kết luận nghẽn ở "fault-target reasoning" (gap VI−DI ≈ 23pp, gấp 2.7 lần gap output).
- Prompt hiện **không** đưa test có sẵn → concept tính trên test công khai/ví dụ mà bản lỗi qua (cần tải test LCB qua lcb_runner) và chèn vào prompt.
- Chi phí: 173 × 3 arm × 1 gọi, Gemini Flash ≈ < $2 → chạy được nhiều seed.
- Code: Apache-2.0 (README ghi MIT, README lệch code); cần `lcb_runner` (LiveCodeBench) + sandbox HTTP :8080 (SandboxFusion Docker). Data "không dùng để phát triển model cạnh tranh" — chỉ đánh giá thì được.
- Rủi ro: chưa peer-review; bug là wrong-answer trên bài thuật toán (khác bài toán "plausible program" chỉ ở chỗ bản lỗi còn trượt test chính thức); stdin programs cần tracer cho script.

## Ứng viên bổ sung (cho phép port concept sang ngôn ngữ khác; GitHub API 2026-10-10)

| Paper | Venue | Repo (lang, license, size) | Bối cảnh bug | Concept tính trên | Port | Chi phí ước |
|---|---|---|---|---|---|---|
| UTBoost 2506.09289 | ACL 2025 | CUHK-Shenzhen-SE/UTBoost (Py, MIT, 19MB) | patch agent qua test SWE-bench nhưng sai | vùng code patch × test có sẵn | Python, nhưng phải chạy trong Docker SWE-bench | trung bình (GPT-4o gốc) |
| PatchDiff 2503.15223 | ICSE 2026 | ZJU-CTAG/PatchDiff (Py, không license) | như trên, test vi sai patch vs gold | như trên | như trên | ~$0.04–0.10/patch |
| RTED 2507.02318 | ASE 2025 | chenyangyc/RTED (Py, không license, 100MB) | lỗi kiểu BugsInPy/TypeBugs | giá trị/kiểu tham số mà test cũ chưa truyền | Python; env từng project | thấp |
| TestWeaver 2508.01255 | ICSE 2026 | FSoft-AI4Code/TestWeaver (Py, Apache, 229MB) | regression test, đo coverage | dòng/điều kiện chưa chạm + giá trị | Python; phải tự thêm đánh giá bug | trung bình |
| AssertFlip 2507.17542 | ICSE 2026 | uw-swag/AssertFlip (Py, Apache) | tái hiện bug từ issue (F2P) | hàm được định vị × test cũ | Python + Docker SWT-bench | cao nếu giữ 10+10 lần thử |
| LLMutantKiller | ISSTA 2026 | neu-se/LLMutantKiller___Artifact (JS/TS, NOASSERTION, 340MB) | test giết mutant sống (Jest) | mutant sống → fact hành vi | **port sang JS** (istanbul/babel instrument) | < $1 cho 13 mutant (paper) |
| DISTINCT 2506.07486 | arXiv | anonymous-user-2309/DISTINCT (Py harness, Java subjects, không license) | Defect Detection Rate trên Defects4J-Desc / QuixBugs-Desc | nhánh chưa chạm của focal method | **port sang Java** (JaCoCo/ASM) | thấp với QuixBugs |
| REFUTE 2502.19414 | tech report | falsifiers/REFUTE (Apache, 35KB) | sinh counterexample cho lời giải Codeforces sai (tốt nhất <9%) | lời giải sai × test công khai | **port sang C++** (gcov) | thấp |
| SWE-Mutation 2605.22175 | arXiv (repo ghi ACL) | Sunny4Coding/SWE-Mutation (Py, MIT) | bộ test phát hiện mutant phức tạp, SWE | mutant sống × test cũ | Python + repo env | trung bình |
| Test-suite auditors 2608.01715 | arXiv | xieTwim/test-suite-auditors (NOASSERTION) | submission "Accepted" mà sai | test chính thức → fact | C++/Python | trung bình |
| crucible 2607.23002 | arXiv | Jott2121/crucible (Py, MIT) | critic dùng mutant sống (mutmut) | thay feedback mutant thô bằng concept | Python | thấp, n rất nhỏ |
| PROBE | Findings ACL 2026 | T90REAL/PROBE (Py, không license) | PBT + phản-implementation, bug dev xác nhận | thư viện × test cũ | Python | cao |

## Vòng 2: quét arXiv API + soát lại 121 paper (2026-10-10)

Quét arXiv API (~70 truy vấn, 2025-01 → 2026-10): 1,016 paper, 914 chưa có trong danh sách, 487 qua lọc từ khoá (test + bug/fault/mutant/oracle… + LLM). Đọc tay cả 487 tiêu đề; phần lớn lệch hướng (test LLM/fairness, GUI, REST, fuzzing DL lib, test-time scaling). Danh sách thô: `scratchpad/arx/sel.json`. Link code lấy từ bản HTML arXiv.

### Ứng viên mới từ arXiv

| Paper | Venue | Code | Ngôn ngữ / dữ liệu | Liên quan concept |
|---|---|---|---|---|
| TC-Bench 2510.08720 | **ICLR 2026** | Luowaterbi/TC-Bench (Py, không license) + HF | wrong codes USACO/NOI/ICPC (C++), 5 baseline sinh test (CRUX/PSEUDO/ALGO/LCB/HardTests), SOTA chỉ ~60% exclusion | cùng họ HardTests/TCGBench (đã loại trước) — concept phải tính trên lời giải đúng + golden tests |
| E-Test 2510.19860 | **ICSE 2026** | ketaiq/E-Test-package (Apache, 270MB) | Java, 1,975 scenario + Defects4J | LLM tìm "scenario test hiện có chưa chạm" rồi sinh test — **đối thủ trực tiếp** của concept "test hiện có chưa bao giờ …" |
| DCAware 2608.05917 | **ASE 2026** | Zenodo 21357436 | Java, oracle hồi quy, đo mutation | context tĩnh + trạng thái động chọn lọc → fault-revealing oracle; concept thay "dynamic states" |
| ABEX 2608.28230 | arXiv (29 tr) | Zenodo 21354853 | Python? 20 hàm số/chuỗi/mảng, mutation score 86% vs 62% | agent LLM khám phá biên — khớp fact BOUND |
| Scientific-Debugging mutation tests 2503.08182 | arXiv | chưa thấy | Python, so với Pynguin | LLM đặt giả thuyết giết mutant — concept = giả thuyết có sẵn |
| ProbeGen 2502.18473 | arXiv (Google) | chưa thấy | Python, phản ví dụ tương đương chương trình (18% mẫu "pass test" bị bác bỏ) | sinh input phân biệt 2 chương trình |
| Codehacks 2503.23466 | ICST 2025 | dataset | Codeforces, 288k hack, 2,196 lời giải bị hack | chỉ là dữ liệu ground truth |
| UOJ-Bench 2606.12864 | arXiv | hehezhou/UOJ-Bench (không license) | C++ submission người viết, task "code hacking" | LLM tìm lỗi <50% one-shot |
| CodeMonitorBench 2607.20852 | arXiv | chưa thấy | 43,677 code qua public test, 23,081 trượt hidden | đúng bài toán "plausible code", nhưng là verifier không sinh test |
| IssueSpecter 2604.26118 | arXiv | chưa thấy | Python, 13 project, so với CoverUp | vùng code chưa cover → LLM tìm bug |
| PDB 2604.17338 | NeurIPS 2026 E&D | Bill1235813/PDB (MIT) | Python, bug nguyên tử đã kiểm chứng | nguồn bug, không phải method sinh test |
| ConcoLixir 2606.26545 | arXiv | chưa thấy | Python concolic + LLM, $1.63 cả eval | chỉ đo coverage |
| BSG-VA 2607.28871 | arXiv | Zenodo | Python repair agent, 3 arm có placebo "reminder" | thiết kế thí nghiệm giống mình, không phải test-gen |

### Soát lại 121 paper: ứng viên trước đó bỏ sót

| Paper | Venue | Code | Ghi chú |
|---|---|---|---|
| EvalAndMitigate 2607.22883 | **ISSTA 2026** | MIT | Java/Defects4J; test LLM sinh từ code lỗi bị "dẫn sai" → concept là cách giảm misguidance; port Java |
| CASCADE 2604.19400 | **FSE 2026** | MIT | xếp nhầm vào nhóm huấn luyện; sinh test để bắt lệch code↔doc, GPT-4.1-mini, Java |
| Testora 2503.18597 | **ICSE 2026** | MIT | Python PR scipy/pandas; concept = diff × test cũ |
| ChaCo 2601.10942 | **ICSE 2026** | ? | Python PR, augment test hồi quy |
| TestPrune 2510.18270 | **FSE 2026** | Apache | dùng test cũ cho SWE issue |
| DiffTestGen 2607.16024 / PatchGuru 2602.05270 | arXiv | MIT / Apache | Python PR, gpt-5-mini, rẻ |
| Agentic PBT 2510.09907 | DL4C ws | không license | Python 100 PyPI, bug thật nhưng không có bản fix chuẩn |
| DiffTrust 2507.00057 | AAAI 2026 | NOASSERTION | incoherence giữa mẫu, không sinh test |

## Paper có metric dương tính giả (FP) (quét full-text arXiv HTML, 2026-10-11)

FP chấm tự động (có bản đúng/fixed làm ground truth):
- PBT-Bench: harness có cờ `false_positive` = test fail cả trên bản buggy lẫn bản fixed (`vendor/PBTbench/eval/run_eval.py:51`, `run_pbt.py:983`).
- EvalAndMitigate (ISSTA 2026, MIT, Java/Defects4J): bảng nhầm lẫn TP/TN/FN/FP theo kết quả trên (fixed, buggy); "false-alarm tests" = fail trên code đúng.
- CASCADE (FSE 2026, MIT, Java): mục tiêu chính là giảm FP; có 814 cặp code–doc nhất quán nên đo được FPR tự động.
- RTED (ASE 2025, Python BugsInPy/TypeBugs): precision cao hơn 173.9–245.9%.
- VIBEPASS: không gọi là FP, nhưng DIO bắt buộc test pass trên silver; khoảng cách VI→VIO = test có output sai.
- DiffTrust (AAAI 2026): theo lý thuyết không có FP. Tensor-kernel 2606.27396: FP trên 16 kernel đúng (cần GPU).

FP gán nhãn tay (báo cáo bug sai):
- PatchGuru (Apache, Python PR): FP rate 0.38 so với Testora 0.68.
- Testora (ICSE 2026, MIT): RQ3 FP. DiffTestGen: 2/7 FP.
- IssueSpecter: 15.4% FP. Agentic PBT: "few false alarms". LogicHunter (MIT): P/R/F1/FPR.
- CodeMonitorBench: miss rate tại FPR 5% (verifier).

## Vòng 3: quét theo venue + lọc cứng 4 tiêu chí (2026-10-11)

Nguồn: Semantic Scholar bulk API (DBLP chặn bot, OpenAlex hết quota ngày). Venue 2025–2026: ICSE, PACMSE (FSE/ISSTA), ASE, ICST, TOSEM, TSE, EMSE, IST, JSS, ASE journal, ACL (+Findings), EMNLP, NAACL, NeurIPS, ICLR, ICML, AAAI. Lấy 4,3k paper có từ khoá test/bug/fault/mutation/oracle/fuzz, lọc còn 165 về LLM + code, đọc tay. S2 thiếu ICSE 2026, ISSTA 2026, ICST 2025, ICLR/NeurIPS 2026 — các venue này đã có trong danh sách accepted Codex-1 quét trước. Kết quả từ venue gần như không thêm ứng viên đạt 4 tiêu chí: đa số là coverage/oracle/APR/fuzzing, hoặc là bản peer-review của paper đã có (Test4Py → TOSEM 2026, ULT → TOSEM 2025). Mới đáng xem: ChatAssert (TSE 2025, oracle bằng prompt engineering, chưa kiểm code/bug GT), LegaTest (TOSEM 2026, LLM+GA).

Lọc cứng 4 tiêu chí bắt buộc trên toàn bộ ~1,000 paper đã xem (1: LLM sinh test có code/benchmark có arm; 2: không huấn luyện; 3: ground truth bản lỗi vs đúng; 4: 2025–2026). Cột 5 = bản lỗi qua bộ test sẵn có; FP = chấm tự động test fail trên bản đúng. License/code lấy từ báo cáo agent + GitHub API, chưa kiểm tay từng repo.

| Paper | Venue | Ngôn ngữ | Ground truth bug | 5 | FP tự động |
|---|---|---|---|---|---|
| PBT-Bench | NeurIPS 26 D&B | Python | 365 bug tiêm + fix | ✓ | ✓ cờ false_positive |
| RTED | ASE 25 | Python | BugsInPy/TypeBugs | ✓ | ✓ precision |
| UTBoost | ACL 25 | Python | patch sai vs gold (SWE-bench) | ✓ | ✓ (test phải pass gold) |
| PatchDiff | ICSE 26 | Python | patch agent vs gold | ✓ | một phần |
| AssertFlip | ICSE 26 | Python | SWT-bench F2P | ✓ | ngầm (F2P) |
| Issue2Test | ICSE 26 | Python | SWT-bench F2P | ✓ | ngầm |
| TestPrune | FSE 26 | Python | SWE-bench | ✓ | ngầm |
| iCoRe | FSE 26 | Python | SWT/TDD-bench | ✓ | ngầm |
| PROBE | Findings ACL 26 | Python | bug dev xác nhận + mutant | ✓ | ? |
| EvalAndMitigate | ISSTA 26 | Java | Defects4J buggy/fixed | ✓ | ✓ bảng TP/FP |
| Coverage/Mutation vs effectiveness | ISSTA 26 | Java | Defects4J | ✓ | ? (nghiên cứu thực nghiệm) |
| LLMutantKiller | ISSTA 26 | JS/TS | mutant sống | ✓ | n/a |
| DCAware | ASE 26 | Java | mutant/Defects4J | ✓ | ? |
| CASCADE | FSE 26 | Java | cặp code–doc lệch/nhất quán | ✗ | ✓ |
| MR-Coupler | FSE 26 | Java | 50 bug thật | ✓ | ? |
| Cleverest | FSE 25 | C (input cấu trúc) | 46 commit hồi quy | một phần | ? |
| TC-Bench | ICLR 26 | C++ (harness Py) | wrong codes vs đúng | một phần | ✓ (test kiểm trên code đúng) |
| VIBEPASS | arXiv | Python | buggy vs silver | ✓ | ✓ (DIO) |
| DISTINCT | arXiv | Java | Defects4J-/QuixBugs-Desc | ✓ | ? |
| REFUTE | arXiv | C++ | lời giải Codeforces sai | ✓ | ✓ (input hợp lệ + đúng) |
| SWE-Mutation | arXiv | Python | mutant phức tạp | ✓ | ? |
| Test-suite auditors | arXiv | C++/Py | accepted-but-buggy | ✓✓ | ✓ (lọc FP số thực) |
| Echo / ReProAgent | arXiv | Python | SWT-bench | ✓ | ngầm |
| crucible | arXiv | Python | mutant sống | ✓ | ? |
| ABEX | arXiv | Python | mutant | ✗ (black-box) | ? |
| UOJ-Bench | arXiv | C++ | submission sai bị hack | ✓ | ? |

Tổng: 27 paper đạt 4 tiêu chí cứng; 17 đã peer-review; 9 Python peer-review.
