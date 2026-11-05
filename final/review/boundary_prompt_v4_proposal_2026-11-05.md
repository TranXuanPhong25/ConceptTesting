# Bộ prompt Boundary v4: đề xuất và so sánh với prompt hiện tại

Update: user yêu cầu thử; v4 đã được áp dụng vào
`final/src/modular/boundary_value_analysis/prompts.py` và `stages.py`. Các đường dẫn và
mục "thay đổi code" dưới đây ghi lại trạng thái lúc viết proposal. Nguồn: ghi chú "Khi nào BVA phát hiện bug" do user cung cấp, slide
[03. Kiem thu chuc nang.pdf](../../test_slides/03.%20Kiem%20thu%20chuc%20nang.pdf)
pp.5–17 và saved artifacts của `final/out/boundary_all_plain_bva_compiled_20261105`.

Run đó dùng prompt trước repair v3, nên số liệu dưới đây giải thích failure đã thấy,
không đo prompt hiện tại và không đo prompt v4.

## Kết luận

Prompt hiện tại chủ yếu nói **không được làm gì**: nó chặn bịa boundary và chặn input
ngoài domain, nhưng không dẫn model qua quy trình BVA. Prompt v4 đổi thành quy trình 5
bước theo ba điều kiện của ghi chú (order, transition, loại bug) và mô hình RIP.

Ba khác biệt quan trọng nhất:

1. **Domain min/max là boundary.** Trong saved run có 18 task `no_applicable_boundary`;
   7 task (69, 71, 103, 115, 122, 157, 159) abstain với lý do "đây là precondition".
   Task 122 và 159 còn trích nguyên câu "excluded precondition inputs are not bugs" của
   prompt. Slide p.5 lại nói BVA tập trung vào chính biên của miền xác định.
2. **Behavior boundary phải đủ ba phía.** 7/8 behavior boundary trong saved run thiếu
   một phía; chỉ 1/8 có đủ below/at/above. Ghi chú yêu cầu b-1, b, b+1.
3. **Code và natural edge được dùng để tìm chỗ test.** Prompt hiện tại đưa PUT source
   vào nhưng không yêu cầu đọc predicate hay so spec với code. Spec vẫn là nguồn duy
   nhất định nghĩa đúng/sai.

## So sánh theo từng điều kiện

| Yêu cầu | Nguồn | Prompt hiện tại | Prompt v4 |
|---|---|---|---|
| Có "giá trị ngay trước/sau" | Ghi chú đk1, slide p.12 | Ngầm qua templates | Step 1 hỏi trực tiếp, loại boolean/label |
| Đo đúng đại lượng | Ghi chú đk2 | Có, qua ví dụ riêng của task | Một nguyên tắc chung; ví dụ riêng chuyển sang guards |
| Domain min/max | Slide pp.5–8 | Dễ bị hiểu thành "không phải boundary" | Nói rõ là boundary, test từ phía trong |
| Biên trong spec | Ghi chú đk2 | Có | Có (`origin: spec`) |
| Predicate trong code | Ghi chú đk2 | Không yêu cầu | `origin: code`, kèm `code_quote` |
| Biên ẩn, giá trị đặc biệt | Ghi chú đk2, slide p.15 | Bị chặn bởi "type alone is not evidence" | `origin: edge`, phải có lý do behavior đổi |
| So biên spec với biên code | Quy trình bước 3 | Không có | Step 3 `alignment` |
| Reach / Infect / Propagate | Mô hình RIP | Không có | Step 4, và context prompt dùng lại |
| b-1, b, b+1 | Ghi chú RIP | Model tự chọn `target_sides` | Bắt buộc với behavior boundary |
| Single-fault, giữ biến khác ở nom | Slide pp.9–11 | Không có | Context prompt rule 1 |
| Robust min-/max+ | Slide p.13 | Cấm | Vẫn cấm nếu spec không nêu cách xử lý |
| Worst-case 5^n | Slide p.14 | Không có | Không dùng, vượt budget |
| Ràng buộc giữa các biến | Slide p.17 | Có | Có, chuyển sang rule riêng |
| ON/OFF cho `x + y <= 100` | Lưu ý 1, slide p.16 | Không biểu diễn được | Trả `unsupported_characteristic`; cần operator mới |
| Không hợp BVA thì chuyển kỹ thuật | Ghi chú đk1, slide p.32 | Chỉ abstain | Thêm `better_technique` |
| Key trong `arguments` | Artifact task 140 | Ví dụ `{"parameter": ...}` bị model chép nguyên văn | Ví dụ dùng tên parameter thật |

