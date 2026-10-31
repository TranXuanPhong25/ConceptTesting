# Plan: kiểm tra claim-role confusion trong concept-guided testing

Ngày 2026-10-21. Status: **plan-only; chưa implement hoặc chạy experiment mới**.
User yêu cầu xuất plan sau khi cấp quyền tự quyết research. Deliverable này không
thay đổi frozen v40/v41 hoặc đảo no-go của chúng.

## 1. Câu hỏi và hypothesis

**H_role:** một phần evidence-integration failures xảy ra khi model trộn normative
requirement, predicted implementation behavior và actual execution observation.
Tách rõ ba vai trò này có thể giảm kết luận trái evidence khi giữ nguyên facts.

Hai claim cần kiểm tra riêng:

- **H_mechanism:** role separation cải thiện semantic integration trong diagnostic.
- **H_concept:** trên cùng evidence và role separation, explicit semantic concept
  còn giúp judgement tốt hơn generic control.

H_mechanism đúng không tự chứng minh H_concept hoặc test-generation improvement.
Một schema dễ parse hơn hoặc model chép observation chính xác hơn chưa đủ.

Motivating cases đã biết từ v40 CA: E2 quan sát equality input→0 nhưng cuối nói
implementation dùng `>=`; E4 có native ValueError nhưng withdraw exception hypothesis;
E6 repeated2→2 nhưng withdraw deduplication. Đây là **post-hoc motivating evidence**,
chưa chứng minh cả ba cùng do role confusion. Các gates mới không được gọi là
preregistered trước v40; chỉ phase model mới, nếu có, mới đăng ký prospectively.

## 2. Prior art trong repo và literature

| Đã thử | Kết quả / giới hạn | Phần plan này thực sự kiểm tra |
|---|---|---|
| v20 | Narrow CPU grounding/provenance | Không xây general flow analyzer |
| v21/v22/v23 | Semantic chain/hypotheses chưa cho gain | Không thêm reasoning stages |
| v24/v26/v32 | Obligation/property/support, interface và semantic losses | Không lấy property oracle làm novelty |
| v30 | Tool contract repair | Tái dùng contract nếu cần; contract không giải semantic integration |
| v33 | Chain thua direct, nhiều upstream stops | Không dùng hard semantic admission gate |
| **v40** | CA24/24 accepted; retention E2/E4 và revision E6 fail; concept-only wins0 | V40 **đã có claim.kind, prediction trước execution và evidence IDs**. Chỉ thêm labels là lặp lại. Can thiệp cần tách các facts/predictions ở presentation và final adjudication, không cung cấp gold |
| v41 | Pool22/33 có exposure, relation selector11/33/no-go | Không dùng rarity/anomaly như normative violation |

ReProAgent/RTED có reasoning/validation loops; KITE có mechanism-guided executable
feedback; Alhazen có hypothesis-testing loop. Xem [paper comparison](CONCEPT_GUIDED_PROPOSAL_20261021.md).
Plan này là mechanism diagnosis; chưa claim methodological novelty hoặc thesis contribution.

## 3. Phase A — audit saved trajectories, zero inference

### Material và đơn vị phân tích

- Frozen v40 retry3:8episodes ×3arms ×3turns =72raw responses,24episode-arm rows.
- Đọc spec/source, actual requests, predictions, raw claims và native feedback;
  giữ cả7failed turns. Không chỉ chọn E2/E4/E6 hoặc bỏ correct/ambiguous controls.
- Dùng [terminal report](../../../trickcatcher_linefacts/analysis/v40_retry3_20261021/REPORT.md),
  semantic audits và frozen records làm evidence; không chạy lại PUT/scorer/model.
- Primary unit = episode-arm row. Ghi first error, first **unrecovered** error và
  secondary errors. Claim/observation counts chỉ là descriptive nested counts,
  không coi72turns là72independent samples.

### Rubric

| Label | Định nghĩa | Ví dụ phân biệt |
|---|---|---|
| SPEC | Binding/requirement sai hoặc unsupported | Equality được coi như inclusion |
| PRED | Sai dự đoán PUT trên input cụ thể | Predict4 nhưng native2 |
| OBS | Đọc sai native result/status hoặc scope | Coi exception/output:null là return None |
| ROLE | Đặt required/predicted behavior vào claim về actual implementation, trái observations | E2 final implementation `>=` sau equality→0 |
| FINAL | Đổi stance/polarity hoặc kết luận trái evidence, chưa đủ chứng minh role confusion | Withdraw một true hypothesis nhưng không có replacement normative claim |
| INTERFACE | Schema/action/admission chặn bước tương ứng | Failed committed replacement |
| UNKNOWN | Evidence không đủ phân loại mechanism | Statement mơ hồ về scope hoặc polarity |

