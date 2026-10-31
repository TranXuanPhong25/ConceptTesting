# Lựa chọn paper sau full-text/source audit

## Update sau audit #76 (2026-10-15)

- **SWT-Bench/BRT method comparator: #76 EvoOtter.** Direct F2P test generation; SWT-Bench-Verified is a reported secondary result (77.8%). High conceptual relevance for mutant-informed test selection. No public author implementation/evaluator/data package was located; main experiments use TDD-Bench-Verified/SWE-Rebench, and no root-cause labels are provided. Exact reproduction is not feasible from verified public artifacts.
- **Defects4J evaluation foundation: #74.** Still the most actionable paper in the high-fit set: real buggy/fixed Defects4J pairs, public MIT source, processed per-method data and no-API analysis notebooks. It studies measurement validity, not concept-guided test generation or root cause.
- **Root-cause objective:** neither #76 nor #74 solves cause attribution. Treat EvoOtter's mutation feedback as related method inspiration only; do not describe it as root-cause analysis.

Audit count: 74 full texts read, 81 source checks/reviews, 7 access-blocked unread, 0 author-code reproductions. Fresh quota cap is 50/50; no further full-text reads without a newly authorized cap.

Cập nhật 15/10/2026. Xếp hạng tạm thời dựa trên các paper đã đọc: 74/500 full texts, 81 source/review checks, 7 full-text access-blocked, 0 reproduction. Đã đạt giới hạn 50 paper bổ sung kể từ quota refresh; không bắt đầu full-text read mới nếu chưa được người dùng cho phép giới hạn mới. Quota UI 90% là remaining theo xác nhận người dùng; telemetry local được ghi riêng. Chưa chạy reproduction.

| Ưu tiên | Paper / task | Lý do chọn | Điều kiện tái hiện |
|---|---|---|---|
| 1 — historical bugs | EvalAndMitigate / Defects4J | Buggy-input test generation; MIT notebooks; đánh giá effective/misguided/false positives trên hai phiên bản | Generator thực tế hardcode o4-mini; model label không đổi runtime model. Cần API và kiểm tra snapshot. |
| 1 — documentation/concepts | CASCADE | MIT generator, data và evaluator; condition/behavior stubs rất gần hướng concept | Dataset riêng về documentation fixes; không phải standard Defects4J bugs. GPT-4.1-mini dùng alias. |
| 1 — fallback dùng original small model | Doc2OracLL | Đã tải được CodeLlama-7B LoRA adapter thực từ archive do tác giả công bố sau này | Evaluator tìm được thuộc nghiên cứu tiếp theo về exception prediction; chưa verify original 374-bug replay hoặc đủ 60 checkpoint combinations. |
| 2 — structural guidance | PANTA | Public implementation, manifest 130 classes, outputs và precise model IDs | Fixed-code coverage/mutation setting; muốn đánh giá historical bugs cần adaptation riêng. Full run tốn thời gian. |
| 2 — intended behavior prior work | DISTINCT | Intended logical branches → semantic consistency → tests; public dataset/source | NLD viết từ fixed code; public có 442 records so với 441 trong paper; còn config/import/stopping discrepancies. |
| 2 — Python, narrow fault class | RTED | BugsInPy/TypeBugs pipeline; backward type constraints và reflection; v2 có Qwen3-Coder | Oracle chỉ TypeError và bỏ assertions; cần xử lý legacy dependencies và model snapshots. |
| 2 — oracle generation | AssertMate | Apache-2.0 source; observation-point selection và expected-value agents; có gap về utility methods | Thiếu config/tokenizer/exact checkpoint; cần xác định đúng paper pipeline. Đã có triggering prefixes và fixed-source extraction. |
| 2 — local execution-context baseline | CAT | MIT source, local Qwen3-Coder-30B; explicit caller/constructor dependencies | Fixed-code regression; output/stagnation defaults khác paper; full run rất dài. |
| Support — root-cause taxonomy | fcd4j / 488 faults | MIT annotations về control/data flow; phù hợp phân loại nguyên nhân lỗi | Không sinh tests; discrepancy 55/56 use labels và external notebook data. |

