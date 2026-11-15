# Kế hoạch arm Equivalence Partitioning, BVA và Decision Table

Cập nhật: 09/11/2026. Trạng thái: **đã implement, review và chạy xong smoke6
Plain vs EP+BVA theo lệnh người dùng**. Cùng phát hiện1/6PUT (task99), novel valid
inputs118vs109;EP+BVA dùng1,92×tokens và chỉ2/6catalogue qua schema. Chưa có lợi ích
detection trên smoke này; không suy rộng từ6task. Source/replayPASS; không tự nối
run mới. Xem [report](review/ep_bva_smoke6_results_2026-11-09.md) và
[audit catalogue](review/ep_bva_smoke6_catalogue_audit_2026-11-08.md).

Implementation nằm trong pipeline hiện có: `arms/classical.py`, `catalogue.py`,
`equivalence_partitioning/`, `boundary_value_analysis/classical.py`, `decision_table/`,
`stages/catalogue_measurement.py` và `catalogue_reporting.py`. Pydantic kiểm schema;
`math.nextafter` và `itertools` xử lý phần mechanical. Bốn arm đợt 1–2 và bốn
biến thể opt-in đợt 3 đã được đăng ký trong code; `ep_bva` là cấu hình chính của
nhóm mới. Default pipeline vẫn `plain`, soft BVA và `BoundarySettings` giữ nguyên.

Giới hạn implementation: coverage hiện chỉ đo novel reference-valid inputs;
base-call coverage, prose/semantic audit, tính đầy đủ/rời nhau của partition và
feasibility chưa chứng minh được giữ `pending`. DT không credit tất cả original
rules từ một merged ID. Robust chỉ gọi model khi task metadata có
`testing_arms.out_of_domain_behavior_defined=true` và `testing_arms.spec_evidence`
không rỗng. Catalogue sai không reject input hợp lệ; budget/design chưa đủ
metadata không được quy về 0. Xem [README](src/modular/README.md) và
[PREREG amendment](src/modular/PREREG.md).

## 1. Phạm vi và quyết định

- Phạm vi chỉ gồm ba kỹ thuật hộp đen trong `test_slides/03. Kiem thu chuc nang.pdf`:
  Equivalence Partitioning (EP), Boundary Value Analysis (BVA), Decision Table (DT).
  Control-flow, data-flow và special value nằm ngoài plan này.
- Mỗi arm phải ứng với **một biến thể có tên trong slide**. Không dùng nhãn chung
  "below/at/above" cho các arm mới.
- Mặc định: **weak EP** và **normal BVA với single-fault assumption**. Strong EP,
  robust BVA, worst-case BVA có code opt-in, chưa có preset mặc định.
- **`ep_bva` là cấu hình chính** theo yêu cầu user. `equivalence` và `bva_normal`
  là ablation. `decision_table` là arm riêng.
- Kỹ thuật phải **kiểm tra được**: model xuất một catalogue compact (classes,
  boundaries, rules) cùng inputs trong cùng một call. Nếu không có catalogue thì
  arm chỉ là "prompt có nhắc kỹ thuật", không được gọi là EP/BVA/DT.
- LLM chỉ sinh inputs và catalogue; expected outputs lấy từ corrected reference
  sau input freeze. Một generation call/task/arm, không feedback loop.
- Implement trong pipeline hiện có. Soft BVA (`boundary`) giữ nguyên làm comparator,
  không đổi tên hay sửa default.

## 2. Đối chiếu với slide

| Kỹ thuật (slide) | Slide định nghĩa | Plan dùng |
|---|---|---|
| BVA normal (p.5–12) | min, min+, nom, max−, max; giữ các biến khác ở nom, đổi từng biến; 4n+1 case | `bva_normal`, phần BVA của `ep_bva` |
| BVA robust (p.13) | thêm min−, max+; 6n+1 | `bva_robust`, chỉ khi spec định nghĩa hành vi ngoài domain |
| BVA worst-case (p.14) | tích Đề-Các 5ⁿ (hoặc 7ⁿ) | `bva_worst_case`, có cap và ghi `budget_limited` |
| EP partition (p.19–24) | miền con không rỗng, rời nhau, hợp lại bằng miền; chia cả input và output | catalogue classes, gồm output classes |
| Weak EP (p.25) | mỗi class xuất hiện ≥1 lần; số case tối thiểu = số class lớn nhất | `equivalence`, phần EP của `ep_bva` |
| Strong EP (p.26) | tích các class | `ep_strong`, có cap |
| Simple EP (p.27) | chỉ valid/invalid | không làm arm; yếu hơn weak theo chính slide |
| EP + BVA (p.30) | "kết hợp với BVA sẽ tốt hơn" | `ep_bva` |
| DT 8 bước (p.36–37, ví dụ p.38–48) | conditions/actions → combinations → gộp cột → coverage → actions → test case | `decision_table` |

