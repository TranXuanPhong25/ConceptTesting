# Paper scan 2025–2026: Defects4J / BugsInPy / SWT-Bench

Ngày kiểm tra: **2026-10-14**. Người dùng yêu cầu **500 paper phù hợp**, ưu tiên source có thể sửa, paper có thể reproduce, hoặc evaluation bằng đúng model của tác giả.

Người dùng đã xác nhận mở rộng cả SWT-Bench và program repair/fault localization, nhưng **xếp riêng theo độ phù hợp**. [Nhóm lõi](CORE_DEFECTS4J_BUGSINPY.md), [nhóm SWT](SWT_REPRODUCTION.md), [nhóm hỗ trợ](REPAIR_FAULT_ANALYSIS_SUPPORT.md) có bảng riêng. Metadata-only candidates giữ trạng thái unverified.

**Kết quả: đã tạo corpus 500 candidate để screening; chưa xác minh được 500 paper thỏa toàn bộ yêu cầu.** Trong corpus có 36 paper đã đối chiếu nguồn chính, còn 464 record chỉ qua bibliographic/keyword screening. Một artifact-only record được kiểm tra riêng và không tính vào 500 paper. Không được dùng corpus này như danh sách 500 paper đã verified dataset use, code availability hoặc reproducibility.

Files:

- [CATALOG_500.md](CATALOG_500.md): 500 candidate, link paper, family, evidence grade và notes riêng từng paper.
- [screened_500.csv](screened_500.csv): bảng để filter theo dataset/model/artifact/evidence.
- [SHORTLIST.md](SHORTLIST.md): 36 paper + 1 artifact-only record đã kiểm tra nguồn; cả limitation và excluded cases.
- [screening_summary.json](screening_summary.json): counts; `locally_reproduced = 0`.
- [papers/](papers/): mỗi paper một folder; notes và metadata. Không clone/sửa source tác giả trong lượt này.

## Kết luận chọn base paper

**Defects4J + EvalAndMitigate** là lựa chọn đầu tiên nếu giữ task sinh test từ buggy code và muốn đánh giá oracle/misguidance. **AssertMate** đáng ưu tiên nếu chấp nhận task assertion generation và muốn thử model nhỏ của paper. **RTED + BugsInPy** phù hợp nhất nếu giữ Python và giới hạn nghiên cứu ở type errors. Đây là recommendation; người dùng chưa chọn base paper hoặc authorize benchmark run.