Tratto là prior work quan trọng cho abstract concepts. Exact source đã truy cập được bằng direct file paths và xác nhận CodeLlama-7B; cả ba published weight-shard links hiện trả 404. Related GitHub source dùng architecture khác. AdverTest có schedule/evaluator discrepancies nên chưa phải lựa chọn dễ tái hiện. E-Test có cached outputs để đánh giá lại, nhưng best personal GPT fine-tune chưa verify public access; task dùng supplied scenarios.

Với câu hỏi dataset ban đầu, **ưu tiên Defects4J để phân tích root causes**: có buggy/fixed pairs và taxonomy 488 faults hỗ trợ. Chọn BugsInPy nếu Python là ràng buộc chính; RTED chỉ hỗ trợ một subset type errors. Tách SWT/SWE papers thành nhóm repository-level issue reproduction.

Các lựa chọn này chưa phải kết luận của toàn bộ 500 paper. Evidence chi tiết nằm trong `audit/reviews/NNN.json` và `papers/<slug>/public_evidence/`. Public source đã kiểm tra không đồng nghĩa exact model có thể dùng hoặc reproduction đã thành công.

Cập nhật thêm: KITE mechanisms (#16) và IntTestGen (#14) rất gần hướng concept nhưng chưa verify author implementation. Bigger Is Not Always Better (#30) có source và model nhỏ, thuộc APR/cost support; source/paper có output-cleaning và energy-baseline discrepancies. Cognitive layered evaluation (#18) hỗ trợ protocol robustness, chỉ bốn layers có experimental results. Xem ledger trước khi chọn.


Issue2Test (#21) là prior work gần nhất cho issue-to-reproducing-test: public pipeline, dataset, Docker evaluator và cached outputs trên SWT-Bench Lite. Xếp cao cho related work/reproduction có điều kiện. Trước khi dùng làm baseline, phải giải quyết GPT snapshot vs alias, 3-vs-20 iteration, license, và số liệu paper không nhất quán; không dùng nó làm kết quả Defects4J/BugsInPy.


ReProAgent (#22) được nâng lên ưu tiên rất cao cho concept-guided bug-revealing tests: explicit execution-path root cause → trigger/setup → assertion plan → triadic review. Public source và cached outputs hỗ trợ phân tích, nhưng exact reproduction chờ giải thích cohort 267/276 và 431/500, missing row trong localization table, JSON Verified completion inconsistency, pin model alias và xác nhận license.


Echo (#23) là prior work concept-aligned nhưng không phải lựa chọn rerun đầu tiên: paper Gemini 2.5 Pro khác GPT-4o trong example config; public repo thiếu kết quả/logs đã claim, license chưa rõ, cần Docker+Neo4j+PostgreSQL và báo cost $1.54/instance. Đưa vào nhóm related work/oracle analysis; lưu ý candidate-patch oracle và graph chỉ có cấu trúc AST/file/text theo source đã kiểm tra.


iCoRe (#24) nổi bật làm retrieval baseline cho controlled comparison: có source/context/predictions/ablations SWT Lite và exact GPT-4o snapshot. Reproduction còn conditional vì TDD final outputs không thấy, AssertFlip cache 268/276, code license chưa khai báo và full endpoint replay ước $194. Contribution là context retrieval, không phải root-cause concept.


e-Otter++ (#26) là prior work bắt buộc cho execution-feedback repair, heterogeneous prompt masks/morphs và surrogate-patch test selection. Zenodo có results/log archives, nhưng không tìm thấy custom source; cached TDD predictions đủ 449, SWT Lite thiếu 4/276 rows. Rerun tốn $1.80–$2.75 mỗi issue và cần closed-model API, nên xếp rất cao cho related work nhưng không phải source dễ tái hiện.


Generalizable APR evaluation (#28) is supporting only: relevant for cross-language APR and imperfect FL on Defects4J/BugsInPy, but not a reproduction-test or root-cause study. Figshare supplement is privately shared, no source scripts found, and dataset cohort counts conflict across prose/table; exact reproduction conditional.


Hierarchical Knowledge Injection (#29) is the strongest BugsInPy bug-type/context artifact so far: public 314-bug annotations, per-layer prompts, patch outputs and result CSVs, matching paper counts. It is APR with perfect function localization, not test generation or a causal root-cause taxonomy. Treat license/API/70B re-run as conditional.


D4C (#31) is a useful MIT, data-rich Defects4J APR artifact for studying FL granularity and artifact context. It is not a test-generation or root-cause taxonomy method; exact rerun depends on old GPT‑4 and Mixtral/A100 plus historical Defects4J, so keep as supporting APR/FL reference.


DCAware (#32) is high-priority oracle-quality related work (Self-Repair Trap, execution-vs-mutation distinction) with full reproducibility artifact. It does not target issue-reproduction benchmarks: current code is treated as correct and a test prefix is supplied. Good protocol/oracle-quality comparator, not direct Defects4J/SWT-Bench base.


SeGa (#33) is a high-priority novelty paper for concepts: requirement/functionality/business-scenario abstraction maps closely to test obligations. Its proprietary industrial Go corpus and SeedCode model make headline replication infeasible; use as related work, not a benchmark baseline.


LISA (#34) is high-priority oracle-quality prior work, with a full source/data artifact and invariant-based fault revelation on C/C++ libraries. Its given-prefix/current-code setting differs from historical bug reproduction; use for fault-revealing oracle metrics and self-repair risk, not as a direct Defects4J/SWT paper.

TOGLL (#35): xếp cao cho oracle-quality/Defects4J because Figshare có checkpoint CodeParrot-110M và toàn bộ artifact route; exact replay còn conditional do RQ5 `tc_mut` vs P6 mismatch và cần Java/PIT stack.

UnitCon (#36) is a top supporting option for explicit error-condition/root-cause triggering on Defects4J (80/198 cases), but not an LLM method; start with author minimal subset because full replay requires 512GB RAM and large storage.

CoverUp (#37): use only as a generic Python coverage-generation baseline or custom-model adapter; CM is BugsInPy-derived project selection, not BugsInPy historical bugs. No causal root-cause/oracle metric.

TAM-Eval (#38) ranks high for running our model on broad test-maintenance workflows and mutation/coverage metrics, but not as bug reproduction; exact paper baseline needs model-config discrepancy resolved.

LLM4UT empirical study (#39) is a key D4J warning baseline: one of 37 LLMs detects 8/163 bugs at 0.74% precision despite decent test-generation metrics. Good justification for separate bug-detection evaluation; exact full fine-tuning reproduction is very expensive.

AnyPoC (#40) is a top causal PoC-generation reference, but its current same-author app has no frozen 192-report paper dataset/results; exact replication is conditional.

BRMiner (#42) is high for report-derived input hints on Defects4J, but no accessible implementation is currently found (anonymous 4Open 401; author-linked GitHub 404); use as conceptual prior, not exact runnable baseline.

The 2026 survey (#43) is a valuable map for related work and metric selection, not a runnable method; treat its 178-paper counts as a secondary review and its 4Open verification package as inaccessible.


**TATG (#44):** nâng vào nhóm close prior work cho tracked behavioral obligations/oracle strengthening. Full text đã đọc và source search hoàn tất, nhưng artifact/subjects chỉ được hứa future release; fixed-code focal methods, không historical bugs. Không chọn làm base reproducible lúc này.


**DA-AG / Mixed-Assertion (#45):** high potential fit because the official ISSTA abstract reports realistic multi-assertion placement and Defects4J bug exposure; paper is access-blocked (ACM 403, coauthor PDF 404) and no implementation was found, so defer selection pending full-text/source access.


**Agentic Bug Reproduction at Google (#46):** top task-fit reference for F→P BRT and bug reproduction, but not reproducible: 80 Google GITS cases, internal code_search/Bazel/Passerine, and Google-code-finetuned Gemini are proprietary. Defects4J/SWT-Bench are cited but not evaluated. Use its evaluation protocol/validity distinctions, not as runnable baseline or root-cause taxonomy.


**TestPrune/TestLoc (#47):** chọn hàng đầu cho issue-level test reuse/localization và làm add-on cho BRT; artifact Apache-2.0 có code+precomputed results, single-task route. Exact API replay conditional; full run khoảng 2 ngày. SWE-Bench Lite/Verified + TDD-Bench Verified harness, không phải SWT-Bench/Defects4J/BugsInPy. Kết quả 31.2→34.0 = +2.8pp, +9% relative.


**DPIAgent (#48):** thematic fit cao nhất cho explicit root-cause → test-plan → SWT-Bench F2P. Exact reproduction chưa khả thi: project page không có code; author GitHub routes/search không thấy artifact; no pinned model snapshots. Keep as novelty comparator, not runnable baseline.


**CoHarden (#49):** top oracle-quality prior work: distinguishes rigorous tests that reject plausible bad fixes from merely symptom-reproducing Lax tests; direct results on the SWE/SWT-Bench intersection. Project page says code “under review”; not yet a runnable baseline. Strong metric/novelty reference, not root-cause taxonomy.


**Defects4J goal-objective study (#51):** supporting baseline with public modified EvoSuite/Defects4J forks and public data bundle. Covers exception/output/time goals with real faults, but no issue-driven root-cause method or LLM. Exact DOI for associated Zenodo artifact needs reconciliation.


**Defects4J multi-objective EvoSuite study (#51):** solid supporting objective-adequacy baseline with public modified source/data; not issue-based BRT, LLM, or root-cause analysis. Reconcile paper Zenodo DOI 11047567 vs matching-title record 11047568 before exact rerun.


**#52 Mutant-killing controlled experiment:** top source-backed Defects4J oracle comparator so far. Full 24-page paper read; author-linked public implementation is MIT, extends Defects4J 3.0.1, and includes a Docker example and CI for Cli-2/Lang-6b. A smoke reproduction is feasible; the 642-bug full study is very expensive (paper reports ~1,177 hours). It targets assertion/revealability gaps, not issue-level root-cause localization or LLM-generated tests. Exact Zenodo full-data record and immutable source commit remain unresolved; no source was run.

Quota correction (user, 2026-10-15): telemetry percentages refer to quota **remaining**. Do not treat 90% remaining as near exhaustion or stop condition. Timers remain disabled; continuation is manual. Current distinct new full-text reads since reset: 24/50.


**APR Agent Traceability (#55):** high-priority protocol/related-work paper for issue-reproducing test quality, overfitting, localization and regression selection. Author repo and 3.28 GB public trajectories are available; cached analysis is conditional/reproducible, while fresh test-generation reruns require Claude APIs, Docker and external Agentless. Uses SWE-bench Verified, not SWT-Bench experimentally; no root-cause taxonomy. See `audit/reviews/055.json`.


**ReduJavator replication (#57):** source-backed support only. Repeats a C# test-reduction study with 30 Defects4J failing tests and finds many AST leaf statements removed, but cannot confirm their higher removal probability (p=.5426). Public Java source is author-linked but lacks license, hardcodes local paths and only configures a tiny default run; restoration of 30-project environments is conditional. No root-cause or test-generation method. See `audit/reviews/057.json`.


**TC-Bench (#58):** strongest direct own-Qwen evaluation route found for test-case generation. It reports Qwen2.5-Coder-7B-Instruct (LCB HackRate 42.17%; HT 21.92%) on 877 algorithmic problems. Public evaluator + MIT-card HuggingFace dataset let us run custom-generated input/output cases without retraining; not a Defects4J/SWT issue-reproduction dataset or root-cause classifier. Main paper generator method code/prompts and API model revisions are not fully released; exact reproduction conditional. See `audit/reviews/058.json`.


**LLM test generation survey (#59):** useful conceptual map for information provenance, test artifact roles, oracle quality and benchmark evidence; covers SWT-Bench/TC-Bench but runs no experiments. The linked repo has 95 records and a draft, but explicitly says it is not a completed SLR: selected full-text reading, no dual screening/IRR or complete coding. Treat as discovery/background and verify primary papers directly. See `audit/reviews/059.json`.


**LLMutantKiller (#60):** strongest source-backed mutant-directed test generator in this audit. Complete MIT implementation, prompts, mutation sample, Docker and stored experiment outputs are public. Can inspect results without API; reduced 13-mutant live run ~17 minutes/<$1 historically. Full rerun ~108 Docker days / ~$1.3k historical cost. Configurable chat-completion endpoint may permit local Qwen. Uses JS/TS mutants, not historical Defects4J/SWT issue bugs; no root-cause taxonomy. Pair with #52 and #55. See `audit/reviews/060.json`.


**TestAgent (#61):** high conceptual fit for requirement-guided tests and root-cause triage. Uses 1,454 Java methods across six projects (five from Defects4J as current-version subjects) and manually labels 154 test-revealed bugs with a five-category root-cause taxonomy; also reports Qwen3-30B and Python results. Main paper has no data/source link, but an overlapping-author FSE tool-demo repo provides a full MIT VSCode/backend implementation with similar headline results. Exact study artifact/dataset correspondence is unverified; industrial data unavailable. Keep as a high-priority concept paper, conditional for custom-model pilot, not exact reproduction. See `audit/reviews/061.json`.


### TestExplora (#63) — top proactive discovery match, conditional reproduction

Full arXiv v2 (16,836 words including appendices) and official Microsoft artifact verified. It uses documentation-derived intent as oracle and evaluates repository-level tests by post-PR pass / pre-PR fail across 1,552 PRs, 2,389 tasks and 482 Python repositories. This is proactive discovery, distinct from issue-conditioned SWT-Bench and historical Defects4J/BugsInPy. Public MIT code includes benchmark construction, inference, local vLLM, and Docker evaluation; the paper reports Qwen3-Coder-30B-A3B. However, task JSONs and output cache are absent from the repo, default subset path is author-local, and the vLLM wrapper names Qwen2.5-Coder-32B instead. Strong own-model research candidate if data can be obtained/rebuilt; exact reproduction is conditional. No explicit root-cause taxonomy. See `reviews/063.json`.

Current audit count: **57/500 full texts; 62 source checks/reviews; 5 unread access-blocked; 33/50 additional full-text reads since reset; 17 remain.** Timers disabled; no reproduction performed.


### Java reproduction-test generation — #98 (strongest current own-model evaluation path)

TDD-Bench-Java is the best direct Java issue-to-reproduction-test evaluation route found so far: all 250 task rows and matching IDs are public, with issue, pre-fix commit, code/test patch, and Docker metadata. IBM's Apache-2.0 repository includes a test-patch evaluator built by pinning SWE-PolyBench and applying a public diff. A local model can generate unified test patches and use the evaluator. This reproduces the benchmark evaluation route, not the paper's e-Otter++ generator: the article explicitly says its generation code is proprietary. Exact paper API model revisions are also not pinned. It reports 43.6% Claude-Sonnet-4.5 / 46.4% GPT-5.2 F2P. No causal labels; no Defects4J/BugsInPy/SWT experiment. See `reviews/098.json`.

Current audit count: **58/500 full texts; 63 source checks/reviews; 5 unread access-blocked; 34/50 additional reads since reset; 16 remain.** Timers disabled; 0 reproductions.


### Dynamic Cogeneration (#75) — close conceptual fit, not reproducible

This Google study is a useful prior for jointly generating fixes and BRTs, comparing Freeform/TDD/TLD, and selecting patches with plausible tests. Its qualitative failure analysis identifies test cleanup, wrong debugging hypotheses and fix-test overfitting. The cohort is 120 private GITS tasks and Passerine is Google's internal agent; no source, data or result trajectory package is linked/found. It does not evaluate SWT-Bench, Defects4J or BugsInPy. Keep as conceptual/root-cause-of-agent-failure reference only; do not choose as a public reproduction or own-model benchmark. See `reviews/075.json`.

Current audit count: **60/500 full texts; 65 source checks/reviews; 5 unread access-blocked; 36/50 additional reads since reset; 14 remain.** Timers disabled; 0 reproduced.


### From Business Requirements to Test Assertions (#79) — high oracle/Defects4J concept fit, artifact access unresolved

Pilot on Defects4J Lang bugs 1 and 3–11 compares business-requirement-derived REQ oracles with actual SUT behavior; DeepSeek-V3 and Qwen3-480B are tested. It is useful for distinguishing specification conformance from implementation behavior, but has only ten bugs and no root-cause taxonomy. Paper links a 171.51 MB Figshare package and claims requirements/labels/tests/scripts, but the landing page says “shared privately”; browser access was inconsistent and direct download returned 403/202-empty. Do not assume it is a public reproducible source or ready Qwen route without successful archive access. See `reviews/079.json`.

Current audit count: **61/500 full texts; 66 source checks/reviews; 5 unread access-blocked; 37/50 additional reads since reset; 13 remain.** Timers disabled; 0 reproduced.


### SWE-Doctor (#92) — strongest public runtime-diagnosis artifact so far

The paper's three-stage method extracts issue behaviors, generates one BRT per behavior, debugs failures into records with suspected location/propagation/runtime evidence, then uses those records to guide patch generation. The author-linked MIT repo has complete BRT/RCA/repair/evaluation code and Python/Go debugger implementations; LiteLLM endpoint configuration makes a local model plausible. However, the current repo's only commit is Oct 2 after the July paper and README calls it an FSE 2027 artifact; exact paper issue-ID lists/results are absent. Treat exact reproduction as conditional. Paper scores final patch resolution, not RCA correctness against labels. Uses SWE-bench Verified/Pro, not SWT-Bench/Defects4J/BugsInPy. See `reviews/092.json`.

Current audit count: **62/500 full texts; 67 source checks/reviews; 5 unread access-blocked; 38/50 additional reads since reset; 12 remain.** Timers disabled; 0 reproduced.


### Targeted unit generation (#69) — strong exception-trigger benchmark, artifact code only partially inspected

ESEM 2026 benchmark contains 210 Java runtime-exception bugs across 66 repos, with 41 post-cutoff cases. Input gives the buggy repository, exception type and exact target line; the objective is to trigger the exception at that stack location. The paper reports Claude Code + GPT-5 at 89.5%; OpenCode + DeepSeek-V3.2 at 65.2%/$0.04 per task and failure causes such as insufficient exploration (41.5%) and inadequate reasoning (25.5%). This gives useful targeted-test/failure analysis but bypasses issue localization and is not an F2P-after-fix task or root-cause taxonomy. Zenodo 20283766 has a 2.16 GB CC BY package; embedded README lists benchmark code/data/Docker/evaluator and subset commands, but full runner source was not inspected. Supporting candidate, conditional for exact reproduction; possible local OpenCode test remains unverified. See `reviews/069.json`.

Current audit count: **63/500 full texts; 68 source checks/reviews; 5 unread access-blocked; 39/50 additional reads since reset; 11 remain.** Timers disabled; 0 reproduced.


### AG-RAG assertion generation (#86) — Defects4J oracle support, Qwen not a drop-in

Author-linked source/data/results are public at `iSEngLab/AG-RAG` (commit `47d69677e371209d9b6665ae879df3708886b1bb`; 74 MB dataset archive). AG-RAG uses CodeT5-base and jointly fine-tunes an encoder-decoder retriever/generator over focal-test/assertion pairs. It reports 64.59%/56.33% accuracy on Data_old/New and finds 41 bugs vs EditAS 21 on 835 Defects4J EvoSuite prefixes. Good assertion/oracle comparator, but not issue-to-BRT or root cause. The repo has no LICENSE; checkpoint download is external Google Drive; the user's decoder-only Qwen2.5 model is not plug-compatible without a substantial architecture change. Training took ~29 hours for 10 epochs on two RTX 4090s. See `reviews/086.json`.

Current audit count: **64/500 full texts; 70 source checks/reviews; 6 unread access-blocked; 40/50 new reads since reset; 10 remain.** Timers disabled; 0 reproduced.


### MutGen (#90) — practical mutation-feedback route for local Qwen, not issue BRT

Author repo includes a 74 MB dataset archive, generation/fix prompts, PITest integration, evaluators and cached outputs. The LLM router is generic LiteLLM with configurable `model`/`api_base` and paper runs Llama-3.3 locally through Ollama, making a Qwen OpenAI-compatible subset evaluation plausible. Main task is method-level HumanEval-Java + Leetcode-Java mutation killing; Defects4J appears only in a separate 835-bug EvoSuite-prefix detection experiment (41 vs EditAS 21). It is not issue-conditioned or root-cause localization. Repo has no license, external model weights are not verified, and README's tar command looks malformed. Strong supporting own-model test-adequacy candidate if license/setup resolved. See `reviews/090.json`.

Current audit count: **65/500 full texts; 71 source checks/reviews; 6 unread access-blocked; 41/50 additional reads since reset; 9 remain.** Timers disabled; 0 reproduced.


### Coverage/mutation validity replication (#74) — top priority for evaluation design

Directly investigates whether coverage/mutation proxy scores track real Defects4J bug detection, distinguishing tests generated from fixed code vs already-buggy code. Strong pick for choosing outcome metrics. Public author MIT repository at pinned commit `4bc2ed63917557a8c879e6c733b8fa41c15b9871` includes per-focal-method CSVs and notebooks; statistical reanalysis needs no API or Defects4J installation. Exact all-model replay is much heavier and original model snapshots are not pinned; Qwen on a bounded Defects4J subset would be a new-model evaluation, not exact reproduction. No root-cause/concept taxonomy; BugsInPy is only related work. See `reviews/074.json`.


### ORACLE-SWE (#111) — F2P signal concept only; no public author code

The paper reports that reproduction tests have the largest single-factor contribution to SWE-agent issue resolution, and that the signal set interacts non-additively. This is useful motivation for a strong F2P test but not a ready experimental base: no author extraction/injection code, result cache or signal dataset was found; benchmark cohorts are SWE-bench Verified/Live/Pro rather than the requested Defects4J/BugsInPy/SWT-Bench. Gold test and patch-derived context injection measures an upper bound. Don't implement this method under current instructions. Prefer #74 for an immediately usable Defects4J data/analysis route. See `reviews/111.json`.


### GIANT (#107) — first choice to revisit if the full paper opens

Very high apparent alignment: Defects4J 2.0, 750 bug reports and reproduction test generation with RAG + verification. Abstract reports 51 instances reproduced vs 32 LIBRO / 8 BASE, but no exact model details or author source are available in the checked materials. SSRN full paper routes returned 403; no public author code found by exact-title/author search. Keep as pending access, not as a verified/reproducible paper; not counted as read. See `reviews/107.json`.


### CATGen (#73) — concept/method inspiration, not runnable from the public package

Relevant context-aware design: retrieve project/test-framework context, construct deterministic test skeletons, condition Qwen generation on the skeleton, and apply static repair/edge-case enhancement. Uses Defects4J Chart/Math/Lang/Time with compile/coverage/pass/mutation metrics; no F2P historical bug measure. The author's linked partial repo documents Qwen2.5-Coder-7B/32B and contains examples/parser/wrapper, but explicitly omits core CATGen code and full dataset; no Defects4J task manifest/evaluator or code license. The user's Qwen-7B checkpoint matches one listed model, but cannot run the method without reimplementing missing core stages. Not an exact reproduction candidate under current rules. See `reviews/073.json`.


### XRepoTest (#65) — supplementary own-Qwen route, excellent Invocation Rate metric

Official MIT author repo at `39fb6ab3173136d3dac2d38ed7c98baf6c470270` plus public ungated MIT-tagged HF data (40 JSONL files; ~105 MB base, ~1.69 GB with LSP/RAG). Complete prompt/generation/evaluation/repair CLI and Docker evaluators support OpenAI-compatible local Qwen endpoints. Good bounded own-model evaluation on five non-Java/Python languages and a useful invocation-rate check for tests that pass without targeting the focal function. Paper's exact models are Qwen3, not Qwen2.5. No issue-to-BRT/F2P, no Defects4J experimental task set/BugsInPy/SWT-Bench or root-cause labels; mutation only 3/5 languages. Keep as a supplementary test-quality benchmark. See `reviews/065.json`.


### Prompt engineering class-level study (#91) — related work only for BRT/F2P

Strong dataset/method relevance at first glance (Defects4J 477 classes; 216,300 test outputs; ZSL/FSL/CoT/ToT/GToT), but the final 2026 paper explicitly says it does not evaluate paired buggy/fixed tests, exception bug detection or mutation. A 2024 arXiv predecessor did include bug detection; do not substitute that for the final paper. The linked MIT 4open package is an older 2024 snapshot and its visible file tree is incomplete relative to README (no RQ3/RQ4 or generation folders). Useful for prompt/compilation lessons only; exact final reproduction unavailable. See `reviews/091.json`.


### Test Oracle Automation (#93) — foundational concept only

Strong vocabulary and motivation for oracle quality: distinguish assertion/contract/metamorphic oracles, assess false positives/negatives, and guard against oracle leakage from public Defects4J tests. This is a 2025 perspective/vision paper (arXiv 2024), not an experiment; Defects4J is only an illustrative example, no source/model/data or reproduction route. Pair it with empirical #74 and #79. See `reviews/093.json`.


### Go-UT-Bench (#81) — secondary SFT data, judge-only evaluation

5,264 public Go code/test pairs; three splits; author paper uses DeepSeek-Coder-V2-Lite LoRA and Llama-3.2-3B full fine-tuning. But only HF data is linked, no training code/checkpoints; license metadata is absent; all reported quality is one GPT-4o-mini preference judge, without compiling/running tests, mutation or bug detection. Not a Defects4J/BugsInPy/SWT benchmark and not a direct reproduction-test task. Consider only if a Go fine-tuning study is later desired, with stronger execution-based evaluation. See `reviews/081.json`.


### CANDOR / Hallucination to Consensus (#82) — top concept fit; conditional run

Strongest fresh oracle-method prior: natural-language requirements plus a multi-agent panel/Curator corrects tentative assertions that may mimic faulty code; evaluated on correct and synthetic Pitest-mutant Java sources. Author GitHub contains pipeline, prompts, HumanEvalJava/LeetCode data and three mutant variants. However, paper explicitly excludes Defects4J and uses no historical bug benchmark; no root-cause labels. Main models are 70B Ollama Llama 3.1 + DeepSeek R1; source has no root license and README structure mismatches tree. User Qwen requires changing model-client config. Good concept/mechanism comparator, but #74 is the easiest direct D4J public-data evaluation route. See `reviews/082.json`.
