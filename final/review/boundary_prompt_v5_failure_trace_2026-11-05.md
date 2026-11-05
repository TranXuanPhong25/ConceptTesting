# Trace 6 task chưa chạm bug trong protocol 5

Trace từ artifact đã lưu: task data → templates → selection → compiled targets
→ raw context → constructor → accepted inputs → native outcomes. Không gọi model,
không chạy lại PUT/reference, không sửa pipeline. Đã replay riêng pure constructor
cho 72/157 và xác nhận output khớp hoàn toàn input đã lưu. Toàn bộ 11 file BVA
hiện tại có hash khớp launch manifest của run này.

Đây là trace của quyết định/output quan sát được, không suy diễn hidden reasoning
của model. Những phần nhận xét về semantics được đối chiếu trực tiếp với spec,
contract và PUT source trong saved prompt.

Run: `final/out/boundary_known_bug10_prompt_v5_20261105`.
Chi tiết máy đọc được, gồm task data, selection và từng seed/target/output:
[failure_trace.json](boundary_prompt_v5_failure_trace_2026-11-05.json).

| Task | Raw context response | Input cuối cùng | Điểm mất |
|---|---|---|---|
| 2 | Không gọi context | `[]` | Selection abstain |
| 11 | Không gọi context | `[]` | Selection abstain |
| 16 | JSON bị cắt; đọc được 17 record hoàn chỉnh ở prefix | `[]` | Bind sai characteristic, rồi generation truncation |
| 23 | Không gọi context | `[]` | Selection dùng semantics của PUT làm đúng, rồi abstain; thiếu characteristic mã ký tự |
| 72 | 8 record | 7 input; 1 duplicate | Chọn context chỉ có số dương |
| 157 | 20 record | 6 input; 14 ngoài domain | False mismatch tại domain edge; template còn thu hẹp float thành int |

## Task 2 — không có input; model phủ nhận integer crossing

PUT dùng:

```python
f = Fraction(number).limit_denominator()
integer_part = f.numerator // f.denominator
fractional_num = f.numerator - (integer_part * f.denominator)
return float(Fraction(fractional_num, f.denominator))
```

Code đưa cho selector template `number:value`, numeric kind `float`, có cả
`step` và `float_adjacent`. Candidate guard duy nhất là contract `number > 0`.
Template là family của characteristic; code chưa enumerate sẵn candidate cụ thể
ở integer 1. Selector phải tự suy ra integer crossing từ spec/code.

Selection trả `no_applicable_boundary`, với reason:

> The specification defines a continuous mathematical operation (extracting the
> fractional part) ... the function's behavior is uniform across the entire valid
> domain (0, +inf).

Đây là nhận định semantic sai: fractional part có discontinuity ở các integer.
Saved prompt đã nói rõ integer crossings cho truncation/fractional arithmetic
và code/edge không cần spec nêu threshold. Khả năng biểu diễn float neighbor có
sẵn; model không sử dụng nó. Không có validator nào loại input ở task này:
model đã trả boundaries rỗng ngay từ đầu.

`BoundaryValueAnalysis.run_stages` dừng khi selection không phải `selected`, nên
không tạo `compiled_targets.json`, không gọi context và trả `inputs: []`.

Witness đã biết từ diagnostic trước: `(0.9999999999999999,)` có expected
`0.9999999999999999` nhưng PUT trả `0.0`. `limit_denominator()` có thể xấp xỉ số
gần integer thành chính integer đó trước bước lấy phần lẻ. Witness này không
được sinh trong run v5.

Evidence: [selection](../out/boundary_known_bug10_prompt_v5_20261105/tasks/2/boundary/6/selection.json),
[saved prompt](../out/boundary_known_bug10_prompt_v5_20261105/tasks/2/boundary/6/select_prompt.json).

## Task 11 — không có input; equality che mất common empty edge

PUT chuyển hai string sang integer:

```python
n = len(a)
val_a = int(a, 2)
val_b = int(b, 2)
```

Contract yêu cầu hai string binary và `len(a) == len(b)`, không cấm empty string.
Templates có `a:length`, `b:length`; public guard ghi đúng equality này.
Không có concrete empty-edge candidate được code dựng sẵn.

Selection trả:

> No numeric thresholds or ordered ranges exist ... the only constraint is
> equality between two parameters, which does not define a boundary value for
> a single quantity.

