# Full-text notes: catalog 61-80

Reviewed 2026-09-18. “Full text” means I read an official PDF, an author-hosted manuscript, or a published open-access PDF. “Abstract-only” means the primary landing page was accessible but no full text was available during this pass. Numbers appear only when the source states them.

## 61. Initial Seeds Generation Based on Communication Logs Using LLM for IoT Device Fuzzing

- **Method.** The LLM receives an IoT device type, captured communication logs, and a named vulnerability class, then produces initial fuzzing seeds. The fuzzer mutates those seeds and observes device crashes.
- **Motivation.** Hand-building seeds for unfamiliar IoT protocols takes protocol and security expertise; weak seeds delay or prevent reachability of fault-handling code.
- **Dataset + shape.** Two IoT-device types. The paper evaluates seeded campaigns for null-pointer-exception and buffer-overflow crashes; it does not present a large public benchmark dataset in the source I read.
- **Evaluation results.** First crashes arrived after 0.40 s and 0.47 s for the two devices. After 24 hours, the LLM seeds found all reported null-pointer and buffer-overflow crashes that manually generated seeds did not find.
- **Concept applicability.** High. A concept block can name the protocol state, message field, allowed value range, and desired vulnerability guard. This paper is close to “concept -> structured seed -> fuzzing” already; the useful ablation is whether a static concept extractor improves seeds beyond raw logs plus a vulnerability name.
- **Evidence.** Full text. [IEICE/J-STAGE PDF and article](https://www.jstage.jst.go.jp/article/transinf/E109.D/1/E109.D_2024EDP7305/_article/-char/en)
- **Artifacts (checked 2026-09-29).** Code: none found (No code/supplement (J-STAGE lists 0 supplementary files); no repo found). Dataset: 2 authors-built BusyBox IoT devices emulating a color bulb + IP camera; own comm logs — not released. Models: Mistral-7B-Instruct-v0.2.

## 62. AugmenTest: Enhancing Tests with LLM-Driven Oracles

- **Method.** AugmenTest adds JUnit assertions to existing tests. It asks an LLM to infer intended method behavior from documentation and developer comments, deliberately excluding implementation code. Variants use simple prompts, extended prompts, and retrieval augmentation.
- **Motivation.** Generated tests often execute code but contain weak or missing assertions. Code-only oracle generation can reproduce an implementation defect instead of specifying the intended behavior.
- **Dataset + shape.** 142 Java classes selected from a corpus of 418 projects and more than 27,000 classes. Every method in a selected class had a developer comment of at least 30 characters. Major mutants produced 203 distinct bug-revealing tests for evaluation.
- **Evaluation results.** The conservative setting reports 30% correct assertions for the extended prompt, versus 8.2% for TOGA. RAG variants reached 18.2%, so retrieval did not help in this setup.
- **Concept applicability.** High for the oracle half of the pipeline. Feed a concept as a candidate postcondition or invariant, then require the LLM to ground each assertion in comments, API documentation, or a reference implementation. The paper also warns against treating more context as automatically better.
- **Evidence.** Full text. [Author arXiv manuscript](https://arxiv.org/abs/2501.17461); [official artifact](https://github.com/se-fbk/augmentest)
- **Artifacts (checked 2026-09-29).** Code: verified source [github.com/se-fbk/augmentest](https://github.com/se-fbk/augmentest) (Python tool (src/: llm, rag, oracle_generation) + Docker, 51 MB, push 2026-06; Zenodo 10.5281/zenodo.13881826). Dataset: 142 Java classes from Gruber et al. 418-project corpus; 203 EvoSuite tests on Major mutants — released by authors [doi.org/10.5281/zenodo.13881826](https://doi.org/10.5281/zenodo.13881826). Models: GPT-4o, Meta-Llama-3-8B-Instruct (quantized), Nous-Hermes-Llama2-13B (quantized), text-embedding-3-large (RAG).

## 63. Enriching Automatic Test Case Generation by Extracting Relevant Test Inputs from Bug Reports

- **Method.** BRMiner mines bug reports for concrete input values, combines regular-expression extraction with GPT-3.5-turbo filtering, and passes retained values to EvoSuite.
- **Motivation.** Search-based unit-test generators often make inputs that satisfy types but miss values that actually reproduce reported failures. Bug reports contain examples, stack traces, and reproduction data that generation tools leave unused.
- **Dataset + shape.** Defects4J projects and their bug reports. The full paper evaluates extracted inputs and their effect on EvoSuite; the accessible sources describe the benchmark rather than a newly released fixed-size dataset.
- **Evaluation results.** The published EMSE abstract reports a Relevant Input Rate of 60.03%, a Relevant Input Extraction Accuracy Rate of 31.71%, and 58 unique bugs detected (an earlier manuscript version gave 68.68% with regex vs 50.21% without, and 45 bugs missed by the baseline). The enriched runs found bugs that the baseline missed and improved line and instruction coverage across the studied projects.
- **Concept applicability.** Very high. Turn a bug report into a fault concept: triggering values, environment, expected/actual behavior, and prohibited preconditions. This is a better semantic target than an AST tag because it originates in an observed defect.
- **Evidence.** Full text. [Open-access publisher PDF](https://orbilu.uni.lu/bitstream/10993/65666/1/s10664-025-10635-z%20%284%29.pdf)
- **Artifacts (checked 2026-09-29).** Code: verified source [anonymous.4open.science/r/BRMiner-C853](https://anonymous.4open.science/r/BRMiner-C853) (Anonymous repo live: Python BRMiner (GitHub/Jira extractors), EvoSuite experiments; anonymous links can expire). Dataset: Defects4J v2.0.0 + GitHub/Jira bug reports; extracted literals released — released by authors [anonymous.4open.science/r/BRMiner-C853](https://anonymous.4open.science/r/BRMiner-C853). Models: GPT-3.5-turbo.

## 64. An MLLM-Assisted Web Crawler Approach for Web Application Fuzzing

- **Method.** A multimodal LLM assists web crawling so the fuzzer can discover interfaces behind multi-step interactions and dynamic page structure; discovered interfaces become fuzzing targets.
- **Motivation.** Conventional web fuzzers miss attack surface when forms, navigation, and client-side state hide endpoints from a crawler.
- **Dataset + shape.** The paper evaluates its crawler/fuzzer on web applications; the open PDF is accessible, but I did not extract a defensible subject count from the available text in this pass.
- **Evaluation results.** The paper reports improved test-interface coverage over its baselines. I am leaving the numerical result out rather than reconstructing it from figures without a verified table read.
- **Concept applicability.** High. The concept should describe page state, required prior actions, form fields, authentication role, and target request property. That is materially more actionable than asking an LLM to “fuzz this URL.”
- **Evidence.** Full text, numeric result not transcribed. [Publisher PDF](https://www.mdpi.com/2076-3417/15/2/962/pdf)
- **Artifacts (checked 2026-09-29).** Code: none found (No repo for CrawlMLLM; built on third-party BoB-WebFuzzing/Request-Crawler; DAS says data in article; gh search empty). Dataset: 9 PHP web apps (Table 1) + DVWA/XVWA/bWAPP + 6 real-world apps; Burp/ZAP audits — public benchmark only. Models: GPT-4o.

## 65. LLM-Driven, Self-Improving Framework for Security Test Automation: Leveraging Karate DSL for Augmented API Resilience

- **Method.** Karate-BOLA-Guard combines LLM generation, retrieval augmentation, observability, and Karate DSL execution to generate and refine API-security tests.
- **Motivation.** API security tests need endpoint semantics, authentication context, and vulnerability-specific attack cases; static hand-written suites age quickly.
- **Dataset + shape.** Abstract-only. The publisher landing page confirms a 26-page IEEE Access article but the accessible primary material did not provide a reproducible dataset description.
- **Evaluation results.** Abstract-only. Do not cite a quantitative effectiveness claim from this note.
- **Concept applicability.** High in principle. CWE/BOLA type, actor roles, ownership relation, endpoint, object identifier, and expected authorization result form a natural concept schema. It is relevant to concept-guided red/green testing, but needs a reproducible benchmark before becoming an evaluation target.
- **Evidence.** Abstract-only. [IEEE Access DOI](https://doi.org/10.1109/ACCESS.2025.3554960)
- **Artifacts (checked 2026-09-29).** Code: verified source [github.com/EmilMarian/Karate-BOLA-Guard-Framework](https://github.com/EmilMarian/Karate-BOLA-Guard-Framework) (Python RAG/Karate test-gen framework + results/logs, 5.9 MB, last push 2025-02; matched by name+author (footnote URL not rendered)). Dataset: VAmPI, crAPI, OWASP Juice Shop + 15 production API specs; generated tests/logs in repo — released by authors [github.com/EmilMarian/Karate-BOLA-Guard-Framework/tree/master/results](https://github.com/EmilMarian/Karate-BOLA-Guard-Framework/tree/master/results). Models: Mistral-7B-Instruct (GGUF Q4_0), Wizard-v1.2-13B (GGUF Q4_0), Llama-3-8B-Instruct (GGUF Q4_0), Phi-3-Mini-Instruct (GGUF Q4_0).

## 66. GRPO with State Mutations: Improving LLM-Based Hardware Test Plan Generation

- **Method.** The work splits hardware verification into a natural-language sub-unit test plan and an executable testbench. It trains a 7B model with supervised fine-tuning plus GRPO-SMu, which varies mutated RTL states in a tree rather than sampling repeatedly from one state.
- **Motivation.** General LLMs produce weak RTL stimuli because a single RTL state yields low reward diversity and poor exploration. The authors want tests that pass golden RTL but expose mutated RTL.
- **Dataset + shape.** Curated RTL-description, golden-RTL, mutated-RTL, test-plan, and testbench examples. The paper describes tree-based mutation with three mutation types per source state; the accessible manuscript does not state a clean total instance count in the abstract sections reviewed.
- **Evaluation results.** DeepSeek-R1 and Claude-4.0-Sonnet pass golden designs for 15.7-21.7% of generated stimuli. The trained 7B model reaches 33.3% golden-test pass and 13.9% mutation detection, a reported 17.6-point absolute improvement over its baseline.
- **Concept applicability.** High. A mutation operator plus changed state is an explicit concept. The transferable idea is to give the generator several semantically related counterfactual program states, rather than only one target line and one coverage bit.
- **Evidence.** Full text. [Author arXiv manuscript](https://arxiv.org/abs/2601.07593)
- **Artifacts (checked 2026-09-29).** Code: none found (NVIDIA/MIT; no code or data link in paper; GitHub search for GRPO-SMu empty). Dataset: Curated set derived from ScaleRTL (1,500 eval RTL; 1,902 SFT traces; mutated RTL tree) — not released. Models: DeepSeek-R1-Distill-Qwen-7B (SFT+GRPO-SMu), DeepSeek-R1, Claude-4.0-Sonnet, Claude-3.7-Sonnet (data curation), LLaMa-3.1-405B, ScaleRTL-32B.

## 67. Generating Failure-Based Oracles to Support Testing of Reported Bugs in Android Apps

- **Method.** AndroB2O takes a bug report and the GUI screen implicated in the failure. It identifies relevant widgets and generates assertions over their properties to detect the reported non-crashing failure. The authors also connect it to the ReBL reproduction tool.
- **Motivation.** Android functional bugs often manifest visually rather than as crashes, so a reproduction trace alone has no oracle. Writing a regression assertion requires reconciling natural-language reports, GUI elements, and erroneous UI state.
- **Dataset + shape.** A new dataset of 152 Android bug-report failures with GUI interactions and failure-revealing oracles.
- **Evaluation results.** AndroB2O generated an oracle that identified the reported failure for 61.2% of the 152 failures. The paper reports an additional integration evaluation with ReBL, but I do not repeat its detailed figures here without the corresponding table.
- **Concept applicability.** Very high. This is almost the desired semantic form: bug report -> affected GUI state -> failure property -> assertion. Concepts can encode widget, property, expected value/relation, reproduction state, and a fixed-version pass condition.
- **Evidence.** Full text. [Author-hosted ASE PDF](https://ojcchar.github.io/files/40-ase25-br-oracles.pdf); [dataset record](https://doi.org/10.5281/zenodo.15556567)
- **Artifacts (checked 2026-09-29).** Code: verified source [doi.org/10.5281/zenodo.15556567](https://doi.org/10.5281/zenodo.15556567) (Zenodo Artifact.zip 5.4 GB: 'Pipeline Script' Python/ipynb (GPT+Llama), prompts, APKs, Espresso repro project). Dataset: FBO4A: 152 non-crashing Android bug reports from 24 apps, with oracles — released by authors [doi.org/10.5281/zenodo.15556567](https://doi.org/10.5281/zenodo.15556567). Models: GPT-4 Turbo (gpt-4-0125-preview), GPT-4o (gpt-4o-2024-11-20), Llama-4-Maverick.

## 68. On the Challenges of Fuzzing Techniques via Large Language Models

- **Method.** Position/challenge paper on using LLMs across fuzzing, rather than a new fuzzer with a benchmarked algorithm.
- **Motivation.** LLM-assisted fuzzing faces recurring problems: valid structured inputs, hallucinated APIs or grammars, expensive calls, weak feedback loops, and evaluation that confuses coverage with fault discovery.
- **Dataset + shape.** No experimental dataset.
- **Evaluation results.** No tool evaluation; it identifies research challenges.
- **Concept applicability.** Useful as design pressure, not as an evaluation baseline. A concept representation should be executable or checkable, so it can be rejected when it contradicts the grammar, program state, or feedback trace.
- **Evidence.** Abstract-only for this pass. [IEEE conference DOI](https://doi.org/10.1109/SSE67621.2025.00028)
- **Artifacts (checked 2026-09-29).** Code: none found (Literature survey/systematic overview; no tool). Dataset: N/A (literature survey, no experimental data) — not released. Models: none (no experiments).

## 69. Harden and Catch for Just-in-Time Assured LLM-Based Software Testing

- **Method.** The paper formalizes hardening tests, which pass now and aim to guard against future regressions, and catching tests, which reveal a fault introduced by a code change. It defines the Catching Just-in-Time Test challenge and discusses deployment outcomes.
- **Motivation.** Coverage and passing tests do not tell a team whether a generated test would have stopped a faulty change before release. The authors want an outcome tied to engineering value.
- **Dataset + shape.** This is a position/keynote paper, not a benchmark release. It discusses early Meta experience but does not offer a public dataset or a comparable aggregate score.
- **Evaluation results.** No standalone controlled evaluation to report.
- **Concept applicability.** Direct. Define the concept around a code change, hypothesized regression, pre-change invariant, and expected post-change behavior; then measure whether the test passes the parent and fails the buggy child. This is a cleaner target for the planned TestExplora-style F2P loop than line coverage.
- **Evidence.** Full text. [Author arXiv manuscript](https://arxiv.org/abs/2504.16472)
- **Artifacts (checked 2026-09-29).** Code: none found (Position/open-challenges paper (Meta); no tool or artifact released). Dataset: N/A (position paper, no experiments) — not released. Models: none (no experiments).

## 70. Program Interoperable Large Language Model Software Testing Scheme: A Case Study on JavaScript Engine Fuzzing

- **Method.** PILLM instruments JavaScriptCore, prompts an LLM with source semantics, evaluates generated tests for semantic relevance, and uses coverage/execution feedback to steer subsequent seed generation.
- **Motivation.** LLMs do not directly interact with a program, and one-shot test generation lacks a trustworthy quality signal. PILLM supplies both a program-to-LLM interaction mechanism and a feedback loop.
- **Dataset + shape.** JavaScriptCore/WebKit, verified by the released artifact against WebKitGTK 2.41.6. The paper runs 24-hour fuzzing campaigns.
- **Evaluation results.** In 24-hour runs PILLM improved coverage by 45.7% over Fuzz4All and 14.9% over Fuzzilli, and found four new JavaScript-engine bugs.
- **Concept applicability.** High. Its semantic seed scorer can become a concept validator: retain generated programs only if they exhibit the target API relation, guard, or execution-state transition. Pairing concepts with coverage feedback is the important part, not merely adding prose to a prompt.
- **Evidence.** Full text evidence via primary article abstract and official artifact. [IEEE article](https://ieeexplore.ieee.org/document/11044883/); [official code](https://github.com/DPCa0/PILLM)
- **Artifacts (checked 2026-09-29).** Code: verified source [github.com/DPCa0/PILLM](https://github.com/DPCa0/PILLM) (Python instrument/generate/fuzz scripts + prompts + Fuzz4All baseline, 32.9 MB, last push 2025-03). Dataset: JavaScriptCore (WebKitGTK 2.41.6) as fuzz target; baselines Fuzz4All, Fuzzilli — public benchmark only. Models: GPT-4o.

## 71. AutoQALLMs: Automating Web Application Testing Using LLMs and Selenium

- **Method.** The framework extracts HTML, asks GPT-4/Claude/Grok to generate Selenium scripts, cleans generated code with regexes, executes it, and reports results. The user supplies a URL.
- **Motivation.** Manual browser-test authoring does not keep pace with frequently changing sites; the authors target one-click test generation from rendered web content.
- **Dataset + shape.** The paper uses web pages/sites as subjects. The accessible full text did not provide a stable benchmark-size statement that I can quote with confidence.
- **Evaluation results.** The paper compares models and says Claude 4.5 achieved slightly higher coverage, while GPT-4 was chosen as the default for cost, reproducibility, and script stability. I am not reporting an unverified aggregate percentage.
- **Concept applicability.** Moderate. Concepts should carry action preconditions, DOM-role selectors, data constraints, and expected page-state assertions. Raw HTML is a poor substitute for this semantic state.
- **Evidence.** Full text, dataset/result count not transcribed. [University-hosted published PDF](https://uhra.herts.ac.uk/id/eprint/26265/1/computers-14-00501.pdf)
- **Artifacts (checked 2026-09-29).** Code: verified source [github.com/Sindhupriya2797/AutoQALLMs](https://github.com/Sindhupriya2797/AutoQALLMs) (Python Selenium+LLM generator, compare-LLM script, backend/frontend, 241 KB, last push 2026-03). Dataset: 30 public automation-practice websites (Table 4) — public benchmark only. Models: GPT-4 (gpt-4), Claude Sonnet 4.5 (claude-sonnet-4-5-20250929), Grok (grok-code-fast-1).

## 72. CrossGuard: Runtime-Adaptive LLM Fuzzing for Cross-Contract Vulnerabilities Detection

- **Method.** LLM-driven fuzzing for vulnerabilities that emerge from interactions across smart contracts, with runtime adaptation.
- **Motivation.** Single-contract fuzzers miss behaviors that require cross-contract call chains and evolving blockchain state.
- **Dataset + shape.** Abstract-only. The accessible Wiley record did not expose the experimental corpus or subject count.
- **Evaluation results.** Abstract-only. No numerical claim recorded.
- **Concept applicability.** High in principle. A concept needs call-chain topology, caller/callee roles, storage state, authorization condition, asset-flow relation, and target vulnerability class. This is a good target domain for stateful concepts but not yet a reproducible source for this repo.
- **Evidence.** Abstract-only. [Wiley DOI](https://doi.org/10.1002/cpe.70421)
- **Artifacts (checked 2026-09-29).** Code: data/prompts only, no tool source [github.com/ghazi1987/CrossGuard/tree/master](https://github.com/ghazi1987/CrossGuard/tree/master) (Paper ref [53]; master branch = 500 .sol contracts only, no fuzzer source; main branch near-empty; last push 2025-09). Dataset: 500 cross-contract Solidity contracts (Etherscan/SmartBugs-Wild); baselines CrossFuzz, xFuzz — released by authors [github.com/ghazi1987/CrossGuard/tree/master](https://github.com/ghazi1987/CrossGuard/tree/master). Models: Llama-3.3-70B.

## 73. One Mutation Fits All: Exploring Universal Library Fuzzing Based on Exogenous Mutation

- **Method.** Exogenous mutation for reusable library fuzzing. The exact construction and evaluation need the paper PDF; the IEEE landing page was accessible but did not provide full text in this pass.
- **Motivation.** Libraries need fuzzing strategies that transfer across APIs instead of bespoke mutators per target.
- **Dataset + shape.** Abstract-only.
- **Evaluation results.** Abstract-only.
- **Concept applicability.** Potentially high. The “mutation relation” is a natural concept, but this needs full-text confirmation before borrowing its method or claims.
- **Evidence.** Abstract-only. [IEEE DOI](https://doi.org/10.1109/TDSC.2025.3588878)
- **Artifacts (checked 2026-09-29).** Code: none found (No repo found (gh/web search); TDSC full text paywalled). Dataset: 20 real-world libraries (C++, Python, Java, JS) with AFL++, libFuzzer, Atheris, Jazzer — unknown. Models: unknown.

## 74. FuzzCoder: Code Large Language Model-Based Fuzz Testing for Industrial IoT Programs

- **Method.** Code-LLM-based fuzzing for industrial IoT programs; the publisher page confirms the article but does not expose enough text here to reconstruct its pipeline safely.
- **Motivation.** Industrial IoT software mixes protocol constraints and safety-critical behavior, which makes random malformed inputs ineffective.
- **Dataset + shape.** Abstract-only.
- **Evaluation results.** Abstract-only.
- **Concept applicability.** Plausibly high. Protocol grammar, device mode, safety guard, and dangerous command/value combinations are the relevant concepts. Do not cite this as evidence for a particular mechanism until the full paper is retrieved.
- **Evidence.** Abstract-only. [IEEE article](https://ieeexplore.ieee.org/document/11028927/)
- **Artifacts (checked 2026-09-29).** Code: verified source [github.com/weimo3221/FuzzCoder](https://github.com/weimo3221/FuzzCoder) (Modified AFL (C) + Python LLM mutation + FuzzInstruct data, 94.7 MB, last push 2025-02; linked from arXiv preprint 2409.01944). Dataset: FuzzInstruct + Fuzz-Bench (nm, readelf, objdump, xmllint, mp3gain, ImageMagick, tiffsplit, jpegtran) — released by authors [github.com/weimo3221/FuzzCoder/tree/main/dataset](https://github.com/weimo3221/FuzzCoder/tree/main/dataset). Models: StarCoder-2-7B, StarCoder-2-15B, CodeLlama-7B, DeepSeek-Coder-7B, CodeQwen-7B, CodeShell-7B.

## 75. A Survey of Coverage-Guided Greybox Fuzzing with Deep Neural Models

- **Method.** Survey and taxonomy of neural assistance at three fuzzing stages: seed generation, seed selection, and seed mutation. It frames coverage-guided fuzzing as an optimization problem and discusses LLM and neurosymbolic directions.
- **Motivation.** Existing surveys split by technique or application and do not organize how neural architectures affect the three operational fuzzing stages.
- **Dataset + shape.** Literature survey; no evaluation dataset and no new fuzzer.
- **Evaluation results.** No experimental comparison. It identifies unresolved issues: semantically invalid seeds, computational cost, weak transfer across domains, limited interpretability, and inadequate benchmarks.
- **Concept applicability.** Strong design guidance. Use concepts as a validity and priority signal at all three stages: generate inputs consistent with a concept, prefer seeds that satisfy more of it, then mutate the fields the concept names. The survey’s warning about invalid seeds argues for an executable checker.
- **Evidence.** Full text. [Open-access PDF](https://research-management.mq.edu.au/ws/portalfiles/portal/505591395/504850412.pdf)
- **Artifacts (checked 2026-09-29).** Code: none found (Survey; no tool). Dataset: N/A (survey; paper states 'No data was used') — not released. Models: none (no experiments).

## 76. Enhancing Differential Testing with LLMs for Testing Deep Learning Libraries

- **Method.** DLLens uses an LLM to synthesize an alternative implementation for a TensorFlow or PyTorch API, statically extracts path constraints from both implementations, and generates inputs that make the two implementations disagree when one is faulty.
- **Motivation.** Differential testing needs both a valid counterpart and diverse valid inputs. Existing DL-library tools struggle with both.
- **Dataset + shape.** 1,862 TensorFlow APIs and 1,121 PyTorch APIs were selected. The main comparison samples 200 APIs; the artifact releases API lists, counterparts, path-constraint tooling, and confirmed-bug CSVs.
- **Evaluation results.** DLLens synthesized counterparts for 1.84x as many APIs as the prior technique, covered 7.23% more branches under the same budget, and found 1.88x as many bugs on the 200-API sample. It reported 71 bugs, 59 developer-confirmed; 46 were previously unknown and 10 of those were fixed.
- **Concept applicability.** Excellent. The concept can be the semantic relation between source API and counterpart plus the joint path constraints. This turns concept guidance into a checkable differential oracle, far closer to fault exposure than TestEval line targeting.
- **Evidence.** Full text/artifact. [Official artifact](https://github.com/maybeLee/DLLens); [paper manuscript](https://arxiv.org/abs/2406.07944)
- **Artifacts (checked 2026-09-29).** Code: verified source [github.com/maybeLee/DLLens](https://github.com/maybeLee/DLLens) (Python tool (codes/: counterpart, constraints, mutation) + RQ notebooks, 10 MB, last push 2025-08). Dataset: TensorFlow 2.10 (1,862 APIs) + PyTorch 2.1 (1,121 APIs); API lists + confirmed-bug CSVs in repo — released by authors [github.com/maybeLee/DLLens](https://github.com/maybeLee/DLLens). Models: gpt-4o-mini.

## 77. Directed Greybox Fuzzing via Large Language Model

- **Method.** HGFuzzer converts target-path constraints into LLM code-generation tasks that create a harness and reachable inputs; it also synthesizes target-function-specific mutators.
- **Motivation.** Directed greybox fuzzers waste effort on path explosion and random mutation before reaching a known target location or vulnerability condition.
- **Dataset + shape.** 20 real-world vulnerabilities, with a separate search for new vulnerabilities.
- **Evaluation results.** HGFuzzer triggered 17 of the 20 known vulnerabilities, 11 within one minute, with at least 24.8x speedup over the compared directed fuzzers. It also found nine new vulnerabilities, all assigned CVEs.
- **Concept applicability.** Excellent. This is the closest fuzzing analogue of target-specific symbolic concepts: path predicates and the target function determine the harness, valid input construction, and mutator. A direct ablation is raw target location versus extracted guard/data-flow concept.
- **Evidence.** Full text. [arXiv manuscript](https://arxiv.org/abs/2505.03425)
- **Artifacts (checked 2026-09-29).** Code: verified source [zenodo.org/records/15553671](https://zenodo.org/records/15553671) (Zenodo HGFuzzer.7z 240 MB: src/main/*.py (harness_gen, mutator_gen, call_chains_analyze), per-CVE outputs; published 2026-07, not linked in arXiv). Dataset: 20 CVEs in 9 C/C++ libs (libming, libpng, libjpeg-turbo, lcms, libxls, libzip, libgd, cjson, libmodbus) — released by authors [zenodo.org/records/15553671](https://zenodo.org/records/15553671). Models: Claude-3.5-Sonnet.

## 78. Low-Cost and Comprehensive Non-textual Input Fuzzing with LLM-Synthesized Input Generators

- **Method.** G2FUZZ asks an LLM to generate and mutate Python input generators rather than producing binary inputs directly. AFL++ then performs local mutations on the generator output. LLM calls are reserved for global jumps in the search space.
- **Motivation.** Most fuzzing targets consume non-textual formats, and direct LLM generation of images, video, and PDFs is slow, expensive, and often invalid. The paper reports that 73% of analyzed FuzzBench programs take non-textual inputs.
- **Dataset + shape.** Programs from UNIFUZZ, FuzzBench, and MAGMA, across TIFF, MP4, and PDF formats. The paper evaluates coverage and bug finding across these platforms.
- **Evaluation results.** G2FUZZ outperformed AFL++, Fuzztruction, and FormatFuzzer on coverage and bug finding across most tested programs. It found ten unique bugs in current real-world software; three received CVEs.
- **Concept applicability.** High. Treat a concept as a generator specification: required chunk types, cross-field constraints, checksum/length relation, feature combination, and target parser state. Generating a small program from this spec is more inspectable and reusable than asking for one opaque binary input.
- **Evidence.** Full text. [USENIX Security PDF](https://www.usenix.org/system/files/usenixsecurity25-zhang-kunpeng.pdf); [official artifact](https://github.com/G2FUZZ/G2FUZZ)
- **Artifacts (checked 2026-09-29).** Code: verified source [github.com/G2FUZZ/G2FUZZ](https://github.com/G2FUZZ/G2FUZZ) (AFL++ fork + program_gen.py/generator_mutation.py, 3.4 MB, last push 2025-11; also Zenodo 14728879). Dataset: UNIFUZZ, FuzzBench, MAGMA + experiment data repo G2FUZZ-DATA (665 MB) — released by authors [github.com/G2FUZZ/G2FUZZ-DATA](https://github.com/G2FUZZ/G2FUZZ-DATA). Models: GPT-3.5, GPT-4, Llama-3-8B-Instruct, Llama-3-70B-Instruct.

## 79. Test Oracle Automation in the Era of LLMs

- **Method.** Survey/roadmap covering assertion, exception, contract, metamorphic, and temporal oracles; it reviews static and dynamic oracle derivation, then examines how LLMs change generation and validation.
- **Motivation.** Test generation without correct, complete assertions cannot reliably detect regressions. LLMs can express likely intended behavior but can also hallucinate unsupported oracles and inherit training-data leakage.
- **Dataset + shape.** Survey/roadmap. No new evaluation dataset or benchmark score.
- **Evaluation results.** No new tool evaluation. The paper identifies oracle accuracy, false positives, uncertainty/validation, formalism choice, and leakage as central research problems.
- **Concept applicability.** High for the assertion layer. A concept should be a candidate invariant/postcondition tied to a source of authority: documentation, reference implementation, differential counterpart, or observed metamorphic relation. Reject concepts that cannot be validated against one of those sources.
- **Evidence.** Full text. [Author arXiv manuscript](https://arxiv.org/abs/2405.12766); [TOSEM DOI](https://doi.org/10.1145/3715107)
- **Artifacts (checked 2026-09-29).** Code: none found (position/roadmap paper, no tool). Dataset: n/a: 6-page SE 2030 position paper, no experiments (illustrative ChatGPT-3.5 examples only) — not released. Models: none (no experiments).

## 80. Agentic Penetration Testing using Secure Shell: Context-Aware Command Generation and Analysis Using Open-Source LLMs

- **Method.** Agentic SSH-based penetration testing with context-aware command generation and analysis. The full pipeline cannot be reconstructed safely from the primary landing page alone.
- **Motivation.** Penetration-test workflows require adapting commands to host state and interpreting outputs instead of issuing a fixed scan script.
- **Dataset + shape.** Abstract-only.
- **Evaluation results.** Abstract-only.
- **Concept applicability.** Moderate to high for security testing: host facts, privilege level, reachable service, credential state, exploit precondition, and expected evidence can form an explicit concept state. Apply only in authorized sandbox environments.
- **Evidence.** Abstract-only. [IEEE DOI](https://doi.org/10.1109/CYBER-AI66431.2025.11233438)
- **Artifacts (checked 2026-09-29).** Code: none found (no repo found (paper page, GitHub search, author accounts)). Dataset: unnamed vulnerable website + custom pentest command-generation prompts (fuzz-score comparison) — not released. Models: CodeGemma-7B-Instruct, CodeLlama, Mistral.

## Inaccessible or incomplete full text

No accessible full text in this pass: 65, 68, 72, 73, 74, 80. Their notes intentionally remain abstract-only.

Accessible full text but I did not transcribe a verified numeric table: 64 and 71. Their notes state that limitation rather than guess from graphs.