Không gán mọi wrong withdrawal thành ROLE. Evidence IDs hợp lệ không chứng minh
claim được support. `keep/revise/withdraw` phải đọc cùng statement/kind; không chấm
từ keyword. Observed output khớp prediction chỉ support prediction trên input đó,
không chứng minh universal hypothesis hoặc spec correctness.

Một ROLE instance đủ evidence phải có: normative relation xác định; actual observation
usable và đúng timing; raw text cho thấy role substitution; có alternative explanations
được xem xét. Ghi explicit rival explanations: polarity-label misuse, scope error,
arithmetic/set reasoning, observation parsing và generic final-answer hallucination.

### Artifacts và review

`labels.csv` có episode/arm/turn/claim, role, first-error fields, evidence paths,
diagnostic eligibility và confidence; `LABEL_GUIDE.md` ghi adjudication rules;
`AUDIT.md` ghi đủ24rows và denominators. Hai người/agents review semantic labels
read-only; disagreement giữ riêng, không ép consensus để qua gate. Có thể dùng
existing audits làm initial annotations, nhưng phải công khai non-blind status.

### Gate A

Chỉ xét B1 nếu có **ít nhất2distinct episodes thuộc ít nhất2semantic relations**
với agreed high-confidence ROLE instances, và phần lớn initially-correct/evidence-
contradicting target rows không bị SPEC/PRED/OBS/INTERFACE upstream giải thích trước.
“Phần lớn” = strictly more than half các eligible target rows, denominator ghi đủ.

Nếu chỉ có một ROLE episode, nhiều UNKNOWN, hoặc FINAL/polarity failures chiếm ưu
thế: **stop H_role như giải thích chính**, ghi đúng failure distribution. Không đổi
rubric/threshold sau khi đọc toàn bộ labels để cứu hypothesis. Gate A là lựa chọn
engineering trên known data, không là significance test hay proof nhân quả.

## 4. Phase B1 — paired final-context diagnostic, chỉ sau Gate A

Question: cùng saved evidence, role separation có sửa semantic contradiction mà
không làm hỏng correct/unknown judgments không?

Material: **toàn bộ8CA final-turn contexts**, không chỉ failure cases. Hai arms:

1. **Replay control:** nguyên context và final instruction/output contract của v40.
2. **Separated roles:** cùng source/spec/initialH/history/observations, trình bày
   final adjudication theo ba sections: spec-derived requirement, predicted PUT
   behavior, observed execution; sau đó mới kết luận implementation/mismatch.

Model vẫn tự diễn giải requirement và đánh giá hypothesis. Controller chỉ render
facts từ saved record, không điền correct binding, expected output, support/refute
verdict hoặc reviewer labels. Cả hai arms thấy cùng literal/status/evidence IDs và
chronology. Exception có `status`, `exception_type`, `output` tách biệt trong cả hai.
Treatment không được sửa một malformed observation mà control vẫn nhận bản lỗi.

Predictions là original model predictions, không post-hoc sửa cho khớp native result.
Không thêm tools/replays hoặc sampled inputs; không phát sinh native execution.
Model quyết định `keep/revise/withdraw/unknown` như cũ. B1 là presentation/output-
organization **package**; không claim isolate riêng một field hay cognitive mechanism.

Original v40 đã có role fields. Nếu renderer không tạo được can thiệp cụ thể ngoài
đổi tên `kind`, dừng trước model calls vì không có distinct treatment.

### Metrics và Gate B1

- Primary: episode có final implementation/normative judgment đúng và không trái
  usable evidence. Human rubric độc lập chấm content, không chỉ echo accuracy.
- Report theo eligible ROLE subset, toàn8episodes, từng relation và control outcome.
- Separate observation recall, normative interpretation, implementation judgment,
  stance consistency, schema validity; không cộng thành opaque score.
- **GO:** sửa đúng ít nhất2eligible episodes mà paired replay control vẫn sai;
  zero regressions trên previously correct judgments; E7 không false bug flag;
  E8 giữ ambiguity; final valid8/8 ở treatment.
- Nếu replay control tự sửa hết target failures: reproduction/ceiling-limited,
  **chưa có causal signal**, không credit treatment win từ historical v40.
