# 500-paper full-text and public-source audit

Updated: 2026-10-15T14:44:09.213071+07:00

**Đã đọc full text và verify public-source verdict: 74/500 paper.**

- Full text đã đọc: 74/500.
- Public-source checks đã ghi evidence: 81/500.
- Full text access-blocked/not read: 7.
- Review hoàn tất (kể cả access-blocked verdict): 81/500.
- Retrieval đã thử: 500/500. Downloaded text không tính là đã đọc.
- Author-code/model reproduction đã chạy: 0.

Yêu cầu người dùng: nếu xong trước 07:00 giờ Việt Nam, xuất report ở root xác nhận 500/500.
Chỉ ghi hoàn tất 500/500 khi ledger có 500 full-text reviews và public-source verdicts đã kiểm chứng.

Lịch tiếp tục: không có timer; tiếp tục thủ công theo yêu cầu người dùng, tối đa 50 paper bổ sung.
Các timer audit systemd đã được disable theo yêu cầu ngày 2026-10-15.

Hai lượt 02:20/07:20 ngày 15/10 đã fail vì thread writer conflict; không hoàn tất trước 07:00.
Scheduler từng dùng codex queue sau lỗi writer conflict; hiện mọi timer đã disable và không có continuation tự động.

## Reviewed papers

