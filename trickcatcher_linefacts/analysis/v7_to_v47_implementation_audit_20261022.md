# Audit v7 → v47: đã thử gì, implementation sát đến đâu?

Ngày 2026-10-22; snapshot source `fd7c45b`, kiểm tra artifacts khoảng 14:54–14:57 UTC.
Đánh giá từ source, preregistration, reports và saved artifacts. Các số lịch sử bên dưới được đối chiếu giữa reports;
không chạy lại toàn bộ experiments. Chỉ chạy CPU probes nhỏ trên các hàm của chính repo, không gọi model, PUT,
canonical hay paid API; không sửa pipeline, frozen output hoặc vendor. Đây không phải audit từng dòng của mọi copy.

## Kết luận

**Đã khảo sát nhiều cơ chế, nhưng chưa có một implementation vừa nối đủ semantic reasoning chain, vừa tổng quát,
vừa chứng minh concept giúp thêm dưới controls phù hợp.** Phần v7/v11 có pipeline chạy thật và fairness audit hữu ích.
Nhiều nhánh sau đó là diagnostics có phạm vi hẹp, với các mức độ hoàn thành khác nhau.

- **Sát ý tưởng:** v7 sát cơ chế coverage/mutation/input-class facts → witnesses → generation. Các ý tưởng mạnh hơn
  như spec obligation → implementation effect → propagated mismatch → discriminating input → hypothesis revision
  chỉ được thực hiện từng phần ở các nhánh khác nhau.
- **Tổng quát:** có operators/templates dùng lại được, nhưng chưa có bằng chứng transfer cho semantic mechanism.
  Taxonomy, expression grammar, Python subset và input domains vẫn hẹp; fixture success không thay thế kiểm chứng
  trên tasks chưa dùng để thiết kế.
- **Hoàn thiện:** hạ tầng khá kỹ ở nhiều nhánh, song lỗi interface và gate đã loại output đúng; một nhánh còn từng
  leak reference. V46/v47 có implementation và partial generation, chưa có final score tại snapshot này.
- **Hiệu quả:** chưa chứng minh rõ phần explicit concept content thắng plain, matched placebo và toolinput.
  Không nên chuyển kết luận đó thành “mọi loại concept đều vô ích”. Toolinput cũng dùng witnesses từ concept facts.

## 1. Các hướng đã thử

Các số trong mỗi hàng chỉ so trong cohort/protocol tương ứng. Dev113, pilot20, authored fixtures và VibePass33 không
phải cùng benchmark; input discrepancy, correct assertion và binding success không phải cùng metric.