Model đồng nhất việc không có independent length threshold trong equality với
việc không có natural edge. Common length 0 vẫn hợp lệ. Known witness `('', '')`
đi tới `int('', 2)` và lỗi, trong khi expected là `''`.

Trace thực tế dừng ở selection, trả `inputs: []`; không phải đã sinh hai string
rồi bị joint-constraint validator loại. Menu hiện tại biểu diễn được length 0.
Việc phải giữ hai độ dài bằng nhau là joint construction constraint, không phải
lý do để loại empty-edge test ở selection.

Evidence: [selection](../out/boundary_known_bug10_prompt_v5_20261105/tasks/11/boundary/1/selection.json),
[saved prompt](../out/boundary_known_bug10_prompt_v5_20261105/tasks/11/boundary/1/select_prompt.json).

## Task 72 — 7 input; sum target đúng, path condition gây bug bị bỏ qua

PUT cộng dồn rồi reject trước khi duyệt hết list:

```python
weight += q[i]
if weight > w:
    return False
```

Spec xét **total sum** của palindrome. PUT xét cả **prefix sums**. Model chọn:

- `b1`: length 0, sides `at/above`.
- `b2`: `sum(q) <= w`, sides `below/at/above`, reach `q is a palindromic list`.

Worksheet đánh `b2.alignment = operator`, quote `if weight > w:`. Dấu `>` của
nhánh reject tự nó không sai so với `<=` của điều kiện accept. Khác biệt thực sự
là `weight` còn là prefix sum, chưa phải total sum. Reach/infect note không giữ
được điều kiện này; context stage được hướng đến palindrome và sum threshold.

Mỗi obligation có context budget 4; raw response chỉ có 8 record trong cap 20.
Model chỉ khai báo `palindrome`, không khai báo sign requirement. Tất cả w dương,
tất cả nonempty seed chứa số dương. Spec examples và 6 existing inputs đưa vào
context cũng chỉ có số dương; đây là similarity quan sát được, chưa phải causal
ablation chứng minh model bị anchor bởi examples.

| Raw index | Obligation | Model đưa seed `(q,w)` | Target code tính | Sau constructor | Kết quả |
|---:|---|---|---:|---|---|
| 0 | `b1:at` | `([],10)` | length 0 | `([],10)` | giữ |
| 1 | `b1:above` | `([3],10)` | length 1 | `([3],10)` | giữ |
| 2 | `b2:below` | `([1,2,1],10)` | sum 9 | `([1,7,1],10)` | giữ |
| 3 | `b2:at` | `([2,2,2],6)` | sum 6 | `([2,2,2],6)` | giữ |
| 4 | `b2:above` | `([3,3,3],6)` | sum 7 | `([3,1,3],6)` | giữ |
| 5 | `b2:below` | `([1],10)` | sum 9 | `([9],10)` | giữ |
| 6 | `b2:at` | `([5],5)` | sum 5 | `([5],5)` | duplicate base input, loại |
| 7 | `b2:above` | `([6],5)` | sum 6 | `([6],5)` | giữ |

`[1,7,1]` và `[3,1,3]` là output của constructor, không phải literal model viết.
Vì requirement là palindrome, code giữ hai đầu và sửa phần tử giữa:
`middle = target - sum(other_elements)`. Hai seed tương ứng cho ra `9-1-1=7`
và `7-3-3=1`.

Trace PUT của các input sau construction:

| Input cuối `(q,w)` | Prefix sums | Native result, cả 2 repeats |
|---|---|---|
| `([],10)` | `[]` | `True`, pass |
| `([3],10)` | `[3]` | `True`, pass |
| `([1,7,1],10)` | `[1,8,9]` | `True`, pass |
| `([2,2,2],6)` | `[2,4,6]` | `True`, pass |
| `([3,1,3],6)` | `[3,4,7]` | `False`, pass |
| `([9],10)` | `[9]` | `True`, pass |
| `([6],5)` | `[6]` | `False`, pass |

Các prefix sum đều không giảm. Với các input này, khi prefix vượt w thì total
cũng vượt w; early return chưa tạo khác biệt với spec. Known witness
`([-1,-1],-2)` khác: prefix đầu `-1 > -2` làm PUT trả False ngay, trong khi total
`-2 <= -2` và list balanced nên expected True.

Không có negative context nào bị validator loại: raw model response đã không
có số âm. Property preservation làm đúng công việc được yêu cầu; việc chọn
family âm/mixed-sign vẫn chỉ là prompt guidance. Budget chưa dùng hết và
`w`/seed không được giữ cố định qua các side; code chưa enforce cross-side
context-family consistency.