Hai điểm cần điều chỉnh so với ghi chú khi áp dụng vào pipeline này:

- `MAX_INT + 1` không áp dụng cho Python `int`, vì `int` không có giới hạn cố định.
- Bộ ba b-1, b, b+1 chỉ dùng đầy đủ cho behavior boundary. Với domain boundary, phía
  ngoài bị contract loại, nên chỉ test phía trong. Giá trị `nom` của slide không phải
  target; nó là context giữ cho các biến còn lại.

Prompt hiện tại cũng có các câu sinh ra từ task trong chính cohort 44 task: nearest
integer (99), `mm-dd-yyyy` (124), consecutive space (140), `max>min` (21), filter
positive (146). V4 bỏ các câu này khỏi prompt. Các rule deterministic trong
`string_guidance.py` và `binding.py` vẫn đưa thông tin đó qua `candidate_guards`.

## Prompt 1: Selection

System:

```text
You are a test analyst applying boundary value analysis. You choose where to test and never decide expected outputs. Return JSON only.
```

User instructions, phần `TASK DATA` giữ nguyên như `selection_messages`:

<!-- PROMPT:SELECTION -->
```text
Apply boundary value analysis (BVA) to one Python function. You decide WHERE to test.
The specification and domain contract define correct behavior. The PUT source may be
wrong: use it to find where to look, never as proof of correct behavior.

STEP 1 ORDER. Keep a candidate only if you can name the value just before and just after
a given value of that quantity, and the rule depends on that order. Measure the quantity
the rule talks about, not the raw input type: a part of a value is not the whole value,
and text may encode a number or a fixed format with its own measure. Booleans and
unordered labels have no boundary.

STEP 2 TRANSITIONS. List the points where the applicable rule changes.
- origin "spec": a stated range, limit or cutoff ("from 18 to 60", "at most 255 characters",
  "above 500000", "at least 1 item") or a contract assertion. The minimum and maximum of a
  valid range ARE boundaries. A precondition forbids only the side outside the domain;
  its inside side is still a boundary test.
- origin "code": a comparison, loop exit, index, slice or arithmetic step in the PUT that
  separates valid inputs into different behavior.
- origin "edge": an unstated natural edge of a valid input: zero and the sign change,
  an empty or one-element container, empty text, and both +b and -b when a rule concerns
  size or digit count. Give the reason behavior may change there.
Observed values are samples, not limits. A type alone is not evidence of a threshold.
Python int has no maximum. Sampling, resource and generation caps are not boundaries.

STEP 3 ALIGN. Compare each spec transition with the code: "match", "operator" (< against
<=), "shifted" (different constant), "missing_in_code", or "code_only". A mismatch is a
hypothesis, not a verdict.

STEP 4 REACH, INFECT, PROPAGATE. For each transition write briefly:
- reach: what the other inputs must satisfy for execution to get there.
- infect: the values where intended and coded behavior can differ. For an operator mismatch
  this is the threshold itself; for a shifted constant, the values between both constants.
- side_rules: which rule the specification applies below, at and above, as rule names only.
Drop a transition if every side follows the same rule and no visible result can change.

STEP 5 SELECT at most {boundary_budget}, in this priority: mismatches; spec behavior
transitions; domain minimum and maximum; remaining code and edge transitions.
- behavior: target below, at and above. Omit a side only if it cannot exist, such as length -1.
- domain_lower/domain_upper: inside sides only. x >= b: at, above. x > b: above.
  x <= b: below, at. x < b: below. Never target inputs excluded by the contract.
These two kinds require an equivalent input-domain clause. Otherwise use behavior: inputs
for which the result is False or empty can still be valid inputs.

BINDING. template_id and characteristic must match a candidate. Operations: value,
parsed_float, length, elements, sum, minimum, maximum, range, run_length (add a one-character
"token"). Threshold: {{"kind":"constant","value":2}} or
{{"kind":"expression","parameter":"limit","operation":"value"}}, using another input and a
scalar operation; never the same characteristic. comparison: <, <=, ==, !=, >=, >.
neighborhood: {{"mode":"step","step":1}} or {{"mode":"float_adjacent"}}, as the template
allows. Use step 1 for length. candidate_guards and projection_evidence are public hints,
not PUT evidence. Each constraints item is an object with description and source_quote,
never a plain string; use [] if the contract adds no joint condition.
source_quote must be an EXACT nonempty quote from the specification or contract governing
this quantity, also for origin code and edge. code_quote must be EXACT PUT text, or "".

OUTPUT JSON only:
{{"status":"selected","reason":"short","boundaries":[{{"id":"b1","template_id":"age:value",
"characteristic":{{"parameter":"age","operation":"value"}},
"threshold":{{"kind":"constant","value":18}},"comparison":">=","boundary_kind":"behavior",
"neighborhood":{{"mode":"step","step":1}},"target_sides":["below","at","above"],
"constraints":[{{"description":"age is an integer","source_quote":"age: int"}}],
"source_quote":"from 18 to 60","explanation":"one sentence",
"origin":"spec","alignment":"operator","code_quote":"age > 18",
"reach":"no earlier return","infect":"18","side_rules":{{"below":"reject","at":"accept","above":"accept"}}}}]}}
If nothing is selected, return empty boundaries with status "no_applicable_boundary" (steps
1-2 left nothing), "unsupported_characteristic" (a transition exists but no operation can
express it, such as a sum over separate parameters), or "uncertain_binding". You may add
"better_technique": "equivalence_partitioning", "decision_table" or "none".
No executable predicates, expected outputs or assertions. Do not force applicability.
```
<!-- /PROMPT:SELECTION -->