| Nhánh | Cơ chế đã thực hiện | Kết quả và giới hạn |
|---|---|---|
| v7 → v8-strict → v11_fair | Code facts + spec input classes; round 1; Hypothesis nhắm missed hints ở round 2; strict giữ selected inputs; cân bằng control requests | v7 ban đầu concept-hybrid 67.0 bug/run. V11 strict/fair: concept 61.0, plain-hybrid 55.7, placebo 57.7, toolinput 64.3; chưa thắng rõ ba controls. |
| v7_mutref + ranking audits | Xếp hint theo fault hypothesis và agreement với spec-only reference programs | Ranking offline có tín hiệu; chạy generation trên odd-dev không tạo gain rõ, 13 wins/10 losses với luật cũ. Không promote. |
| CrossHair gap probe | Symbolic search cho gaps fuzz/Hypothesis chưa tới | Không thêm bug; nhiều timeouts, một phần witnesses ngoài contract. Đây là bounded gap experiment, không phải complete symbolic execution. |
| v9_callfb | Thay Hypothesis strategies bằng concrete calls + feedback | Concept-hybrid 51.3 so với v8-strict 61.0; chỉ 2.4% proposed valid-ish calls hit hint. Strategy construction phù hợp hơn literal construction ở run này. |
| v10_spechint | Đào behavioral requirements và activation domain từ spec | Chỉ thêm 7 hints/5 tasks; odd-dev good@3 không tăng; không chạy generation. |
| v12_rel / B3 | Gắn quan hệ giữa facts và spec/code; so với flat facts | Dev rel 63.33 vs flat 62.33; primary 16–15, p=1. Chưa chứng minh quan hệ giúp thêm. |
| v13_hyp / B4 | LLM fault hypotheses + witnesses + targeted generation | Dev hyp 46.33 vs flat 62.67/toolinput 63.00. Hypothesis/control actual requests khác nhau; matched-input analysis vẫn bất lợi cho hyp. |
| v14_obgraph, v15_mrconcept; Python-format copies | Grounded obligation paths, conditional metamorphic relations | Original: 0 accepted cards, chưa tạo usable treatment. Repaired: graph chỉ 3/20 tasks có cards; MR 16/20 nhưng MR/blind đều 5/20 D_IO, ba property reports đều FA. |
| v16_behavior | AST/control graph + finite observed states + generated semantic DSL | Representation gate 17/20; live concept gate 0/20. Unsupported DSL operators/IDs và grounding chặn generation; D_IO chưa đo. |
| v17_templates | Thay generated expressions bằng 9 executable semantic templates | Concept gate 2/20, dừng trước generation. Synthetic selection probe 6/6 nhưng parameter synthesis đủ semantics+schema chỉ 1/6. |
| v18_modelselect | Tool enumerate/base-filter candidate models; LLM chọn model ID | Sample-consistent requirement: LLM 11/20 vs lexical rule 12/20, random expectation 9.17. Có 119 confirmed discrepancy events/12 tasks; không phải 119 bugs hay end-to-end D_IO. |
| v19_rulegen | Rule-selected model/fault cards + pseudocode → Hypothesis strategy | Concept/behavior/plain đều 3/20, toolinput 4, witness-only 13. Nhiều strategy replies bị parser reject; source audit còn thấy missing semantic/source links. |
| v20_groundedflow_domainfix | Ground multiplicity loss qua exact set operation và transport tới return | Narrow CPU increment: support 1/20 known tasks; 35/35 authored expectations. Chưa có reviewed real-task obligation, model run hoặc D_IO. |
| v21_flowtools → v30 contract repair | Hypothesis + inspect_flow/data/replay/check_path tools | Qwen pilot chỉ 1–4/20 confirmed, nhiều FA; model chủ yếu inspect_flow, không replay/check_path ở pilot. V30 sửa tool contracts ở CPU; không có gain run mới. |
| v21_qwenchain → v22 | Five stages: spec concept, code behavior, alignment/hypothesis, input, revision | Controlled pilots chủ yếu fail upstream IDs/schema/semantics; v22 có 6 S4 inputs nhưng 0 S5 final. Không phải completed benchmark comparison. |
| v23_concepthyp | So concept/direct/hyp-only trên controlled16 | Qwen cả ba chỉ 2/7 buggy cases có correct assertions; dù JSON schema valid, triggers/expected values còn sai. Luna retest C/D/H = 5/7, 7/7, 5/7; một phần losses là serialization. |
| v24_obligations, v25_interface_gate → v32_scope_support | Executable obligations/trigger checks, split-output interface, comprehension-scope/support repair | Qwen v24 contracts 0/9, generation 0/54. Luna v24 selected verified 1/3 vs text/toolinput/witness 3/3; v25 false reject legal comprehension scopes. V32 sửa scope nhưng fresh diagnostic vẫn block trigger interface; chưa chứng minh gain. |
| v26_proporacle → v27_codexoracle | Exact expected vs property/MR oracle; model × prompt diagnostic | Qwen property/MR precision .15/.18, thấp hơn exact .21. Luna strict property pilot precision 1.00, nhưng không tự chứng minh concept-guided input gain hay generalization. |
| v28_codexflow | Full tool-less Luna pipeline | Pilot mọi arms 16–17/20, FA 0–3: ceiling/no concept gain. |
| v29_vibepass | Port strong-model pipeline sang 66 VibePass PUTs | **INVALID:** prompt dùng `_plus.test` chứa evaluator/reference. Không dùng số này để kết luận effectiveness. Later v31-derived loaders dùng public test file riêng. |
| v31_faulttemplate → v34_ftplacebo → v35 ceiling | Fault types từ surviving mutants + input templates; same-input placebo; CPU ceiling | v31 18 vs plain15/33, 4–1, yếu. V34 18 vs placebo12, 8–2 nhưng FA27>23 nên không đạt rule; 5/8 wins không có exposing concept input. V35 pool chỉ expose17/33; mutant/reference ceiling14<17, stop package này. |
| v32_qwenchain_or30 → v33_lunachain30 | Chạy chain trên 30 real dev tasks; Luna chain vs direct cùng maximum budgets | Qwen final-S5 0/30 do interface. Luna any-stage value-unequal detection chain8 vs direct25; chain-only0, direct-only17. Actual budgets/output coverage khác nhau do gates. |
| v36_llm_localize | Qwen32B code vs code+CFG localization/input proposal | Hit@3 6/14 cả hai; revealing inputs 3 vs 2/33. CFG-supported19/33; không thấy CFG thêm giá trị. |
| v37_mokav_gate → v38/v39 spec alternatives | Ceiling: surviving mutants hoặc spec-derived programs có làm useful alternative không? | V37 correcting mutant3/20, no-go. V38 HumanEval programs gần hết trùng canonical về behavior, không tách được correctness khỏi memorization. V39 VibePass C'=12/33, H'=2, consensus precision .77; no-go, chưa chạy full DET search. |
| v40_concept_agent | Supplied concept/binding/gap + fallible hypothesis + adaptive tools; generic/committed controls | 8 seen authored fixtures: mọi arm reveal6/6 bugs, cùng4/4 new task discoveries ngoài supplied revealing rows; 0 concept-only wins. CA retain đúng H ở E2/E4 fail; E3 binding sai; E6 đọc sai dedup evidence. |
| v41_iorel | Sampled I/O metamorphic minorities → selected relation questions | Pool expose22/33 nhưng package chỉ11/33, median lift .38; no-go. Sampling có inputs tốt nhưng selection/oracle chưa nhận đúng. |
| v42_mutoracle | Mutant disagreements trên larger sampled pool → oracle questions | D1 package15/33, uncapped19; median lift .62. Nhiều questions PUT-right; no-go cho selection policy này. |
| v43_concept_identify | Model đề xuất bindings trong 7 concepts/17 operators; tools compare saved rows/contrast/return reads | Complete binding+judgment raw1/8 vs tool2/8, one win. Initial all-or-nothing schema block E1/E3/E6; final chỉ được chọn IDs cũ. Không phải active input search hay full binding repair. |
| Concept-binding ablation | Bỏ allowed_outcome hoặc whole concept packet ở v40 E4 T2 | 6 calls/2 contexts; allowed_outcome removal không đổi; whole-packet effect mixed → inconclusive. Không kết luận single binding field gây semantic failure. |
| v44_concept_matrix | 6 kinds × tool methods: class, boundary, coverage, mutants, MR, property | Input union21/33 vs random21.36, no-go. Nhưng perfect class instance20 vs random instance10.1: selection accuracy vẫn là signal chưa được hiện thực hóa. |
| v45_mutjudge (cũ mang số v43) | Direct in-head A/B/neither/unsure judge trên 607 questions | Concept1/15, precision .08; prompt 300 tokens và unsure exit. Audit xác nhận **không dùng pipeline program oracle**, nên không đóng toàn bộ oracle direction. |
| v46_mutoracle_fixed | Program oracles: DPP reuse, 10 TC variants, TC+concept; repaired direct judge | Source/prereg + partial artifacts; chưa score. Đã bổ sung program filtering/voting và named calls, larger judge budget. Chưa có evidence effectiveness. |
| v47_concept_select (đăng ký ban đầu là v46) | Thêm spec_range/value_biased generators; LLM chọn top3 từ menu6 input kinds; random/perfect/kind controls | Có prepared33, 0 recorded preparation case/kind errors; partial calls, chưa score. Part A exploratory vì design sau khi xem hidden inputs của cùng tasks. Chưa có transfer hoặc end-to-end oracle result. |