| # | Paper | Full text read | Public source | Reproduction feasibility |
|---:|---|---|---|---|
| 1 | Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests | True | public_implementation | conditional |
| 2 | Agent-Based Test Assertion Generation via Diverse Perspective Aggregation | True | public_implementation | conditional |
| 3 | Reflective Unit Test Generation for Precise Type Error Detection with Large Language Models | True | public_implementation | conditional |
| 4 | DISTINCT: A Description-Guided Branch-Consistency Analysis Framework for Non-Regressive Test Case Generation | True | public_implementation | conditional |
| 5 | LLM Test Generation via Iterative Hybrid Program Analysis | True | public_implementation | conditional |
| 6 | An Anatomy of 488 Faults from Defects4J Based on the Control- and Data-Flow Graph Representations of Programs | True | public_implementation | conditional |
| 7 | Test vs Mutant: Adversarial LLM Agents for Robust Unit Test Generation | True | public_implementation | conditional |
| 8 | Tratto: A Neuro-Symbolic Approach to Deriving Axiomatic Test Oracles | True | public_implementation | conditional |
| 9 | E-Test: E’er-Improving Test Suites | True | public_implementation | conditional |
| 10 | Doc2OracLL: Investigating the Impact of Documentation on LLM-Based Test Oracle Generation | True | partial | conditional |
| 11 | Exploring Automated Assertion Generation via Large Language Models | False | public_implementation | unknown |
| 12 | LLM vs. Human Unit Tests: Fault Detection on Real Python Bugs | True | not_found | unknown |
| 13 | Call-Chain-Aware LLM-Based Test Generation for Java Projects | True | public_implementation | conditional |
| 14 | LLM-based Low-Level Integration Test Generation for Java | True | not_found | unknown |
| 15 | NeuroTestGen: Neuro-Symbolic Guided Test Generation with Large Language Models | True | public_implementation | conditional |
| 16 | Knowledge-Guided Synthetic Bug Feedback for LLM-Based Unit Test Generation | True | not_found | unknown |
| 17 | Fail-Aware and Explainable Test Oracle Prediction | True | not_found | unknown |
| 18 | Test Case Generation from Bug Reports via Large Language Models: A Cognitive Layered Evaluation Framework | True | not_found | unknown |
| 19 | Less Is More: On the Importance of Data Quality for Unit Test Generation | True | public_implementation | conditional |
| 20 | AssertFlip: Reproducing Bugs via Inversion of LLM-Generated Passing Tests | True | public_implementation | conditional |
| 21 | Issue2Test: Generating Reproducing Test Cases from Issue Reports | True | public_implementation | conditional |
| 22 | ReProAgent: Tool-Augmented Multi-Stage Agentic Generation of Bug Reproduction Tests from Issue Reports | True | public_implementation | conditional |
| 23 | Echo: Graph-Enhanced Retrieval and Execution Feedback for Issue Reproduction Test Generation | True | public_implementation | conditional |
| 24 | iCoRe: An Iterative Correlation-Aware Retriever for Bug Reproduction Test Generation | True | public_implementation | conditional |
| 25 | SWE-Tester: Training Open-Source LLMs for Issue Reproduction in Real-World Repositories | True | public_implementation | conditional |
| 26 | Heterogeneous Prompting and Execution Feedback for SWE Issue Test Generation and Selection | True | partial | conditional |
| 27 | A Taxonomy of Failing Bug Reproduction Tests on SWT-Bench | False | partial | conditional |
| 28 | Exploring Generalizable Automated Program Repair with Large Language Models | True | partial | conditional |
| 29 | Hierarchical Knowledge Injection for Improving LLM-based Program Repair | True | public_implementation | conditional |
| 30 | Bigger Is Not Always Better: Performance and Sustainability Trade-Offs in LLMs for Python Bug-Fixing Tasks | True | public_implementation | conditional |
| 31 | Aligning the Objective of LLM-based Program Repair | True | public_implementation | conditional |
| 32 | Escaping the Self-Repair Trap: Improving Test Oracle Generation via Dual-Context Awareness | True | public_implementation | conditional |
| 33 | Uncovering Business Logic Bugs via Semantics-Driven Unit Test Generation (Experience Paper) | True | partial | not_feasible |
| 34 | LLM-Based Invariant Testing for Software Functional Bugs | True | public_implementation | conditional |
| 35 | TOGLL: Correct and Strong Test Oracle Generation with LLMs | True | public_implementation | conditional |
| 36 | UnitCon: Synthesizing Targeted Unit Tests for Java Runtime Exceptions | True | public_implementation | conditional |
| 37 | CoverUp: Effective High Coverage Test Generation for Python | True | public_implementation | conditional |
| 38 | TAM-Eval: Evaluating LLMs for Automated Unit Test Maintenance | True | public_implementation | conditional |
| 39 | A Large-Scale Empirical Study on Fine-Tuning Large Language Models for Unit Testing | True | public_implementation | conditional |
| 40 | AnyPoC: Universal Proof-of-Concept Test Generation for Scalable LLM-Based Bug Detection | True | public_implementation | conditional |
| 41 | Automated Unit Test Generation via Chain-of-Thought Prompt and Reinforcement Learning from Coverage Feedback | False | partial | conditional |
| 42 | Enriching automatic test case generation by extracting relevant test inputs from bug reports | True | restricted | not_feasible |
| 43 | Large Language Models for Unit Test Generation: Achievements, Challenges, and Opportunities | True | restricted | conditional |
| 44 | TATG: Tracking-Aware Testing Objective for LLM-based Test Generation | True | not_found | not_feasible |
| 45 | Towards More Realistic Assertion Generation under Mixed-Assertion Scenario | False | not_found | unknown |
| 46 | Agentic Bug Reproduction for Effective Automated Program Repair at Google | True | not_found | not_feasible |
| 47 | Can Old Tests Do New Tricks for Resolving SWE Issues? | True | public_implementation | conditional |
| 48 | DPIAgent: Divide, Protocol, Isolate for Agentic Reproduction Test Generation | True | not_found | not_feasible |
| 49 | Beyond Fail-to-Pass: Iterative Hardening of Co-Generated Bug Reproduction Tests and Fixes | True | not_found | not_feasible |
| 50 | Enhancing LLM-Based Bug Reproduction via Code Entity Retrieval and Test Case Repair | False | not_found | unknown |
| 51 | Exploring the Interaction of Code Coverage and Non-Coverage Objectives in Search-Based Test Generation | True | public_implementation | conditional |
| 52 | How Does Killing Surviving Mutants Help Detect Real Bugs with Assertion Generation? A Controlled Experiment | True | public_implementation | conditional |
| 53 | Retrieval-Augmented Fine-Tuning for Improving Retrieve-and-Edit Based Assertion Generation | True | public_implementation | conditional |
| 54 | STMutants: A Mutation Testing Dataset for Structured Text Programs in Industrial Automation | True | partial | not_feasible |
| 55 | Understanding Automated Program Repair Agents through the Lens of Traceability: An Empirical Study | True | public_implementation | conditional |
| 56 | CASCADE: Detecting Inconsistencies between Code and Documentation with Automatic Test Generation | True | public_implementation | conditional |
| 57 | Evaluating Developer-written Unit Test Case Reduction for Java -- A Replication Study | True | public_implementation | conditional |
| 58 | How Many Code and Test Cases Are Enough? Evaluating Test Cases Generation from a Binary-Matrix Perspective | True | public_implementation | conditional |
| 59 | LLM-Based Test Generation: Information Sources, Generation Strategies, and Quality Evidence | True | public_implementation | not_feasible |
| 60 | LLMutantKiller: Using Large Language Models to Generate Tests that Kill Mutants | True | public_implementation | conditional |
| 61 | Multi-Agent LLM Collaboration for Unit Test Generation via Human-Testing-Inspired Workflows | True | partial | conditional |
| 63 | TestExplora: Benchmarking LLMs for Proactive Bug Discovery via Repository-Level Test Generation | True | public_implementation | conditional |
| 65 | XRepoTest: Benchmarking Multilingual Repository-Level Unit Test Generation for Large Language Models | True | public_implementation | conditional |
| 69 | Beyond Heuristics? Rethinking Targeted Unit Test Generation in the Era of LLM Agents | True | partial | conditional |
| 71 | Bug Whisperer: Unleashing LLMs to Craft Context-Aware Tests Guided by Path Constraints and Bug Clues | False | partial | unknown |
| 73 | Context Matters: Improving the Practical Reliability of LLM-Based Unit Test Generation (Experience Paper) | True | partial | not_feasible |
| 74 | Do Coverage and Mutation Scores of LLM-Generated Test Suites Correlate with Their Effectiveness? (Replicability Study) | True | public_implementation | conditional |
| 75 | Dynamic Cogeneration of Bug Reproduction Test in Agentic Program Repair | True | restricted | not_feasible |
| 76 | EvoOtter: Evolutionary Reproduction Test Generator | True | not_found | not_feasible |
| 79 | From Business Requirements to Test Assertions: Evaluating LLM-Generated Oracles on Real Bugs | True | restricted | conditional |
| 81 | Go-UT-Bench: A Fine-Tuning Dataset for LLM-Based Unit Test Generation in Go | True | partial | not_feasible |
| 82 | Hallucination to Consensus: Multi-Agent LLMs for End-to-End JUnit Test Generation | True | public_implementation | conditional |
| 86 | Improving Retrieval-Augmented Deep Assertion Generation via Joint Training | True | public_implementation | conditional |
| 89 | Multi-SWT-Bench: A Multilingual Benchmark for Reproduction Test Generation | True | public_implementation | conditional |
| 90 | Mutation-Guided Unit Test Generation With a Large Language Model | True | public_implementation | conditional |
| 91 | Prompt engineering in LLMs for automated unit test generation: A large-scale study | True | partial | not_feasible |
| 92 | SWE-Doctor: Guiding Software Engineering Agents with Runtime Diagnosis from Multi-Faceted Bug Reproduction Tests | True | public_implementation | conditional |
| 93 | Test Oracle Automation in the Era of LLMs | True | not_found | not_feasible |
| 98 | Reproduction Test Generation for Java SWE Issues | True | public_implementation | conditional |
| 107 | GIANT: Leveraging Retrieval-Augmented Generation for Automated Bug Reproduction Test Generation | False | not_found | unknown |
| 111 | ORACLE-SWE: Quantifying the Contribution of Oracle Information Signals on SWE Agents | True | not_found | not_feasible |