## Prompt 2: Context

Chỉ thay nhánh `construction_mode == "compiled"`. Nhánh literal giữ nguyên để tương thích.

System:

```text
You complete the surrounding values of compiled boundary tests. Return JSON only.
```

<!-- PROMPT:CONTEXT -->
```text
Complete input CONTEXTS for the compiled obligations, up to {input_budget} total calls.
Code builds targets and Python calls. You choose only the values around each target.

1. ONE FACTOR. Keep inputs that are not the target at ordinary valid values, and reuse one
   context for all sides of a boundary so the sides differ only in the target.
2. REACH. Use each boundary's reach note. The target must really be used by the function:
   not skipped, sliced away or bypassed by an early return.
3. PROPAGATE. Choose a context where the side_rules difference can change the visible
   result. No other element, cap or early return may hide it. With spare budget, place the
   target where the code takes a different path, such as first, middle or last position.
4. CONSTRAINTS. Keep all joint input-domain constraints.

Return JSON, here for a function with parameters age and name:
{{"inputs":[{{"obligation_id":"b1:at","arguments":{{"name":"Ann"}}}}],"reason":"optional"}}.
Use EXACT obligation_id values. Each arguments key must be a real parameter name of THIS
function. Values are JSON values, never Python args/kwargs strings or expressions. Supply all
required context parameters; a controlled value or parsed_float parameter may be omitted. For length, elements,
extrema and sum give a small valid seed container. For run_length give prefix/suffix text.
For a fixed-format string give a seed in that format. Code sets the size or numeric target.
Do not compute adjacent floats, repeat long arrays, use arithmetic inside strings, or invent
targets or sides. Actual tuples/sets use {{"__python_type__":"tuple","items":[1,2]}} or
{{"__python_type__":"set","items":[1,2]}}.
If few distinct feasible contexts exist, return fewer inputs; do not pad. No assertions,
expected outputs, executable predicates or reference information.
```
<!-- /PROMPT:CONTEXT -->

## Bốn dòng trong bảng reference