Nguồn số liệu: [RESULTS](../RESULTS.md), [v11 report](final_protocol_v11_dev.md), các reports được dẫn trong phần dưới
và `analysis/v*_results.md`, `analysis/v*/RESULTS.md`. Hai nhánh cùng số v21/v32 là experiments khác nhau; số lớn hơn
không có nghĩa kế thừa và sửa hết lỗi của nhánh trước.

## 2. Những phần implementation chưa sát cơ chế được mong muốn

### 2.1 “Concept” hiện có nhiều vai trò khác nhau

V7 fact là coverage gap/mutation/input class; v18 concept là candidate executable model; v23 là abstraction trong
prompt; v40 là supplied normative relation; v43 là fixed-vocabulary binding; v47 là menu item của input generator.
Các representation này có điểm chung nhưng không thể gộp mọi result thành một phép thử duy nhất của “concept”.

Source [v7/spec_facts.py](../pipelines/v7/spec_facts.py) có bốn classes LARGE/DUP/NONASCII/SPACE, fixed transformations
và mined validator. Đây là useful input classes, chưa phải general semantic spec extraction. `facts.pick()` trong
[v7/facts.py](../pipelines/v7/facts.py) dùng kind priorities, witnessed-only filtering và diversification, không phải
semantic bug-likelihood estimator. Do đó coverage fact đúng chưa có nghĩa fault hypothesis đúng.

