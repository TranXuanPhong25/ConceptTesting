# Ongoing audit recommendations

## High-fit paper #76 — EvoOtter

- Strong conceptual fit for SWT-Bench bug reproduction tests: it directly optimizes F2P test quality and uses mutant-derived execution feedback for selection; reports 77.8% on SWT-Bench-Verified.
- Not a runnable/reproducible base from public materials checked: no author implementation, evaluator, data manifest, or cached outputs located; exact reported models are Claude-Sonnet-4.5/Claude-Opus-4.7. Main controlled datasets are TDD-Bench-Verified/SWE-Rebench, not Defects4J/BugsInPy.
- It has no root-cause labels or explicit cause explanation. Treat as a method comparator, not an RCA solution. #74 remains the more actionable Defects4J evaluation foundation because its MIT artifact provides fixed/buggy data and analysis notebooks.

2026-10-15: full-text/public-source audit in progress. Previous shortlist is provisional.
Use `audit/reviews/` for new verified evidence; no paper/model reproduced yet.

Recommendations will be appended after full-text and author-artifact checks, distinguishing core
Defects4J/BugsInPy test generation, SWT reproduction, and supporting repair/fault taxonomy.

## Batch 1 — 2026-10-15

- #6 remains strong support taxonomy: public archive now verified, 488 annotations inspected.
  Full notebook reproduction is conditional on external repair-pattern inputs and checking a label-count discrepancy.
- #12 is not a priority base: patch-informed regression setting and missing verified author implementation/manifest.
  Its model-name availability does not establish experiment reproducibility.

## Batch 2 — 2026-10-15

- #44 TATG is close prior work for structured, tracked objectives. The paper only promises a future
  code/benchmark release; public implementation was not located. Fixed-version/mutation setting;
  retain as conceptual prior work rather than selecting it as a ready reproducible base.

## Batch 3 — 2026-10-15

- #56 CASCADE promoted among adjacent base papers: author MIT implementation, public data/archive,
  modular generators, end-to-end evaluator and pre-computed-result route verified. Main model config
  matches GPT-4.1-mini at temperature 0. No local reproduction or paid calls performed.
- Dataset is documentation-fix commits, including projects in Defects4J, rather than standard buggy/fixed
  Defects4J task IDs. Choose it for documentation-grounded concepts; a standard Defects4J experiment
  would require a separately declared adaptation.

## Batch 4 — 2026-10-15 08:15

- #25 SWE-Tester now has verified author source (paper v2), correcting the initial scan. Main SFT
  checkpoints remain unresolved; an inspected public author LoRA model repo is empty of weights.
  Retain as conditional, not a ready small-model inference baseline.
- #17 FOCAL: no public code/checkpoint located; discriminative oracle task rather than test generation.

## Batch 5 — core Defects4J

- #1 EvalAndMitigate remains first core candidate after full-text/source audit. Configure actual API
  models explicitly: notebook defaults mix GPT-4.1 docstrings and o4-mini tests. Filename labels alone
  do not select the model. Main pipeline requires no training; sequence-score GPU work is optional
  for a primary detection pilot, but part of full-paper reproduction.


### Audit batch 6 — 2026-10-15: RTED and DISTINCT