Evidence: [raw context response](../out/boundary_known_bug10_prompt_v5_20261105/tasks/72/calls/bva_4_inputs/response.json),
[compiled targets](../out/boundary_known_bug10_prompt_v5_20261105/tasks/72/boundary/4/compiled_targets.json),
[accepted/rejected inputs](../out/boundary_known_bug10_prompt_v5_20261105/tasks/72/boundary/4/generation.json).

## Task 16 — output cuối rỗng; 3 lỗi nối tiếp trong trace

PUT chạy `ord(char)` sau `.lower()`, dùng array 256 và bỏ qua code >= 256.
Menu chỉ có `length`, `run_length`, `parsed_float`; không có code-point
characteristic. Selection reason nhận ra code-point boundary, nhưng trả:

- `b1`: string length 1 → targets 0/1/2.
- `b2`: string length 256 → targets 255/256/257.

Explanation của b2 còn nói length 256 là minimum để có thể chứa mọi ASCII code.
Đó không phải điều kiện của bug: một string chỉ dài 1, như `'Ā'`, đã đủ.
`ord(char)` và `len(string)` là hai quantity khác nhau. Code quote
`seen = [False] * 256` có thật, nhưng không chứng minh threshold length 256.

Validator nhận cả hai: kiểm template reference, numeric target và quote có trong
source, chưa kiểm semantic entailment giữa array capacity/ord và string length.
`b2.binding_status` chỉ là `llm_semantic_hypothesis`.

Compiler cấp budgets 4/4/3/3/3/3 cho 6 obligation. Trong raw generation stream,
model lặp context và tự viết chuỗi dài thay vì dùng small seed. Prefix đọc được:

| Obligation | Số record hoàn chỉnh trong prefix | Seed quan sát được |
|---|---:|---|
| `b1:below` | 4 | `''` lặp 4 lần |
| `b1:at` | 3 | `'a'` lặp 3 lần |
| `b1:above` | 3 | `'ab'`, `'aa'`, `'AB'` |
| `b2:below` | 4 | cùng một ASCII seed length 486 |
| `b2:at` | 3 | cùng một ASCII seed length 487 |

Có 17 record hoàn chỉnh nhưng chỉ 7 record distinct trong prefix. Các long seed
chỉ chứa ASCII, max character code 126; chúng không đáp ứng chính b2.reach đã
viết là có character code >= 256. Nếu được constructor xử lý, length sẽ được
code sửa về target, nhưng content ASCII vẫn không chạm known bug.

Response dừng ở token 2048, giữa string của `b2:above`, tổng 6088 characters.
`finish_reason = length` bị `parse_response` reject trước khi xử lý từng record.
Kết quả thật là `invalid_generation`, `inputs: []`. Không có partial record nào
được chấp nhận hay chạy; 17 record nói trên chỉ được đọc để forensic analysis.

Evidence: [selection](../out/boundary_known_bug10_prompt_v5_20261105/tasks/16/boundary/4/selection.json),
[raw generation stream](../out/boundary_known_bug10_prompt_v5_20261105/tasks/16/calls/bva_4_inputs/response.json),
[generation result](../out/boundary_known_bug10_prompt_v5_20261105/tasks/16/boundary/4/generation.json).

## Task 23 — không có input; model lấy byte length của PUT làm intended behavior

Spec: `Return length of given string`. PUT:

```python
return len(string.encode('utf-8'))
```

Selection trả `no_applicable_boundary`, reason kết thúc bằng:

> the function simply returns the byte length of the input string.

Spec không nói byte length. Đây là semantics của implementation được model dùng
để giải thích applicability, bỏ qua khác biệt character length với encoded byte
length. Known witness ở U+0080 có 1 character nhưng 2 UTF-8 bytes; các ASCII
examples trong spec không phân biệt hai cách tính này.

Menu giống task 16: `length`, `run_length`, `parsed_float`, không có code-point
characteristic. Vì vậy có cả semantic selection failure và capability gap.
Không thể kết luận chỉ thêm characteristic là model sẽ chọn đúng. Trace thực
tế dừng ngay selection, không context call, `inputs: []`.

Evidence: [selection](../out/boundary_known_bug10_prompt_v5_20261105/tasks/23/boundary/7/selection.json),
[saved prompt](../out/boundary_known_bug10_prompt_v5_20261105/tasks/23/boundary/7/select_prompt.json).