### 2.2 Source/behavior artifacts chưa bảo đảm reasoning thật sự dùng chúng

[V19 audit](v19_flow_audit.md) cho thấy cả29 concept-bearing slots có `block_ids=[]`; observed FSM không vào guidance;
cards không có precise template definitions; activation chỉ log sau random input selection. Case149 mất duplicate
qua `set`, nhưng fixed first3 fault list còn bỏ đúng distinct mutation. Đây là missing mechanism, không chỉ poor prompt.

[V20](v20_cpu_results.md) thực hiện source→loss→return tốt hơn nhưng chỉ support exact direct-input multiplicity
subset, một known task. Không thể cộng breadth v19 với depth v20 để coi đã có general behavior engine.

[V21 saved-data audit](v21_failure_audit/REPORT.md) xác nhận pilot40 actions có16 interface errors; 38 actions là
inspect_flow, 0 replay/check_path; không có structured hypothesis revision. Đây chưa phải successful adaptive
hypothesis-discrimination experiment. V30 là CPU contract repair, chưa có efficacy result thay thế v21.

### 2.3 Interface/gates đã có false negatives thực tế

[Luna retest](luna_versions_continue_20261019/REPORT.md): legal reuse của comprehension variable bị coi là mutation;
raw correct hypotheses bị JSON rejection; v24 generated đúng f06 discriminator nhưng frozen prep support gate vẫn
discard. V32_scope_support sửa một phần, không sửa ngược các historical branches.

[V33](v33_lunachain30_results.md): 6 rejects do >12 valid source refs mà prompt không nói rõ cap. Tuy nhiên cứu riêng
7 blocked tasks cũng chỉ có bound15 detections, vẫn dưới direct25; không quy toàn bộ loss cho parser.

[V43 source](../pipelines/v43_concept_identify/identify.py): schema final chỉ có `selected`, không có replacement
binding; `validate_selection()` cấm IDs ngoài initial pool. E2 nhận ra cần count_ge nhưng không thể tạo nó. Một
unrelated malformed candidate làm initial proposal fail cả case; E3 đúng subset binding vẫn không có final.
[Report](v43_concept_identify_20261021/REPORT.md) đã ghi nhận những giới hạn này. Đây là selection/retention diagnostic,
chưa phải full concept identification + repair loop.

### 2.4 Tool evidence chưa phải spec truth hoặc causal proof