Bảng này cho biết prompt **có thể biểu diễn** obligation nào, chưa đo model có chọn đúng
hay không.

| Task, input | Saved run | V4 có thể biểu diễn |
|---|---|---|
| 44, `change_base(0, 2)` | Đã chọn `x >= 0`, có input `(0, 2)` | Giống hiện tại (domain min) |
| 97, `multiply(-1, 2)` | `no_applicable_boundary` | `origin: edge`, sign change tại 0: -1, 0, 1 |
| 122, `add_elements([-99], 1)` | `no_applicable_boundary`, trích câu precondition | `elements` tại ±99, ±100; thêm domain của `k`, `len(arr)` |
| 140, `fix_spaces("  ")` | Chọn `run_length > 2` với at/above; cả 2 input bị loại vì model chép key `"parameter"` | Thêm below; ví dụ JSON mới; `reach` và rule 3 đặt run ở cuối chuỗi |

Bốn dòng này là lỗi của **reference gốc**, không phải bug của PUT. Dưới HumanEval+
corrected reference, các disagreement đó biến mất. Cả bốn task đều thuộc cohort 44 task,
nên không được đưa vào few-shot và không được dùng làm bằng chứng held-out. Ví dụ trong
prompt v4 chỉ lấy từ ghi chú và slide (tuổi 18–60, 255 ký tự, 500000).

## Thay đổi code cần có trước khi chạy

Chưa thực hiện. Xem kết quả kiểm tra offline ở cuối file.

1. `BoundarySelection.validate` tạo `result` từ các field cố định, nên `origin`,
   `alignment`, `code_quote`, `reach`, `infect`, `side_rules` bị bỏ. Phải giữ lại để
   context prompt đọc được, và kiểm tra `code_quote` có trong PUT source.
2. Giữ `better_technique` trong selection artifact.
3. Đo lại `selection_tokens=2048`; output v4 dài hơn và response bị cắt sẽ thành invalid.
4. Tăng protocol version và dùng output directory mới. Không dùng lại checkpoint cũ.
5. Tùy chọn: operator cho tổng nhiều parameter (slide p.16, `t + l + h >= 28`) và digit
   count. Hiện cả hai chỉ có thể trả `unsupported_characteristic` hoặc bind gián tiếp.

## Rủi ro và điều kiện đánh giá

- Step 3–4 gần với các hướng đã thử: v31 fault template (18 vs 15), nhưng v34 placebo
  không đạt rule; hybrid C1 diff hints không khác có ý nghĩa so với plain/checklist;
  v47 LLM chọn từ menu không hơn random. Không nên kỳ vọng gain chỉ vì prompt có RIP.
- Bớt abstain sẽ tăng số boundary và số input. So sánh phải cùng input/call budget với
  plain và có placebo prompt độ dài tương đương.
- `origin: code` và `edge` có thể làm model chọn nhiều biên không có ý nghĩa. Cần đếm
  riêng theo `origin` để biết nguồn nào có ích.
- Model nhỏ có thể không theo được worksheet 5 bước. Failure đó phải báo là interface
  failure, không phải kết luận về BVA.

## Kiểm tra offline

Không gọi model. Prompt được render từ file này; response viết tay được đưa qua
`BoundarySelection.validate` hiện tại, dùng templates/guards đã lưu của từng task.

| Kiểm tra | Kết quả |
|---|---|
| Độ dài selection instructions | 4287 ký tự hiện tại, 4700 ký tự v4 |
| Ví dụ JSON trong prompt | Parse được |
| 97: `a:value` tại 0, ba phía | PASS, `llm_semantic_hypothesis` |
| 122: `arr:elements` tại -99, ba phía | PASS, `llm_semantic_hypothesis` |
| 122: `k <= len(arr)`, `domain_upper` | PASS, `recognized_necessary_domain_clause` |
| 140: `run_length > 2`, ba phía | PASS, `matched_public_guard` |
| Field mới sau validate | Bị bỏ hết, xác nhận thay đổi code số 1 là bắt buộc |

Các PASS chỉ chứng minh output contract của v4 tương thích với validator. Chúng không đo
khả năng model tự chọn các boundary này.