## Task 157 — 6 input đều xa boundary; 14 record còn lại ngoài domain

Contract cho phép int/float và yêu cầu a,b,c > 0. PUT reject a,b,c <= 0, rồi
kiểm `abs(lhs-rhs) < 1e-9`. Known bug ở một cạnh sát cạnh huyền: residual khác 0
nhưng nhỏ hơn tolerance của PUT.

Selection bỏ qua residual và chọn `a > 0`, threshold 0, với reason:

> Code uses strict inequality (<= 0) for rejection while contract requires strict
> positivity (> 0), creating a boundary mismatch at 0.

Đây là false mismatch: reject `a <= 0` khớp domain `a > 0`. Model còn gắn
`boundary_kind: behavior` và sides below/at/above dù side_rules của nó ghi rõ
below/at là invalid. Validator nhận dưới dạng `matched_public_guard`, nhưng
không sửa role hoặc prune excluded sides ở bước này.

Compiler dùng integer step 1, dựng a=-1/0/1 và chia context budgets 7/7/6.
Raw model response theo đúng các obligation này. Constructor gán lại a theo
target, giữ b,c; 14 record a=-1 hoặc0 bị domain checker reject đúng. Sáu record
a=1 còn lại được giữ:

| Input cuối | `abs(lhs-rhs)` | PUT / reference, 2 repeats |
|---|---:|---|
| `(1,4,5)` | 8 | False / False |
| `(1,6,8)` | 27 | False / False |
| `(1,7,25)` | 575 | False / False |
| `(1,5,7)` | 23 | False / False |
| `(1,12,13)` | 24 | False / False |
| `(1,8,17)` | 224 | False / False |

Model đặt b,c gần các số trong existing input examples; 5/6 cặp b,c cuối cùng
trùng cặp trong existing inputs. Tuy nhiên a đã bị cố định về 1, nên các tuple
này đều có residual lớn, cách xa vùng sát 0 mà bug cần. Chọn giá trị b,c giống
Pythagorean examples không giữ được quan hệ Pythagorean khi thay a.

Có một hạn chế upstream khác, tách biệt với lựa chọn sai đã quan sát: 11 base
inputs chỉ có int, hàm không có annotation. InputTypeExtraction ghi observed
int; BoundaryTemplates đặt cả a/b/c thành `numeric_kind: int`, chỉ cho `step`,
dù contract cho phép float. Vì thế menu hiện tại còn cấm controlled
`float_adjacent` trên a/b/c. Nó cũng không biểu diễn threshold như
`sqrt(a*a+b*b)` hay characteristic Pythagorean residual. Đây là giới hạn của
không gian candidate, không chỉ là ranking chọn nhầm trong một menu đầy đủ.
Điều này không có nghĩa mọi non-target context float đều bị cấm; hạn chế đang
nói đến characteristic được code điều khiển.

Evidence: [type evidence](../out/boundary_known_bug10_prompt_v5_20261105/tasks/157/boundary/3/input_types.json),
[selection](../out/boundary_known_bug10_prompt_v5_20261105/tasks/157/boundary/3/selection.json),
[compiled targets](../out/boundary_known_bug10_prompt_v5_20261105/tasks/157/boundary/3/compiled_targets.json),
[raw context](../out/boundary_known_bug10_prompt_v5_20261105/tasks/157/calls/bva_3_inputs/response.json).

## Các điểm code giải thích flow

- [pipeline.py](../src/modular/boundary_value_analysis/pipeline.py): selection
  khác `selected` dừng trước construction/generation.
- [stages.py](../src/modular/boundary_value_analysis/stages.py): quote presence
  và schema checks không chứng minh binding/mismatch đúng; truncated response
  bị reject nguyên envelope trước per-record validation.
- [templates.py](../src/modular/boundary_value_analysis/templates.py): numeric
  kind từ type evidence có thể thu hẹp observed int thành integer neighborhood.
- [construction.py](../src/modular/boundary_value_analysis/construction.py):
  compile sides, chia context budget, gán target, sửa tâm palindrome và kiểm domain.
- [binding.py](../src/modular/boundary_value_analysis/binding.py): behavior có
  thể match public domain guard nhưng không bị chuyển thành domain role;
  final domain check mới reject input ngoài contract.

Các file/run output cũ được giữ nguyên. Phân tích này chỉ thêm report/trace và
memory pointer; không có code fix hay model rerun mới.
