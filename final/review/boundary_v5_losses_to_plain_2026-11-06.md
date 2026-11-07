# Vì sao boundary v5 thua naive ở 2 / 11 / 157

Đối chiếu raw requests/responses và checkpoints của v5 với original plain
generation; native outcomes lấy từ rescore cùng corrected oracle. Không gọi
model mới, không sửa pipeline hoặc thêm test generation. Chỉ tính stablev5,
không gộp checked6/Luna. Một vài phép tính stdlib/float được kiểm độc lập,
không chạy lại PUT để thay outcome.

Kết luận: có hai loại lỗi rõ trong artifact: **abstention chặn generation** ở
2/11 và **chọn target sai rồi khóa toàn bộ input quanh nó** ở157. Thêm hướng dẫn
về BVA không bảo đảm model áp dụng đúng; menu/ranking/schema còn tạo thêm điểm
mất. Naive vẫn sinh boundary values và có nhiều implementation evidence hơn.

## Information access thực tế khác nhau

| Task | PUTs trong naive prompt | PUTs trong BVA selector | Naive temperature | BVA selection temperature |
|---|---:|---:|---:|---:|
|2|9|1|0.7|0.0|
|11|10|1|0.7|0.0|
|157|10|1|0.7|0.0|

Naive được yêu cầu sinh20small distinct inputs để tìm spec violations, thấy
public spec/contract, original base-test assertions và nhiều implementations
kèm line numbers. BVA selector thấy spec/contract, một PUT, compact type evidence,
candidate templates/public guards; base literal calls chỉ đưa vào context sau
khi selection thành công. Nên “nhiều hướng dẫn về boundary” không tương đương
“nhiều evidence hơn” hoặc “thêm BVA vào đúng cùng một information packet”.

Chính xác ở task2, naive thấy PUT8có `if number < 1.0:` và các cách tính bằng
floor/modulo/int cạnh PUT6Fraction. Ở11, naive thấy nhiều zip/join implementations
bên cạnh int-conversion implementations. Ở157, naive thấy exact-equality và
tolerance variants cạnh nhau. Những đối chiếu này có thể hỗ trợ chọn input;
đây là một explanation khả dĩ, chưa có ablation chứng minh riêng effect đó.

## Task 2: có đủ constructor, nhưng model phủ nhận boundary tồn tại

TargetPUT6:

```python
f = Fraction(number).limit_denominator()
integer_part = f.numerator // f.denominator
fractional_num = f.numerator - integer_part * f.denominator
return float(Fraction(fractional_num, f.denominator))
```

Spec yêu cầu phần lẻ của positive finite float. Plain sinh20inputs, trong đó có
một neighborhood quan sát được:

```text
0.9999999999
1.0
1.0000000001
```

Hai plain inputs làm PUT fail là0.9999999999và999.9999999999. Giá trị đầu có
expected0.9999999999nhưng PUT0.0. `Fraction(...).limit_denominator()` cho hai giá
trị đó lần lượt là1và1000, làm mất phần lẻ trước bước integer/fraction split.
Ở integer crossing, expected fractional part có jump; model BVA lại gọi nó là
continuous và uniform.

BVA đã có template `number:value`, numeric kindfloat, neighborhood modes step/
float_adjacent. Prompt còn nói integer crossings cho truncation/fractional
arithmetic và code/edge không cần spec nêu numeric threshold. Nhưng response:

> The specification defines a continuous mathematical operation ... the
> function's behavior is uniform across the entire valid domain (0, +inf).

Selection statusno_applicable_boundary, finishstop, chỉ129completion tokens trên
budget4096. Pipeline dừng trước compiler/context:0inputs. Không phải float
constructor thất bại, invalid constraint, thiếu token budget hoặc không biểu
diễn được quantity. Mất do semantic abstention và orchestrator tin nhãn đó để
không thử bất kỳ boundary candidate nào.

Naive thành công không chứng minh nó reasoning Fraction đúng. Artifact chỉ
chứng minh nó đã chọn concrete near-integer inputs, trong prompt còn có code
threshold1.0từ implementation khác. Không cần vượt qua một applicability gate.

