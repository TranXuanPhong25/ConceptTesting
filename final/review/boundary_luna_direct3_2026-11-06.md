# GPT-5.6 Luna: input trực tiếp sau feedback về các record bị loại

User yêu cầu exact `gpt-5.6-luna`, không dùng tools, trả ngay input. Một bundled
native CLI call chứa23/72/157và feedback từ run checked6. Model trả đúng3calls,
mỗi task1input; cả3hợp lệ, novel và làm PUT fail ổn định qua2native repeat slots.

Đây là diagnostic có feedback, được thiết kế sau khi xem lỗi. Khác model, harness,
schema và information context với Qwen/BVA. Không phải matched comparison hoặc
detection rate, và chưa isolate stronger model với simpler direct prompting.

## Output nguyên bản

```json
{"tasks":[{"task_id":"HumanEval/23","inputs":[{"arguments":{"string":"é"}}]},{"task_id":"HumanEval/72","inputs":[{"arguments":{"q":[10,-20,10],"w":5}}]},{"task_id":"HumanEval/157","inputs":[{"arguments":{"a":1,"b":1,"c":1.41421356237}}]}]}
```

Không có analysis, expected outputs hay assertions trong final message. Không
model tool call hoặc denied tool attempt quan sát được. Host/features disabled,
empty ephemeral cwd; CLI có thể vẫn expose tool schemas. Không claim tools array
trên wire là rỗng khi chưa có request-level evidence. Hai pre-turn warning events
về feature/disabled host được phân biệt với tool events.

Requested model/effort là `gpt-5.6-luna/low`, local model catalog có exact slug.
Server events không report model ID riêng, nên identity claim là CLI-requested,
không độc lập xác minh served weights. Không model substitution hoặc fallback.
Official model reference: [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

## Vì sao ba input này làm PUT fail

| Task | Direct input | Reference | PUT, cả2repeats | Trace |
|---|---|---|---|---|
| 23 | `string="é"` |1|2| Một character, UTF-8encode thành2bytes; PUT đếm byte |
| 72 | `q=[10,-20,10], w=5` |True|False| Palindrome, total0<=5; prefix đầu10>5khiến PUT reject sớm |
| 157 | `a=1,b=1,c=1.41421356237` |False|True| c là literal gần sqrt(2), residual khác0nhưng nhỏ hơn tolerance1e-9của PUT |

Không stage nào chỉnh giá trị để hit target. Shared CallBuilder chỉ encode named
arguments thành literal call. Cả3batch được freeze trước contract/reference/PUT
evaluation; không có iterative feedback từ native execution về model.

## Feedback đã cung cấp và những gì không cung cấp

Prompt có public spec, contract, exact PUT và mô tả failure của lần trước:

-23đã nhận ra character/byte nhưng abstain và thiếu field; yêu cầu direct string
  inputs thay vì selection schema.
-72đã nhận ra prefix/total; chỉ ra các seed `[10,-5,10],w=15` và
  `[20,-15,20],w=25` không có proper prefix>w. Yêu cầu tự làm arithmetic.
-157đã bỏ false mismatch nhưng chọn excluded side0; nhắc giữ positive domain và
  xét arithmetic/tolerance của PUT. Float literals hợp lệ được cho phép.

Không đưa corrected-reference output, hidden input hoặc successful witness trong
packet. JSON-shape examples chỉ là benign existing examples, không phải gold
witnesses. Prompt được freeze trước call; [bản lưu](prompts/boundary_luna_direct3_20261106.txt).

## Check lại các record fail của checked6

Task23là JSON đúng syntax nhưng thiếu `boundaries`, không phải truncation. Reason
đã hiểu đúng character/byte; pipeline không gọi context vì envelope invalid.

Task157ghi đúng strict domaina>0và `alignment: match`, nhưng side list cònat0.
Validator reject trước compiler; early pruning không có cơ hội chạy ở case này.

Task72có **thêm một selection rejection** chưa xuất hiện trong bảng aggregate:
boundaryb2(length0) dùng `boundary_kind: edge`. Enum đúng chỉ có behavior/
domain_lower/domain_upper; edge là origin. b1(sum) còn hợp lệ nên run tiếp.
Partial selection rejection này được giữ trong selection.json nhưng summary
chủ yếu tính rejections của generation result, nên phải đọc raw checkpoints để
thấy nó. b2còn gọi w>=0là điều kiện để empty list “valid”, dù đó là điều kiện
behavior, không phải contract precondition.

Năm contextb1bị loại đều không thỏa property đã khai báo. Ví dụ `[10,-5,10]`,w15
có prefixes10,5,15; below-side constructor đổi thành `[10,-6,10]`, prefixes10,4,14.
Cảhai không có proper prefix>15. Model-generated mixed signs tự nó không đủ;
Luna lần này chọn đầu10>w5rồi dùng giữa-20để total về0, thực hiện đúng condition.

15native failures của task16trong checked6là các test làm lộ bug PUT, không phải
15pipeline engineering test failures. Trước đó toàn bộ278engineering tests pass.

## Accounting và integrity

-1CLI invocation,1response,0unknown,không retry. Khoảng10.7giây generation.
-8.108input tokens, trong đó5.760cached;345output tokens, gồm257reasoning tokens.
  Tổng8.453tokens. Hidden reasoning tokens không phải tool use hoặc visible
  analysis. CLI không enforce hard output-token budget tương đương Qwen.
-0tool executions,0forbidden tool events,0denied router attempts.
-83source/data/runner/request files và273prior checked6files giữ hash prelaunch.
  Freeze barrier verified; đầy đủ3stable failure inputs; full read-only replay
  khớp3valid/3detected.
- Pipeline evaluation summary báo tester calls0vì dùng frozen producer, không có
  model calls ở scoring stage. Native cost được tính riêng trong native_costs.json;
  không diễn giải số0đó thành không gọi model.
- Source `generators/methods.py` đang được phiên khác chỉnh không bị sửa. Diagnostic
  inject một frozen direct-input producer vào pipeline hiện có; không phụ thuộc
  method-generation implementation đó.

Output `final/out/boundary_luna_direct3_20261106`, gồm raw CLI event log, single
attempt ledger, request, model final output, encoded/frozen batches, evaluation,
replay receipt và postrun audit. [Audit JSON](boundary_luna_direct3_2026-11-06.json).

Kết quả xác nhận Luna trong điều kiện feedback/direct-schema này có thể dựng
được3input mà Qwenchecked6không giữ được. Chưa có evidence để quy riêng gain cho
model strength, bỏ schema, hay feedback; không đổi/promote default BVA từ đây.
