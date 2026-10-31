# Đối chiếu prior work và đề xuất concept-guided testing

Ngày 2026-10-21. Deliverable research theo yêu cầu người dùng: đọc đối chiếu, chốt
đề xuất và kết quả assessment. Không có new model/LLM-API/GPU/benchmark run, paper
reimplementation, thay đổi author source hoặc sửa frozen pipeline trong công việc này.

## 1. Quyết định

**Không mở thêm semantic chain chỉ bằng cách ghép v20–v33. Hướng đáng giữ là
concept-guided behavioral validation và adaptive testing: reusable semantic relations
giúp đánh giá observed behavior, chọn execution experiments và sửa fallible hypotheses.**

Đây là một candidate research question có thể bác bỏ, chưa là confirmed novelty
hay method đã có efficacy. Cơ chế giao trực tiếp với diagnostic v40 hiện có; ưu tiên
đọc kết quả của diagnostic đó khi hoàn tất, không tạo một version tương tự hay duplicate
run. Chưa có bằng chứng để mở rộng fault-template hoặc train concept-to-input.
Trong lúc đọc, shared workspace đã có final CPU report v41: sampling pool có
exposure22/33, displayed relation package11/33, median lift0.38 và registered no-go.
Đây là kết quả của existing run, không phải experiment do lượt research này thực hiện.
Vì vậy ưu tiên semantic validation/selection trên observed executions; chỉ query thêm
khi evidence chưa phân biệt được claim. Không mặc định input reach là bottleneck chung.

Correction cho trao đổi trước: nhận định “fault-concept + template có tín hiệu tốt
hơn” chỉ phản ánh v31/v34. Các retrospective checks v35–v39 đã làm yếu hướng đó;
phải dùng latest state khi quyết định. Đồng thời “hypothesis discrimination” không
phải novelty chung: active testing đã có prior work.

## 2. Phạm vi và evidence

Đọc lại method, experimental assumptions, ablations và limitations của bốn core
papers từ saved primary full texts, đối chiếu primary web records. Source-read
ReProAgent, RTED và UnitCon; KITE chưa verified public implementation/KB.