## Reports and evidence

- [Original report](research/benchmark-papers-2025-2026/REPORT.md)
- [Audit recommendations](research/benchmark-papers-2025-2026/audit/RECOMMENDATIONS.md)
- [Provisional paper selection](research/benchmark-papers-2025-2026/audit/PAPER_SELECTION.md)
- [Per-paper review ledger](research/benchmark-papers-2025-2026/audit/reviews/)
- [Continuation instructions](research/benchmark-papers-2025-2026/audit/CONTINUE.md)


## Quota checkpoint

Checked: 2026-10-15T14:44:07+07:00 from newest local rate_limits event in rollout-2026-10-14T23-09-47-01a13b2d-4f8e-74d0-96f1-df4907bdd441.jsonl.
Quota còn lại (100% - used_percent): primary 54.0% (đã dùng 46.0% ; reset 2026-10-15T18:12:42+07:00); weekly 93.0% (đã dùng 7.0% ; reset 2026-10-22T13:12:42+07:00).
Quota reset was user-reported at 2026-10-15T12:34:00+07:00; the latest local telemetry event is recorded above. The UI percentage the user reported is remaining quota; raw local `used_percent` is converted to remaining as 100 minus usage.
Người dùng báo UI hiện còn 90% quota primary (báo lúc 2026-10-15T14:42:00+07:00); đây là số remaining theo UI, tách riêng với snapshot local telemetry phía trên.
Continuation: Manual only; 0 of 50 additional distinct full-text reads remain. Timers disabled.
