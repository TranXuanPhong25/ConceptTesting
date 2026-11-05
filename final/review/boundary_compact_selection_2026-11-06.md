# Diagnostic rút gọn selection prompt: 23 / 72 / 157

Bản ngắn nhận ra khác biệt byte/character ở task 23, trong khi fresh long control
vẫn coi byte length là intended behavior. Hai lỗi semantic ở 72/157 còn nguyên.
Task 157 còn trả `origin: contract` ngoài enum. Downstream của bản ngắn giữ được
11 input hợp lệ, không phát hiện bug. Chưa có bằng chứng để áp dụng rộng bản này.

Đây là diagnostic sau khi đã xem ba lỗi, so bundle compression/rephrasing.
Không tách được tác động của token length với salience/cách viết/chi tiết bị lược,
không phải efficacy hoặc held-out evidence.

## Thiết kế đã freeze trước inference

- Cùng 3 PUT: 23/PUT7, 72/PUT4, 157/PUT3 từ known_bug_10, không sinh PUT mới.
- Chỉ thay selection instruction text, từ 5.908 xuống 3.347 characters (~43%).
  System message, task-data JSON và output JSON example giữ nguyên byte.
  Context instructions giữ nguyên byte. Menu, parser, compiler, validators và
  budget/seed/temperature không thay. Protocol identity lên 6 để tách checkpoint.
- Không thêm task-specific hint về byte/character, prefix sum, polarity hay
  hypotenuse. Candidate-space gaps đã biết vẫn tồn tại.
- Runtime đã đổi sau v5, nên chạy thêm 3 fresh long-selection controls trên cùng
  runtime hiện tại. Thứ tự: 23 long→short, 72 short→long, 157 long→short.
- Sau 6 selection calls mới chạy pipeline chuẩn với các short-selection response
  đã cache. Không gọi lại selection completion; chỉ phát sinh context khi cần.
  Cả 3 task freeze generation trước reference/PUT execution.
- Model qwen3.5-27b-awq, context 8192, selection 4096 / generation 2048 tokens,
  input cap 20/task. Cùng corrected HumanEval+ reference và 2 native repeat slots.
- Independent review và 234 modular tests pass trước launch. Prospective PREREG
  amendment thêm controls và nâng cap lên 9 logical calls; thực dùng 8.

| Task | Long prompt tokens | Short prompt tokens | Giảm |
|---|---:|---:|---:|
| 23 | 2.158 | 1.542 | 616 |
| 72 | 2.987 | 2.371 | 616 |
| 157 | 2.610 | 1.994 | 616 |

Tổng prompt giảm khoảng 21–29%, ít hơn mức giảm instruction text vì task data
được giữ nguyên. Cả hai phía dùng cùng output token budget.

## Kết quả semantic và schema

| Task | Fresh long control | Short selection | Đánh giá |
|---|---|---|---|
| 23 | `no_applicable_boundary`; “the function simply returns the byte length” | Nhận ra byte encoding có thể khác character count với non-ASCII; chọn length 0 | Có semantic recognition mới, binding chưa trúng bug condition |
| 72 | Gọi total `<=` với reject `>` là operator mismatch | Vẫn gọi đây là operator mismatch; thêm length 1 và boundary ngược `w` so với sum(q) | Chưa phân biệt được prefix sum với total sum |
| 157 | Gọi contract `>0` với reject `<=0` là mismatch | Vẫn nhận định sai này cho cả a/b/c; `origin: contract` | Không cải thiện semantic; thêm schema rejection |

Cả 3 fresh long response text đều **byte-identical** với response v5 tương ứng.
Vì thế thay đổi output ở cặp mới không chỉ là khác giữa run lịch sử và runtime
hiện tại. Tuy nhiên một response mỗi variant trên 3 case đã nhìn trước vẫn không
đủ suy ra hiệu quả chung hoặc quy riêng nguyên nhân cho độ dài.

### Task 23: nhận ra vấn đề nhưng không chuyển thành test thích hợp

Short reason có câu:

> code uses byte encoding which may differ from character count for non-ASCII

Đây là thay đổi rõ so với long control. Nhưng selection chọn `string:length=0`,
`alignment: match`, infect `0`. Empty string không phân biệt character length với
byte length: cả hai bằng 0. `above` có target length 1, có thể mang non-ASCII,
nhưng context model chỉ trả:

```text
b1:at     → ''
b1:above  → 'x'
```

Cả hai trùng base input nên bị loại. Không có input cuối cùng. Task này chỉ có
semantic recognition improvement, chưa có input-generation success. Missing
code-point characteristic và semantic-to-context transfer chưa được giải quyết.

### Task 72: prompt ngắn vẫn giữ false mismatch

Short reason:

> where code uses strict inequality while spec uses inclusive

Boundary sum explanation:

> The spec requires <= but the code uses > for rejection, creating a potential
> mismatch at the exact boundary where sum equals w.

Đây vẫn là lỗi cũ: reject `>` bổ sung cho accept `<=`; khác biệt gây bug là PUT
dùng prefix sum trong loop. Short selection chỉ ghi “accumulated weight compared
inside loop”, không giải thích vì sao early rejection có thể sai khi total sum
vẫn nằm trong limit.

Context trả 20 record. Constructor/validator giữ 11, loại 7 duplicate và 2 vi phạm
palindrome requirement sau length construction. Tất cả nonempty accepted lists
vẫn chứa số dương, w không âm. Các input cuối:

```python
([], 0)
([], 10)
([3], 3)
([1], 2)
([2], 4)
([1, 2, 1], 5)
([3, 2, 3], 7)
([1, 1], 1)
([1, 2, 1], 4)
([3, 2, 3], 8)
([1, 2, 1], 3)
```

Tất cả pass ở hai native repeat slots. Việc chọn thêm boundary làm response dài
hơn nhưng không giữ được điều kiện cần cho bug đã biết.

### Task 157: false mismatch còn nguyên và có thêm invalid origin

Short reason:

> Domain boundary at 0 for side lengths shows mismatch between contract (>) and
> code (<=) handling.

Model chọn 3 behavior boundaries tại 0 cho a/b/c. Cả 3 dùng `origin: contract`,
trong khi schema chỉ nhận `spec`, `code`, `edge`. Validator reject cả 3 với
`invalid_boundary_origin`; không gọi context, không sinh input.

Parser/output example không đổi. Đây là raw-response schema regression trong
candidate prompt đã thử. Bản ngắn vẫn nêu ba origin nhưng đã lược diễn giải dài
rằng contract assertion thuộc origin spec; đó là một khác biệt instruction cần
ghi nhận, không phải bằng chứng chắc chắn về nguyên nhân duy nhất của regression.
Không sửa prompt/normalize origin/retry sau khi thấy response này trong run.

## Accounting và integrity

- Short pipeline: 5 calls = 3 selection + 2 context; 16.289 tokens; 11 valid
  inputs, 0 detected PUTs. Task 23 no_inputs, 72 generated, 157 invalid_selection.
- Long controls: 3 selection calls; 9.019 tokens, không chạy long generation.
- Tổng: 8 responses / 0 unknown; 19.378 prompt + 5.930 completion = 25.308 tokens.
  Không periodic keepalive completion, không semantic retry hoặc task expansion.
- Chỉ tính selection, short tiết kiệm 1.848 prompt tokens nhưng dùng thêm 1.617
  completion tokens; tổng selection tokens 8.788 so với long 9.019. Prompt ngắn
  không tự động đồng nghĩa response ngắn hoặc giảm cost tương ứng.
- 76 source/data files và 312 prior v5 output files giữ hash trước launch.
  3 input-freeze hashes và generation-before-oracle barrier verified.
- Full read-only short-pipeline replay pass, khớp 11 valid / 0 detected, không có
  source drift trong run này. Accounting không bao gồm shared cohort writer cost.

Output: `final/out/boundary_compact_selection3_20261106`.
`comparison_audit.json` lưu raw paired responses, short validation/results,
request identity checks, token accounting và prior-output hash verification.
`prelaunch_requests/` lưu exact messages/budgets; `long_selection_control/` lưu
control calls riêng. Báo cáo chuẩn `REPORT.md` chỉ tính short pipeline; tổng
paired-diagnostic cost phải cộng controls như trên.

Source đang giữ candidate prompt đã thử để review; không launch thêm case hoặc
chỉnh tiếp prompt trong diagnostic này.