| Ưu tiên | Paper | Year | Dataset/task | Author model / artifact | Điểm phù hợp và hạn chế |
|---:|---|---|---|---|---|
| 1 | [EvalAndMitigate](https://arxiv.org/abs/2607.22883) | ISSTA 2026 | Defects4J; buggy-input test generation | [MIT source](https://github.com/drixs2050/EvalAndMitigate); Gemini 2.5 Flash/Pro, GPT-4.1, DeepSeek-V3/R1… | Có buggy/fixed evaluator và 4 outcome categories. Thay specification docstring bằng grounded concept/obligation là extension có thể kiểm soát. Notebook pipeline và exact model endpoints cần pin. |
| 2 | [AssertMate](https://arxiv.org/abs/2608.05822) | arXiv 2026 | Defects4J; assertions | [Apache-2.0 source](https://github.com/LeonYang95/AssertMate); DeepSeek-Coder-7B-Instruct theo paper | Source chia actual-value construction, expected-value reasoning, judge. Author-model route nhỏ hơn nhiều setting khác; exact checkpoint và logprobs cần audit. Task được cấp test prefix, không tự tìm bug-triggering input. |
| 3 | [RTED](https://arxiv.org/abs/2507.02318) | ASE 2025 | BugsInPy + TypeBugs; type errors | [Source](https://github.com/chenyangyc/RTED); DeepSeek-V3 | Type constraints và reflection rất gần concept. Có generation/verification workflow; scope chỉ type errors, dependencies theo project và software license chưa verified. |
| 4 | [DISTINCT](https://arxiv.org/abs/2506.07486) | arXiv 2025 | Defects4J-Desc; buggy-input tests | [Source](https://github.com/anonymous-user-2309/DISTINCT); DeepSeek-V3 / Qianfan scripts | Description-guided branch consistency sát abstract reasoning. NLD được tạo từ repaired methods; cần xem là supplied-spec setting. Scripts/path và license chưa hoàn thiện. |
| 5 | [PANTA](https://arxiv.org/abs/2503.13580) | ICSE 2026; preprint 2025 | Defects4J; CFG/coverage-guided generation | [Source](https://github.com/PANTA-TestAutomation/Panta); Llama3.3-70B, GPT-4o-mini, Claude3.5-Haiku… | Base program-analysis pipeline và ablations thuận tiện. Main objective coverage/mutation; không tự đổi thành buggy-input detection mà vẫn gọi exact reproduction. |
| Support | [An Anatomy / Flow Graph Classification](https://arxiv.org/abs/2502.02299) | EASE 2025 | 488 Defects4J faults; taxonomy | [MIT classifications](https://github.com/alexvdspuy/fcd4j); không cần LLM | 8 fault classes theo control/data flow để stratify kết quả và phân tích generalization. Không phải automated concept extractor hoặc test generator. |

Các proposal extension trong bảng là đánh giá của người nghiên cứu, **không phải kết quả đã chứng minh**. Một paper có source không có nghĩa môi trường đã chạy được trên máy này.

## Setting cần phân biệt

1. **Buggy-input test generation:** model thấy buggy code/spec/issue, cần sinh test fail trên buggy và pass trên fixed. EvalAndMitigate, DISTINCT và RTED gần mục tiêu này, nhưng mỗi paper có oracle/spec assumptions riêng.
2. **Regression test generation:** model thấy current/fixed implementation, sinh test mô tả behavior rồi chạy lại trên faulty version/mutants. AdverTest và [KITE mechanism feedback](https://arxiv.org/abs/2607.11573) có setting như vậy trong evaluator/experiment đã đọc. Không so raw scores trực tiếp với mục 1.
3. **Oracle completion:** được cấp test prefix; chỉ sinh assertion. AssertMate, Doc2OracLL, TOGLL, LLM4AG và Tratto giảm phần input generation nhưng đánh giá khác nhau. AssertMate dùng bug-triggering test cases; Tratto sinh axiomatic pre/postconditions và đánh giá bằng manually validated oracle dataset.
4. **Scenario-assisted generation:** [E-Test RQ5](https://arxiv.org/html/2510.19860v1) được cấp scenarios tương ứng golden trigger tests. Không diễn giải kết quả như tự tìm root cause từ buggy code.
5. **Repository issue reproduction:** SWT-Bench có localization, imports, test integration và environment. [Issue2Test](https://arxiv.org/abs/2503.16320) với [source](https://github.com/test-generation/issue2test) và GPT-4o-mini-2024-07-18 là route inference đáng cân nhắc; [ReProAgent](https://github.com/iSEngLab/ReProAgent) có root-cause-analysis stage trực tiếp. Docker setup và model/retrieval budget cần matched.

## Những paper gần concept nhưng chưa chọn làm base

- [KITE: Knowledge-Guided Synthetic Bug Feedback](https://arxiv.org/abs/2607.11573): chuyển historical bugs thành mechanism knowledge rồi synthetic feedback, rất gần hướng khái quát nguyên nhân. Generation dùng correct-version code và GPT-5.4; chưa verified public implementation. Cần đọc như prior work để tránh claim novelty trùng. Không nhầm với paper KITE khác trong nghiên cứu cũ.
- [NeuroTestGen](https://arxiv.org/abs/2609.30178): symbolic constraints + LLM path reasoning trên Defects4J; chưa verified author source. Symbolic phase bỏ loop bodies nên không suy ra completeness.
- [Tratto](https://arxiv.org/abs/2504.04251): formal pre/postconditions rất hữu ích về concept; source tồn tại nhưng exact fine-tuned checkpoint/replication package cần audit.
- [SWE-Tester](https://arxiv.org/abs/2601.13713): có [training dataset public](https://huggingface.co/datasets/adityasoni17/SWE-Tester), paper fine-tune Qwen2.5-Coder 7B/14B/32B và model khác. Chưa xác minh public SFT weights/inference scaffold. Không dùng base Qwen hiện tại rồi gọi đó là model của paper.
- [Doc2OracLL](https://doi.org/10.1145/3729354) và [TOGLL](https://arxiv.org/html/2405.03786v2): có small-model/Defects4J experiments; checkpoint của model sau fine-tuning chưa verified trong scan. TOGLL v2 có Defects4J real-bug study; không nhầm 1,023 unique mutants với 1,023 real defects.

## Những hit bị loại hoặc hạn chế

- [SeGa](https://arxiv.org/abs/2604.23509) nhắc Defects4J/BugsInPy nhưng experiment dùng private industrial Go repos. Đây là ví dụ cụ thể keyword hit không chứng minh dataset use.
- [DCAware](https://arxiv.org/abs/2608.05917) có static/dynamic oracle context nhưng chưa tìm thấy Defects4J evaluation trong full text được đọc; là adjacent work.
- [Lisa invariant testing](https://arxiv.org/abs/2607.18711) dùng C/C++ libraries; không thuộc benchmark được yêu cầu.
- [Understanding and Improving LLM-Based Test Oracle Generation](https://zenodo.org/records/19228870) là artifact record, chưa verified publication và files restricted. Không tính như paper đủ điều kiện.
- [SWT failure taxonomy](https://zenodo.org/records/19075731) có publication [CASCON 2026](https://conf.researchr.org/details/cascon-2026/cascontechnical-papers2026/14/A-Taxonomy-of-Failing-Bug-Reproduction-Tests-on-SWT-Bench), nhưng labelled artifact files restricted; taxonomy nói về generator failures, không phải production-bug root causes.

## Search protocol và evidence

Discovery bằng OpenAlex full-text search cho `Defects4J`, `BugsInPy`, `SWT-Bench`, giới hạn publication date 2025-01-01 đến 2026-10-14. Đã tải đủ pages: 809 + 111 + 317 query hits, union **1,142 OpenAlex records**. Sau paper-like type filtering và normalized-title dedup còn **842 title records**. Đây là discovery metadata, không phải 842 experiment dùng benchmark.

Đối chiếu thêm author artifact/paper pages, [AwesomeLLM4UT survey catalog](https://github.com/iSEngLab/AwesomeLLM4UT), [DLTG survey catalog](https://github.com/chengxiuzeng/DLTG) và research notes cũ trong repo. Survey catalogs chỉ dùng discovery; recommendation dựa trên paper/author source được link riêng. Không lấy ngày crawl hoặc repo update làm publication year. Preprint 2024 vẫn có thể được đưa vào nếu venue publication là 2025, như TOGLL; mỗi record có year/venue annotation.

Corpus 500 là nhóm source-reviewed ưu tiên rồi candidate software papers theo metadata relevance score. Ngoài Defects4J/BugsInPy test generation, có SWT reproduction, APR, fault localization, surveys và related coding-agent work; những nhóm này đã gắn family riêng. Việc đưa related work vào corpus giúp screening rộng, **không xác nhận tất cả phù hợp yêu cầu cuối cùng**. Titles được dedup và known arXiv aliases được gộp; metadata-only publication variants có thể vẫn là cùng một underlying study và cần manual identity audit.

Evidence grades:

- **A (9):** public source + documented model/evaluation route; chưa reproduce local. Bao gồm support taxonomy không dùng model.
- **B (8):** source/artifact exists nhưng setup, exact model, checkpoint, scope hoặc dataset provenance còn điểm cần audit.
- **C (16 trong corpus):** dataset/task đọc được nhưng chưa verified usable source/checkpoint, hoặc artifact restricted. Có APR support papers.
- **X (3 trong corpus):** inspected paper ngoài exact-dataset scope. Artifact-only exclusion ở ngoài count 500.
- **U (464):** bibliographic screening only. Dataset use, model và code **unknown**; không được gắn nhãn paper phù hợp/reproducible.

**Không có paper reproduction, model call, fine-tuning, benchmark build hoặc author-source edit trong lượt này.** `discover.py` và `export_catalog.py` chỉ là bibliography tooling, không reimplement paper. Discovery outputs và per-paper notes lưu để lần sau tiếp tục kiểm chứng, không phải synthetic evidence.

## Evaluation route cho base paper được chọn

Trước run, pin paper version, artifact commit, dataset version/IDs, exact model checkpoint/API snapshot, prompt và retry/token budgets. Chạy baseline gốc trên pilot nhỏ bằng model của tác giả; baseline chạy được mới thêm concept ở một stage và so với plain/matched placebo/tool-input controls.

Với buggy-input setting, primary metric nên là tỷ lệ bug có ít nhất một test **fail buggy / pass fixed**, kèm FP/misguidance, compilation và environment failures. Giấu fixed source/patch/golden reproducer khỏi generation context trừ khi paper thực sự định nghĩa supplied-spec hoặc fixed-input setting. Generalization đánh giá trên held-out projects/fault classes; không chọn toàn bộ easy single-method bugs rồi claim toàn Defects4J.

## Full-text/public-source audit — 2026-10-15, batch 1

User yêu cầu đọc hết 500 candidate và kiểm chứng public source, tiếp tục qua quota reset. Báo cáo ở root:
[PAPER_AUDIT_500_REPORT.md](../../PAPER_AUDIT_500_REPORT.md). Counts lấy từ review ledger, không suy từ download.

- **#6 fault taxonomy:** đọc paper v2 và xác minh thêm [Figshare replication package](https://doi.org/10.6084/m9.figshare.28855634), ngoài GitHub classifications đã biết. Có author `statistics.ipynb` dùng numpy/matplotlib. Notebook còn absolute path tới external repair-pattern dataset; full reproduction có điều kiện. Kiểm tra combined JSON ở cả archive và GitHub cho 488 records nhưng 55 `use` labels, trong khi Table 1 paper ghi 56; cần đối chiếu per-project files trước claim exact replication. Không chạy notebook và không sửa source.
- **#12 LLM vs Human Python:** full text xác nhận model nhận **patch diff và bug context** qua top-3 lexical retrieval, còn human tests là pre-existing/general-purpose. Đây là fix-time regression experiment, không phải unknown-bug discovery. Paper nhắc replication package nhưng scan chưa xác minh usable author URL hoặc frozen 29-bug manifest. Có Gemini model name chưa đủ reproduce; giảm ưu tiên làm main base. [Primary paper](https://arxiv.org/html/2606.08588v1).

Chi tiết và source locations trong `audit/reviews/006.json`, `012.json`; local paper reproduction vẫn 0.

## Full-text/public-source audit — 2026-10-15, batch 2

**#44 [TATG](https://arxiv.org/html/2607.03194v1)** có objective cards gồm evidence, setup, action, oracle, acceptance, status và behavioral dedup key: rất gần hướng tracked concept obligations. Tuy nhiên IV-D chỉ thông báo source/subjects *sẽ* public; chưa tìm thấy usable author implementation. Experiment dùng 110 KTester methods + 31 bổ sung (9 methods từ fixed Defects4J revisions), Qwen3.6-35B-A3B và DeepSeek-V4-Flash-284B. Primary effectiveness metric là mutation score. Đưa vào close prior work, chưa chọn làm reproducible base; có model name/settings không thay thế source/data release. Full-text/source review nằm trong `audit/reviews/044.json`.

## Full-text/public-source audit — 2026-10-15, batch 3

**#56 [CASCADE, FSE 2026](https://arxiv.org/html/2604.19400v1):** nâng ưu tiên trong nhóm adjacent base. Đã đọc paper, xác minh [source MIT](https://github.com/TobiasKiecker/CASCADE), pinned HEAD `4dc5a8d525c8967ea8dd11ae46cfe5834dbda156`, và [public Zenodo archive](https://zenodo.org/records/19483108). `PaperEvaluation/README.md` có route rerun benchmark lẫn evaluate pre-computed results; source gồm dataset, generators, configs và evaluation scripts. Config RQ1/RQ2 dùng `gpt-4.1-mini`, temperature 0; generator có default `gpt-4o-mini-2024-07-18`, nên cần dùng đúng paper config.

Dataset 71 inconsistent + 814 consistent documentation/code pairs, lấy từ documentation-fix commits ở mining pool gồm các Defects4J projects; **không phải standard Defects4J buggy/fixed task set**. Doc-derived conditional behavior là concept hook tốt, nhưng generated code/test có thể cùng hiểu sai spec. Source/model route khả thi có điều kiện; chưa chạy model/evaluator. Review chi tiết: `audit/reviews/056.json`.

Retrieval pass đầu đã thử đủ **500/500 record**, có 385 full-text candidates theo heuristic, 73 unavailable và 42 landing/partial. Đây không phải số đã đọc. Full-text/source reviews tiếp tục ở ledger; root report công bố actual counts. Lịch systemd local tiếp tục 02:20:15 và 07:20:15 giờ Việt Nam; weekly quota cũng được kiểm tra trước resume.

## Full-text/public-source audit — 2026-10-15, batch 4 (08:15)

**Scheduling correction:** timer thực sự fired lúc 02:20/07:20, nhưng cả hai CLI `exec resume` bị thread-store active-writer conflict do app đang sở hữu thread. Không có paper review nào chạy qua hai lượt đó. Đã đổi runner sang `codex queue` vào owning app; lần queue kiểm chứng exit 0. Status `queued` chỉ xác nhận queue acceptance, không phải paper review hoàn tất. Deadline có điều kiện 07:00 đã qua mà audit chưa hoàn tất; root report giữ actual counts.

- **#25 [SWE-Tester v2](https://arxiv.org/html/2601.13713v2):** sửa kết luận source availability của scan đầu. Có [public implementation](https://github.com/adityasoni9998/SWE-Tester), commit `700784149fed0ca349c8e03a54b1fdb12f691d2c`, gồm training/eval/context/SWT harness. Exact trained checkpoints chưa được xác minh: author HF repository 7B LoRA đã kiểm tra chỉ chứa `.gitattributes`, adapter config 404. Repo eval README mô tả oracle retrieval; không gộp với full localization setting. Source đã có nhưng inference bằng chính paper SFT model vẫn có blocker.
- **#17 [FOCAL](https://arxiv.org/html/2607.11342v1):** đọc đầy đủ main paper; CodeT5 shared encoder + LoRA/classification head, không sinh executable assertion. Không tìm thấy public author implementation hay trained checkpoint. Defects4J-derived training pairs chủ yếu là mutation labels; IG counterfactual chỉ kiểm tra model decision. Không chọn làm base trực tiếp cho test generation.

## Full-text/public-source audit — 2026-10-15, batch 5

**#1 EvalAndMitigate:** đã đọc full paper và source instructions/inference notebooks tại `751f9f4153fce0d55c111602a27e19009dec0721`. Giữ ưu tiên đầu cho core Defects4J: source MIT, dual-version evaluator, không cần fine-tuning cho main method. Nhưng mặc định **docstring dùng `gpt-4.1`, test generation dùng `o4-mini`/high reasoning**; `tgt_model` filename label không đổi model thật. Phải pin một original model/config ở cả hai stage để reproduce đúng setting; GPU logprob scoring là experiment riêng, không bắt buộc cho primary detection pilot. Source có đủ route nhưng chưa chạy local; verdict conditional.


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


### Audit batch13 — 2026-10-15: access-blocked LLM4AG/EASE (#11)

Fullpaper remains **unread**:officialDOI/PDF403;bothauthorpages havenoPDF;OpenAlexreportsclosed/noOA;targetedtitle search no legitimatefulltext located. Crossref supports2025journaldate whileauthors label2024. Public source exists at `dd1fc165bda852c79c0c3e40c0aa319a80def6c9`,README/CodeT5training/RQ2Defects4Jscript inspected. ExternalSharePointdatafolder returns200, buttrainedweights/filedownloads notyetverified. [Paper](https://doi.org/10.1145/3699598), [source](https://github.com/iSEngLab/LLM4AG).

Ledger now has **16 reviewed/source-checked candidates**, including **15 fulltexts read** and **1substantiated access-blocked paper**. Fulltextread/sourceverdict numerator stays **15/500**. No reproductionrun.


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


### Audit batch16 — 2026-10-15: SWT failure taxonomy (#27), fulltext blocked

Corrected retrieval identity:cached“fulltext”wasZenodolanding,notpaper. Actual10pagepaperfoundonOpenReviewOLHKkIidVs,butPDF/attachment/API403andwebbrowserverification;**notread/notincludedinfulltextnumerator**. OfficialCASCON2026acceptedlistcorroboratestitle/authors.

[AuthorZenodoartifact](https://zenodo.org/records/19075731) iscurrentlypublic:all4CSVfilesdownloaded,MD5verified.437totalrows,433nonemptyClasslabels(28/45/180/180bytool-modelpair). Thisdiffersfrom254failuresintheindexedpaperexcerpt;reconcileversions/unitsbeforeusingpaperstatistics. Artifactsupportsmanualfailure-analysislabels,notstandaloneauthorgenerator. Taxonomyisaboutgeneratedreproductiontestfailures,notunderlyingprogrambugrootcauses.

Cumulative: **17/500fulltextsread**, **19/500sourcechecks/reviews**, including**2access-blockedunreadpapers**, **0locallyreproduced**.


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


### Quota checkpoint 2026-10-15T10:30:07.023955+07:00

Actual counts:21fulltextsread,23sourcechecks/reviews,2unreadaccess-blocked,477remaining,0reproduced. Weeklyquota98%near-exhaustion;5hprimary35%. Weeklyresetreported2026-10-20 13:22:13Asia/Ho_Chi_Minh. Installedone-shottimer13:22:30onthatsamedate;existing02:20/07:20timersremainquota-aware. Schedulerweeklyguardnow98%,so5hresetdoesnottriggerresearchwhileweeklyquotaexhausted. NoCOMPLETE.jsoncreated.


### Audit batch21 — 2026-10-15: CleanTest (#19)

Đã đọc đủ PDF chính thức 24 trang. Artifact của tác giả ở Zenodo là CC-BY-4.0; versions v1/current có các filename/checksum giống nhau. Đã tải/verify README, script archive, models archive metadata. Paper fine-tune CodeBERT, CodeT5/AthenaTest, StarCoder15.5B, CodeLlama7B; CodeGPT dự đoán coverage filter. Dataset includesMethods2Test/Atlas andDefects4Jdual-versionbug detection. [Paper](https://doi.org/10.1145/3715778), [artifactcurrent](https://zenodo.org/records/15347368).

Artifact is substantive, but `models.zip` is only1865bytes/empty model directories: trained checkpoints absent. README provides scripts/data, training uses4RTXA800. Thus exact originalmodel result needs retraining; noauthor code/modelrun. Noise counts/splits inREADME and paper need pinning and recomputation. Supporting data-quality baseline, not concept generator.

Cumulative: **22fulltextsread/24sourcechecks**,2unreadblocked,0locallyreproduced.


### Audit batch22 — 2026-10-15: AssertFlip (#20)

Paper v2 and public Apache-2.0 replication repo at a5cd61992e0791b6a167549b1e2eca13627eed3f read/checked. Excellent SWT-Bench candidate: passing test on buggy behavior → invert assertion → LLM validate bug-specific failure. Public datasets, pipeline, prediction logs and evaluation outputs are present. [Paper](https://arxiv.org/html/2507.17542v2), [source](https://github.com/uw-swag/AssertFlip).

Model is Azure GPT-4o alias/temp0, no checkpoint or immutable deployment pin; about $1 per Verified issue at 10 regeneration attempts. Agentless localization is a required external component. Important denominator: paper reports 189/433=43.6%, while generating tests for only 326 issues (conditional rate 58%); keep generation coverage and conditional success distinct. Cached artifact supports output inspection, but no author run was performed.

Cumulative: **23 full texts read, 25 source checks, 2 blocked, 0 reproduced**.


### Audit batch23 — 2026-10-15: Issue2Test (#21)

Đã đọc toàn bộ arXiv v4 (10,980 words; method, evaluation, discussion, references). Benchmark là SWT-Bench Lite 276 issue (Verified subset 90), không phải Defects4J/BugsInPy. Repo tác giả có implementation, dataset, Docker evaluator, outputs; HEAD `ff947aec0dd8189514edf91cf4d4d279cb062092`, nhưng không có root license. [Paper](https://arxiv.org/html/2503.16320v4), [source tại commit đã kiểm tra](https://github.com/test-generation/issue2test/tree/ff947aec0dd8189514edf91cf4d4d279cb062092).

Headline model GPT-4o-mini-2024-07-18 không khớp config alias `gpt-4o-mini`; YAML có absolute paths và đặt 3 iterations trong khi paper Algorithm 1/code mặc định 20. Các số liệu abstract, introduction, Table 2 và conclusion còn mâu thuẫn (30.4%/84 GPT vs 32.9%/91 Claude; 20 vs 28 unique issues). Vì vậy public implementation nhưng exact reproduction chỉ conditional, cần pin snapshot/config/cohort trước. Không chạy code hoặc API.

Cumulative: **24 full texts read, 26 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch24 — 2026-10-15: ReProAgent (#22)

Đã đọc toàn bộ arXiv v1 (10,854 words). Đây là paper concept-aligned nhất trong nhóm gần đây: execution-path RCA, minimal trigger conditions, environment setup, expected assertion và triadic review. Author source tại [commit đã kiểm tra](https://github.com/iSEngLab/ReProAgent/tree/99b112b9e1de88a451d24e273121f8bceaf3c8b4) gồm implementation, tests, uv lockfile, Docker evaluator và cached predictions/results; không có LICENSE ở root. [Paper](https://arxiv.org/html/2607.09123v1).

Exact replay conditional: GPT-5-mini config là mutable alias và cần hosted API; cache chỉ có 267/276 Lite và 431/500 Verified cases, không giải thích exclusions. Table 8 Verified localization strata tổng 430; cached Verified result JSON lại ghi completed=0 cùng lúc resolved=303/unresolved=128/errors=0. Không gọi API/chạy source. Paper báo $0.14/instance (ước tính $97.72 cho 698 cached rows, chưa chi). Dataset SWT-Bench, không phải Defects4J/BugsInPy.

Cumulative: **25 full texts read, 27 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch25 — 2026-10-15: Echo (#23)

Đã đọc toàn bộ arXiv v1 (11,135 words). Echo ghép code-graph retrieval, regression-test retrieval, Prometheus candidate patch, execution và dual-version refinement trên SWT-Bench Verified. Paper báo 287/433 success (66.28%); chỉ 419/433 đi qua pipeline do giới hạn 500 steps. Cost Table 5 là **$1.54/instance**; 433 instances tương đương khoảng $667.82 theo trung bình paper (ước lượng, không chi). [Paper](https://arxiv.org/html/2603.07326v1), [author source tại commit đã kiểm tra](https://github.com/EuniAI/Echo/tree/89e6e1ebd9d706adf21788f3febed95722d50a51).

Source có implementation nhưng reproduction conditional: model config công khai mặc định GPT-4o thay cho Gemini 2.5 Pro/temp .5 trong paper; repo không chứa logs/results/predictions dù Data Availability claim có, không có root license, và cần Docker + Neo4j + PostgreSQL. Graph edge types trong code chỉ biểu diễn filesystem/AST/text, không có explicit call/import edges. Paper tự lưu ý candidate patch làm oracle có thể sai và chỉ chạy một stochastic run. Không chạy source/gọi API.

Cumulative: **26 full texts read, 28 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch26 — 2026-10-15: iCoRe (#24)

Đã đọc toàn bộ arXiv v2 (13,873 words, kể cả appendices). iCoRe tách production-code/test retrieval, rồi dùng sketch BRT, BM25 và weighted function-call-tree similarity để lặp retrieval; benchmark là SWT-Bench Lite 276 + TDD-Bench Verified 449. Author source tại [commit đã kiểm tra](https://github.com/ZJU-CTAG/iCoRe/tree/4ef1b08a288e519ff5d5a44775b5be8d0afb5626) có code, prompts, retrieval artifacts, ablations/baselines và 276 SWT Lite predictions. [Paper](https://arxiv.org/html/2604.19224v2).

Model route khá cụ thể (GPT-4o-2024-08-06, DeepSeek-V3, Qwen3-32B), nhưng inference cần API-compatible endpoints và source không có code license/requirements lock. TDD retrieval contexts có, song không thấy final TDD prediction outputs để kiểm tra reported 52.8%; AssertFlip cached baseline chỉ có 268/276 rows. Paper cost $0.26–$0.28/instance, khoảng $194.02 cho đủ 725 cases theo phép tính (chưa chi). Verdict conditional; không chạy code/gọi API.

Cumulative: **27 full texts read, 29 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch27 — 2026-10-15: e-Otter++ (#26)

Đã đọc toàn bộ arXiv v3. Method gồm Otter candidate generation, execution-feedback repair (critic + context, tối đa 10 attempts), 5 context masks + 5 issue morphs và selector dùng 5 Agentless surrogate patches. Evaluation: TDD-Bench Verified 449, SWT-Bench Lite 276, SWE-rebench 267. Bài báo cáo 63.0% Claude / 51.4% GPT-4o trên TDD; 52.5% / 40.2% trên SWT Lite. [Paper](https://arxiv.org/html/2508.06365v3), [Zenodo results + supplementary (CC BY 4.0)](https://zenodo.org/records/18169083).

Đã checksum-verify supplementary files và GPT-4o prediction JSONs: TDD có 449 rows, SWT Lite chỉ 272/276. Benchmark harness IBM public, nhưng không tìm thấy source implementation e-Otter/e-Otter++ trong linked Zenodo record hay IBM repo; result/log archives có nhưng source không. Full rerun cần closed GPT‑4o/Claude APIs và chi phí paper báo $1.80/$2.75 mỗi instance (kể cả Agentless selection). Verdict partial/conditional; không gọi API/chạy source. Không tự reimplement.

Cumulative: **28 full texts read, 30 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch28 — 2026-10-15: Generalizable APR evaluation (#28)

Đã đọc toàn bộ arXiv v2 (12,406 words). Paper so sánh 13 LLM trên Defects4J, BugsInPy, BugsJS, BugsPHP; phân tích test-error prompt, perfect line/function FL, FLACOCO imperfect FL, patch complexity. Đây là APR study, không sinh reproduction tests hoặc phân loại root causes. [Paper](https://arxiv.org/html/2506.03283v2), [supplement](https://figshare.com/s/947fd7030f10a67a1c9f).

Artifact Figshare 457.69 MB có CC BY 4.0 nhưng hiện được đánh dấu “shared privately”; file download không mở được qua kiểm tra anonymous. Paper v2 nói scripts sẽ được bổ sung sau acceptance, nhưng chưa tìm được source/scripts repo. Counts giữa prose và Table 1 chưa khớp (Defects4J 854/845; BugsJS 453/513; BugsPHP 513/452; BugsInPy single-hunk 82/132). Reproduction conditional; không chạy code/gọi API. Xếp supporting evidence cho dataset/FL design, không phải base chính.

Cumulative: **29 full texts read, 31 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch29 — 2026-10-15: Hierarchical Knowledge Injection (#29)

Đã đọc toàn bộ arXiv v3. Paper dùng BugsInPy 314 single-function fixes, annotate 6 bug types, và inject bug → repository → project context. Llama 3.3 đạt 79%, GPT-4o-mini 73%; cung cấp thêm taxonomy/context evidence phù hợp BugsInPy, nhưng đây là APR study chứ không sinh tests. [Paper](https://arxiv.org/html/2506.24015v3), [author replication package tại commit đã kiểm tra](https://github.com/SOAR-Lab/llm-apr-knowledge-injection/tree/74df4532846f0f903907a168b02196196ca61364).

Artifact public thật sự có notebooks, 314 bug annotations, prompts, patch outputs và 8 results CSVs; parsed row counts/category counts khớp Table I. Reproduction conditional vì repo không có code license, dependencies không pin, GPT-4o-mini API/70B Llama compute cần thiết. Bug-type labels cũng không tương đương causal root-cause taxonomy; perfect function FL được giả định. Không gọi API/chạy notebook.

Cumulative: **30 full texts read, 32 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch30 — 2026-10-15: D4C (#31)

Đã đọc toàn bộ arXiv v5. D4C APR method: tạo cả refined function để khớp decoder-only completion objective và tránh cần buggy-hunk localization; dùng function-level FL và artifacts. Dataset Defects4J v1.2+2.0 (437 single-function bugs; 180 correct patches) và DebugBench (590). Source MIT tại [commit đã kiểm tra](https://github.com/CUHK-Shenzhen-SE/D4C/tree/33f63280da92951cbb07078ccbfda06bee4e3a3e) có code/data/validation/archived results; counts của archive phù hợp headline. [Paper](https://arxiv.org/html/2404.08877v5).

Không phải test-generation/root-cause taxonomy. Exact rerun conditional: GPT-4-0613 cần historical paid endpoint; Mixtral 8x7B paper chạy trên 8xA100; Defects4J v3.0 thay đổi cases và DebugBench live evaluation cần LeetCode cookies. Không chạy code/API. Paper cost wording ambiguous ($0.023/patch, 10 patches rồi gọi $0.23 “entire dataset”).

Cumulative: **31 full texts read, 33 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch31 — 2026-10-15: DCAware (#32)

Đã đọc toàn bộ arXiv v2. DCAware hoàn tất oracle cho test prefix có sẵn, xem current code là expected; không phải bug-reproduction test cho buggy/fixed pair. Pipeline fold static context, hỏi JDB các runtime state do model chọn, rồi generate assertion không repair lặp. Dataset TECO-derived 500 Java prefixes/38 projects; mutation-valid N=362. GPT-5-mini đạt 88.2% pass/78.17 Kill Golden; Qwen3-Coder-30B 80.8%/73.2. [Paper](https://arxiv.org/html/2608.05917v2).

Author artifact tại [Zenodo](https://zenodo.org/records/21357436) (CC BY 4.0) có source MIT, contexts, prompts, 500 result files/model, JavaServer, Docker/PIT evaluator và smoke/result-print scripts. Range-inspected ZIP manifest có 18,134 entries (1.26GB compressed/1.69GB expanded); không download đầy đủ/chạy source. Full run cần Java8/21, Maven, Docker, PIT và 40GB A100 cho Qwen hoặc Azure GPT‑5‑mini. Đây là prior work mạnh về oracle strength/self-repair trap, không phải Defects4J/BugsInPy/SWT-Bench generator. Không gọi API.

Cumulative: **32 full texts read, 34 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch32 — 2026-10-15: SeGa (#33)

Đã đọc toàn bộ arXiv v3. Đây là prior work rất sát concept thesis: PRDs được chuyển thành functionality rồi thành business scenarios có preconditions/action/expected outcomes/constraints để sinh Go unit tests. Nhưng paper đánh giá trên 60 business logic bugs trong 4 repo ByteDance và deploy thêm 6 repo nội bộ; toàn bộ codebase/PRD/labels/results bị giữ kín. [Paper](https://arxiv.org/html/2604.23509v3), [public core agent](https://github.com/chenyangyc/SeGa/tree/be63f3e87c828a71a3a0b39f75156963ddebc068).

Repo chỉ có core agent, prompts, AST tools và Swerex runtime, không có evaluation corpus. Paper dùng SeedCode API/model không công bố snapshot. Vì vậy source partial nhưng tái hiện headline results not feasible; có thể dùng cho related work/novelty analysis, không thay bằng custom reimplementation nếu chưa được hỏi. No code/API run.

Cumulative: **33 full texts read, 35 source checks/reviews, 2 blocked unread, 0 reproduced**.


Artifact follow-up for DCAware (#32): official Zenodo latest record 21357436 contains the full source/results/data archive, 18,134 entries, 1.69GB uncompressed; a range-based ZIP manifest confirms DCAware source modules and MIT LICENSE. GitHub CNTG is the invariant-generation component; CGNTG is PromptFuzz. This confirms `public_implementation`; no archive extraction, local test, or model call performed.


### Audit batch33 — 2026-10-15: LISA (#34)

Đã đọc toàn bộ paper v1 và appendices A–E. Lisa sinh C/C++ API-sequence tests rồi chèn invariants từ API docs/Daikon; phát hiện functional bugs. Lisa-Bench dùng 25 historical bugs trên năm libraries, phát hiện 12/25 (48%) so với CITYWALK 3 và OSS-Fuzz 2. TECO-derived 500 test-prefix oracle completion cases là benchmark khác. Vì test prefix/correct current code được cho sẵn, đây là oracle quality work, không phải issue-to-reproduction trên Defects4J/BugsInPy/SWT. [Paper](https://arxiv.org/html/2607.18711v1), [author artifact](https://zenodo.org/records/21357436).

Zenodo artifact CC BY 4.0, ZIP manifest range-inspected; bên trong có implementation MIT, prompts, code, data, Docker/PIT evaluator và cached outputs. Full replay cần Java8/21, Maven, Docker/PIT và 40GB A100 Qwen3-Coder hoặc Azure GPT‑5‑mini. No code/API run. Reproduction conditional, but artifact unusually complete for offline analysis.

Cumulative: **34 full texts read, 36 source checks/reviews, 2 blocked unread, 0 reproduced**.


### Audit batch34 — 2026-10-15: TOGLL (#35)

Đã đọc toàn bộ arXiv v2 (11,131 words). TOGLL dùng CodeParrot-110M fine-tuned, prompt P6 = test prefix + Javadoc + method; paper đánh giá OracleEval25 và 374 Defects4J prefixes (304 assertion, 70 exception). 69,793 PIT mutants là evaluation riêng, không phải 69,793 real bugs. [Paper](https://arxiv.org/html/2405.03786v2), [author artifact](https://figshare.com/articles/dataset/Artifact_TOGLL_Correct_and_Strong_Test_OracleGeneration_with_LLMs/28282721).

Figshare v3 có README, data/scripts RQ1–RQ5 và fine-tuned checkpoint `model.safetensors` (444,048,000 bytes uncompressed); artifact archive MD5 được metadata verify. Đã đọc source/config liên quan bằng HTTP Range, không tải đầy đủ/extract/chạy archive 6.66 GiB. License PDF ghi ODbL 1.0 và DBCL 1.0 cho nội dung database; chưa thấy license phần mềm riêng. Exact replay conditional vì RQ5 script chọn `tc_mut`/`codeparrot_tc_mut`, khác paper P6 và checkpoint nằm ở thư mục `TOGLL`. Cần giải quyết mismatch trước khi chạy. Không gọi model/API.

Cumulative: **35 full texts read; 37 source checks/reviews; 2 access-blocked unread; 0 reproduced.**


### Audit batch35 — 2026-10-15: UnitCon (#36)

Đã đọc toàn bộ paper FSE’25 (22 trang). UnitCon sinh chuỗi method calls để kích hoạt runtime exception tại target line, dùng Infer-derived error conditions để prioritize và method summaries để prune. RQ1 có 198 case (Bears, Genesis, NPEX, VFix, Defects4J; trong đó 80 Defects4J), đạt 104/198 trong 10 phút; RQ2 áp dụng trên 51 repo hiện tại và báo 21 NPE bugs mới sau manual inspection. [Paper](https://doi.org/10.1145/3729362), [author source](https://github.com/prosyslab/unitcon-artifact/tree/f7ab2e23a57e12060b50af91cf7098dfc347b9ff), [Zenodo artifact](https://zenodo.org/records/15460355).

BSD-3-Clause source, benchmark/data, Dockerfiles, scripts, UnitCon submodule và archived results đều public. README đưa reproduction routes, nhưng full replay rất nặng: 512GB RAM, 188GB storage, 125 ngày sequential hoặc 330 giờ cho baselines chạy song song; 8-project minimal RQ1 ước hai ngày. Không chạy code. Đây là strong support cho Defects4J exception triggering/root-condition analysis, không có LLM và không bao quát functional bug classes.

Cumulative: **36 full texts read; 38 source checks/reviews; 2 access-blocked unread; 0 reproduced.**


### Audit batch36 — 2026-10-15: CoverUp (#37)

Đã đọc toàn bộ paper arXiv v4. CoverUp dùng coverage prompt, get_info để LLM truy vấn code context, execute/isolate tests và follow-up repair để tăng Python line/branch coverage. CM có 425 modules/35 projects *được chọn từ các project từng dùng trong BugsInPy/Pynguin studies*; paper không dùng BugsInPy historical bug versions, Defects4J hay SWT-Bench. Đây là coverage regression, không đo root cause hay bug-revealing oracle. [Paper](https://arxiv.org/html/2403.16218v4), [replication package](https://github.com/plasma-umass/coverup-eval/tree/f3173196b90181974b0b684600ffde42ac36672c), [implementation](https://github.com/plasma-umass/coverup/tree/d9ca25b9282621d2779560f2be397ab0683a6733).

Hai repo Apache-2.0 có source, Docker, configs, datasets, test outputs/logs và cached results. Evaluation config pin GPT-4o-2024-05-13 (temp 0); LiteLLM cho phép custom model, nhưng exact replay là conditional. Paper báo $399 cho run chính CM, artifact README cảnh báo tái hiện toàn bộ nhiều hệ thống tốn hàng nghìn USD. Không chạy code/model.

Cumulative: **37 full texts read; 39 source checks/reviews; 2 access-blocked unread; 0 reproduced.**


### Audit batch37 — 2026-10-15: TAM-Eval (#38)

Đã đọc toàn bộ arXiv v1. TAM-Eval có 1,539 whole-test-file tasks trên 192 repo Python/Java/Go, chia Create/Repair/Update; metrics là pass rate, Δcoverage và Δmutation score. Repair set có lỗi syntax/execution, assertion bị loại và weak coverage; Update ghép test file cũ với focal code hiện tại. Đây là benchmark test maintenance, không dùng bug-linked SWT-Bench/Defects4J/BugsInPy. [Paper](https://arxiv.org/html/2601.18241v1), [author repo](https://github.com/trndcenter/TAM-Eval), [mirror](https://github.com/Tech871/tameval).

Apache-2.0 source và benchmark TOMLs public; code nhận model endpoint tương thích OpenAI/OpenRouter, có Docker evaluator và up to 3 attempts. Nhưng `run_model_evals.sh` hiện dùng Qwen2.5-Coder, Gemma3, Qwen3-235B, o4-mini-high, DeepSeek R1; khác rõ với Table II (Qwen3 480B, GPT-5, GPT-OSS-120B, Gemini 2.5 Flash, v.v.). Không thấy outputs/results được commit trong package tree, cũng không có model snapshots. Vì vậy dùng được để đánh giá model của mình, còn exact reproduction conditional. Không chạy model/code.

Cumulative: **38 full texts read; 40 source checks/reviews; 2 access-blocked unread; 0 reproduced.**


### Audit batch38 — 2026-10-15: LLM4UT empirical study (#39)

Đã đọc toàn bộ paper ISSTA’25/arXiv v1. Nghiên cứu so sánh 37 model qua test generation, assertion generation, test evolution; TestGen dùng Methods2Test_filter 56,132 pairs và đánh giá 163 Defects4J bugs ở năm project. Paper còn có 156,760 TAP assertion records, 5,196 test evolution cases và internal dataset riêng. [Paper](https://doi.org/10.1145/3728951), [author replication package](https://github.com/iSEngLab/LLM4UT_Empirical/tree/a6e9508878df96445cfe83fa981c8c92399ebf49).

Artifact có fine-tuning/inference/Defects4J scripts, một phần datasets và Total_result.pdf, nhưng không có fine-tuned checkpoints; TestGen folder thiếu processed 56,132-pair dataset, còn Defects4J runner hardcode `/efs_data/sy/defect4j` paths. Authors report hơn 3,000 A100 GPU-hours. README nói MIT nhưng `LICENSE` trả 404; paper CC BY 4.0. Kết quả quan trọng cho thesis: DeepSeek-Coder-6b chỉ tìm 8/163 bug và precision 0.74%, nên passing/correct test không thể thay bug-detection metric. No code/model run.

Cumulative: **39 full texts read; 41 source checks/reviews; 2 access-blocked unread; 0 reproduced.**


### Audit batch39 — 2026-10-15: AnyPoC (#40)

Đã đọc toàn bộ arXiv v2. AnyPoC nhận candidate bug report, phân tích trigger/root cause/consequence/oracle, sinh executable PoC theo execution feedback rồi độc lập kiểm tra trong môi trường mới. Paper báo 121 bugs trong 12 hệ thống, 108 confirmed, 92 fixed, 46 PoCs thành regression tests; validation corpus gồm 192 true/false reports. Bug classes gồm logic/robustness/security. [Paper](https://arxiv.org/html/2604.11950v2), [author’s public implementation](https://github.com/zzjas/anypoc/tree/e91ed3ade5726e1cf6ddcdde7659ff747952eb1f).

Repo Apache-2.0 thuộc first author, nhưng hiện là implementation tiếp tục phát triển (README báo 130+ bugs; paper 121). Không thấy frozen 192-report corpus, traces/results hay paper-specific table runner. Paper dùng Claude Code/Opus và Codex/GPT-5 Codex, cost trung bình $5.02/$2.61 mỗi report. Rất sát causal bug reproduction/false-positive filtering, nhưng không phải Defects4J/BugsInPy/SWT benchmark. Không chạy code/model.

Cumulative: **40 full texts read; 42 source checks/reviews; 2 access-blocked unread; 0 reproduced.**


### Access/source check — 2026-10-15: TestCTRL (#41; full paper unread)

Tried official ACM DOI/PDF, the author publication page, HKUST repository and Paperity. ACM is 403, HKUST redirects to CAPTCHA, and Paperity exposes only the opening pages. **This item is not counted as full text read.** Official abstract says TestCTRL uses CodeLlama-7B policy + CodeGPT coverage reward with PPO and tests on Defects4J; the full methodology/results are not audited.

A public Zenodo replication package with matching title has CC BY 4.0 README, datasets, training/evaluation scripts and generated tests; however it is anonymous and dated 2023. `checkpoints.zip` and `pretrain.zip` are only 2.5KB and 1.2KB and contain empty directories—no model weights. README asks for external base weights and lists 8xA800 80GB; reproducing the complete result would also need substantial training and potentially GPT-3.5 CoT generation. Keep as possible coverage-RL related work, not a selected reproduction baseline until full paper access and artifact linkage are verified.


### Audit batch40 — 2026-10-15: BRMiner (#42)

Đã đọc toàn bộ arXiv v2 và đối chiếu final Springer PDF (60 trang, CC BY 4.0, published 24/03/2025). BRMiner lấy string/numeric literals từ bug report bằng Javalang + regex, dùng GPT-3.5 ToT lọc rồi seed vào EvoSuite; so sánh thêm Randoop. Defects4J 2.0 dùng 809 bugs/22,111 reports qua 17 projects; 7,855 test literals có 1,129 exact matches với report. BRMiner đạt RIR 60.03%, RIEAR 31.71%. AllLitLLM detects 313 bugs with EvoSuite vs 295 NoLit; 111 vs 93 with Randoop; 58 unique bugs over variants, 13 exclusive in main sample. [Paper](https://doi.org/10.1007/s10664-025-10635-z), [final PDF](https://d-nb.info/1372487530/34), [author data listing](https://orbilu.uni.lu/profile?uid=50043787).

Paper claims full implementation/data at anonymous 4Open, but that URL now returns 401 `not_connected`; author-linked GitHub `Cwendkuuni/BRMiner` returns 404. Source/license unverified; exact replay not feasible until repo access is restored. Run requires GPT-3.5-turbo, modified EvoSuite 1.2.1/Randoop 4.3.1, Defects4J and 640GB RAM. Relevance is mainly exact literal overlap with fixed human tests, so it undercounts related/patterned inputs; method supplies input hints, not causal explanation. No run/API calls.

Cumulative: **41 full texts read; 44 source checks/reviews; 3 access-blocked unread; 0 reproduced.**


### Audit batch41 — 2026-10-15: LLM unit-test generation survey (#43)

Đã đọc toàn bộ arXiv v3 survey. Paper tổng hợp 178 publications đến 31/07/2026, quality-appraisal 11 tiêu chí (QC1–QC8 phải đạt 2; tổng ≥18/22), có second-pass audit 60 studies và double-classification 20 studies. Taxonomy bao phủ context/input/prefix/oracle construction và validation/repair/coverage/mutation/maintainability. Kết luận phù hợp với đề tài: compile/pass/coverage không chứng minh oracle đúng hay phát hiện bug; cần báo các outcome riêng. [Paper](https://arxiv.org/html/2511.21382v3).

Đây là survey, không có model hay benchmark để reproduce. Paper nói anonymous 4Open package chứa query/logs, nhưng endpoint hiện 401 và git access not found; replication package chưa verify. Dùng làm taxonomy/discovery source, không phải baseline. No code/API run.

Cumulative: **42 full texts read; 45 source checks/reviews; 3 access-blocked unread; 0 reproduced.**


### Supplemental full-text/source verification — 2026-10-15: TATG (#44)

Đã đọc toàn bộ 9,403 từ trích xuất của arXiv v1 và kiểm tra nguồn tác giả. TATG mô hình hóa từng test objective bằng evidence, prerequisite setup, action, oracle shape, acceptance predicate, status và behavioral de-duplication key; sau structural generation mới dùng mutation feedback để harden oracle. Đây là prior work rất sát với concept-guided testing. Paper đánh giá 110 KTester focal methods và 31 methods bổ sung trên source cố định; 9 methods bổ sung thuộc các revision Defects4J cố định, không phải historical bug IDs hay buggy/fixed pairs. Vì vậy coverage/mutation scores không chứng minh issue reproduction. Paper chỉ hứa implementation/subjects sẽ được public, không đưa repository URL; đã kiểm tra arXiv, public search theo title và GitHub profile/repositories của first author nhưng không thấy TATG artifact. Qwen3.6-35B-A3B/local vLLM và DeepSeek-V4-Flash-284B/Fireworks được nêu, nhưng thiếu immutable model revisions. Kết luận: high-fit conceptual comparator, exact reproduction hiện chưa khả thi; không tự reimplement. Xem `audit/reviews/044.json`.

Rank #44 đã thuộc review ledger trước quota refresh; lượt kiểm tra lại này chỉ sửa/bổ sung evidence, không cộng vào hạn mức 50 lượt đọc mới. Counts tổng vẫn là 42/500 và 18/50 lượt mới.

Telemetry correction: người dùng xác nhận quota vừa reset. Local rate-limit event cũ không còn dùng làm current percentage; report thể hiện trạng thái user-reported reset và ghi rõ chưa có số đo live mới. Không có timers.


### Access/source audit — #45 DA-AG (full paper blocked)

Official ISSTA 2026 listing verifies the abstract: mixed single/multiple assertions, unknown insertion positions, 358,117 tests from 7,061 projects, 13 LLMs, and Defects4J bug-exposure evaluation. ACM DOI/PDF endpoints currently return 403, while coauthor Meng Yan’s listed PDF returns 404; no arXiv copy or implementation repository found. Abstract-only is not a full-text read. Keep as high-priority candidate pending paper/artifact access; exact setting and reproduction verdict remain unknown. Review: `audit/reviews/045.json`.

Cumulative totals: 42/500 full texts read, 46 source/review checks, 4 access-blocked unread, 454 records not yet review-complete, 0 reproduced. Fresh-quota cap: 18/50 distinct additional full texts read; #44 was a prior-reviewed reread and #45 is blocked, so neither increments that cap.


### Audit batch — #46 Agentic Bug Reproduction at Google

Đã đọc toàn bộ 10,291 từ arXiv v2. Đây là paper sát nhiệm vụ bug-reproduction nhất: định nghĩa BRT theo Fail-to-Pass và nhận issue report + buggy source; nhưng toàn bộ cohort 80 bugs là GITS nội bộ Google, không phải Defects4J/SWT-Bench. BRT Agent dùng code_search/Bazel nội bộ và code-editing Gemini fine-tuned trên code Google; model này, Passerine, data và source không public. Headline: 85% candidate / 28% plausible BRT vs adapted LIBRO 41% / 10%; 86% plausible patches đạt tiêu chí thủ công, nhưng 11% làm đổi test sẵn có và bị coi invalid. Passerine có plausible fixes 17/23 khi được cấp BRT vs 13/23 khi không, song tác giả gọi đây là upper bound do chọn BRT với oracle ground truth. EPR top-1 chọn plausible fix 70% trong pool 20. Dùng làm protocol/related work, không chọn làm base có thể tái hiện. Paper đề cập root-cause utility nhưng không có taxonomy/root-cause classifier. [Paper](https://arxiv.org/html/2502.01821v2); chi tiết `audit/reviews/046.json`.


### Audit batch — #47 TestPrune / “Can Old Tests Do New Tricks?”

Đã đọc full text 13,000 từ và kiểm tra source/data/model route. Author artifact [IBM/Issue-Test-Localizer](https://github.com/IBM/Issue-Test-Localizer) xác nhận đúng paper FSE 2026, Apache-2.0; pin tại `b9100eb6a4550486a26a07704d2d93560eaf751e`. Static inspection `run_pipeline.py`, model client, localization, test-file retrieval, minimizer, requirements và shell runner; repo có result logs, regression/BRT outputs và quick-start. Không chạy code/API. Workflow issue→suspicious functions→top-10 test files→coverage→greedy minimization; tăng quality/cost of downstream Otter++ BRT generation và repair/patch selection. SWE-Bench Lite (300) + Verified (500), Python; F→P scoring dùng TDD-Bench Verified harness, **SWT-Bench chỉ được bàn trong related work**, không có Defects4J/BugsInPy result. Bảng paper: Claude Verified 31.2→34.0 (+2.8 percentage points; 9.0% relative); GPT-4o Verified 29.0→30.8 (+1.8pp; 6.2% relative). Không được ghi +9pp. Author README cho 3–5 phút/case và khoảng 2 ngày/full Verified run. Exact replay conditional do Docker/SWE-Bench environments và paid API models; README hỗ trợ custom endpoint nên own-model eval riêng khả thi nhưng không phải exact reproduction. Rất đáng chọn làm baseline/add-on cho issue-level regression-test context, không phải root-cause taxonomy. Xem `audit/reviews/047.json` và `public_evidence/source-audit.json`.


### Audit batch — #48 DPIAgent

Đã đọc toàn bộ 14,550 từ arXiv v1, gồm appendices A–E. DPIAgent chia agent thành defect exploration và test generation; `ready_to_write_test` bắt buộc handoff 6 fields: bug location, root cause, expected/actual, reproduction strategy, reference tests và test plan. Test-writing phase bỏ exploration tools. Đây là thematic fit mạnh nhất cho root-cause-informed BRT và được đánh giá trực tiếp trên 433 task Python của SWT-Bench Verified, ba backbone (GPT-5-Mini, GPT-5, Claude Opus 4.5), trung bình 3 runs. DPI-only success: 74.28%, 81.76%, 78.98%; selection đạt 82.32%, 86.17%, 81.38%. Selection tốn thêm 6 candidate issue variants + 3 SWE-Agent surrogate fixes/issue. Có function-localization metrics nhưng root cause được ghi free-form, không có root-cause taxonomy/accuracy metric.

Source: paper chỉ dẫn project page; page chỉ có paper/arXiv, không code/data. Kiểm tra public GitHub profile/repositories của first author và repo routes (DPIAgent/Microsoft) không tìm thấy source, predictions, pinned commit hay outputs. Các RPG/SWE-Agent/Echo repositories là dependencies/related projects, không phải implementation DPIAgent. Software license không xác minh được. Verdict `not_feasible` exact reproduction; cần authors release code, và reimplementation chưa được phép. Xem `audit/reviews/048.json`.


### Audit batch — #49 CoHarden

Đã đọc toàn bộ 15,387 từ arXiv v1 gồm Appendices A–D. Paper cho thấy F→P chưa đủ đánh giá BRT: test “Lax” có thể pass cả golden và plausible wrong fix; MPE chia Rigorous/Lax/Misaligned qua năm mutation operators. Trên 1,104 F→P BRT injection pairs, Rigorous tăng Resolved +8.5 điểm phần trăm, Lax +0.0, Misaligned −3.6. CoHarden sinh witness test trước, rồi harden cặp test+fix bằng Temporal Matrix. Main cohort là 433 giao của SWE-bench Verified ∩ SWT-bench Verified; Lite giao nhau 276. Kết quả GPT-5-mini 69.4% Resolved / 78.9% F→P; API cost $0.84/instance. Cross-backbone: GPT-5.4 76.2% and Claude Opus 4.5 78.7% Resolved, nhưng cost tương ứng $6.69/$18.07 mỗi issue.

Rất mạnh cho test-oracle rigor và tránh test chỉ bắt triệu chứng, nhưng không phải root-cause taxonomy. Official project page có nút GitHub bị disable và ghi “Code under review”; không có implementation/output bundle public. Không tái lập được hiện tại. Review: `audit/reviews/049.json`.


### Audit batch — #51 Coverage + non-coverage objectives (Defects4J)

Đã đọc full-text Chalmers, paper exact 2025 STVR. Public modified EvoSuite fork và Defects4J fork được pin/đối chiếu; source của EvoSuite differs upstream in 72 files, có ExecutionTime fitness, fork LGPL-3.0; Defects4J fork MIT. Zenodo record 11047568 có 5.6GB archive ghi chứa algorithm/data; PDF lại cite 11047567 nên cần reconcile exact snapshot. Study dùng Defects4J 2.0.1, sample 93 faults/14 Java projects, 6 objective configs, 2 budgets (180/300 sec), 10 trials = 11,160 suites. Branch + Exception/Output/Execution-Time giữ gần tương đương branch coverage; multi-objective tăng fault discovery so với goal-only, nhưng không significantly beat Branch Coverage alone. Đây là reproducible supporting baseline cho explicit testing goals/adequacy; không phải LLM, issue-based reproduction, hay root-cause classification. Full rerun lớn; data/package cho reanalysis, source không chạy. [Chalmers full text](https://research.chalmers.se/publication/548656/file/548656_Fulltext.pdf), [author EvoSuite fork](https://github.com/afonsohfontes/evosuite), [data record](https://zenodo.org/records/11047568). Details `audit/reviews/051.json`.


### Audit batch — #51 search-based goal objectives on Defects4J

Đã đọc paper full-text ở kho Chalmers và kiểm tra author artifacts. Đã xác minh fork EvoSuite của tác giả tại HEAD `207c2b1d7da86cb93268d37e08cb71cd1fd18e3e` (72 files diverge from upstream, gồm ExecutionTime fitness classes; LGPL-3.0) và Defects4J fork tại `00b83d3bb1c02a6ed599b90fa342a6bdea1ecc8f` (MIT). Matching-title Zenodo package `11047568` có 5.6 GB `defects4j.zip` và mô tả chứa experiment data/algorithms; paper lại trích DOI `11047567` nên package/version identity cần reconcile. Study dùng Defects4J 2.0.1, 93 faults/14 projects, 6 fitness configs, 180/300s budgets, 10 trials/config × fault, tổng 11,160 test suites. Coverage+Exception/Output/ExecutionTime hầu như không giảm branch coverage; tìm nhiều fault hơn so với goal-only, nhưng không significant hơn Branch alone. Rerun toàn bộ tốn compute; reanalysis data dễ hơn. Supporting baseline về explicit test objectives/Defects4J, nhưng không phải LLM, issue reproduction hay root-cause method. Không execute source. Review `audit/reviews/051.json`.


Access update — #52: the full 24-page author-hosted PDF was found at Hang Du’s official publication page after ACM returned 403. It is downloaded/extracted for the next continuation but remains **unread**, so counts do not change. The author page links public Zenodo artifact records; inspect source/data after full-paper review.


### Audit batch — #52 Mutant-killing assertion generation on Defects4J

Đã đọc toàn bộ 24 trang/14,945 từ từ PDF trên trang publication chính thức của first author. Paper dùng Defects4J 3.0.1 (642 bugs, 15 subjects); phân loại reachability, infection-propagation, revealability gaps. Tập trung 104 revealability-gap bugs; 3,742/11,832 surviving mutants có assertion augmentation; mutation-derived assertions phát hiện 63/104 bugs. Mô hình ngẫu nhiên 30% mutant-killing cho mean detection probability 84.5% trên 63 bugs này. Đây là kết quả oracle/mechanism, không phải issue-to-root-cause hay LLM test generation.

Artifact public do tác giả duy trì, MIT, mở rộng Defects4J và có Docker + CI examples cho Cli-2/Lang-6b; smoke reproduction khả thi. Full study tốn kém (paper báo 1,177 giờ/ba máy). Paper cites Zenodo 21328338, README liên kết Docker example Zenodo 21013232; exact full-data record/license và immutable source commit chưa resolve. No code run/reimplementation. `audit/reviews/052.json` có chi tiết.

Cumulative: **48 full texts read; 53 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since the user-reported quota refresh, **24/50 distinct new full texts** have been read; 26 remain.


### Audit batch — #53 EditAS2 (retrieve-and-edit assertion generation)

Đã đọc toàn bộ paper IEEE TSE 24 trang/21,398 từ. Đây là paper rất phù hợp để evaluate model gốc của project: dùng đúng tên model **Qwen2.5-Coder-7B-Instruct** với CoT trên Dataatlas/Dataintegration, đạt 31.68%/12.07% exact accuracy và 17.79%/8.48% CodeBLEU. Tuy nhiên, paper không dùng Qwen để đo BugFound trên Defects4J; BugFound là từ EditAS2/CodeT5 và một số baselines. Vì vậy có thể tái lập exact Qwen inference route, nhưng không gọi đó là paper’s Qwen Defects4J evaluation.

Paper dùng Defects4J 2.0.0, 588/835 assertion-triggerable bugs; EditAS2 đạt 20.1 average BugFound với EvoSuite prefixes và 27 với Defects4J prefixes, nhưng compilation rate chỉ 30.97% và precision 0.42%. Dataatlas/Dataintegration dùng random split, cho phép cùng project ở train/test; cross-project accuracy thấp hơn nhiều (19.20%/26.03%). Artifact: author-linked Zenodo record 15118614 CC BY 4.0, một zip 1.94 GB; matching public source snapshot commit `47b1a657857c23c6a5e17958364723a8bbb4092f` tải được (139 MB) và static-inspected. Repo thiếu root software LICENSE, scripts hard-code paths và dựa trên PyTorch 1.10.1/CUDA 11.3; archive/checkpoints chưa tải/inspect. Exact rerun conditional; no model/code run. See `audit/reviews/053.json`.

Cumulative: **49 full texts read; 54 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since the user-reported quota reset, **25/50 distinct new full texts** have been read; 25 remain.


### Audit batch — #54 STMutants (PLC Structured Text mutation dataset)

Đã đọc toàn bộ arXiv v1 (6,770 từ). Dataset Figshare public CC BY 4.0, 110 generated/108 retained mutants ở 11 Structured Text/PLC programs; paper chạy test generation rồi mutation execution bằng MATIEC với GPT-5.2, Gemini 2.5 Pro, Claude Sonnet 4.5. **Defects4J chỉ ở related work**, không phải dữ liệu thực nghiệm; SWT-Bench/BugsInPy không dùng. Artifact `Mutations.zip` 213 KB chứa mutant source files, không có author runner/harness hay full test-generation implementation; cần paid API models để tái chạy headline baseline, nên exact reproduction không khả thi từ artifact hiện có. Làm PLC mutation research có thể hữu ích về sau, nhưng out-of-scope cho Java/Python root-cause issue testing. Xem `audit/reviews/054.json`.

Cumulative: **50 full texts read; 55 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since user-reported quota reset: **26/50 new full-text reads** (24 remain).


### Audit batch — #55 APR agent traceability / test-validation study

Đã đọc full text arXiv v3 (13,613 từ) và kiểm tra artifact. Nghiên cứu 5 APR agents trên SWE-bench Verified 500 tasks; phân tích patch style, issue difficulty, reproducer tests, overfitting, regression-test selection và tooling. Agentless reproducer generation 40 samples đạt trigger 46.0% ở temperature .2; localization context nâng successful tests 614/1,500 lên 697/1,500 trên Verified-50 (27/50 tasks có cải thiện). SWE-Agent và Agentless khác nhau về overfit; workflow agent test reproducibility thấp hơn, nhưng overfit thấp hơn. Đây là protocol/model-behavior evidence tốt; không có causal root-cause labels và SWE-bench Verified là benchmark chính (SWT-Bench chỉ related work).

Author repo có scripts, tables, raw results; Hugging Face public trajectory/log dataset 3.28 GB. Cached-trace analyses có thể chạy lại, nhưng exact API runs cần Claude/GPT, SWE-bench Docker và Agentless repo. Repo/dataset chưa khai báo software/data license. Không chạy code hay API. Xem `audit/reviews/055.json`.

Cumulative: **51 full texts read; 56 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since quota reset: **27/50 distinct new full texts** (23 remain).


### Audit batch — #57 ReduJavator test-reduction replication

Đã đọc toàn bộ paper 3,781 từ, full text và source author. Paper dùng 30 Defects4J test failures + 30 mutant tests để đo AST statement reduction. Xác nhận leaf/non-tree statements bị giảm nhiều theo số lượng, nhưng không xác nhận xác suất removal cao hơn đáng kể (Defects4J Wilcoxon p=.5426; mutant p=.5731). GitHub ReduJavator source public, nhưng không có software license; TestObject chứa absolute paths và Main mặc định chỉ chạy một case. `Observations.txt` ghi build/test-result issues và cần sửa thủ công Maven/Gradle configs. Supporting work về test minimization/FL, không phải test generation, issue reproduction hay root-cause taxonomy. No code run. Review `audit/reviews/057.json`.

Cumulative: **52 full texts read; 57 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since quota reset: **28/50 distinct new full texts**; 22 remain.


### Audit batch — #58 TC-Bench binary-matrix test-generation benchmark

Đã đọc toàn bộ arXiv v3 (16,339 từ, gồm appendices) và kiểm tra source/dataset. TC-Bench công bố 877 competitive-programming problems, 9,347 wrong C++ solutions, 7,016 accepted solutions; HF dataset MIT card và 877 rows. GitHub có construction/evaluation scripts; test generator được biểu diễn bằng JSONL input/output, nên có thể nạp tests do Qwen local sinh vào evaluator mà không gọi model API. Paper báo cáo đúng Qwen2.5-Coder-7B-Instruct: LCB HackRate 42.17%, HT 21.92%. Đây là lựa chọn tốt nhất hiện tại để evaluate năng lực test-case generation của model riêng, nhưng chỉ là benchmark algorithmic C++, không phải SWT-Bench/Defects4J/BugsInPy hay bug-root-cause. Exact reproduction các 13 model/methods không trọn vẹn vì generator implementation/prompts và API snapshots thiếu; dataset construction code hard-code author path và source repo không có license rõ. Review `audit/reviews/058.json`.

Cumulative: **53 full texts read; 58 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since quota reset: **29/50 distinct new full texts**; 21 remain.


### Audit batch — #59 LLM-based test generation narrative survey

Đã đọc toàn bộ arXiv v1 (12,871 từ) và kiểm tra repo materials. Survey tổ chức 95 records theo test objective/artifact, information provenance, generation/learning mechanism và quality evidence; có thảo luận SWT-Bench/TC-Bench. Tuy nhiên authors nói rõ đây là preliminary structured narrative, không phải completed SLR: phần lớn chỉ metadata/abstract, full text chọn lọc, chưa dual-screening, inter-rater validation, full variant coding hay quantitative synthesis. Public repo có register/search notes/manuscript nhưng không có experiment/model để reproduce. Dùng làm map/related-work finder, không coi là primary verified evidence. Review `audit/reviews/059.json`.

Cumulative: **54 full texts read; 59 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since quota reset: **30/50 distinct new full texts**; 20 remain.


### Audit batch — #60 LLMutantKiller

Đã đọc toàn bộ 23-page author PDF và kiểm tra replication artifact. Tool nhận original/mutated source fragment, sinh Jest test, xác minh pass-original/fail-mutant, rồi retry đến 10 vòng với feedback lỗi. Paper đánh giá 915 surviving StrykerJS mutants ở 13 JS/TS repos; 815 behavior-changing, 100 equivalent. Valid kill: Claude Sonnet 4.6 777/815 (95.3%), Devstral 509/815 (62.4%), Llama 3.3 216/815 (26.5%); test validity được manual-audit, max 3.7% mutant-kills chỉ từ invalid test. Public artifact gồm MIT source, prompts, Docker, labels, outputs và claim map. Hỗ trợ custom OpenAI-compatible chat endpoint nên có thể thử Qwen local, nhưng chưa chạy. Reduced 13-mutant demo ~17 min/<$1 historical; full 12 configs estimated ~108 days in Docker/$1,313 historical. Không phải Defects4J/SWT issue study. Xem `audit/reviews/060.json`.

Cumulative: **55 full texts read; 60 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since quota reset: **31/50 distinct new full texts** (19 remain).


### Audit batch — #61 TestAgent human-testing-inspired unit-test generation

Đã đọc full arXiv v1 (11,090 từ). TestAgent chia planner, generator, reviewer; planner tạo test obligations, generator dùng repository knowledge graph/tool feedback, reviewer kiểm tra coverage/mutation, và failure root-cause analysis phân biệt lỗi test với defect. Dataset chính 1,454 Java methods, trong đó năm project lấy từ Defects4J nhưng là current-version test-generation subjects; internal UTXXX 658 methods là private; Python cohort 141 methods. Paper báo Qwen3-30B-A3B: 60.44% mutation score, 81.25% line/78.21% branch coverage; 154/167 test-revealed failures được authors xác nhận là bug (92.22%), có taxonomy root-cause.

Main paper không link source/data. Tìm được related FSE tool-demo repo bởi authors có overlap, cùng architecture/metrics; public MIT backend/VSCode, prebuilt CKG JAR and configurable OpenAI base. Tuy nhiên repo không được arXiv paper cite, author list khác, dataset/labels không kèm, MIT copyright có placeholder; exact provenance version chưa xác minh. High conceptual fit; exact replication conditional. Không chạy code/model. Review `audit/reviews/061.json`.

Cumulative: **56 full texts read; 61 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since quota reset: **32/50 distinct new reads**; 18 remain.

### Audit batch — #63 TestExplora proactive repository-level bug discovery

Đã đọc toàn bộ arXiv v2 (16,836 từ / 4,336 dòng trích xuất, gồm phụ lục A–G, prompt templates, case studies và inventory 482 repositories). TestExplora dùng documentation-derived intent làm oracle; test phải pass trên post-PR và fail trên pre-PR. Bản đầy đủ có 1,552 PR / 2,389 tasks / 482 Python repositories; Lite có 330 PR / 517 samples. Bài nhắc SWT-Bench/TDD-Bench như benchmark so sánh, không chạy thực nghiệm trên chúng; không dùng Defects4J/BugsInPy. Không có explicit root-cause labels.

Paper link tới Microsoft/TestExplora và README xác nhận official implementation. Source MIT, kiểm tra tĩnh tại commit `11e6952261f58d3ceb9f4d2571e03aa35dad9523`; có repository construction, inference, vLLM call wrapper và Docker evaluator. Nhưng source tree không có benchmark JSON, generated test patches hay result cache; README yêu cầu người dùng tự cung cấp `data_path`, không đưa URL tải dataset. Loader mặc định đọc một absolute author-local path khi `subset=True`; Lite cần JSON thứ hai. Paper báo Qwen3-Coder-30B-A3B trong khi wrapper cấu hình Qwen2.5-Coder-32B-Instruct. Kết luận: task-fit rất cao, exact reproduction/own-model evaluation có điều kiện cho tới khi giải quyết được dataset và model mismatch. Không chạy source/API/model. Chi tiết: `audit/reviews/063.json` và paper folder.

Cumulative: **57 full texts read; 62 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since user-reported quota reset: **33/50 distinct new full-text reads** (17 remain).

### Audit batch — #98 Reproduction Test Generation for Java SWE Issues

Đã đọc toàn bộ arXiv v2 (9,651 từ / 1,514 dòng trích xuất). Đây là reproduction-test generation từ issue + pre-fix Java repo, chấm bằng test fail trước patch/pass sau patch. TDD-Bench-Java có 250 tasks/13 repos, lọc từ Java samples của SWE-PolyBench và Multi-SWE-bench; tác giả còn dùng 150 IBM internal issues nhưng private. Paper báo e-Otter++ đạt 43.6% F2P với Claude-Sonnet-4.5, 46.4% với GPT-5.2; candidate F2P@6 là 54.8% cho cả hai. Generator pipeline có localization, contextualization, execution-feedback refinement, issue morphing và test selector. Không có causal root-cause labels; SWT-Bench/TDD-Bench-Verified là related work, Defects4J chỉ được trích dẫn.

Kiểm tra public artifact IBM/TDD-Bench-Verified tại commit `3df8be066e486789d0b8e0d2865a3a4422b4560f` (Apache-2.0). CSV có đúng 250 dòng/250 unique IDs, khớp đủ `id_list.txt`; 250/250 records có issue, base commit, code patch, test patch, test command và Dockerfile metadata, thuộc 13 repos. Java README đưa ra JSON prediction format và cách chạy Docker evaluator; `setup.sh` pin SWE-PolyBench commit `1963184` rồi apply `tdd_java.diff`. **Model evaluation trên local Qwen khả thi qua output test patches + public evaluator.** Nhưng paper ghi rõ generator code proprietary, nên không thể tái lập đúng e-Otter++ hoặc số liệu model của tác giả; exact API snapshots cũng không pin. Không chạy code, benchmark hay model. Xem `audit/reviews/098.json`.

Cumulative: **58 full texts read; 63 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since user-reported quota reset: **34/50 distinct new full-text reads** (16 remain).

### Audit batch — #89 Multi-SWT-Bench multilingual reproduction tests

Đã đọc toàn bộ arXiv v1 (10,158 từ / 1,378 dòng, gồm Appendix A–C). Benchmark 1,963 issues/51 repos/8 ngôn ngữ; 340-instance Lite/Flash subset được dùng cho toàn bộ thí nghiệm. Oracle yêu cầu có ít nhất một test fail trước fix/pass sau fix và toàn bộ test set pass sau fix. Paper so sánh MSWE-agent, MOpenHands, Codex CLI, Claude Code; best overall Claude Code + Claude Opus 5 = 65.29%, MOpenHands + Claude Sonnet 5 = 57.94%. Failure analysis cho thấy test convention, implicit setup và mất semantics/compile sau khi sửa test. Đây là issue-reproduction paper, không có causal fault taxonomy; Defects4J/BugsInPy không dùng.

Paper link Zenodo `10.5281/zenodo.22961970`. API metadata khớp title, record CC BY 4.0; archive 225,722,979 bytes, MD5 `1ad4bc29eaf2bb7d8198a2f6afc69053`. Không download/extract archive đầy đủ; HTTP Range kiểm ZIP central directory 289 entries, README, LICENSE, model config và runner. Xác minh `benchmark/full.txt` có 1,963 unique IDs, `benchmark/flash.txt` có 340; package gồm expected/golden data, evaluation harness, method scripts/prompts, configs và 12 compressed result bundles. Package README mô tả full/one-method setup, build, run/evaluate. Own local Qwen có thể nối qua configurable MOpenHands `base_url`/API proxy, nhưng cần endpoint allowlisting/config và chưa test. Exact model aliases không immutable snapshot; full Docker/multilingual rerun nặng. Code package Apache-2.0 nhưng MSWE-agent fork license metadata conflict; benchmark source/patches retain upstream terms. Không chạy source, API hay model. Xem `audit/reviews/089.json`.

Cumulative: **59 full texts read; 64 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since user-reported quota reset: **35/50 distinct new full-text reads** (15 remain).

### Audit batch — #75 Dynamic Cogeneration of Bug Reproduction Test in Agentic Program Repair

Đã đọc toàn bộ arXiv v3 (10,618 từ). Paper so sánh Fix-only/BRT-only với cogeneration Freeform, TDD và TLD trên 120 bug nội bộ Google/GITS, sáu ngôn ngữ, 20 trajectories/bug/config, 25-step limit; dùng Gemini 2.5 Pro. Freeform có joint plausible-fix+BRT cao nhất ở k=20; ranked test-aware selector đạt precision/recall 0.16/0.71 cho patch vừa có plausible fix vừa có plausible BRT, so với default 0.08/0.57. Failure analysis hữu ích: agent xóa test trước khi submit, mắc trong debugging loop/sai hypothesis, hoặc fix-test overfit lẫn nhau. Đây là root cause của **failure trajectory**, không phải taxonomy nguyên nhân của underlying defects.

Paper mô tả Google Passerine + GITS/private monorepo; không link source/data/logs. Exact title, official FSE page và Github search không tìm được artifact. Không có Defects4J/BugsInPy/SWT experiment. Rất sát về ý tưởng nhưng reproduction và own-model same-cohort evaluation không khả thi. No code/API/model run. Xem `audit/reviews/075.json`.

Cumulative: **60 full texts read; 65 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since user-reported quota reset: **36/50 distinct new reads** (14 remain).

### Audit batch — #79 From Business Requirements to Test Assertions

Đã đọc toàn bộ arXiv v1 (4,938 từ). Paper dùng 10 Defects4J Lang bugs (1, 3–11), tự chuyển buggy/fixed diff thành business requirements và REQ oracle thủ công, sau đó sinh Java oracle chỉ từ requirement + method signature. Đánh giá riêng agreement với REQ (intended spec) và SUT (behavior thực tế). DeepSeek-V3 macro-F1 0.8179 với REQ / 0.7476 với SUT; Qwen3-Coder-480B 0.7779 / 0.7030. Đây là concept fit cao cho oracle/requirement behavior, nhưng không phải issue-to-BRT hay root-cause analysis; pilot chỉ 10 bugs một project, correlation có n rất nhỏ.

Paper nói replication package 171.51 MB MIT có requirements, REQ, generated oracles, test suites và scripts trên Figshare. Landing page xác nhận “ESEM data”, Lang bugs 1/3–11, MIT label nhưng ghi rõ “shared privately”. Browser follow-up 403, direct shell download 202/empty; chưa xác minh archive/checksum/nội dung. Do đó không coi đây là public/easy own-Qwen route cho tới khi truy cập được package. Không chạy code/API/model. Xem `audit/reviews/079.json`.

Cumulative: **61 full texts read; 66 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since user-reported quota reset: **37/50 distinct new full-text reads** (13 remain).

### Audit batch — #92 SWE-Doctor runtime diagnosis from multi-faceted BRTs

Đã đọc toàn bộ arXiv v1 (9,646 từ / 739 dòng). SWE-Doctor có ba stage: extract mỗi behavioral requirement thành targeted BRT; debug BRT bằng PDB/Delve và ghi diagnosis record (fault location, symptom, propagation, runtime values, suggested fix); dùng requirements + RCA records để sửa patch và completeness-check. Dataset là 436 bug-fix SWE-bench Verified, 107 bug-fix SWE-bench Pro Python và pilot 50 Pro Go; không chạy SWT-Bench/Defects4J/BugsInPy. Bài báo 75.7% Verified / 59.4% Pro, hơn baselines 2.0–3.9pp và 8.0–8.9pp; ablation 50 Pro tasks cho thấy multi-faceted BRT và diagnosis đều đóng góp. Điểm quan trọng: paper không đo RCA correctness với ground-truth root-cause labels; final metric là patch resolution.

Paper link official GitHub `SWE-Doctor/SWE-Doctor`, repo MIT, có BRT/RCA/repair/evaluation 4-stage pipeline, Python/Go, PDB/Delve, Docker grader. Statically inspected README, key runners/configs and source tree at only commit `90ed1d949cae8345b6571394454dd59ec12dc7b2`. LiteLLM model config/endpoint có vẻ cho phép local Qwen; chưa test. Reproduction conditional: repo commit Oct 2 postdates July paper and README labels it an FSE 2027 research artifact; task-ID lists/results cache are missing and repo does not pin exact model snapshots. Full run Docker + 543 benchmark issues + hosted models; paper cost $0.43/Verified and $0.64/Pro issue. No code/API/model run. See `audit/reviews/092.json`.

Cumulative: **62 full texts read; 67 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since user-reported quota reset: **38/50 distinct new reads** (12 remain).

### Audit batch — #69 Beyond Heuristics? Targeted Unit Test Generation

Đã đọc full official LIPIcs ESEM 2026 paper (21 trang; 9,997 từ). Benchmark có 210 Java runtime-exception bugs/66 projects, gồm 169 case từ nhiều benchmark (có Defects4J) và 41 bugs được công bố sau model cutoff. Task đưa buggy repo + exact exception type + target line; evaluator yêu cầu đúng exception và target location ở top stack frame. Không phải issue-report-to-BRT, không dùng buggy/fixed F2P và không có root-cause labels. Claude Code + GPT-5 đạt 89.5%; UnitCon 49.6%; OpenCode + DeepSeek-V3.2 đạt 65.2% với khoảng $0.04/task. Phân loại 200 failure trajectories (Cohen κ=.76): insufficient exploration 41.5%, inadequate reasoning 25.5%, tool misuse 14%, incorrect focus 11.5%.

Paper trỏ Zenodo 20283766; API record title khớp, CC BY 4.0, archive `ESEM-2026.zip` 2.16 GB. Đọc root README bên trong qua HTTP Range; README liệt kê 210 repo snapshots, Docker/JDK images, `run_evaluation.py`, `build_image.py` và random subset option. Không tải/extract toàn bộ archive; full runner/source chưa inspect nên verdict reproduction conditional/partial. Một bounded pilot model có vẻ khả thi qua OpenCode, nhưng custom model config chưa xác minh. No run. Chi tiết: `audit/reviews/069.json`.

Cumulative: **63 full texts read; 68 source checks/reviews; 5 access-blocked unread; 0 reproduced.** Since quota refresh: **39/50 distinct new reads** (11 remain).

### Audit check — #71 Bug Whisperer (full text access-blocked; NOT counted as read)

Đây là candidate rất sát hướng path-constrained targeted tests/Defects4J, nhưng official ACM PDF DOI `10.1145/3846194` trả 403; OpenAlex reports closed access/no OA full text; author publication page chỉ xác nhận acceptance, không link PDF/source. File local là metadata page, không phải article. Tìm thấy Zenodo cùng title `17093597` (2025-09-10) với 503 Defects4J focal methods và scripts/results, nhưng không có DOI link/version mapping từ paper TOSEM 2026; cohort/model description có vẻ là bản cũ. Không gán artifact này cho 2026 paper.

Review 071 ghi rõ fulltext_read=false, access blocked; không tính vào giới hạn 50 paper read. Cumulative remains **63 full texts read; 69 source/review checks; 6 unread access-blocked; 0 reproduced.** Fresh quota stays **39/50**; còn 11 fulltext reads.

### Audit batch — #86 AG-RAG joint retrieval/generation for assertions

Đã đọc toàn bộ arXiv v2 (13,872 từ). AG-RAG jointly fine-tunes dense CodeT5 retriever + retrieval-augmented assertion generator. Main datasets are Data_old 156,760 TAPs and Data_new 265,420 TAPs; exact accuracy 64.59%/56.33%, vs EditAS 53.46%/44.36%. A separate real-fault test uses EvoSuite prefixes on 835 Defects4J bugs/17 projects and detects 41 bugs vs 21 for EditAS. This is strong oracle/assertion and Defects4J fault-detection evidence, not issue-to-BRT or root-cause localization.

Official author source `iSEngLab/AG-RAG` is substantive at commit `47d69677e371209d9b6665ae879df3708886b1bb`: data archive (74 MB), RQ1–RQ3 code, baseline outputs and evaluators; paper says checkpoints are linked via Google Drive, not in repo. Repo has no LICENSE. Main pipeline uses T5 encoder-decoder and CodeT5-base; user's decoder-only Qwen2.5-Coder is not a drop-in. Full paper reproduction needs two RTX 4090s (~29.2h/10 epochs on old data) or accessible checkpoint. The README's `tar -xzcf` extract command appears to have conflicting c/x flags and should be checked; no code run. See `audit/reviews/086.json`.

Cumulative: **64 full texts read; 70 source checks/reviews; 6 unread access-blocked; 0 reproduced.** Since quota refresh: **40/50 distinct full-text reads** (10 remain).

### Audit batch — #90 Mutation-Guided Unit Test Generation (MutGen)

Đã đọc toàn bộ arXiv v8 (13,489 từ). MutGen tóm tắt source để bỏ misleading comments, đưa PITest live/uncovered mutant feedback vào prompt, sửa test compile/runtime failures, rồi lặp tối đa 4 vòng. Main evaluation có 104 HumanEval-Java + 100 Leetcode-Java method-level subjects, tổng 3,044 mutants; Llama-3.3-70B via Ollama đạt 89.5%/89.1% mutation score, Genvanilla 77.9%/69.9%. Riêng supplementary Defects4J experiment dùng EvoSuite prefixes trên 835 bugs/17 project và phát hiện 41 bugs so với EditAS 21. Paper nói rõ full Defects4J cross-module testing là future work; không issue-to-BRT/root-cause.

GitHub author repo public tại commit `69dd37ddfab16b8c5efd22117dc3d213ab05418d`, có 74MB dataset archive, prompts, core generator/router, results và eval scripts. LLM wrapper dùng LiteLLM `model` + `api_base`; sample là local Ollama Llama3.3, nên Qwen qua OpenAI-compatible endpoint có vẻ khả thi nhưng chưa test. **Repo không có software LICENSE**, và fine-tuned checkpoints nằm ở Google Drive chưa verify. README có vẻ sai lệnh extraction `tar -xzcf` (x và c cùng lúc); cần kiểm tra trước setup. Local model subset evaluation có thể khả thi sau khi giải quyết license/setup; exact paper rerun điều kiện. No code/API/model run. Xem `audit/reviews/090.json`.

Cumulative: **65 full texts read; 71 source checks/reviews; 6 unread access-blocked; 0 reproduced.** Since quota refresh: **41/50 distinct new reads** (9 remain).

### Audit batch — #74 coverage/mutation validity replication (2026-10-15)

Read the full 13,276-word article (arXiv:2607.22880) and verified direct experimental use of Defects4J v3: 318 buggy focal methods across all 17 projects, paired with fixed versions and developer tests. BugsInPy is cited only in related work; SWT-Bench is not used. Study uses 11 LLMs/13 settings, 8,268 generated suites and 101,123 test cases to analyze coverage, mutation and F2P detection, including fixed-code vs buggy-code inputs. Key relevance: coverage/mutation may correlate with bug detection in regression-style fixed-code input, but coverage becomes unreliable when the input is already buggy; mutation analysis is inapplicable in that setting. This makes direct real-bug detection the right outcome for a buggy-input study.

Verified the paper-linked public MIT author repository at HEAD `4bc2ed63917557a8c879e6c733b8fa41c15b9871`; inspected README, LICENSE, NOTICE, setup/config, prompt, generation and analysis notebooks, and processed per-method CSV tree. Statistical analysis is readily re-runnable from published data without API keys or Defects4J. Some camera-ready per-model boxplots use values copied from the paper tables. Re-generating all suites is conditional and expensive: Java 11, Defects4J, PIT/JaCoCo/CodeCover, model API and unpinned provider snapshots. A local Qwen on a bounded subset is plausible as independent evaluation, not exact reproduction. No code/model run. See `audit/reviews/074.json` and the paper's `public_evidence/source_audit.md`.

Cumulative after this batch: **66/500 full texts read; 72 source checks/reviews; 6 access-blocked unread; 0 reproduced.** Since the user-reported quota refresh: **42/50 distinct new full-text reads; 8 remain.** Quota UI percentage is remaining; 90% remaining is ample. Timers remain disabled.

### Audit batch — #111 ORACLE-SWE oracle-signal ablation (2026-10-15)

Read the full 12,542-word arXiv v2 article and appendices, including signal-extraction rules, prompts, model/dataset table, ablation/validation results and limitations. It defines five handoff signals for SWE agents; the gold F2P reproduction test is the strongest single signal, while combined factors interact. Experiments use SWE-bench Verified/Live/Pro only (459/353/220 Python/211 Go after filtering); Defects4J is background citation, and BugsInPy/SWT-Bench are not used. Oracle arms deliberately inject gold tests/patch-derived locations to measure an upper bound. No author implementation, extracted signal dataset or result cache was found; SWE-agent is only the cited third-party base. Exact reproduction would require writing the missing method and expensive unpinned hosted-model calls, so do not implement. Useful motivation for direct, high-quality F2P oracle evaluation, but not a concept/RCA method or runnable baseline. See `audit/reviews/111.json`.

Cumulative after this batch: **67/500 full texts read; 73 source checks/reviews; 6 access-blocked unread; 0 reproduced.** Since the user-reported quota refresh: **43/50 distinct new full-text reads; 7 remain.** Quota UI percentage is remaining; recent local telemetry also shows substantial remaining headroom. Timers disabled.

### High-fit access check — #107 GIANT (2026-10-15; abstract only, NOT read)

SSRN abstract is an excellent topical match: it explicitly says 750 Defects4J 2.0 bugs and a RAG → test-generation → iterative-verification pipeline; reports 51 reproductions vs 32 LIBRO / 8 BASE. But official SSRN page and PDF are blocked with 403 and direct fetch refused. No author source link appeared in the accessible abstract or exact-title/author source search. Exact model and details are unknown. Logged as access-blocked; abstract/snippets do not count as a full-paper read and reproduction verdict remains unknown. See `audit/reviews/107.json`.

Cumulative after this source/access check: **67/500 full texts read; 74 source/review checks; 7 unread access-blocked; 0 reproduced.** Since quota refresh: **43/50 distinct new full-text reads; 7 remain.**

### Audit batch — #73 CATGen context-aware unit-test generation (2026-10-15)

Read the full 12,187-word arXiv v1 paper and checked the paper-linked author repository at pinned commit `b60476d34fb3b130dea653588810e482d30fa13d`. CATGen combines project context extraction, deterministic framework-aware skeleton construction, Qwen/LLM completion, and static repair plus edge-case tests. It evaluates eight private industrial projects/183 methods and Defects4J Chart/Math/Lang/Time. Defects4J aggregates: 80.64% CovL, 75.58% CovB, 92.40% compilation success, 79.65% pass; average mutation score 69.8% (+7.4pp over RATester). Models include local Qwen2.5-Coder-7B-Instruct and 32B; Defects4J result uses 32B. But no direct buggy-vs-fixed F2P metric or root-cause labels.

Public author package is explicitly partial: docs, examples, parser utilities, model wrapper and partial results, but full CATGen implementation, private industrial dataset, exact Defects4J focal IDs and evaluator are absent; repo has no declared code license. Despite the same Qwen2.5-Coder-7B checkpoint being listed, the method cannot be faithfully run with user's model without reimplementing missing stages. No code/model execution. Keep as high conceptual context/skeleton prior, not a viable reproduction baseline. See `audit/reviews/073.json` and paper `public_evidence/source_audit.md`.

Cumulative after this batch: **68/500 full texts read; 75 source checks/reviews; 7 unread access-blocked; 0 reproduced.** Since user quota refresh: **44/50 distinct new full-text reads; 6 remain.** Timers remain disabled.

### Audit batch — #65 XRepoTest multilingual repository-level test generation (2026-10-15)

Read full arXiv v2 (20,558 words, all appendices) and verified paper-linked MIT GitHub source at `39fb6ab3173136d3dac2d38ed7c98baf6c470270`; tree contains 313 entries, complete generation/context/eval/repair modules, Docker evaluators and tests. HuggingFace API confirms public, ungated dataset `solis-soict/xrepotest`, MIT metadata, 40 JSONL files; base data ~105 MB, LSP ~106 MB, RAG ~1.48 GB (~1.69 GB total). README has public fetch/setup and CLI commands and custom OpenAI-compatible `--api_base`; local Qwen is straightforward for a bounded run. Paper evaluates 14 models including Qwen3 models, so the user's Qwen2.5-Coder-7B is a custom evaluation, not an exact model replication. Benchmark has 3,642 focal functions across Rust, Go, Julia, PHP, Ruby; Java/Python explicitly excluded and Defects4J is related-work only. No BugsInPy/SWT-Bench, issue-conditioned F2P or root-cause labels. Strong metric contribution: Invocation Rate catches tests that pass or get coverage without directly invoking the focal function. Mutation testing only Go/Rust/Ruby; Docker `latest` tags and 14-model exact replay are limitations. Supporting own-model repository test-quality benchmark, not primary issue reproduction. No code/data/model run. See `audit/reviews/065.json` and `public_evidence/source_audit.md`.

Cumulative after this batch: **69/500 full texts read; 76 source checks/reviews; 7 unread access-blocked; 0 reproduced.** Since the user-reported quota refresh: **45/50 distinct new full-text reads; 5 remain.** Timers disabled.

### Audit batch — #91 class-level prompt engineering on Defects4J (2026-10-15)

Read the complete 58-page final EMSE manuscript via ORBilu institutional author repository (22,895 extracted words). It evaluates four legacy LLMs × five prompts at class level, 30 generations each, across Defects4J token-filtered 477 classes/16 projects, SF110, and a 31-class post-2023 CMD; outcomes include extraction/syntax/compilation/readability/test smells/coverage. The final article's §5.2.1 explicitly states it does **not** run paired buggy/fixed F2P, exception-based fault detection, or mutation analysis. Some §6.5 text contradictorily says mutation is integrated, but there is no mutation RQ/result table; flag this inconsistency, and follow explicit limitations/results. The earlier arXiv preprint `2407.00225` had bug-detection experiments, but is an older different-title/version and cannot be used as the 2026 article's method/result.

The paper-linked MIT 4open package was statically inspected through its public API: 2024 source snapshot/README title, Defects4J/SF110/CMD JSON, 391 dependency files, partial RQ1/RQ2 summaries and test suites. Current visible root has no RQ3/RQ4 or Test-Generation folders and only GPT-3.5/EvoSuite test roots, despite README's broader claims. This is an older artifact version; exact mapping to final 2026 paper is unresolved. No code/model was run. See `audit/reviews/091.json`.

Cumulative after this batch: **70/500 full texts read; 77 source checks/reviews; 7 unread access-blocked; 0 reproduced.** Since user quota refresh: **46/50 distinct new reads; 4 remain.**

### Audit batch — #93 Test Oracle Automation in the Era of LLMs (2026-10-15)

Read the full 5,912-word arXiv article (v1, 2024; final TOSEM 2025 DOI 10.1145/3715107). It is a perspective paper discussing three oracle types (assertions, contracts, metamorphic relations), false-positive/false-negative oracle deficiencies and the need for an assurance layer. It warns that Defects4J's public tests may be memorized by LLMs; its Commons Collections example is illustrative only. No dataset experiment, model evaluation, source code or quantitative outcomes exist; no reproduction possible. Useful concept/threat-model reference, not a runnable baseline. See `audit/reviews/093.json`.

Cumulative after this batch: **71/500 full texts read; 78 source checks/reviews; 7 unread access-blocked; 0 reproduced.** Since quota refresh: **47/50 distinct new reads; 3 remain.**

### Audit batch — #81 Go-UT-Bench fine-tuning dataset (2026-10-15)

Read the full 6,299-word arXiv v2 paper and checked its author-linked HF dataset. Go-UT-Bench contains 5,264 Go source/test pairs from 10 repositories, split 3,684/790/790; public ungated HuggingFace revision `24074620e2be3db20c11cba007649533cb677a30` totals ~175 MB. Paper trains DeepSeek-Coder-V2-Lite with LoRA and Llama-3.2-3B full fine-tuning; results are pairwise GPT-4o-mini judge win rates 81.9% and 76.7%. Critical limitation, explicitly acknowledged: no human judge triangulation, compilation/execution/coverage/mutation metrics, or significance tests. The dataset API has no license metadata; the paper claims upstream source repos are permissively licensed, so individual terms still apply. No training code/checkpoints found. Go code-to-test SFT, not issue-conditioned F2P or Defects4J/BugsInPy/SWT-Bench. Secondary data lead only; no code/model run. See `audit/reviews/081.json`.

Cumulative after this batch: **72/500 full texts read; 79 source checks/reviews; 7 unread access-blocked; 0 reproduced.** Since user quota refresh: **48/50 distinct new reads; 2 remain.**

### Audit batch — #82 CANDOR multi-agent oracle consensus (2026-10-15)

Read full arXiv v7 (15,083 words) and statically inspected paper-linked public code/data at GitHub HEAD `157165cc7ac76d72e59ed60d13084d74822c9e2e`: 1,356 tree entries / 20.9 MB with `initialize.py`, `generate.py`, `fix_oracle.py`, prompts, tools, HumanEvalJava/LeetCodeJava and three Pitest mutant variants. CANDOR splits prefix generation (Initializer/Planner/Tester/Inspector) from description-grounded oracle fixing (Requirement Engineer, three DeepSeek-R1 Panelists + Interpreters, Curator). It reports comparable coverage to EvoSuite, higher mutation scores, and ≥21.1pp oracle-correctness gains over TOGLL on correct and synthetic-mutant source. Critical fit limit: paper explicitly excludes Defects4J/SF110 because dependencies; test “faulty code” is generated by Pitest on HumanEvalJava/LeetCodeJava, not historical bug pairs. No RCA labels. Source lacks root LICENSE and hardcodes local Ollama 70B models; README paths conflict with pinned root-level code. Qwen needs client/model adaptation; full run requires large VRAM and 3 repetitions. Conditional concept reproduction only; no source/model run. See `audit/reviews/082.json`.

Cumulative after this batch: **73/500 full texts read; 80 source checks/reviews; 7 unread access-blocked; 0 reproduced.** Since user quota refresh: **49/50 distinct new reads; 1 remains.** Timers disabled.

### Audit batch — #76 EvoOtter (2026-10-15)

Read the complete 9,024-word arXiv v1. EvoOtter directly targets fail-to-pass bug reproduction tests, using heterogeneous issue prompts, localization, rule-based mutants, test selection based on execution-log changes, and batched LLM crossover. The paper reports 77.8% on SWT-Bench-Verified, but its main controlled evaluation is on TDD-Bench-Verified and SWE-Rebench; it does not experimentally use Defects4J or BugsInPy and provides no root-cause labels.

Checked the official author publication page and exact-title/author repository searches. No attributable public implementation, evaluator, pinned source archive, dataset manifest, or cached result set was found. The paper names Claude-Sonnet-4.5 and Claude-Opus-4.7. Prompts are mentioned as supplementary material, but prompts do not enable a faithful reproduction. Exact rerun is not feasible from verified public artifacts; a custom-model study would require implementing the method and would be a new evaluation. No code/model/API was run. See `audit/reviews/076.json` and the paper folder's `public_evidence/source_audit.md`.

Selection consequence: EvoOtter is a high-priority conceptual comparator for the SWT-Bench/BRT direction, especially mutation-derived test-selection feedback, but not a runnable base or a root-cause method. Keep #74 ahead for direct Defects4J analysis because its public MIT artifact contains buggy/fixed data and runnable statistical notebooks.

Cumulative after this batch: **74/500 full texts read; 81 public-source checks/reviews; 7 access-blocked unread; 0 reproduced.** Since the user-reported quota refresh: **50/50 distinct new full-text reads.** Stop new full-text reads at this cap. Quota UI percentage means remaining; user reports 90% remaining. Timers remain disabled.