[V43 identify_tools](../pipelines/v43_concept_identify/identify_tools.py) tự ghi return_dependencies chỉ là partial
return-expression/top-level-assignment read inventory, bỏ guards/aliases/side effects/nested scopes. Contrast chọn
saved pairs đổi một argument, không bảo đảm một semantic dimension. Không được diễn giải thành dynamic value slice
hoặc controlled intervention. Observed relation holds chỉ cho biết relation hợp PUT trên finite rows.

[V40 report](v40_retry3_20261021/REPORT.md) có cả useful revealing inputs lẫn wrong hypothesis retention. Sinh được
input lộ bug không chứng minh model hiểu đúng mechanism. E8 ambiguous spec cho thấy cần giữ unknown; thêm I/O
samples không xác định được normative eligibility bị thiếu trong spec.

## 3. Độ tổng quát và độ tin cậy của kết luận

1. **Input domain còn được suy từ public examples.** `iorel.strategy_for()` giữ positive/nonnegative range khi public
   values đều như vậy, strings chỉ dùng observed alphabet, độ dài thường cap30. Đó là sampling heuristic, không phải
   specification domain. V47 mở thêm numeric range/repeated values nhưng không tự giải các dạng structure/state/API.
2. **Hand-authored vocabulary/templates không tự là overfit**, nhưng cần công bố supported subset và đo transfer.
   V40 cấp sẵn concepts trên8 seen fixtures; v43 vocabulary thiết kế theo fixtures đó; chưa đo open concept discovery.
3. **VibePass33 đã trở thành development cohort.** Nhiều lần chọn phương pháp/threshold theo nó. V47 Part A còn có
   explicit hidden-input-informed design; preregistration sau đó giúp giữ trung thực quá trình, không biến cohort thành
   fresh held-out. Không gọi performance trên cùng33 là generalization evidence.
4. **Fairness cần theo đúng resource.** V11 concept không thắng matched placebo/toolinput; baseline ACH/CoverUp có
   yield rất thấp. Trong equal-input contrast, TC-full còn hơn concept-hybrid khoảng43.0 vs29.8. Không dùng bảng raw
   “beats five baselines” để suy ra concept advantage hoặc đồng ngân sách. Witness-only zero generation calls vẫn
   dùng preprocessing/oracle, không phải zero total cost.
5. **Không có một bottleneck đúng cho mọi cohort.** V35 pool reach17/33 là bottleneck của templates; v41 broader pool
   reaches22/33 nên recognition/selection quan trọng hơn; v40 fixtures mọi arm reaches6/6 nhưng interpretation fail.
   Không nên đóng một hướng dựa trên bottleneck của một sampler/model khác.
6. **Negative gate có phạm vi.** V34 có directional8–2 nhưng FA rule fail và attribution yếu. Đúng khi không promote;
   quá mạnh nếu nói “concept content không có signal”. V44 perfect instance20 vs random10.1 cũng là selection signal,
   chưa phải achieved LLM performance. V45 không đo program oracle, v46 đang sửa instrument đó.

## 4. CPU probes mới: giới hạn trong code mới nhất

Các probes dùng AST-extracted functions từ source thật, chỉ stdlib, không import runner hay execute generated code.
Không thay source/score. Đây là counterexamples về generality; **chưa chứng minh chúng gây loss trên current33**.

### A. Numeric constraint parser có silent partial parse

[V44 `constraints()`](v44_concept_matrix/matrix.py), được v47 gọi lại ở `prepare_case()`:

```text
constraints('-100 <= nums[i] <= 10**9', ['nums']) -> {(0, 'elem'): (-100, 10)}
constraints('-100 <= nums[i] <= 10^9',  ['nums']) -> {(0, 'elem'): (-100, 1000000000)}
constraints('0 <= len(nums) <= 30', ['nums'])     -> {}
constraints('0 <= nums.length <= 30', ['nums'])  -> {(0, 'length'): (0, 30)}
```