- **RTED (#3), v2 2025:** main paper and substantive author source checked at `ef10c4e1620cb618037a901092d266590e6b80bb`. Strong type-constraint concept fit on 69 BugsInPy/TypeBugs errors. Code removes assertions and uses TypeError, so findings do not establish general functional oracle quality. Correction to the initial scan: v2 evaluates Qwen3-Coder, including DS-generation/QC-reflection. Main configuration still DeepSeek-V3 API; model snapshots and full legacy environments need work. [Paper](https://arxiv.org/html/2507.02318v2), [source](https://github.com/chenyangyc/RTED).
- **DISTINCT (#4), latest v3 January 2026:** very close prior work for intended behavioral branches guiding bug-revealing tests. NLDs were authored from fixed methods. Public implementation and dataset verified at `ae28e128f36ae82fdadc8505af72a8ca6687bd28`. Public Defects4J JSON has **442 records**, paper says441; no exact duplicate records. Qianfan source temperature0.1 differs from paper0; local paths/helper case mismatch and stopping logic need reconciliation. MIT badge alone does not establish a source license. Promote concept fit, keep reproduction conditional. [Paper](https://arxiv.org/html/2506.07486v3), [source](https://github.com/anonymous-user-2309/DISTINCT).

Cumulative full-text/source audit: **9/500**, including **6 public implementations and3 source-not-found verdicts**, **0 locally reproduced**. These are reviewed candidates, not nine unconditional reproduction successes.


### Audit batch 7 — 2026-10-15: PANTA (#5)

Read full main paper v2 and inspected author implementation/evaluation at `e8e0c679263b27b9e5bf590110827f4beadc52ce`. Public subjects, manifest CSVs, analysis data and result reports are present. Exact paper-model mappings verified: Bedrock Llama3.3-70B Instruct and Mistral-Large2407; GPT4o-mini2024-07-18 and Claude3.5Haiku20241022. No learned weights needed. This is a strong reproducible-on-paper **coverage/path baseline**, conditional on environment/API access; no author evaluator was run.

Crucial setting:130classes/2971methods from14 **fixed** Defects4J versions, retaining tests that pass those versions. Coverage and PIT mutation score do not establish historical real-bug detection. CFG path approximation is structural guidance, not solver-certified feasible paths. The paper's26.3/22.7 coverage differences are percentage-point differences of70.18−43.91 and60.83−38.17, not relative percent improvement. Full rerun averages53minutes/class, about115sequential hours. [Paper](https://arxiv.org/html/2503.13580v2), [artifact](https://github.com/PANTA-TestAutomation/Panta).

Cumulative: **10/500 full-text/source reviews**, **7 public implementations**, **3 source-not-found**, **0 locally reproduced**.


### Audit batch 8 — 2026-10-15: AssertMate (#2)

Read full substantive v1 and checked Apache-2.0 author source at `3ca2a7e8d3390c6a1d7a3277a6f284bb55b02376`. Good oracle candidate, but **not immediately reproducible from README**: missing basic_config, config-schema mismatch, uninitialized tokenizer, debug single-response entrypoint, sample/token defaults differing from paper. Exact served DeepSeek-Coder checkpoint remains unpinned; the ungated6.7B model is only a plausible candidate, not confirmed identity. [Paper](https://arxiv.org/html/2608.05822v1), [source](https://github.com/LeonYang95/AssertMate).

Task is assertion generation on667human FM-prefix pairs/112known bugs, plus2203EvoSuite pairs. Human prefixes are already bug-triggering, retain prior assertions, and focal selection uses patch evidence. Public UTMapper extracts from **fixed** checkouts; do not label this unconditionally as buggy-input generation. Some public routes derive actual values/function categories from original target assertions; exact final ActVCon pipeline needs reconciliation. Mutation experiment does not report pass-rate/BDR, so stronger killed counts do not settle false alarms.

Useful next direction stated in paper: observation points requiring parameterized public methods (e.g., getRMS(problem)), plus where-to-assert when prefixes contain several scenarios. This supports concept-guided observation planning, but no extension has been implemented.

Cumulative: **11/500 full-text/source reviews**, **8 public implementations**, **3 source-not-found verdicts**, **0 locally reproduced**.


### Audit batch 9 — 2026-10-15: AdverTest (#7)

Read full substantive v3; author Java/Python source pinned `ef64ea33a9997796b459a3279b5bc72b7a375c17`. Actual setting generates tests/mutants from **fixed reference code** (200Defects4J+47GrowingBugs;12Python SWE-Rebench), not unknown buggy code. S3 mutation on covered-but-unmutated Python lines changes7/12 to11/12; do not attribute91.7% to original S1+S2 alone. [Paper](https://arxiv.org/html/2602.08146v3), [source](https://github.com/jmueducn/AdverTest).

Exact reproduction has material static-audit blockers: Java scheduling is mutation-score-threshold-driven, contrary to README/paper fixed T-M-T-M-T. Python evaluator counts `buggy_set != fixed_set`, which is broader than nonempty `buggy_set - fixed_set`; for example losing a fixed-only failure would satisfy inequality without revealing a new buggy failure. Java compares failure counts/raw stdout. These are source-level discrepancies, not executed findings about published result validity. Python default temperature0.7 versus paper0; referenced Python input data absent from tracked tree; exact200-bug manifest unverified.

RIP-aware feedback is explicitly future work: current feedback supplies survivor source diffs and does not classify reachability/infection/propagation dynamically. Suitable close prior work; conditional reproduction, no author source edited/run.

Cumulative: **12/500 full-text/source reviews**, **9 public implementations**, **3 source-not-found**, **0 locally reproduced**.


### Audit batch10 — 2026-10-15: Doc2OracLL (#10)

The cached arXiv HTML was incomplete (ends afterRQ1); downloaded and read the full23page v2PDF, including all5RQs, tables, threats and references. SF110 documented-subset fine-tuning and374Defects4Jprefix evaluation confirmed. Normative P2 excludes MUT, but86/374missing docs are GPT-generated from implementation; provenance matters. [Paper](https://arxiv.org/pdf/2412.09360v2).

**New model availability evidence:** original artifact link/full checkpoint suite still missing, but a later paper by the authors supplies a CC-BY4.0 [Figshare archive30110098.v1](https://doi.org/10.6084/m9.figshare.30110098.v1). Checked ZIP directory and fetched actual CodeLlama adapter:16,794,456bytes,128safetensors tensors, SHA256 `ee78e9cbe9985e2d84da40895b736fb0277e8e9aff79c7b98ecc2553fa8059c9`. Config pins base family `codellama/CodeLlama-7b-hf`, LoRA r16/alpha64/q_proj/v_proj. No weights loaded or inference performed.

This provides a **partial author-model route**, satisfying an important fallback criterion, but follow-up scripts evaluate exception-marker subsets onSF110/OE25, not full original374bug replay. Do not claim original60model/prompt-combination reproduction. [Follow-up paper](https://arxiv.org/html/2608.00884); [official author publication page](https://assert-lab.github.io/publications/).

Cumulative: **13/500 full-text/source reviews**, **9 public implementations**, **1 partial author artifact/model route**, **3 source-not-found**, **0 locally reproduced**.


### Audit batch11 — 2026-10-15: Tratto (#8)

Read full substantive v2 and verified artifact links from [paper](https://arxiv.org/html/2504.04251v2) and [official coauthor page](https://homes.cs.washington.edu/~mernst/pubs/axiomatic-oracles-issta2025-abstract.html). Very high abstract-concept fit: grammar/type-constrained axiomatic pre/postconditions. These constraints establish compilability, not semantic correctness. Defects4J is used for annotated oracle extraction and6projectmutation evaluation; not historical-bug detection. On the full negative-rich set, paper reports precision49% rather than selected-set72%.

**Artifact identity correction:** exact anonymous replication link now401`not_connected`; GitHub `AML14/tratto-replication-package`404. Public [AML14/tratto](https://github.com/AML14/tratto) at `edd9b67a1bb8580cf8fa6f68adcb8618122b0219` contains substantive source but README/server actually use separate CodeT5+770M token-class/token-value models. Paper uses CodeLlama7Bmultitask. Do not count related CodeT5 source or SWITCH checkpoint links as the exact paper model. Keep partial-source/unknown-exact-reproduction verdict.

Cumulative: **14/500 full-text/source reviews**, **9 public implementations**, **2 partial routes**, **3 source-not-found**, **0 locally reproduced**.


### Audit batch12 — 2026-10-15: E-Test (#9)

Read full substantive v1; Apache-2.0 author artifact verified at `9bb95c1bf252a752f7ac8758e306d6f694a8a8dd`. Best model is a **personal GPT3.5Turbo fine-tune**, not public baseGPT3.5. No public access to that exact fine-tune verified. Actual fine-tuned-output archive downloaded (117941bytes,1948members); notebooks provide an offline metric route, not yet executed. [Paper](https://arxiv.org/html/2510.19860v1), [artifact](https://github.com/ketaiq/E-Test-package).

Task supplies candidate inputs;1975scenarios classify relative to existing suites. Error-prone/need-test pairs share triggeringinputs and differ bybuggy/fixedcode. RQ5 on673triggeringscenarios instructs model to modify assertions to make tests fail; source loop accepts when failures appear. Thus83.2%reportedfailure-revealing generation is not evidence of false-alarm-controlled unknown-bug discovery without fixed replay. Exact privatefine-tune availability and oracle validation remain base-selection blockers.

Cumulative: **15/500 full-text/source reviews**, **10 public implementations**, **2 partial routes**, **3 source-not-found**, **0 locally reproduced**.


### Audit batch14 — 2026-10-15: CAT (#13)

Read full substantive latestv2(11Oct2026),all7chunks;MITartifact checked at `9da2e360b14c623067555acf806f98b297b0fbdd`. LocalQwen3-Coder30B, nofinetuning, strong call-chain/object-initialization context and publicSootUp analyzer.130fixedDefects4Jclasses/2971methods plus112classes/2707methods from4newprojects. This explicitly generates **regression** assertions matching currentcode;notindependent semantic bugoracles. [Paper](https://arxiv.org/html/2604.22046v2), [source](https://github.com/Amocy-Wang/CAT).

Reproductionconditional:publicdefaults propagate100000outputtokens vs16384paper;runner stagnation10 vspaper3;hardcodedmodelendpoint needsconfiguration andOllamadigest/quantization notpinned. FullD4Jgeneration353.8hplus8.35hstaticanalysis;newprojectgeneration321.3hplus61.63hstatic. Noauthorrun. Callgraphs overapproximate feasiblebehavior;paperreports2.41%spuriouspaths. CAT+path naiveintegration reducescoverage, relevant toselectiveconcept/contextdesign.

Cumulative: **16fulltextsread/500**, **17source-checked/reviewed**, including1access-blocked unreadpaper; **0locallyreproduced**.


### Audit batch15 — 2026-10-15: NeuroTestGen (#15)

Read fullmainandAppendixA/B ofv1;exactanonymousartifacthasdirectfiles200despiteroot401. README,methodology,symbolicexecutor,modelinvoker/evalsourcechecked. **Documentedbatchcommanddisablessymbolicexecution,LLMpathsolverandverifier** (runnerlines67–69,alsoexplicitinevalREADME). Thismustbereconciledbeforeclaimingexactfullmethodrun. [Paper](https://arxiv.org/html/2609.30178v1), [artifactREADME](https://anonymous.4open.science/r/Symbolic_Execution_Based_Test_Generation-F4F3/README.md).

FixedDefects4J130classes/2971methods;coverage/passrate,notrealhistoricalbugdetection. Pure-numericalZ3translator skipsloopsandmethodbodies,canignoreunsupportedexpressions,modelsfloatingpointasReals. Objectpaths(80.96%)useLLMsolver/verifier. ThereforeSAT/UNSATandLLMacceptancearenotgeneralJavafeasibilityproofs. Strongconceptualpriorworkbutconditionalreproduction;noauthorrun.

Cumulative: **17fulltextsread**, **18sourcechecks/reviews**, including1unreadaccessblockedpaper. No500/500claim.


### Correction after direct-file verification — 2026-10-15T08:38:44.892872+07:00

Root401 did not imply the whole anonymous artifact was inaccessible. ExactREADME,modelinstructions,server/source andRQ3instructions arepublic viaindividualpaths. ExactCodeLlama7Barchitectureconfirmed. Checkpointconfig/indexdownloadable, but**all3weights-shardlinks404**. Upgrade exactsource topublicimplementation;conditionalreproductionduemissingweights. EarlierpublicCodeT5repository remains different. Noauthorcode/modelrun. Evidence:exact-source-manifest.json andexact-weights-access.json.


### Audit batch17 — 2026-10-15: Bigger Is Not Always Better (#30)

Đã đọc toàn bộ PDF chính thức 20 trang, thay cho publisher landing bị collector nhầm là full text. Paper đánh giá localized block repair trên BugsInPy: 40 bugs ban đầu, 35 bugs/2100 runs trong balanced analysis. Hai author repositories đều public; source chính pinned `e3cc68f625c69eacd334437f1c9c1343aae6b348`, publisher còn cung cấp Software Heritage archive. Model nhỏ nhất là Qwen2.5-Coder-1.5B; không cần fine-tuning. [Paper](https://doi.org/10.4230/LIPIcs.ESEM.2026.34), [source](https://github.com/syedfakhar25/empirical-llm-bugfix-benchmark).

Static audit thấy source hiện tại clean Markdown/AST blocks dù paper nói không clean outputs; inference dùng deterministic decoding. Energy code trừ idle energy đo trong 5 giây khỏi tổng generation energy, không scale theo generation duration. Public manifest 40 bugs khác subset trong results CSV; CSV có 2401 rows và 7 model IDs, cần xác định đúng balanced 35-bug cohort. Các discrepancy này cần giải quyết trước exact reproduction; chưa chạy author code.

Xếp nhóm supporting APR/cost analysis, không phải test-generation base. Cumulative: **18 full texts read, 20 source checks/reviews, 2 unread access-blocked; 0 locally reproduced**.


### Audit batch18 — 2026-10-15: KITE mechanisms (#16)

Đã đọc toàn bộ main paper v1, gồm method, mọi RQ/tables và threats. Đây là close prior work rất quan trọng: what/where/how bug-mechanism summaries, AST structural instantiability, dual retrieval và executable synthetic-bug feedback. Benchmark 172 method-local Defects4J tasks; offline KB có 1325 reviewed mechanisms. [Paper](https://arxiv.org/html/2607.11573v1).

Tuy nhiên, tất cả methods nhận **correct-version code**; buggy version chỉ dùng cuối cùng để chấm detection. Backend là GPT-5.4, khoảng177k–225k tokens/method tùy cohort. Chưa tìm được public author source, mechanism KB hoặc exact evaluator/manifest qua paper và targeted source searches. Vì vậy xếp ưu tiên cho novelty/prior-work analysis, chưa là base dễ tái hiện. Không tự reimplement.

Cumulative: **19fulltextsread/21sourcechecks**,2unreadblocked,0locallyreproduced.


### Audit batch19 — 2026-10-15: IntTestGen (#14)

Đã đọc full main v2 (6chunks), gồm tất cả RQs, tables, ablations và threats. Fixed Defects4J130classes/2971methods và Deps4J30classes/540methods. Usage slicing, ClassIndex, Markov typestate và experience memory là prior work trực tiếp cho state/protocol concepts. [Paper](https://arxiv.org/html/2605.26851v2).

Original Qwen3-Coder-30B-A3B-Instruct-FP8 base model metadata public đã verify; nhưng chưa tìm được author pipeline/source hoặc Deps4J exact manifest. Source search dùng cả IntTestGen và tên cũ MocklessTester. Paper thừa nhận learned typestate có thể chặn sequence tiết lộ implementation bug; đây là guidance heuristic, không phải formal protocol oracle. Evaluation là coverage/mutation/DepLC trên fixed code, không phải historical-bug discovery.

Cumulative: **20fulltextsread/22sourcechecks**,2unreadblocked,0locallyreproduced.


### Audit batch20 — 2026-10-15: Cognitive layered evaluation (#18)

Đã đọc toàn bộ main v1 và kiểm tra officialPDF; AppendixAfigures4–7 được đọc trực tiếp từ rendered pages19/20. Paper đề xuất sáu Bloom layers, nhưng **Evaluate§4.5 để trống** và Create là future work; chỉ bốn layers có experimental results. Defects4J/GHRB và LIBRO-based reproduction được xác nhận. [Paper](https://arxiv.org/html/2510.05365v1).

Chưa tìm được original study source/mutated dataset/annotation artifact. Identifier masking làm mất cả semantic API cues nên drop không tự chứng minh memorization; open-book dùng near-identical examples từ cùng dataset. RandomForest feature importance là association, không phải causal evidence cho từng report component. Xếp supporting evaluation methodology, không phải base dễ tái hiện hoặc concept generator.

Cumulative: **21fulltextsread/23sourcechecks**,2unreadblocked,0locallyreproduced.


### Audit batch21 — 2026-10-15: CleanTest (#19)

Đã đọc đủ PDF chính thức 24 trang. Artifact của tác giả ở Zenodo là CC-BY-4.0; versions v1/current có các filename/checksum giống nhau. Đã tải/verify README, script archive, models archive metadata. Paper fine-tune CodeBERT, CodeT5/AthenaTest, StarCoder15.5B, CodeLlama7B; CodeGPT dự đoán coverage filter. Dataset includesMethods2Test/Atlas andDefects4Jdual-versionbug detection. [Paper](https://doi.org/10.1145/3715778), [artifactcurrent](https://zenodo.org/records/15347368).

Artifact is substantive, but `models.zip` is only1865bytes/empty model directories: trained checkpoints absent. README provides scripts/data, training uses4RTXA800. Thus exact originalmodel result needs retraining; noauthor code/modelrun. Noise counts/splits inREADME and paper need pinning and recomputation. Supporting data-quality baseline, not concept generator.

Cumulative: **22fulltextsread/24sourcechecks**,2unreadblocked,0locallyreproduced.


### Audit batch22 — 2026-10-15: AssertFlip (#20)

Paper v2 and public Apache-2.0 replication repo at a5cd61992e0791b6a167549b1e2eca13627eed3f read/checked. Excellent SWT-Bench candidate: passing test on buggy behavior → invert assertion → LLM validate bug-specific failure. Public datasets, pipeline, prediction logs and evaluation outputs are present. [Paper](https://arxiv.org/html/2507.17542v2), [source](https://github.com/uw-swag/AssertFlip).

Model is Azure GPT-4o alias/temp0, no checkpoint or immutable deployment pin; about $1 per Verified issue at 10 regeneration attempts. Agentless localization is a required external component. Important denominator: paper reports 189/433=43.6%, while generating tests for only 326 issues (conditional rate 58%); keep generation coverage and conditional success distinct. Cached artifact supports output inspection, but no author run was performed.

Cumulative: **23 full texts read, 25 source checks, 2 blocked, 0 reproduced**.


### 2026-10-15 — Issue2Test (#21)

Issue2Test is one of the closest prior works for failure-specific tests from issue reports: root-cause hypotheses, project conventions, and iterative execution feedback. It has public implementation and cached evaluation assets, but exact replay is conditional due to an unpinned GPT-4o-mini alias/config, iteration-count discrepancy (3 in public YAML vs 20 in algorithm/default loop), missing root license, Docker build burden, and contradictory paper metrics. Treat as strong SWT-Bench Lite candidate, not evidence on Defects4J/BugsInPy.


### 2026-10-15 — ReProAgent (#22)

Very high concept fit: explicit root-cause/execution path, triggering conditions, environment and assertions, followed by issue–test–execution triadic review. Public implementation and cached outputs make it a promising SWT-Bench analysis baseline. Exact replay remains conditional because of unexplained 267/276 and 431/500 denominators, a 430-vs-431 localization-table mismatch, inconsistent cached Verified completion metadata, mutable GPT-5-mini alias, and absent root license. The paper reports $0.14/instance; do not incur API cost without separate approval. Not a Defects4J/BugsInPy study.


### 2026-10-15 — Echo (#23)

Echo is highly relevant concept-aligned issue reproduction work, but less practical to reproduce than AssertFlip/Issue2Test: the paper uses Gemini 2.5 Pro, tracked sample config defaults to GPT-4o, claimed outputs/logs are absent, source license is unverified, and full replay averages $1.54/instance with Docker+Neo4j+PostgreSQL. The paper’s patch-generated oracle is acknowledged as potentially misleading. Static source graph has AST/file/text structure but no explicit call/import edge types. Keep as strong related work and oracle-design evidence; not a first rerun choice.


### 2026-10-15 — iCoRe (#24)

iCoRe is a strong, fairly reproducible retrieval baseline for the concept-guided test project. It releases meaningful source, prompt templates, model-specific retrieval outputs, and full SWT Lite predictions/ablations; exact GPT-4o snapshot and inference settings are specified. It is not a root-cause taxonomy or concept representation method. Exact TDD rerun remains conditional: no final TDD prediction file was found, baseline artifacts are incomplete (AssertFlip 268/276), software license is undeclared, and full API replay is about $194 by paper-cost arithmetic. Keep it high for retrieval control/related work, pending budget and artifact coverage decisions.


### 2026-10-15 — e-Otter++ (#26)

Critical related work for issue-aware execution repair, heterogeneous test hypotheses and surrogate-patch selection. Public Zenodo contains results/log archives and TDD harness, but custom e-Otter++ source was not found. The cached TDD GPT-4o predictions match 449 cases; SWT Lite cache has 272/276. Re-run is expensive ($1.80 GPT-4o/$2.75 Claude per issue including Agentless), and exact pipeline reproduction is conditional on locating code and patch artifacts. Do not reimplement without approval. Keep its surrogate-patch oracle as an important limitation/control in our own study.


### 2026-10-15 — Generalizable APR evaluation (#28)

Useful supporting study for cross-language repair and realistic FL: 13 models across Defects4J, BugsInPy, BugsJS, BugsPHP, with test-error and FL controls. It is APR, not test-generation/root-cause taxonomy. Results supplement is a 457.69 MB Figshare share marked private; no runnable source/scripts found, and several cohort counts differ between prose and Table 1. Keep as background for benchmark/cohort design; reproduction is conditional and lower priority.


### 2026-10-15 — Hierarchical Knowledge Injection (#29)

Strong BugsInPy supporting paper for bug-type analysis and repository-context layers. Unlike the initial scan, the exact author repo is public and contains notebooks, annotations, prompts, patch outputs and result CSVs; all 314-row tables/labels were checksum-verified. It remains APR with perfect function localization, not BRT generation or causal diagnosis. Reuse is conditional because the repo lacks an explicit license and environment/model versions are not locked; GPT-4o-mini API and 70B local model resources are needed for a full regeneration. Good source to inform bug taxonomy, not a replacement for SWT-Bench test-generation work.


### 2026-10-15 — D4C (#31)

D4C is a strong, MIT-licensed APR artifact on Defects4J with archived outputs and a useful perfect-vs-method-level localization comparison. It is not test generation or root-cause analysis. Exact rerun is conditional on historical GPT-4-0613 API, 8xA100-scale Mixtral inference, Defects4J v1.2/v2.0 reconstruction and LeetCode cookies for DebugBench. Use as APR/FL support only.


### 2026-10-15 — DCAware (#32)

High-priority oracle-generation related work: its “Self-Repair Trap” supports measuring fault-revealing strength separately from execution success. A complete MIT/CC BY artifact provides source, dataset, cached outputs, smoke tests and PIT evaluation. But it assumes a supplied test prefix/current code as expected behavior; it is not issue-to-reproduction generation on Defects4J/BugsInPy/SWT. Rerun is conditional on Java/Maven/Docker/PIT and 40GB A100 or Azure API; no calls made.


### 2026-10-15 — SeGa (#33)

Very high novelty-related work for concept-guided testing: PRD requirements are organized as functionality entries and converted to executable business scenarios with constraints. The public repo is only the core agent; industrial Go repos, PRDs, 60-bug labels and deployment data are private, and the exact SeedCode endpoint/checkpoint is unavailable. Treat as important related work, not a reproducible baseline. It is not a Defects4J/BugsInPy bug-reproduction study.


DCAware artifact correction: full public Zenodo package (MIT source, CC BY 4.0 archive) is available under record 21357436; CNTG/CGNTG are supporting components. Its code/data/results are inspectable, although full reproduction still has substantial environment/model requirements.


### 2026-10-15 — LISA invariant testing (#34)

Very high oracle-quality related work: separates API reachability from documentation-grounded invariant oracles and directly studies self-repair/oracle weakness. Its public artifact is complete and includes results/source, but the benchmark is C/C++ library oracle completion with given prefixes, not issue-based bug reproduction. Strong protocol/metric reference, not a direct Defects4J/SWT baseline. Full rerun requires Java/Maven/Docker/PIT and 40GB GPU or Azure.


TOGLL (#35) is a strong oracle-generation/Defects4J paper with unusually useful public data, scripts, and a bundled 110M fine-tuned checkpoint. Keep it high for correctness-vs-strength evaluation, but exact replay is conditional until the RQ5 `tc_mut`/checkpoint-path discrepancy is reconciled with paper P6. It supplies prefixes and is not a direct concept-guided issue-reproduction method.


UnitCon (#36) is high-priority supporting work for targeted Defects4J exception reproduction: it makes sufficient trigger conditions explicit and provides BSD-3-Clause code/data plus reproducibility instructions. Keep it below direct functional-test/LLM papers because it targets runtime exceptions only and has extreme full-run requirements (512GB RAM, 188GB storage; authors estimate 125 days sequential). Its minimal eight-project experiment is much more practical for a bounded baseline.


CoverUp (#37) is a good public baseline for coverage-guided Python test generation and custom-model evaluation, with Apache-2.0 implementation/evaluation code and archived test outputs. It must not be counted as BugsInPy bug reproduction: its CM set derives from earlier BugsInPy project subjects, but has no historical bug versions. It does not model causal root causes or oracle strength; full GPT-4o reproduction is expensive.


TAM-Eval (#38) is one of the best candidates if the goal is easy evaluation of the user’s own model: it provides public Apache-2.0 code/data and pass-rate, coverage-delta, mutation-delta metrics across Python/Java/Go test maintenance. It does not test issue-to-bug reproduction or root-cause correctness. Exact paper reproduction is conditional because current published model script disagrees with the paper’s model table and no raw outputs/checkpoints were found.


LLM4UT empirical study (#39) is high-value related work for Defects4J bug-detection evaluation and for separating test pass/correctness from real fault detection. Its strongest empirical warning is that DeepSeek-Coder-6b found only 8/163 bugs at 0.74% precision. Public scripts/results support analysis, but exact full reproduction is costly (>3,000 A100 hours), test-generation data/checkpoints are absent, and the D4J runner hardcodes author-local paths. It supplies no causal root-cause labels.


AnyPoC (#40) is among the closest conceptual fits for causal report-to-trigger generation: it extracts trigger, root cause, consequence and oracle, then verifies PoCs independently and rejects false reports. The public Apache-2.0 author code is an evolving current CLI, not a frozen replication package; the 192-report corpus and raw outputs are absent, model calls are costly, and it uses bespoke systems instead of Defects4J/BugsInPy/SWT. Use as strong related work and design reference, not as a direct baseline until the paper data/version are available.


TestCTRL (#41) is a plausible coverage-RL/Defects4J lead, but its full paper is access-blocked in this audit. The matching-title 2023 anonymous Zenodo package contains data/scripts and generated tests, but both checkpoint and pretrained-model ZIPs are empty. Leave selection pending full-text access and confirm the final paper-to-artifact link before reproduction.


BRMiner (#42) is a strong Defects4J-related method for report-grounded test-input concepts. The paper links issue literals to EvoSuite/Randoop inputs and measures both test strength and coverage; this is a useful precursor for bug-report hints. However, the author-linked repository currently returns 401/404, so exact source reproduction is not feasible. Its relevance measure is exact token/literal overlap with post-fix tests, a restrictive proxy that excludes semantically related inputs.


The 178-paper LLM unit-test generation survey (#43) is useful for related-work taxonomy and metric design, especially its separation of construction from quality assurance and its warning that pass/coverage do not prove oracle correctness or real fault detection. It is not an experimental baseline; the underlying anonymous search-log package is currently inaccessible.


### TATG (#44) — 2026-10-15

Read the full 9,403-word paper. TATG is a very close concept/objective-tracking prior: it makes evidence, setup, action, oracle shape, acceptance, lifecycle status and behavioral de-duplication explicit, then separates branch reachability from mutation-guided oracle hardening. It evaluates fixed-code focal methods (110 KTester plus 31 additions; only nine additional methods come from fixed Defects4J revisions), not historical bug IDs or buggy/fixed pairs. The paper promises code/subjects but links no package; checked arXiv, exact-title public search and first-author public GitHub profile, finding no TATG implementation. Qwen3.6 and hosted DeepSeek-V4-Flash are named, but immutable revisions are not pinned. Keep high for novelty/related-work comparison, not as a currently reproducible base; revisit after the promised source/manifest release.


### DA-AG / mixed assertions (#45) — access-blocked

Official ISSTA abstract describes assertion-sequence generation with unknown insertion positions and reports Defects4J bug exposure, making this one of the strongest apparent matches for oracle generation. The official ACM route returned 403 and the coauthor PDF link returned 404; no author source package found. Keep high-priority for later access, but do not call it reproduced or select as a ready baseline until the full paper, artifact and exact model configs can be checked.


### Agentic Bug Reproduction at Google (#46)

Highest task alignment for BRT as a concept: explicit Fail-to-Pass oracle, issue + buggy-code input, and test usefulness for APR/fix selection. However, the 80-bug GITS cohort, Google code_search/Bazel, Passerine, and fine-tuned Gemini editor are private; Defects4J/SWT-Bench are only related work. Do not call it reproducible or treat its 28% result as a public benchmark score. Keep as a protocol/related-work comparator; its use of root-cause language is motivation, not a causal taxonomy.


### TestPrune / TestLoc (#47) — ưu tiên tái lập cao

Public Apache-2.0 author artifact pinned at `b9100eb6a4550486a26a07704d2d93560eaf751e`, substantive pipeline + precomputed results, and custom endpoint. High relevance to issue-focused existing-test selection and as context for bug-reproduction generation; strong choice for a one-task own-model evaluation after approval for model/API spend. Paper evaluates Python SWE-Bench Lite/Verified (uses TDD-Bench Verified harness for F→P), not SWT-Bench/Defects4J/BugsInPy. Full exact run is about two days and needs Docker plus API models. Keep percentages honest: 31.2→34.0 = +2.8 pp / +9% relative. Not a causal root-cause classifier.


### DPIAgent (#48) — thematic fit cao nhất, chưa reproducible

Ưu tiên theo hướng concept/root-cause: handoff có field root cause và expected/actual behavior trước khi tạo BRT; đánh giá đúng SWT-Bench Verified. Tuy nhiên hiện không thấy implementation, predictions, stable commit hay experimental outputs; model APIs cũng không pin snapshot. Đưa vào close related work/novelty comparator, chưa chọn làm exact reproduction base. So với #47: DPIAgent phù hợp hơn về root-cause handoff; TestPrune phù hợp hơn nếu ưu tiên chạy lại source/model ngay.


### CoHarden (#49) — prior work mạnh về oracle rigor, code chưa public

Rất phù hợp nếu novelty xoay quanh test thật sự constraining đúng fix: MPE cho thấy Rigorous BRTs +8.5pp Resolved, Lax BRTs 0.0pp, Misaligned −3.6pp; CoHarden dùng witness-first và hardening feedback. Cohort là intersection SWE-bench∩SWT-bench (433 Verified/276 Lite), API costs cao với GPT-5.4/Opus. Project page hiện để GitHub “Code under review”, nên chưa phải base tái lập. Dùng làm direct oracle-quality comparator và metric inspiration; không gọi đây là root-cause taxonomy.


### Goal-based EvoSuite objectives on Defects4J (#51)

Strong supporting artifact: modified EvoSuite + Defects4J fork and matching 5.6GB Zenodo experiment bundle; pin source commits before rerun. Useful for explicit behavioral/goal objectives (exception discovery, output diversity, execution-time) and real-fault detection. Multi-objective helps over goal-only but does not significantly beat Branch Coverage alone in fault detection; extra objectives increase suite size. No LLM, issue report, or root-cause taxonomy. Paper cites Zenodo 11047567 while matching-title public record found is 11047568; resolve before claiming exact artifact identity.


### Defects4J multi-objective EvoSuite study (#51)

Retain as a reproducible supporting baseline for branch+non-coverage testing objectives (exceptions/output diversity/runtime) and real Defects4J fault detection. Public author-modified EvoSuite and Defects4J forks plus matching 5.6GB Zenodo data make it unusually transparent, but full rerun is large and the DOI in the article (11047567) differs from the matching-title record found (11047568). Not an LLM, BRT, or root-cause method; use for objective/adequacy background and possible data reanalysis.


### EditAS2 (#53) — high priority for the original Qwen model

Promote for an own-model assertion-generation evaluation and a Defects4J oracle baseline. The paper directly evaluates Qwen2.5-Coder-7B-Instruct with CoT on Dataatlas/Dataintegration (31.68%/12.07% exact accuracy, 17.79%/8.48% CodeBLEU), so this is an unusually direct path to compare the project’s local model. Important limit: Qwen is not used for the paper’s Defects4J bug-finding experiment; do not attribute their CodeT5/EDITAS2 bug-found results to Qwen. Author-linked Zenodo package (CC BY 4.0 metadata, 1.94 GB) claims source/data/checkpoints/results; substantive matching public source is available at commit `47b1a657857c23c6a5e17958364723a8bbb4092f`. Full run conditional: old CUDA/PyTorch, hard-coded paths, no explicit GitHub software license, model package not audited. Results also have weak absolute oracle quality (30.97% compile, 0.42% precision) and random within-project train/test split. No code/model run.


### STMutants (#54) — adjacent only, not selected

The public Figshare dataset has 110 ST mutant files across 11 PLC programs (108 retained); CC BY 4.0. It does not use Defects4J experimentally—Defects4J is cited in related work—and has no author experiment runner/harness. The paper reports API results for GPT-5.2, Gemini 2.5 Pro, and Claude Sonnet 4.5; prompt parameters are incomplete. Keep only as adjacent PLC mutation-testing work. Exact replication is not feasible from the released package without implementing the missing pipeline and using paid APIs; no such work/calls performed.


### APR agent traceability (#55) — high conceptual fit, cached analysis feasible

Strong protocol paper for test generation/validation: studies reproducers, trigger rate, test overfit, regression-test selection, and localization context on SWE-bench Verified. Public author repo plus 3.28 GB Hugging Face traces and cached analysis outputs. Rerunning descriptive analyses is feasible without API calls; exact original agent trajectories are already cached. New 50-issue reproducer/localization sweeps require paid Claude Sonnet 4 API, Docker/SWE-bench and an external Agentless repo. Not a root-cause taxonomy and not a SWT-Bench experiment (SWT is related work only). Software/trace license not declared. See `reviews/055.json`.


### ReduJavator replication (#57) — supporting test-minimization paper only

Uses 30 Defects4J failed tests + 30 Java mutant tests to replicate AST-based test reduction. Public author Java reducer source exists, but source has no license, `TestObject` hardcodes author-specific paths, default run selects only one case, and its own observations log documents build/test reliability problems. Study finds statements in leaf nodes are removed more often in count, but probability of removal is not significantly higher (D4J p=.5426; mutants p=.5731). Useful for debugging/FL test-minimization background; not generation, BRT, oracle quality or root-cause taxonomy. Exact rerun conditional.


### TC-Bench (#58) — highest-priority own-Qwen test-generation evaluation

Public 877-problem C++ benchmark and evaluator; HF dataset MIT card, GitHub scripts. Paper directly evaluates Qwen2.5-Coder-7B-Instruct: LCB HackRate 42.17%, HT 21.92%. This is an excellent complementary custom-model evaluation for input/output generation and fault-discriminating test adequacy. It is not Defects4J/BugsInPy/SWT-Bench historical issue repair and gives no root-cause labels. Exact paper method reproduction remains conditional because generator prompts/implementation and API snapshots are missing; own model can still be evaluated by feeding JSONL tests to the public evaluator. Inspect matrix-rank theoretical claim carefully.


### LLM test-generation narrative survey (#59) — useful map, not reproduced evidence

High-value framing for behavioral information provenance, test artifact types, oracle quality and benchmark claims; includes SWT-Bench and TC-Bench discussion. The author-linked repository has a 95-record source register and manuscript, but explicitly describes a preliminary narrative synthesis, not an SLR. Most records are abstract/metadata inspected; independent dual screening, complete coding, IRR and quantitative synthesis are pending. Use as a discovery map; verify every method/metric claim in the cited primary paper. No experiment/model to reproduce.


### LLMutantKiller (#60) — strongest source-backed mutant-guided test generator

Complete MIT implementation + Docker, full prompts, 915-mutant sample, manual labels, stored per-attempt outputs and TestPilot comparison. Claude 4.6 validly kills 777/815 non-equivalent survivors (95.3%); Devstral 62.4%, Llama 26.5%. Reduced 13-mutant live run is ~17 min/<$1 historically; full twelve-run live recreation estimates 108 Docker days/$1.3k. Stored result inspection needs no API, and custom chat endpoint supports possible local Qwen use. This is excellent for behavioral-difference test generation/oracle validity, but JavaScript/TypeScript mutants only, not real issue reports, Defects4J/SWT historical bugs or root-cause taxonomy. Pair with #52 for real Java faults and #55 for issue BRT. No code/API run.


### TestAgent (#61) — highest root-cause concept fit, partial artifact route

High priority for explicit requirements → generation → review and test-failure root-cause triage. The paper evaluates Qwen3-30B-A3B and five Defects4J-derived Java project subjects; it manually verifies 154/167 test-revealed defects and categorizes causes (input validation 58.44%, boundary 20.13%, inconsistent state 14.29%, etc.). A full MIT VS Code/backend implementation exists from the overlapping-author FSE tool demo, with OpenAI-compatible model base config. However, the main article links no artifact, the demo has different author list/version, and exact method list/bug labels/UTXXX industrial dataset are absent. Use as strong conceptual prior and possible custom-model smoke, but do not claim exact reproduction or Defects4J historical-task evaluation. No code/model run.


### TestExplora (#63) — highest proactive-discovery task fit, conditional own-model route

This is a strong candidate for testing whether the user's model can discover latent bugs from documentation-derived intended behavior in real repositories. The test oracle is a pre-PR fail / post-PR pass transition; the benchmark has 2,389 tasks across 482 Python repos. The official Microsoft source is MIT and includes a local vLLM path and Docker evaluator. However, the checked public repo lacks task JSONs and result caches, the default subset loader reads an author-local absolute path, and the Qwen3-Coder-30B-A3B reported in the paper differs from the Qwen2.5-Coder-32B wrapper. Reproduction is conditional until data and model identity are resolved. It is proactive discovery, not issue-conditioned SWT-Bench or historical Defects4J/BugsInPy, and gives no root-cause taxonomy. See `reviews/063.json`.


### TDD-Bench-Java / Otter for Java (#98) — strongest practical local-model route

Top choice for evaluating the user's own model on Java issue-to-reproduction-test generation. IBM's Apache-2.0 artifact provides all 250 benchmark records, 250 matching IDs, test/code patches, pinned SWE-PolyBench patch and Docker evaluator. A model only needs to produce per-instance unified test patches for the JSON prediction format. The paper reports 43.6% Claude-Sonnet-4.5 and 46.4% GPT-5.2 F2P. The test generator itself is explicitly proprietary, so exact e-Otter++ replication is not possible; this is an easy benchmark/model evaluation route, not a faithful reproduction of their method. No root-cause taxonomy, and no Defects4J/BugsInPy/SWT-Bench experimental cohort. See `reviews/098.json`.


### Dynamic Cogeneration / Passerine (#75) — close concept, private benchmark

High conceptual value for issue-to-BRT co-generation: compares Fix-only/BRT-only with Freeform/TDD/TLD and adds test-aware patch selectors. Its failure analysis identifies discarded tests, debugging loops/wrong hypotheses and fix-test overfitting. However, 120 tasks are private Google GITS and the Passerine agent/source/trajectories are internal; no public implementation or task set was found. It cannot be replicated or run with the user's model on the same data. Use as a conceptual prior and failure-analysis lens only. It does not experiment on SWT-Bench, Defects4J or BugsInPy. See `reviews/075.json`.


### Business-requirement oracle generation (#79) — Defects4J conceptual lead, package not verified

Useful for separating intended specification (manual REQ oracle) from observed SUT behavior. It evaluates five hosted LLMs on 10 Defects4J Lang bugs and reports weaker agreement with SUT than with REQ. The claimed MIT replication package is a private Figshare share; binary download was not verifiable. Keep as concept/protocol prior, not an easy own-model baseline until data and scripts are actually obtainable. Small-n and no causal root-cause taxonomy. See `reviews/079.json`.


### SWE-Doctor (#92) — top public method for runtime-grounded diagnosis

Best current fit for the user's desired chain from issue behavior through failing tests and runtime diagnosis into patch generation. Official paper-linked MIT repository contains the full 4-stage Python pipeline and Go/PDB/Delve debugging, benchmark graders, and LiteLLM model config; a local Qwen endpoint looks possible. Reproduction remains conditional because the sole Oct 2026 repo commit postdates the July paper and labels itself an FSE 2027 artifact, paper-specific issue IDs/raw results are missing, and hosted model aliases are not immutable snapshots. It reports final patch resolution only, not diagnosis accuracy against root-cause labels. SWE-bench Verified/Pro, not SWT-Bench/Defects4J/BugsInPy. See `reviews/092.json`.


### Targeted LLM unit tests (#69) — useful supporting benchmark, not issue reproduction

DROPS ESEM 2026 paper evaluates 210 Java runtime-exception instances with target type and line given. 89.5% best (Claude Code + GPT-5), 65.2% OpenCode + DeepSeek-V3.2 at about $0.04/task. Good for targeted crash reproduction and failure-mode analysis (exploration/reasoning/tool misuse), but it is not an issue-text→BRT task, does not check a test against a fixed version, and has no ground-truth root-cause labels. Public Zenodo package (2.16 GB, CC BY 4.0) README confirms intended evaluation scripts and random subset route; full runner code was not inspected. Use as supporting route after validating package internals and custom local-model endpoint. See `reviews/069.json`.


### AG-RAG (#86) — high Defects4J assertion/oracle value, not an easy Qwen baseline

Useful source-backed assertion generator: jointly trains CodeT5 dense retrieval and generation, evaluates two TAP datasets, and detects 41 bugs vs EditAS 21 when assertions are inserted into EvoSuite test prefixes for 835 Defects4J bugs. Public repo includes 74 MB data, training/eval code and cached results, but no LICENSE; model checkpoints are external Drive. It is T5 encoder-decoder-specific and Qwen2.5-Coder decoder-only is not a drop-in. Training is ~29 hours on 2×RTX4090. Use for oracle/F2P design and CodeT5 reproduction only if license and weights are resolved; no causal RCA. See `reviews/086.json`.


### MutGen (#90) — easiest local-model mutation-feedback pilot, with licensing caveat

Unlike T5-specific AG-RAG, MUTGEN uses a LiteLLM text-completion router with model/api_base settings and the authors ran Llama-3.3 via local Ollama, so an OpenAI-compatible Qwen endpoint is a plausible minimal configuration change. Public author repo includes Java subjects, 74 MB dataset, PITest scripts, prompts and cached results. It reports 89% mutation scores and 41 vs EditAS 21 Defects4J bug detections (the latter on EvoSuite prefixes). Core benchmark is synthetic mutation/algorithmic method tests, not issue-level bug reproduction; source has no declared license and the README extraction command needs checking. See `reviews/090.json`.


### Coverage/mutation validity replication (#74) — top priority for evaluation design

Best direct evidence for the user's question of what makes a test-evaluation paper useful: it uses 318 buggy/fixed Defects4J focal methods and directly contrasts proxy metrics with F2P real-bug detection, including generation from buggy code. Author-linked MIT GitHub artifact at pinned commit `4bc2ed63917557a8c879e6c733b8fa41c15b9871` includes processed per-method CSVs and analysis notebooks, so the statistical results can be reanalyzed without API or Defects4J setup. This is much easier than repeating all 11 original models. Exact generation replay is conditional and expensive; original model snapshots are not pinned, and a few final boxplots use paper-transcribed correlations. Qwen on a selected Defects4J subset is a plausible independent-model evaluation route, not exact reproduction. High fit to direct bug-detection evaluation, but this is metric-validity work, not a concept/RCA method, and BugsInPy is only related work. See `reviews/074.json`.


### ORACLE-SWE (#111) — useful F2P signal motivation; not a reproduction candidate

Full paper and appendices define five SWE-agent handoff signals; F2P reproduction tests are the strongest individual signal in the oracle ablations. The paper uses SWE-bench Verified/Live/Pro, not Defects4J/BugsInPy/SWT-Bench; gold tests and patch-derived context are intentionally injected for the upper-bound study. No author source, data cache, or result archive was found. Reproduction would require implementing missing extraction/injection and using expensive, unpinned GPT/Claude APIs. Keep as conceptual evidence that strong F2P tests carry actionable information; do not use as a runnable baseline or RCA taxonomy. See `reviews/111.json`.


### GIANT (#107) — highest topical fit, but full text blocked

The SSRN abstract describes a direct Defects4J 2.0 bug-reproduction test generator using RAG over prior reports plus iterative test validation; it reports 51/750 reproduced bugs vs LIBRO 32 and BASE 8. This is one of the most directly relevant apparent papers for the user's dataset choice. However, the official 13-page SSRN PDF/HTML routes returned 403, exact-title/author source searches found no confirmed repo, and the abstract does not reveal the exact model or replication instructions. Treat as a high-priority access follow-up, not a verified or reproducible recommendation. Full text is not counted as read. See `reviews/107.json`.


### CATGen (#73) — strong context/skeleton design prior, partial source only

Directly evaluates Defects4J Chart/Math/Lang/Time and reports compilation, coverage, pass rate and mutation score. Its nine local checkpoints include Qwen2.5-Coder-7B-Instruct (same model as the user's current setup), plus 32B; Defects4J paper comparison uses QC-32B. However, the author-linked GitHub package explicitly withholds full CATGen implementation and industrial data: public artifacts are docs/examples/parser/LLM wrapper/partial results, with no runnable full generation/repair workflow or Defects4J focal-ID/evaluation harness. No LICENSE is present. It is not direct F2P bug detection or root-cause work. Strong method inspiration; exact reproduction/faithful own-Qwen evaluation not feasible without implementing missing parts. Prefer #74 for immediate Defects4J data analysis. See `reviews/073.json`.


### XRepoTest (#65) — strongest supplementary custom-Qwen repository-test benchmark

Public MIT author repository and public ungated MIT-tagged HuggingFace dataset; full pipeline includes prompts, LSP/file/RAG context, OpenAI-compatible local vLLM response generation, Docker evaluators for five languages, repair, metrics and tests. The base dataset is about 105 MB; complete LSP/RAG context grows to ~1.69 GB. A bounded local-Qwen run on Go/Rust/Ruby/PHP/Julia is fairly straightforward. The paper's exact models are Qwen3-8B and Qwen3-Coder-Next-80B, so Qwen2.5-Coder-7B is a custom model evaluation, not exact replication. Strong evaluation contribution: Invocation Rate catches tests that pass/get coverage by calling wrappers instead of the target. Limits: excludes Java/Python, Defects4J is related work only, no BugsInPy/SWT-Bench or issue F2P pairs, no root-cause labels; mutation is only Go/Rust/Ruby. Use as a supplementary repository-level quality benchmark, not the primary issue-reproduction dataset. See `reviews/065.json`.


### Prompt engineering at class level (#91) — relevant but final paper does not evaluate bug revealing

Read the complete final 58-page EMSE 2026 manuscript. It uses Defects4J (477 classes/16 projects), SF110 and CMD; four legacy LLMs and five prompts, 30 runs per setting, with extractability, compilation, readability, smells and coverage. Crucial correction: the final paper's §5.2.1 explicitly says it does **not** evaluate buggy/fixed F2P, exception-based fault detection or mutation. Some §6.5 prose inconsistently claims mutation is integrated, but no results table/RQ supports that. Its linked MIT 4open artifact is a 2024 snapshot whose README title/citation is an earlier study, and the visible tree lacks RQ3/RQ4/Test-Generation folders and many claimed model output roots. Keep as prompting/compilation background, not a direct BRT baseline. Exact final replication is not feasible until version/source mapping is resolved. See `reviews/091.json`.


### Test Oracle Automation in the Era of LLMs (#93) — conceptual grounding, no experiment

Position/perspective paper on assertion, contract and metamorphic-relation oracles; highlights false-positive/false-negative oracle deficiencies and proposes an assurance layer. Its Commons Collections/Defects4J example illustrates public-test oracle leakage only; it does not experimentally use Defects4J or evaluate a model. No implementation/results/data to reproduce. Useful foundational related work/threat model for concept-guided test oracles, but not a runnable baseline. See `reviews/093.json`.


### Go-UT-Bench (#81) — public fine-tuning data, weak test-quality validation

A public ungated HuggingFace dataset of 5,264 Go source/test pairs across 10 repositories, with commit provenance and train/test/validation splits. Paper fine-tunes DeepSeek-Coder-V2-Lite and Llama-3.2-3B, then uses only GPT-4o-mini as pairwise judge (81.9%/76.7% wins). Its own limitations admit no human triangulation, no execution/compilation/coverage or mutation validation, a single metric and no significance test. No training/evaluation code or tuned weights found; HF dataset has no license metadata despite paper's claim of permissive source repos. Go-only code→test SFT, not issue/F2P/Defects4J/BugsInPy/SWT. Keep as a secondary data lead, not a reliable benchmark or immediate replication base. See `reviews/081.json`.


### CANDOR / Hallucination to Consensus (#82) — strongest concept/oracle prior; synthetic mutants only

Best conceptual match among the latest reads for the user’s test-oracle direction: it explicitly demonstrates that oracles generated from faulty implementation can repeat the bug, then uses natural-language descriptions, a Requirement Engineer, three reasoning Panelists and a Curator to correct assertions. Public author-linked source and HumanEvalJava/LeetCodeJava datasets include three Pitest mutant variants. Reported oracle correctness is high and panel ablations are substantial. Limits: the paper explicitly excludes Defects4J/SF110 due to project dependencies; faulty programs are synthetic Pitest mutants, not historical issues; no root-cause labels. Source has no root LICENSE; local Ollama tags are hard-coded to 70B models and README paths conflict with current root-level tree. Qwen endpoint requires client/config changes, and hardware is 48GB+. Treat as high related-work/oracle-method comparator and conditional reproduction, not the primary benchmark base. See `reviews/082.json`.
