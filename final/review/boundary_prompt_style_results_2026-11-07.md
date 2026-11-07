# Direct / soft BVA / worksheet: scheduled diagnostic result

Controller chạy đúng19:51:15ngày6/11/2026(Asia/Ho_Chi_Minh), đủ readiness và hoàn
tất19:57:06.9requests đều nhận response,0unknown, tất cả finish_reason=stop.
Không task expansion, semantic retry hay prompt/source edit sau freeze.

| Arm | Task2 | Task11 | Task157 | PUTs detected | Valid novel inputs | Total tokens |
|---|---|---|---|---:|---:|---:|
| direct | Có | Không | Có |2|60|3.892|
| soft_bva | Có | Không | Có |2|58|3.934|
| worksheet | Không | Không | Có |1|54|6.942|

Mỗi arm có3calls, cap20inputs/task, cùng qwen3.5-27b-awq, một exactPUT/task,
spec/contract/base calls/system/output schema giống nhau; temperature0.7,
seed314159+task,max_tokens2048/context8192. Only guidance block differs. All9
outputs freeze before corrected-reference/PUT evaluation; input values chỉ được
encode, không có target compiler/applicability gate hoặc tool use của model.

## Task2: worksheet thiếu input đủ sát integer phía dưới

Direct có các input fail ổn định:

```python
0.999999999
0.9999999999999999
```

Soft BVA có:

```python
999.9999999999999
2.9999999999999996
```

Các input này có phần lẻ gần1, nhưng Fraction.limit_denominator của PUT xấp xỉ
thành integer và trả0.0. Worksheet vẫn sinh19distinct calls chứ không abstain,
nhưng các giá trị quanh integer chủ yếu là0.9/1.0/1.1và100.0000001. Có
999999.999999nhưng giá trị đó vẫn được limit_denominator giữ một fractional
rational, nên không tạo cùng lỗi round-to-integer. Các pairs gần1/3,0.123456...
hay10.5không thay thế được near-integer-below condition cần cho bug này.

Worksheet có20rawrecords, trong đó0.3333333333333333và0.33333333333333331decode
thành cùng float nên common parser giữ19. Không có truncation hay constraint
rejection làm mất một witness đã được sinh đúng. Khác biệt nằm ở concrete values.

## Task11: cả3arms đều bỏ empty string

Direct bắt đầu với strings length2,3...; soft và worksheet có singleton strings,
nhưng không arm nào sinh `('', '')`. Sau encoding có20calls/arm; soft mất1novel
input vì base duplicate. Tất cả input được chạy đều passPUT1.

Vì direct cũng miss trong cùng single-PUT packet, không thể quy toàn bộ empty-edge
failure cho worksheet/applicability gate. Historical naive164thấy10implementations
và sinh empty input, còn trial này chỉ thấy1PUT. Visibility/context/sampling có
thể là explanation, chưa isolate riêng yếu tố đó.

## Task157: bỏ hard gate/compiler cho phép cả3arms tìm arithmetic-sensitive inputs

Mỗi arm đều có ít nhất một novel valid witness theo corrected benchmark oracle:

| Arm | Ví dụ args | Reference | PUT, cả2native repeats |
|---|---|---|---|
| direct | `(1,1,1.4142135623730951)` |False|True|
| soft_bva | `(0.1,0.1,0.1414213562373095)` |False|True|
| worksheet | `(0.001,0.001,0.00141421356)` |False|True|

Worksheet ở setting này không bị bắt chọn một scalar threshold0và không bị
integer-only controlled-template constraint của v5. Nó sinh15calls và đều hợp
domain. Direct/soft sinh20; soft có1base duplicate. Raw worksheet vẫn là cùng
family instruction5steps nhưng output trực tiếp, không phải full2-stage v5.
Không được lấy việc worksheet bắt157ở đây làm bằng chứng bước nào của fullv5
được sửa riêng lẻ; nhiều giới hạn orchestration đã được loại đồng thời.

## Diễn giải có phạm vi

- Thêm soft BVA không tăng số bug tasks so với direct trong3case này.
- Worksheet tốn khoảng1.78lần total tokens của direct và mất task2. Kết quả
  tương thích với hypothesis rigid instructions có thể làm giảm useful exploration.
- Chưa chứng minh prompt length hay “mất tính tự nhiên” là nguyên nhân duy nhất:
  content/salience/wording cũng đổi, mỗi task/arm chỉ có1response, tasks đã được
  nhìn để thiết kế diagnostic. Không có statistical/general-efficacy claim.
- Task11cho thấy bỏ scaffolding tự nó chưa đảm bảo nhớ mọi natural edge. Task157
  cho thấy direct-output interface có thể tránh một số mất mát của fullpipeline.

Giữ stablev5default và historical baselines nguyên trạng; không tự promote soft
BVA hoặc expand run. Đây là mechanism signal để thiết kế bước tiếp, không phải
held-out evaluation hoặc một kết quả detection-rate đại diện.

## Accounting / audit

-9logical calls,9physical received responses,0unknown.9.435prompt +5.333completion
  =14.768known tokens. Direct:2.237/1.655;soft:2.417/1.517;
  worksheet:4.781/2.161(prompt/completion).
- All9requests có actual saved identity khớp frozen requests. Tất cả complete,
  không truncation. Không oracle rejection ngoài2base duplicates; một float
  duplicate nội bộ được loại trước scoring ở task2worksheet.
-92frozen source/data/request/controller files và1.205prior output files giữ
  nguyên hash khi kiểm lại7/11.3input-freeze hashes và generation barrier khớp.
- Stable failures verified ở2native repeats; full read-only replay đã khớp.
  Scheduler và runner đều terminal, không còn process chạy.

Output `final/out/boundary_prompt_style3_20261106`; machine-readable
[audit/results](boundary_prompt_style_results_2026-11-07.json). Exact requests,
raw model responses, decoded inputs, native outcomes, token ledger, replay receipt,
schedule/attempt records được giữ trong run. Không gọi model mới ở lần kiểm7/11.