Các điểm plan phải xử lý vì slide bỏ ngỏ hoặc sai:

1. **Biến phụ thuộc nhau.** Slide p.17 thừa nhận BVA sinh case vô lý khi các biến
   ràng buộc nhau. Plan: cố định các chiều khác trước, rồi tính min/max của chiều
   đang xét trong context đó (ví dụ maxDay theo month/year).
2. **Bảng DT bước 3–4 của slide** (p.43, ví dụ tính lương, R1–R6) cho C3–C7 cùng T, trong
   khi các điều kiện này loại trừ nhau. Plan bắt buộc đánh dấu combination
   infeasible trước khi lập cột.
3. **Gộp cột (bước 5) cần biết action, nhưng slide đến bước 7 mới điền action.**
   Plan dùng action xác định ở bước 1 làm căn cứ gộp; bước 7 chỉ hoàn thiện thứ tự.
4. **Ví dụ điểm chữ (p.21):** `[0,4]→F` và `[4,5]→D` chồng nhau tại 4, vi phạm tính
   rời nhau. Fixture dùng ví dụ này để kiểm việc phát hiện overlap/ambiguity.
5. **Invalid input trong Python.** Slide p.28 nhấn mạnh lỗi sai kiểu phổ biến với
   Python. HumanEval hầu như không định nghĩa hành vi reject, nên invalid classes và
   robust BVA thường `not_applicable`. Báo cáo phải ghi rõ số task bị loại vì lý do
   này, không ngầm coi là đã test robust.
6. **Domain không phải số** (slide p.12: enum, boolean). Dimension có thể là length,
   count, position, giá trị parse từ string. Boolean/enum không có min+/max−; chỉ
   lấy các giá trị của nó. Python int không có min/max: phía không bị chặn thì không
   có boundary, không bịa giới hạn.