| Paper | Primary evidence | Finding ảnh hưởng proposal |
|---|---|---|
| [ReProAgent](https://arxiv.org/html/2607.09123v1) | §§3.4–3.6; author prompts/planner | RCA → trigger → plan → test; reason–validate–refine và execution review đã có |
| [KITE](https://arxiv.org/html/2607.11573v1) | §§II-A–II-D; §§III-A/C | Mechanism representation/ranking, trigger recipe và executable feedback đã có; generation dùng correct version |
| [UnitCon](https://doi.org/10.1145/3729362) | §§2–4; pinned artifact source | Error-condition-guided synthesis và prioritization đã có; supplied target, runtime-exception setting |
| [RTED](https://arxiv.org/html/2507.02318v2) | §III; generation/constraint source | Backward type constraints → generation → semantic reflection đã có; TypeError scope |

Finding về việc source “không có X” luôn giới hạn ở inspected schema/controller;
không suy ra LLM không thể tự làm X trong free-form reasoning. Paper ablation không
tự chứng minh concept gây gain nếu evidence, requests hoặc tool access cũng thay đổi.

Chi tiết từng paper và source anchors:
[ReProAgent](../papers/reproagent/MECHANISM_COMPARISON_20261021.md),
[KITE](../papers/kite-mechanisms/MECHANISM_COMPARISON_20261021.md),
[UnitCon](../papers/unitcon/MECHANISM_COMPARISON_20261021.md),
[RTED](../papers/rted/MECHANISM_COMPARISON_20261021.md).

Supplementary checks, không claim đọc full audit ngang bốn bài:

- [DPIAgent](../papers/dpiagent-divide-protocol-isolate-for-agentic-reproduction-test-generation-7122a47a/public_evidence/paper_fulltext.txt),
  §3.2–3.3: structured diagnosis/test-plan handoff đã có. Không lấy việc có intermediate card làm novelty.
- [AnyPoC v2](https://arxiv.org/html/2604.11950v2), §IV và saved audit:
  candidate-report fact checking, execution và independent validation đã có.
  Không lấy việc bác bỏ hypothesis sai làm novelty riêng. Không trộn số liệu v1/v2.
- [Alhazen](../papers/alhazen-2020/READING_20261021.md): active generation để
  strengthen/refute hypotheses là prior work trước LLM.
- [Mokav](../papers/mokav/READING_20261021.md): difference-exposing inputs dùng
  paired execution feedback đã có, nhưng hai executable programs là assumption khác.

Đây là focused comparison, không phải exhaustive novelty clearance. Không thay count
74/500 của audit cũ; không kiểm tra lại toàn bộ corpus hoặc mọi paper năm 2026.

## 3. Những contribution không còn bảo vệ được ở mức chung

| Claim dự kiến | Verdict |
|---|---|
| Chia spec/code understanding → hypothesis → test thành stages | Đã overlap ReProAgent/RTED/DPIAgent và repo v21–v23 |
| Dùng structural/semantic evidence để rank fault mechanisms | Đã overlap KITE; repo v7/v31 và ranking trials |
| Fault type → trigger/input recipe | Đã overlap KITE/RTED/UnitCon; đổi representation sang template chưa đủ |
| Dùng runtime feedback để sửa hypothesis | Đã overlap ReProAgent/Alhazen/AnyPoC |
| Tạo input phân biệt behaviors/hypotheses | Đã overlap active testing/Mokav; không được claim first |
| Tool replay, CFG, executable predicates | Đã có prior work và nhiều repo versions; là infrastructure |

Không có public source, khác language/model, hoặc chạy trên benchmark khác không
tự tạo methodological novelty. Khác input assumptions có giá trị nếu method xử lý
được khó khăn mới đó bằng evidence, không chỉ đổi tên setting.

## 4. Repo đã thử gì: không tái đề xuất dưới tên mới

| Prior implementation | Kết quả cần giữ khi refine |
|---|---|
| v7/v11, v13 | Grounded facts/witnesses và hypothesis-guided generation đã có; fair v11 chưa cho concept gain rõ, v13 thua flat/toolinput |
| v18/v19 | Candidate selection chưa hơn rule; generation không gain. v19 audit thiếu connected semantic grounding |
| v20 | Narrow multiplicity/provenance CPU mechanism; không general flow/FSM reasoning |
| v21_qwenchain/v22/v23 | Semantic extraction/alignment/hypothesis đã triển khai; có interface và semantic failures, chưa concept gain |
| v21_flowtools/v30 | Tools và contract repair đã có; v30 CPU checks không chứng minh online reasoning |
| v24/v25/v32_scope_support | Executable obligation/support; có useful inputs bị gate loại. Unknown support không đồng nghĩa không thể search |
| v26–v28 | Oracle model capability có tác động; mạnh hơn không tự tạo concept advantage |
| v32_qwenchain/v33 | v33 value-equality sensitivity chain8/direct25; 17 direct-only gồm11 terminal decisions,5 mechanical failures,1 search miss |
| v31/v34/v35 | v34 không qua registered FA rule;5/8 wins không có exposing concept input. v35 conditional ceiling14/33 không qua gate17 |
| v36 | Code+CFG không giúp localization; bug-revealing inputs2–3/33, nhiều invalid inputs |
| v37–v39 | Mutant/spec-program routes no-go hoặc contamination. Không mặc định có clean executable alternative để dùng DET |
| v40 | Đã thiết kế/triển khai diagnostic selective revision, concept-adaptive/generic-adaptive/committed controls; không tuyên bố kết quả khi run đang chưa có final report |
| v41 | Final CPU no-go: sampled pool22/33 có exposure, relation package11/33, median lift0.38; không dùng minority anomaly làm concept oracle |

Nguồn: [failure attribution](../../../trickcatcher_linefacts/analysis/recent_concept_failure_attribution_20261020.md),
[v40 design](../../../trickcatcher_linefacts/analysis/astra_concept_design_20261020/DESIGN.md),
[v41 protocol](../../../trickcatcher_linefacts/analysis/v41_iorel/PREREG.md),
[v41 results](../../../trickcatcher_linefacts/analysis/v41_iorel/RESULTS.md),
[v35](../../../trickcatcher_linefacts/analysis/v35_concept_ceiling/RESULTS.md),
[v36](../../../trickcatcher_linefacts/analysis/v36_llm_localize/RESULTS.md), memory index và version reports.
Các cohorts/model/harness khác nhau không được pool thành một cross-version effect.

## 5. Đề xuất cụ thể

Research question: **Trên cùng raw execution evidence và budget, một reusable
semantic concept được bind đúng có giúp LLM phân biệt observed violation với valid
behavior, chọn next input contrast hữu ích và sửa hypothesis chính xác hơn generic
exploration không?**

Đây là refinement của v24/v26 (obligation/property validation), v40 (revision/query)
và learning từ v41 (pool/selection). Không gọi chuyển concept sang oracle là ý mới:
v26 đã thử, còn v27/v28 đã cho thấy model/prompt và ceiling làm thay đổi kết quả.
Observed pool cung cấp factual behavior; normative relation cung cấp câu hỏi cần
đánh giá. Anomaly hoặc model disagreement tự nó không phải violation.

Concept = relation có semantics, domain và output projection, ví dụ occurrence
conservation hoặc membership inclusion. “Duplicate”, “boundary”, “empty” chỉ là
input dimensions nếu chưa gắn với relation. Instance phải có spec binding và finite
measured gap/contrast; gap được tính bằng execution hoặc measurement có provenance.
Concept tag hoặc source paraphrase không tự thêm empirical information.

### Cơ chế tối thiểu

1. Bind một relation vào requirement; giữ normative unknown khi spec thiếu.
2. Đề xuất falsifiable implementation hypothesis; phân biệt requirement với actual behavior.
3. Đọc raw observations và đo contrast/gap còn thiếu. Tool không trả private expected output.
4. Chọn query, ghi prediction và observation nào sẽ bác bỏ claim **trước execution**.
5. Chạy PUT; giữ/revise/withdraw hypothesis trong finite scope; chọn next input.
6. Giữ những observed/candidate inputs liên quan dù hypothesis bị bác bỏ; evaluator
   độc lập chấm bug, domain validity và assertion. Không discard toàn pool theo một
   anomaly heuristic hoặc một uncertain binding.

Không bắt mọi task đi qua global semantic gate. Tools kiểm tra syntax, domain/resource
limits và concrete behavior; LLM chịu trách nhiệm semantic binding/reasoning. Unknown
không cấm bounded generic exploration. Relation cần thiết chưa chắc là complete oracle.

Điểm có thể trở thành contribution là **định nghĩa và kiểm tra tác dụng của semantic
relations lên behavioral judgments và experimental choices khi binding/hypothesis có thể sai**. Đây là claim
hẹp hơn “agent biết hypothesis testing”. Chưa chứng minh literature chưa có đúng
combination này, chưa đủ để viết claim “first”.

### Ví dụ reasoning, không phải paper simulation

Giả sử spec yêu cầu giữ mọi eligible occurrence. Có hai fallible hypotheses:
H1 bỏ duplicate; H2 chỉ giữ phần tử ở zero-based even positions. Với mọi phần tử
đều eligible, query có thể tách hai predicted behaviors:

| Input | Spec length | H1 predicted length | H2 predicted length |
|---|---:|---:|---:|
| `[2,2,3,4]` |4|3|2|
| `[2,3,4,5]` |4|4|2|

Concept occurrence conservation chỉ ra contrast multiplicity. Execution quan sát
được giúp kiểm tra implementation hypotheses; spec mới quyết định length nào là
đúng. H1/H2 đều có thể sai. Một local `set` không chứng minh loss tới return.
Đây là minh họa thiết kế, không là experiment/result mới hay code mô phỏng paper.

## 6. Chốt experiment và go/no-go

**Bước quyết định trước mắt là existing v40 D1, không mở thêm run trong task đọc này.**
D1 đã có supplied correct/wrong/ambiguous bindings, predictions, raw feedback và
concept-adaptive/generic-adaptive/committed-query controls. Giữ nguyên frozen protocol.
Không giả D1 đo extraction tự động, generalization hay pure concept semantics:
concept packet hiện bundle semantics, binding và measured-gap summary.

Khi có final outputs, đọc đủ trajectory theo các questions sau:

- Model có bác bỏ premise/hypothesis sai và giữ hypothesis đúng khi feedback không bác bỏ nó?
- Query có nhắm contrast cụ thể, prediction có chính xác, next query có thay đổi đúng vì evidence?
- Có input mới expose bug ngoài supplied/shared witnesses? Báo witness-only floor riêng.
- Concept-adaptive có incremental discoveries và không tăng unsupported bug claims so generic?
- Adaptive có evidence-linked benefit so committed khi thật sự có unresolved opportunity?

Áp dụng nguyên gates đã đăng ký ở D1; không đổi threshold theo output. Transport
failure là unmeasured semantic result, không phải no-go của concept. Protocol valid
nhưng không có incremental signal thì dừng refinement này; không tăng K/n để cứu.
Ceiling hoặc không đủ revision opportunities thì kết luận inconclusive, không tự
thêm fixtures cho đến khi thắng.

**Chỉ nếu có mechanism signal**, candidate tiếp theo mới là extraction/transfer và
isolation study. Có thể freeze một sampled execution pool để nghiên cứu judgement/
selection trước, rồi query thêm khi model còn uncertainty. v41's22/33 là evaluation-only
opportunity bound của pool cụ thể, không cấp gold filtering vào guidance. Không coi
pool đó là fresh held-out hoặc cho model private exposing-input labels. Trước khi
model run cần đăng ký riêng, không được tự launch từ đề xuất:

| Control | Semantics/binding packet | Computed gap summary | Raw observations |
|---|---|---|---|
| Generic adaptive | Không | Không | Giống nhau |
| Semantic relation | Có | Không | Giống nhau |
| Gap summary | Không | Có | Giống nhau |
| Combined | Có | Có | Giống nhau |

Controls này phân biệt contribution của semantics với computational abstraction.
Gap summary phải giữ toàn bộ thông tin hành vi cần thiết nhưng không cấp normative
verdict ngầm; nếu không tách được hai yếu tố, chỉ claim hiệu quả của combined package.
Equal maxima chưa phải actual token parity; report actual cost, input count, invalid
input rate, unsupported claims, bug discoveries và FA ở đơn vị đăng ký trước. D1
committed control trả lời adaptation riêng; không cần launch mọi control cùng lúc.

Automatic binding phải được chấm độc lập trước search, gồm unknown/unsupported
cases. Không dùng gold để chọn concept trong claimed automatic arm. Human supplied
binding chỉ là diagnostic condition. Ground-truth reference/fixed execution chỉ thuộc
evaluator; PUT replay không tự giải oracle problem. Report input reach, selected-input
yield và assertion soundness riêng với oracle chung, không trộn các bottlenecks.
v41 validity53% của sampled inputs là hạn chế thật;22/33 không chứng minh sampling
giải được mọi task/domain.

HumanEval/MBPP không đủ để khẳng định transfer vì contamination đã quan sát. Các
VibePass/dev cohorts đã dùng không trở lại thành fresh held-out. Chưa chọn benchmark
run mới trước mechanism go; không chi thêm API để cứu các borderline results.

## 7. Vai trò của các paper và kết luận cuối

- ReProAgent là comparison gần nhất về architecture; có thể dùng author implementation
  nếu sau này đổi sang SWT-Bench, giữ same setting/model/tool budget. Không coi port
  vào function-level task là exact reproduction baseline.
- KITE là novelty comparator quan trọng nhất cho mechanism knowledge và executable feedback;
  thiếu correct code/KB là trở ngại thật của việc dùng nó trong setting hiện tại.
- UnitCon là reference cho explicit condition-guided search; dùng original Java artifact
  nếu nghiên cứu target exceptions, không tự dựng Python clone.
- RTED là candidate thực tế nếu chọn narrow Python TypeError thesis; proposal
  general functional concepts cần chứng minh thêm, không lấy TypeError result thay thế.

**Final verdict:** có lý do để hoàn tất/audit mechanism diagnostic đã có về
concept-guided adaptive testing. Chưa có evidence để promote một combined pipeline,
chưa xác lập novelty, và không ưu tiên mở rộng fault-template hay semantic hard-gated
chain. Kết quả của lượt đọc này là contribution boundary và một quyết định có điều
kiện rõ ràng; không phải claimed experimental improvement.