- Nếu chỉ chép đúng observation nhưng judgement vẫn sai: no-go. Không extra repair
  turn, prompt retry, model swap hoặc tăng repetitions để qua gate.

Gate này chỉ support khả năng giữ đúng semantic roles trên seen cases; chưa đo
input discovery hoặc incremental concept benefit.

## 5. Phase B2 — isolate concept value, chỉ sau B1 signal

Fresh contexts từ cùng8episodes; common evidence panel deterministic/frozen từ saved
native observations. Cả bốn arms thấy cùng original spec/source, fallible initialH,
same raw outcomes và same generic task. Không đưa prior model claims có concept
content vào generic history. Không dùng reference exposure labels để select panel.
Full-source derivation và public projection phải được review trước calls.

| Arm | Explicit concept/binding/gap packet | Role-separated adjudication |
|---|---|---|
| G | Không | Không |
| G+R | Không | Có |
| C | Có, giữ fallibility như v40 | Không |
| C+R | Cùng packet như C | Có |

Packet là bundled treatment; chưa isolate concept semantics khỏi binding/gap summary.
Raw evidence đều như nhau; mọi factual gap phải recompute được từ panel và không
chứa gold bug verdict. Supplied concepts chỉ là diagnostic, không automatic extraction.

Primary comparison: C+R vs G+R. **GO cho nghiên cứu concept tiếp** chỉ khi ít nhất
2episode-level semantic wins,0opposite losses, không tăng false bug claims; E7/E8
controls đúng. C+R vs C đánh giá role organization riêng. Đây là engineering signal,
không statistical efficacy claim. Generic ngang concept = không incremental concept
signal; đóng hướng này. Không lấy số valid JSON hoặc input đã có sẵn thay semantic wins.

Tất cả observations ở B2 đều đã supplied. B2 **không đo new input discovery** và
không đủ để claim test-generation improvement. Chỉ nếu passes mới có cơ sở lập
plan transfer/input-search riêng; không tự launch từ plan này.

## 6. Budget, integrity và implementation boundary

- A:0model/0native executions. B1 tối đa16completions; B2 tối đa32; combined<=48.
- Same requested Qwen2.5-Coder32B/temperature0/top_p1 như v40; metadata không phải
  proof actual weights. Không fallback sang model/API khác để hoàn tất slots.
- Giữ context8192; input<=6144/output<=1536 nếu transport enforce được. Maximum
  inference tokens:294,912input +73,728output cho48slots. Đây là ceilings, không cost estimate.
- Preflight tokenizer kiểm tra cả hai/all arms; không silently truncate history.
  Packet không fit thì stop readiness, không đọc outputs rồi mới giảm evidence.
- No content/transport retry; unknown usage được giữ riêng, invalid vẫn consume slot.
  Quota remaining<=15% thì stop theo standing rule. Default local endpoint; không
  phát sinh paid fallback từ plan này.
- Nếu implementation: fresh folder từ best-v7 + explicitly hashed ports cần thiết,
  `CHANGELOG.md`; dùng stdlib cho JSON/CSV/hash/render. Không sửa frozen parents hoặc
  vendor/source paper. Không cần training, symbolic engine hay external agent framework.
- Freeze input corpus, rubric, arm rendering/order, source/config/deps và budget
  trước calls. Register B1/B2 prospectively riêng; B2 không tự chạy chỉ vì B1 complete.
- Sau implementation, independent read-only review về correctness/practicality,
  library use và plan adherence; áp must-fixes bằng PREREG amendment trước outcome.
  Reviewer không thấy future labels/results trong prompt builder. Kiểm tra leakage,
  role-preserving render và case/arm coverage bằng CPU trước model calls.

## 7. Deliverables và quyết định cuối

| Phase | Deliverable | Nếu fail |
|---|---|---|
| A |24row audit, labels, rival-mechanism analysis, Gate A verdict | Dừng role-confusion hypothesis |
| B1 |16saved responses, blinded/content review, paired outcomes/costs | Dừng representation package |
| B2 |32saved responses, factorial table, concept attribution verdict | Không promote concept method |

Kết quả tốt nhất ở đây là evidence cho một mechanism cụ thể và incremental concept
signal trên diagnostic. Kết quả âm cũng hoàn thành plan; không chuyển thành thêm
dataset/K để salvage. Scientific no-go của v40/v41 và literature-overlap assessment
vẫn giữ nguyên. **Lượt xuất plan này chỉ tạo tài liệu, chưa thực hiện A/B hoặc spend.**