`10**9` bị hiểu thành10 thay vì explicit unsupported. Nếu dùng trên Python-style specs, sinh boundary/range sai dù
pipeline không báo lỗi. Kiểm tra public prompts của current33 không thấy hai dạng Python power/len bounds trên;
không gán historical/current score loss cho counterexample này.

### B. Range expansion dùng maximum của mọi arguments

[V47 `prepare_case()`/`spec_range_members()`](v47_concept_select/select_run.py): pool_max là max absolute integer trên
toàn input, rồi so mọi argument bound với một scalar đó.

```text
xs = [([1,2], 10**9)], constraint arg0 elements in [0,1000], pool_max = 10**9
spec_range_members(...) -> {}
```

Argument thứ hai làm mất expansion cần thiết cho list argument thứ nhất. Đây là lỗi liên kết range giữa arguments,
không phải thiếu budget. Ngoài ra `log_uniform(-100,-1)` luôn trả -1; “full spec range” chỉ đúng cho subset chủ yếu
positive mà hàm hiện hỗ trợ. Chưa audit prevalence của các trường hợp này trên current33.

### C. Menu dedupe phụ thuộc thứ tự inputs

V47 `menu()` dùng `tuple(flagged[:32])` làm key. Hai instances cùng shown input set `[a,b]` và `[b,a]` vẫn tạo2 menu
items, merged0. Preregistration nói dedupe theo flagged set; implementation chưa tương đương set dedupe. Khi xảy ra,
menu capacity/random baseline có thể phụ thuộc ordering. Chưa đo effect trong prepared33, không thay menu giữa run.

### D. Audit caveats cần giữ khi đọc v46/v47

- V46 đã dùng đúng family program-oracle mechanism, nhưng TC vote vẫn bỏ PUT failures theo baseline semantics;
  repaired judge bỏ `expected=None` ở neither branch. Chưa phải general exception/sentinel oracle.
- V47 trả `errors` theo kind trong preparation nhưng final incomplete gate chỉ bắt case-level `error`/score exceptions;
  kind errors có thể không tự ngăn scientific verdict. Current prepared33 có0 case errors và0 kind errors, nên đây là
  latent robustness gap, không phải observed incomplete treatment ở run này.
- V47 ghi prompt_sha256 nhưng cached-call reuse và scorer không verify digest với current prompt. V46 có digest check
  trong generation reuse. Chưa có bằng chứng stale prompt cache trong current run; không khẳng định result sai.
- V46 chưa có score; v47 đang có partial call records, chưa có score. Không chạy scoring trước generation completion
  để tạo verdict cho audit này.

## 5. Tiêu chuẩn còn thiếu để gọi “sát và hoàn thiện”

Không cần thêm v-number chỉ để phối lại các ý đã thử. Một method được claim đầy đủ cần chứng minh các links sau
trên chính treatment đang chạy:

1. Spec-justified obligation với domain, ambiguity và output/exception semantics rõ.
2. Executable concept binding đúng; bad candidate không vô tình xóa good independent candidates.
3. Source effect thực sự ảnh hưởng returned value; unsupported control/dataflow phải được phân loại rõ.
4. Input construction/check xác nhận discriminator giữa hypotheses, không chỉ site reach hoặc local mutant change.
5. Feedback có thể giữ/sửa/rút claim và tạo binding mới khi cần; expected, observed và prediction có roles riêng.
6. Oracle độc lập với PUT đủ chính xác, coverage gồm relevant sentinel/exception cases.
7. So sánh tách concept content khỏi witnesses/input pool/tool feedback/extra calls, với controls đã dùng ở v11/v34.
8. Source/interface issues được xử lý trong copy mới theo protocol; sau đó mới dùng fresh cohort để kiểm tra transfer.

Các links này là tiêu chuẩn review, không phải cam kết rằng nối đủ sẽ tăng score. V40 đã cho thấy kể cả khi
input/tool interface chạy được, evidence interpretation vẫn có thể sai. V46/v47 cần được đánh giá theo đúng registered
diagnostic trước khi cân nhắc method claim rộng hơn.