Evidence: [BVA selection](../out/boundary_known_bug10_prompt_v5_20261105/tasks/2/boundary/6/selection.json),
[BVA request](../out/boundary_known_bug10_prompt_v5_20261105/tasks/2/boundary/6/select_prompt.json),
[naive request](../out/v11_concept_inputs/tasks/2/calls/plain/request.json),
[naive raw response](../out/v11_concept_inputs/tasks/2/calls/plain/response.json).

## Task 11: biến joint construction constraint thành lý do loại edge

TargetPUT1:

```python
n = len(a)
val_a = int(a, 2)
val_b = int(b, 2)
```

Contract cho phép binary strings, cầnlen(a)==len(b), không có minimum length.
Empty set là subset của {'0','1'}, nên hai empty strings hợp domain. Plain đưa
`('', '')` ngay record đầu. Reference trả'', PUT lỗiValueErrorởint('',2).

BVA có `a:length`, `b:length`; public guard đã ghi equality. Nhưng response:

> the only constraint is equality between two parameters, which does not define
> a boundary value for a single quantity.

Đúng là equality không tự cho một numeric threshold cố định. Nhưng **common
length0vẫn là natural edge**. Điều kiện hai length bằng nhau cần được giữ khi
dựng input, không phải lý do phủ nhận edge. Model bỏ qua empty edge dù prompt
đã cho phép. Selectionno_applicable, finishstop82tokens; không context call,
không có input nào bị validator loại ở đây.

Naive không cần gắn label threshold/template/source_quote trước khi đề xuất hai
literal rỗng. Các implementation zip/join trong packet cũng cho thấy một cách
biểu diễn cùng spec có thể xử lý empty sequence khác conversion-to-int.
Không có bằng chứng naive cần “ít kiến thức BVA” để thắng; nó đơn giản không
bị gate bởi một khái niệm applicability mà selector đang hiểu sai.

Evidence: [BVA selection](../out/boundary_known_bug10_prompt_v5_20261105/tasks/11/boundary/1/selection.json),
[public guards](../out/boundary_known_bug10_prompt_v5_20261105/tasks/11/boundary/1/public_guards.json),
[naive request](../out/v11_concept_inputs/tasks/11/calls/plain/request.json),
[naive raw response](../out/v11_concept_inputs/tasks/11/calls/plain/response.json).

## Task 157: false mismatch + capability narrowing + mất relation trong context

TargetPUT3:

```python
if a <= 0 or b <= 0 or c <= 0:
    return False
sides = sorted([a, b, c])
lhs = sides[0]**2 + sides[1]**2
rhs = sides[2]**2
return abs(lhs - rhs) < 1e-9
```

Plain sinh cả integer Pythagorean tuples, non-right tuples và float tuples.
`(0.5,1.2,1.3)` làm referenceFalse, PUTTrue trong corrected benchmark semantics:

```text
lhs = 1.69
rhs = 1.6900000000000002
abs(lhs-rhs) = 2.220446049250313e-16 < 1e-9
```

Naive còn sinh `(3.0,4.0,5.0000000001)` dù input này không làm đúng PUT3fail.
Không phải mọi numerical perturbation đều hữu ích, nhưng batch vẫn giữ được
một input gần arithmetic equality. Không suy ra hidden reasoning của model từ
một tuple; kết quả nói về input cụ thể theo oracle đã chọn.

BVA chọn `a:value > 0`, threshold0, alignmentoperator và nói contract>0mâu
thuẫn với code reject<=0. Đó là false mismatch: complement của rejecta<=0là
điều kiện để tiếp tụca>0. Nó ưu tiên domain edge nhìn thấy được thay vì xét
arithmetic residual ở return.

Compiler cấp quotas7/7/6choa=-1/0/1.14recordsa=-1/0bị domain checker loại đúng.
Sáu input cuối đều cố định a=1:

```python
(1,4,5)
(1,6,8)
(1,7,25)
(1,5,7)
(1,12,13)
(1,8,17)
```

Residual tuyệt đối lần lượt8,27,575,23,24,224: rất xa vùng0/tolerance. Việc lấy
b,cgiống Pythagorean examples không giữ relation khi ađã bị constructor đặt1.
Tất cả6inputs pass, PUT/reference đềuFalse. Selection finishstop416tokens,
không truncation.

Hai limitation của code góp phần làm không gian tìm kiếm hẹp:

- Base inputs chỉ int, không annotations; v5templates suy numeric_kindint và
  chỉ chostep, dù contract cho phép float. Controlled float_adjacent bị khóa.
  Điều này không cấm mọi non-target context parameter mang float.
- Threshold expressions chỉ có constant hoặc một parameter/aggregate operation,
  chưa biểu diễn hypotenuse/Pythagorean residual nhiều operands. Không đủ để
  điều khiển trực tiếp một cạnh phụ thuộc hai cạnh kia.

Validator kiểm quote/schema/domain nhưng không chứng minh alignmentoperator
đúng hoặc target liên quan bug. `matched_public_guard` chỉ xác nhận có domain
clause phù hợp, không xác nhận alleged spec/code mismatch. Constructor làm đúng
target được giao, nhưng toàn bộ batch bị khóa quanh target không liên quan.

Evidence: [BVA selection](../out/boundary_known_bug10_prompt_v5_20261105/tasks/157/boundary/3/selection.json),
[compiled targets](../out/boundary_known_bug10_prompt_v5_20261105/tasks/157/boundary/3/compiled_targets.json),
[generation](../out/boundary_known_bug10_prompt_v5_20261105/tasks/157/boundary/3/generation.json),
[type evidence](../out/boundary_known_bug10_prompt_v5_20261105/tasks/157/boundary/3/input_types.json),
[naive request](../out/v11_concept_inputs/tasks/157/calls/plain/request.json),
[naive response](../out/v11_concept_inputs/tasks/157/calls/plain/response.json).

## Vì sao thêm kiến thức vẫn có thể thua

**Quan sát chắc chắn từ code/artifact:**

1. “BVA knowledge” là instructions, không phải quantity/predicate interpretation
   đã được verify. Model có thể phát biểu sai ngay ở một bước bắt buộc.
2. Selection là hard gate: sai ở2/11dẫn tới0test, dù compiler có capability cần.
3. Chọn một boundary là bottleneck của diversity: sai ở157làm mọi context dùng
   cùng scalar target; tăng số context không tự mở lại arithmetic relation.
4. Quote/schema checks cho phép semantic claim sai đi tiếp nếu hình thức hợp lệ.
5. Một số abstract representations thu hẹp domain/capability hơn input contract.
6. Actual information packets khác: nhiều method instructions hơn nhưng ít
   alternative implementations và không có original base assertions ở selection.

**Các giả thuyết chưa được isolate:** instruction load, vai trò “test analyst”
khác với “generate tests”, model thiên về threshold có quote/constant rõ, lợi
ích từ nhiều implementations, và temperature0.7vs0.0. Không được lấy bảng3losses
để tuyên bố yếu tố nào là nguyên nhân duy nhất. Rút prompt ở trial trước cũng
không sửa157, nên chưa thể quy mọi lỗi cho prompt dài.

Kết luận thực dụng: BVA có thể giúp chính xác hóa target **sau khi** quantity/
condition/context đã đúng, nhưng kiến trúc hiện tại dùng chính phán đoán chưa
được verify đó để giới hạn hoặc loại toàn bộ candidate search. Đây là cơ chế
thua quan sát được, không phải bằng chứng boundary testing vốn kém hơn naive.

Nếu tiếp tục, cần kiểm tra cùng model/information packet/sampling rồi tách
applicability gating, capability restriction và target selection. Các input đã
nhìn ở ba task này chỉ dùng mechanism checks, không được xem như held-out gain.
Không chạy ablation hay thay code trong phân tích này.