Lịch sử liên quan: V7/V11 classical mixed không chứng minh gain so với plain
(matched-valid-budget p≈0.7483); soft BVA 7 so với direct 6 trên diagnostic 10 task.
Arm mới không được coi là novelty chỉ vì đổi tên kỹ thuật. Xem
[kết quả lịch sử](../memory/final-humaneval-pipeline.md) và
[giới hạn bucket adapters](../research/boundary-input-generation-2026-11-07/PIPELINES_AFTER_REPAIR.md).
Prior work: [DSpec2Test §2](https://arxiv.org/html/2609.29713v1) (formal contract →
ECP/BVA → solver), [LLM EP/BVA 2025 §3](https://arxiv.org/html/2505.09830v1)
(prompt spec+code, correlated inputs). Không tái hiện paper.

## 3. Arms

| Arm | Kỹ thuật | Đợt |
|---|---|---|
| `equivalence` | weak EP, input + output classes | 1 |
| `bva_normal` | normal BVA, single-fault, 4n+1 | 1 |
| `ep_bva` | weak EP, rồi normal BVA trên biên của các class | 1 (**chính**) |
| `decision_table` | DT 8 bước, mỗi feasible rule → một input | 2 |
| `ep_strong` | strong EP, có cap | 3 |
| `bva_robust` | robust BVA, chỉ khi spec định nghĩa out-of-domain | 3 |
| `bva_worst_case` | worst-case BVA, có cap | 3 |
| `ep_dt_bva` | DT với conditions lấy từ EP classes, cộng normal BVA | 3 |

Comparator có sẵn: `plain` và `boundary` (soft BVA). Không bật tất cả arm cùng lúc.

## 4. Cơ chế từng kỹ thuật

Mục này là định nghĩa đầy đủ dùng cho checker, audit và report. Prompt (mục 11)
chỉ mang phần cốt lõi; các ràng buộc còn lại được kiểm sau generation.

### Equivalence (weak EP)

1. Domain từng parameter lấy từ spec/contract; code có thể sai.
2. Chia mỗi parameter, hoặc một quan hệ giữa các parameter khi spec xử lý chúng
   chung, thành các class mà spec xử lý giống nhau. Trong một partition: không
   rỗng, rời nhau, hợp lại bằng domain.
3. Output partition: mỗi loại kết quả spec mô tả có một class input tạo ra nó.
4. Invalid class chỉ khi spec định nghĩa hành vi cho nó.
5. Weak: chọn inputs sao cho mỗi class xuất hiện ≥1 lần; một input có thể phủ class
   của nhiều parameter. Lấy giá trị điển hình, không cố tình chọn biên. Bỏ class đã
   có base call phủ.

Các partition theo những axis khác nhau được phép overlap; mỗi partition tự thỏa
tính rời nhau. Output khác nhau không tự chứng minh hai input khác class.

### BVA normal

1. Với mỗi dimension bị chặn (parameter hoặc length/count/position/parsed value),
   xác định min, max của domain hoặc của class.
2. Lấy min, min+, max−, max. Integer: ±1. Float: bước có nghĩa theo spec hoặc giá
   trị representable kế bên; không giả định epsilon cố định.
3. Single-fault: giữ các dimension khác ở nom, đổi từng dimension một; thêm một
   input toàn nom. n dimensions → tối đa 4n+1 inputs.
4. Dimension phụ thuộc: cố định context trước, tính lại min/max trong context đó.
5. Nếu 4n+1 vượt budget: ưu tiên các dimension mà spec đổi hành vi tại biên; ghi
   `budget_limited` và số boundary bỏ lại.

### EP + BVA (`ep_bva`)

Weak EP trước: một representative cho mỗi class. Sau đó normal BVA trên biên của
từng class (biên giữa hai class kề nhau sinh min/max của mỗi bên). Representative
của class không phủ các boundary của class đó. Neighbor có thể thuộc class kề bên:
ghi class thực tế, không ép vào cùng class. Thứ tự ưu tiên khi thiếu budget: đủ
representative cho mọi class → boundary giữa các class có hành vi khác nhau →
boundary của domain.

### Decision Table (8 bước)

1. Xác định conditions (biến, quan hệ hoặc predicate) và actions, kể cả thứ tự
   action. Không bịa action cho behavior spec không nói.
2. Liệt kê conditions với giá trị: T/F (bảng hạn chế) hoặc nhiều giá trị/class
   (bảng mở rộng).
3. Tính các combination; đánh dấu combination infeasible (có lý do) và unresolved.
   Tìm không ra không có nghĩa là infeasible.
4. Mỗi combination feasible là một cột/rule, ID ổn định.
5. Gộp cột khi actions và thứ tự giống nhau; dùng `-` (don't care) chỉ khi giá trị
   condition thật sự không đổi action. Giữ mapping `merged_from`.
6. Kiểm coverage: thiếu, chồng lấn, mâu thuẫn; đánh dấu rule mà base calls đã phủ.
7. Hoàn thiện actions từng cột, đánh số thứ tự nếu nhiều action.
8. Mỗi cột chưa được phủ → một input thỏa đủ conditions và joint domain. Expected
   output do reference cung cấp sau freeze.

Coverage tính trên **feasible rules gốc**, không trên bảng đã gộp, để việc gộp
không làm coverage cao giả.

## 5. Output contract

Envelope mới cho các arm này (decoder riêng; `plain`/`boundary` giữ envelope cũ).
Catalogue giữ tối giản để không thành gánh nặng cho model:

```json
{
  "catalogue": {
    "classes": [{"id": "E1", "description": "month with 31 days"}],
    "boundaries": [{"id": "B1", "dimension": "day (month=2, leap year)",
                    "values": [1, 2, 28, 29]}],
    "rules": [{"id": "R1", "conditions": {"C1": "T", "C2": "-"},
               "actions": ["A1", "A3"], "merged_from": ["R1a", "R1b"]}]
  },
  "inputs": [{"arguments": {"day": 29, "month": 2, "year": 2024},
              "covers": ["E1", "B1"]}]
}
```

- `classes` chỉ có ở EP arms, `boundaries` ở BVA arms, `rules` ở DT arms.
- `covers` không bắt buộc. Thiếu `covers` thì coverage tính bằng checker nếu được,
  còn lại là `pending`.
- `inputs` decode qua CallBuilder hiện có. Catalogue sai hoặc thiếu → status
  `catalogue_invalid`, **không reject input hợp lệ**.
- Catalogue tốn token: mọi arm trong cùng comparison dùng chung completion cap
  **4096 tokens/call** trong preset mới và báo cáo tokens thực tế từng arm.
  Preset cũ ghi rõ 2048 để giữ budget. Chế độ `catalogue=false` trên console hoặc
  `--catalogue-off` trên CLI là instruction-only ablation, giữ completion cap chung.

## 6. Đo lường

| Đo | Cách tính | Ghi chú |
|---|---|---|
| Declared coverage | class/boundary/rule có ≥1 input hợp lệ sau freeze trong `covers` | self-reported |
| Mechanical check | BVA: giá trị input khớp min/min+/max−/max khi boundary có dimension và số cụ thể; single-fault: các dimension khác bằng nom | chỉ khi catalogue máy đọc được |
| Partition check | trùng ID, class rỗng, overlap dễ phát hiện | không chứng minh tính rời nhau |
| Semantic audit | đọc tay một mẫu có seed: class/rule đúng spec không, input có thật sự thuộc class đã khai | precision; phần chưa audit là `pending` |
| Detection | unique confirmed detected PUTs/eligible evaluated PUTs; detected tasks riêng; wrong-value/exception/timeout-resource riêng | giống pipeline hiện có |

Coverage của catalogue không chứng minh detection, và ngược lại. Một input phủ nhiều
obligation vẫn chỉ tính một input. `budget_limited`, `not_applicable`, `unresolved`,
`catalogue_invalid` báo riêng, không quy về 0.

## 7. Integration

- `boundary_value_analysis/`: thêm biến thể classical (normal/robust/worst-case)
  cạnh soft BVA; không đổi `BoundarySettings` default.
- `equivalence_partitioning/` (mới): prompt, settings, decoder catalogue.
- `decision_table/` (mới): prompt, decoder rules, kiểm feasible/merge mapping.
- `catalogue.py` (mới, dùng chung): schema, envelope decoder, coverage và mechanical checks.
- `arms/`: đăng ký `equivalence`, `bva_normal`, `ep_bva`, `decision_table`; dùng chung
  budget split, freeze, reference oracle, execution cache, checkpoint/replay.
- Mở rộng CLI/Prefect allowlist khi arm đã qua fixtures.

Luồng: prompt → một call → decode inputs + catalogue → global input freeze →
domain/reference → catalogue measurement → PUT evaluation → report.

## 8. Fixtures từ slide

| Fixture | Kiểm |
|---|---|
| Tháng `1≤x≤12` (p.8) | normal BVA ra đúng {1,2,6,11,12} |
| Hai biến x, y (p.10–11) | đúng 4n+1 = 9 inputs, single-fault |
| Xét tuyển: t, l, h float ∈ [0,10], `t+l+h ≥ 28` → đỗ (p.16) | BVA float; relational boundary tổng 28 cần context; output classes đỗ/trượt |
| Điểm chữ (p.21) | phát hiện overlap tại 4 |
| NextDay (p.29) | EP theo month/leap year/vị trí day; boundary của day là 1, 2, maxDay−1, maxDay với maxDay tính theo month/year (maxDay+1 chỉ thuộc robust); 1900/2000 là representative của class chia hết, không phải biên số; 31/12/9999 unresolved nếu spec không nói |
| Tính lương (p.38–48) | phát hiện combination infeasible ở bảng bước 3–4; ra 10 rules sau gộp; coverage tính trên rules gốc |

Fixture là engineering test cho decoder/checker và prompt rendering, không gọi model.

## 9. Lộ trình

| Đợt | Việc | Hoàn tất khi |
|---|---|---|
| 0 | `catalogue.py`, envelope decoder, fixtures | decode/check đúng trên fixtures; không đổi default/checkpoint hiện có |
| 1 | `equivalence`, `bva_normal`, `ep_bva` | single-fault/4n+1 check, dependent context, class kề bên ghi đúng |
| 2 | `decision_table` | infeasible/merge mapping/coverage trên rules gốc đúng |
| 3 | `ep_strong`, `bva_robust`, `bva_worst_case`, `ep_dt_bva` | cap/`budget_limited`/`not_applicable` minh bạch |
| 4 | Read-only review, PREREG amendment, Prefect presets | preview offline đủ config/budget, zero model calls |

User đã yêu cầu implement ngày 08/11/2026. Code và preset definitions đã có;
engineering validation/review là gate trước run. Các tiêu chí semantic và
base-call coverage chưa hoàn tất được ghi rõ `pending`, không coi là đã chứng
minh toàn bộ lộ trình. Không tự launch benchmark.

Preset definitions mới: Plain vs `ep_bva` chính trên boundary smoke6; Plain vs
`equivalence` trên equivalence smoke6; Plain vs `bva_normal` trên boundary smoke6;
Plain vs `decision_table` trên equivalence smoke tasks 11/85 (XOR hai bit;
element chẵn × index lẻ). Mỗi task dùng một representative PUT, 20 inputs/task/arm,
4096 completion tokens/call và context 8192. Smoke6 tối đa 12 calls/240 input
records; DT smoke2 tối đa 4 calls/80 input records. Việc chuẩn bị preset không
cấp quyền chạy hoặc tự chuyển sang dev/check/full.

## 10. Protocol khi user chọn chạy

- Chọn task từ frozen full HumanEval cohort bằng `task_numbers`; chỉ chạy scope
  được user chỉ định. Eligibility của DT dựa trên spec có ≥2 conditions tương
  tác dẫn tới actions khác nhau, không chọn theo hidden outcomes.
- Cùng visibility/order, model/sampling/seed, completion/context cap, parser/oracle/
  timeout/scorer.
- Raw và matched-valid-input-budget là hai báo cáo; subset ngẫu nhiên có seed.
- `ep_bva` so với `equivalence` là so instruction tổng thể, không cô lập riêng BVA.
- Prefect: console/importer/observer hiện có, một `flow_run_id`/source run, report
  tiếng Việt có đơn vị/mẫu số, metric chưa có là `pending`, gửi direct run link.

## 11. Prompts

### Nguyên tắc viết prompt

Soft BVA (`boundary`) là bản đang tốt nhất và nó ngắn, gợi ý, không ép. Prompt mới
theo cùng kiểu:

- Chỉ mô tả **kỹ thuật làm gì**, viết dạng khẳng định, mỗi prompt ≤ ~8 dòng.
- Không lặp phần shared prompt đã có: spec định nghĩa đúng/sai, PUT có thể sai,
  giữ input trong contract, tránh base calls, không trùng, không xuất expected
  output, budget.
- Không đưa câu dành cho người viết report (claim coverage, partition rời nhau
  "đã chứng minh", mutants, oracle) vào prompt.
- Cho phép model thêm test hữu ích khác ngoài kỹ thuật, như soft BVA.
- Ràng buộc chuyển ra khỏi prompt, do code/report xử lý:

| Ràng buộc bản cũ đặt trong prompt | Giờ do đâu xử lý |
|---|---|
| Invalid/robust chỉ khi spec định nghĩa | domain check sau freeze; arm `bva_robust` có eligibility riêng |
| Không bịa giới hạn cho int không chặn | checker đánh dấu boundary không có căn cứ trong spec khi audit |
| Overlap giữa partition axes, "không claim partition đã chứng minh" | partition check + semantic audit |
| Ưu tiên khi thiếu budget, `budget_limited` | report tính từ catalogue so với inputs |
| Infeasible phải có lý do, unresolved ≠ infeasible | DT checker/audit; prompt chỉ hỏi "bỏ tổ hợp không thể xảy ra" |
| Không bật DT/BVA khi config chưa bật | mỗi arm chỉ nhận guidance của nó |
| Không xuất reasoning/assertion/expected | shared prompt đã có |

### `equivalence`

```text
Equivalence Partitioning is a useful source of test ideas here. Split the
inputs into classes that the specification handles the same way (per parameter,
or for parameters that work together), and also by the kinds of result the
specification describes. Pick one typical input from each class; one input can
cover classes of several parameters. You may also add other useful tests.
List the classes in the catalogue.
```

### `bva_normal`

```text
Boundary Value Analysis is a useful source of test ideas here. For each bounded
quantity (a parameter, or a length, count, position, or parsed value), take
min, min+1, max-1 and max from the specification. Vary one quantity at a time
while the others stay at typical values, plus one all-typical input. When a
limit depends on other parameters, fix them first. You may also add other
useful tests. List the boundaries in the catalogue.
```

### `ep_bva`

```text
Use Equivalence Partitioning together with Boundary Value Analysis. First split
the inputs into classes the specification handles the same way, including by
kind of result, and pick one typical input per class. Then test the edges of
those classes: min, min+1, max-1, max, varying one quantity at a time. A value
just past an edge belongs to the neighbouring class; that is fine. You may also
add other useful tests. List classes and boundaries in the catalogue.
```

### `decision_table`

```text
Use Decision Table Testing. (1) Find the conditions and the actions the
specification requires. (2) List each condition's values. (3) Form the
combinations and drop the ones that cannot happen. (4) One rule per
combination. (5) Merge rules whose actions are the same, using "-" for a
condition that does not matter. (6) Check for missing or overlapping rules.
(7) Fill in the actions of each rule. (8) Write one input per rule not already
exercised by the existing calls. List the rules in the catalogue.
```

Độ dài: mỗi guidance 6–8 dòng, gần bằng `GUIDANCE` của soft BVA (5 dòng), so với
15–30 dòng của bản trước. Guidance đợt 1–2 đã được giữ cố định trong code; schema
catalogue là phần riêng. PREREG amendment ngày 08/11/2026 đăng ký contract,
budgets và giới hạn trước mọi run mới.
