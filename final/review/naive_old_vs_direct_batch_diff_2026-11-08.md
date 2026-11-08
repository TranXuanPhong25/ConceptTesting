# Naive cũ (82 PUT) và Direct batch mới (68 PUT): diff đã kiểm tra

Hai arm đều không có BVA guidance nhưng không phải cùng một treatment. Khác biệt
đã xác nhận là instruction, output schema/adapter và response được sinh ở lần khác.
Context giống nhau trên phần lớn task; scorer giữ cùng điều kiện xác nhận lỗi.
Chưa cô lập tác động riêng của từng khác biệt. Đây là phân tích artifact có sẵn,
không gọi model/tokenizer, không execute reference/PUT và không sửa input của run.

## 1. Nguồn và kết quả

| Thuộc tính | Naive cũ sau packaging repair | Direct batch mới |
|---|---|---|
| Generation | `final/out/v11_concept_inputs/tasks/*/calls/plain` | `final/out/bva_batch_matched164_evaluation_20261108_140053/generation/tasks/*/calls/direct` |
| Evaluation | `final/out/naive_packaging_audit_20261108_0200/evaluation` | `final/out/bva_batch_matched164_evaluation_20261108_140053/evaluation` |
| Arm | `plain` | `direct` |
| PUT được evaluate | 1454 | Cùng đúng 1454 PUT |
| PUT có detection ngoài base tests | 82 | 68 |
| Input mới hợp lệ | 2758 | 2926 |
| Task có detection | 29 | 21 |
| PUT có stable wrong-value witness | 53 | 46 |

Hai run cùng phát hiện 52 PUT; old-only 30, new-only 16. Chênh lệch ròng old−new
là14 PUT. Hai run không chỉ khác nhau ở14 PUT.

## 2. Những gì giống nhau

- Served model name đều `qwen3.5-27b-awq`. Cùng tên không chứng minh weights/server
  state giống tuyệt đối giữa hai thời điểm.
- SYSTEM trong actual request giống từng ký tự:
  `You generate valid Python function inputs to expose implementation bugs.`
- Cùng temperature0.7,max output2048tokens,context8192tokens,input seed314159+
  task number. Requesttask72ở cả hai bên có seed314231.
- Cùng cách batch:1call/task,nhìn nhiều base-passing PUT,không có BVA guidance.
- Cùng spec/domain làm chuẩn,không yêu cầu model sinh expected outputs/assertions.
- Khi chấm82và68:cùng đúng1454targetPUT,cùng corrected HumanEval+ reference
  v0.1.10,fileSHA256 `7a0a41bdcaa5220dcb4f2e405349678a82853a42f6bbf8db837e520825c8c5af`.
- Comparator `equivalent()` giống AST,SHA256
  `3b4b9e4aa17fd79abe4f13edf51b20a8023ba1006467c95f781d45ed1b8647c1`.
  Không có đổi numerical tolerance hoặc expected-output semantics giữa hai số này.

## 3. Instruction khác nhau

| Nội dung | Naive cũ | Direct mới |
|---|---|---|
| Quota | `Generate exactly 20 ...` | `Generate up to 20 ...` |
| Ràng buộc kích thước | `Keep floats finite, integers bounded, strings/lists modest (normally <=30 elements), and execution under 3 seconds.` | `Keep values finite and inputs small enough for the execution budget; resource caps are not semantic boundaries.` |
| Chất lượng/số lượng | Có câu validity/diversity hơn lặp input nhưng mở đầu vẫn exactly20 | `Fewer valid calls are better than padding.` |
| Format | Python-literal strings `args/kwargs`; field `concept_id` | Named JSON values;field `guidance_id`;hướng dẫn tuple/set tag,defaultparameter và CallBuilder |
| Generic guidance cuối | `No additional analysis packet. Choose useful new tests from the information above.` | Không thêm guidance;user message kết thúc sau shared common prompt |

Không thêm checklist boundary vào Direct mới. Câu `resource caps are not semantic
boundaries` và toàn bộ instruction mới cũng được dùng cho Soft batch.

Actual old requests đều chỉ dùng common prompt + generic guidance:đã kiểm tra
156/156request. Oldpacket có analysis/cards/pool để phục vụ arm khác trong run
lịch sử nhưng chúng không xuất hiện trong `plain` request. Không được suy rằng
naive cũ thấy concept cards chỉ vì packet.json lưu các field đó.

## 4. Context: mức thay đổi thực tế

Quét actualpacket/request của157task eligible của run mới:

-153/157task:cùng visiblePUTIDs và cùng thứ tự.
-156/156task mà cả hai bên có request:spec,contract,original base tests giống
  từng ký tự sau khi tách heading.
-1437PUT code xuất hiện ở cả hai bên:compact code và original line labels đều
  giống từng ký tự. Không có đổi từ compact code sang raw code giữa hai run này.
-4taskkhác visibility do gỡ resource exclusions lịch sử:

| Task | Số PUT visible cũ | Số PUT visible mới |
|---|---:|---:|
| 144 | 8 | 9 |
| 147 | 3 | 10 |
| 150 | 2 | 10 |
| 160 | Không có request,resource skip | 1 |

Naive cũ loại17resource-riskPUTkhỏi context gốc. Packaging evaluation vẫn chấm
đủ1454targetPUT,nhưng giữ response/input cũ;task160vẫn0input. Direct mới có thêm
17PUTvisiblevà có requesttask160. Cả4task này đều0detectionở cả hai run,do đó
visibility thay đổi ở4task này không giải thích chênh lệch82−68 trong kết quả đã lưu.

## 5. Output schema và adapter

Ví dụ biểu diễn cùng giá trị cho `will_it_fly(q,w)`:

Naive cũ:
```json
{"inputs":[{"args":"([-1, -2, -1], -4)","kwargs":"{}","concept_id":null}]}
```

Direct mới:
```json
{"inputs":[{"arguments":{"q":[-1,-2,-1],"w":-4},"guidance_id":null}]}
```

Trong format cũ,model phải tự viết positional packing và singleton tuple comma.
Packaging audit sửa1250rawslots/64task khi có static signature/annotation/contract
proof,chỉ sửa wrapping,không đổi literal values. Không reparse invalid/truncated
responses hoặc tự sửa ambiguous binding. Các rawsource/receipt vẫn còn nguyên.

Direct mới đưa named values cho CallBuilder tự tạo args/kwargs và kiểm tra binding.
JSON strings không còn cần encode thêm Python tuple/list syntax. Nhưng JSON phải
dùng `true/false/null`,Python literal có thể dùng `True/False/None`. Parser hiện
đọc cả JSON envelope trước:chỉ một invalid JSON value có thể làm mất cả response.
Parser mới vẫn có legacy args/kwargs fallback sau khi JSON envelope parse thành công.

**Case thực tế task151:** Direct có `"lst": [True, False, 1, 2, 3]`.
`json.loads` lỗi tại line23,column17;finish_reason=`stop`,907completiontokens.
Đây không phải truncation. Direct giữ0encodedinputs/0validinputs/0detections.
Naive cũ có literal boolean trong chuỗiargs;packaging repair giữ20encodedinputs,
18novelvalidinputs và phát hiện10PUT. Riêng task151 đóng góp10PUT vào chênh lệch
ròng14PUT. Chưa suy ra boolean lỗi do chính format hay instruction nào gây ra.

**Case task23:** old có16validinputs,bao gồm`你好`,`🎉`,`café`;bắtPUT7.
Direct có20validinputs nhưng tập ASCII;không bắtPUT7. Context/visiblePUTgiống nhau.
Đây là khác nội dung input,không phải lỗi parser hoặc scorer.

## 6. Scorer: đổi lượng thực thi,giữ điều kiện detection

| Trường hợp | Full two repeats (82) | Confirm first failures (68) |
|---|---|---|
| Firstpass=pass | Chạy lần2nhưng không thể confirmedfail vì lần1đãpass | Bỏ lần2 |
| Firstpass=fail/error/timeout | Chạy lần2 | Chạy lần2 |
| Cả2lần thuộc fail/error/timeout | Tính failinginput | Tính failinginput |
| Firstpassfail,lần2pass | Không tính detection | Không tính detection |
| Thống kê unstable | So mọi input | Chỉ input đã retest |
| Reference/domain | Chạy2lần | Chạy2lần |

Với cùng input và cùng outcomes,hai scorer cho cùng detection predicate.
`fail` nghĩa là actual value khác expected;error/timeout cũng được tính vào tổng
detection nếu confirmed. Stable wrong-value metric chỉ lấy failở cả2lần.
Không được giải thích82→68 bằng tên scorer khác mà thiếu bằng chứng outcome drift.

Executor run mới còn có bản sửa C-call timeout:Python SIGALRM có thể không được
dispatch trong`reduce(operator.add,range(...))`. Outerwallguard10+timeoutseconds
chỉ trả timeout cho singleinput có active-user-call marker;startuphang vẫn là
infrastructureerror. Task60đã đi qua cả firstpass/confirmation. Đây là thay đổi
execution harness cần ghi riêng,không phải đổi reference hoặc tolerance. Run mới
giữ native checkpoints cũ cho60taskđã hoàn tất trước khi sửa.

## 7. Cách hiểu chênh lệch

82và68là hai lần sinh khác nhau,với instruction/outputschema/interface khác nhau.
153task có context giống nhau không làm cho model response giống nhau;seed giống
không triệt tiêu tác động của prompt khác,backend hoặc servingstate khác.

Đã xác nhận ít nhất hai dạng mất detection:response bị reject ởtask151và thiếu
Unicode partition ởtask23. Không có bằng chứng từ hai tổng số cho kết luận prompt
mới hay outputJSON mới kém hơn về semantic trên mọi task. Cặp đánh giá BVA guidance
đúng trong run mới vẫn là Direct68vàSoft73:với cùng packet/parser/scorer/budget,
chỉ guidance khác;shared52,Direct-only16,Soft-only21,wrong-value46và59.

Nguồn trực tiếp:
-`final/out/v11_concept_inputs/tasks/72/calls/plain/request.json`
-`final/out/bva_batch_matched164_evaluation_20261108_140053/generation/tasks/72/calls/direct/request.json`
-`final/out/bva_batch_matched164_evaluation_20261108_140053/generation/tasks/151/calls/direct/response.json`
-`final/out/naive_packaging_audit_20261108_0200/evaluation/modular_manifest.json`
-`final/out/bva_batch_matched164_evaluation_20261108_140053/evaluation/modular_manifest.json`

## Bổ sung: phân loại 30 PUT old-only theo input gây lỗi (saved artifacts, 0 model call)

Nghi vấn: câu mới `Keep values finite and inputs small enough for the execution budget;
resource caps are not semantic boundaries.` làm Direct bỏ giá trị biên lớn.

| Nhóm | PUT old-only | Task | Status của old input |
|---|---:|---|---|
| Giá trị lớn (int32 limits, 1000–100000, n≥40) | 14 | 13,31,41,53,55,63,83,97 | toàn bộ `timeout` hoặc `RecursionError` |
| JSON boolean `True/False` bị parser từ chối | 10 | 151 | Direct 0 input |
| Non-ASCII (`你好`, `café`, `🎉`) | 1 | 23 | wrong value |
| Whitespace-only (`' '`, `'( )'`) | 2 | 6,140 | wrong value |
| Semantic khác (palindrome, ngày 02-29) | 3 | 10,124 | wrong value |

Ở 8 task nhóm đầu, max magnitude trong union Direct+Soft là 20–1000 (task 97: 987654321)
so với cũ 1000–2147483648. Toàn run: input có số |x|≥1000 là old 179 input/50 task,
Direct 57/20, Soft 67/25; non-ASCII 10/4, 0/0, 10/2. Empty/zero/negative/±1 gần như
không đổi (Direct 54/231/334/697 input so với old 58/224/311/654).

Kết luận: 24/30 PUT old-only giải thích bởi instruction resource-size (14, loại detection
timeout/RecursionError) và JSON format (10). Không phải BVA cơ bản (empty/0/âm/±1) bị
mất. Câu này nằm trong common prompt nên Soft cũng bị ảnh hưởng: Direct 68 vs Soft 73
vẫn so cùng điều kiện, nhưng cả hai arm bị chặn nhóm resource-boundary. Chưa có prompt
ablation để đo tác động nhân quả.

## Bổ sung 2: tách resource detection (phương án 2) và nguyên nhân từng PUT

Người dùng chọn giữ câu `resource caps are not semantic boundaries` trong common prompt
và báo resource detection thành cột riêng. Tool: `final/src/audits/detection_kinds.py`
(read-only, 0 model call, không execute). Dữ liệu chi tiết:
`final/review/detection_kinds_2026-11-08.json`.

Định nghĩa kind cho mỗi input xác nhận lỗi (lỗi ở cả hai lần chạy):
- `wrong_value`: cả hai lần trả giá trị khác reference;
- `resource`: có `timeout`, `RecursionError` hoặc `MemoryError` (phụ thuộc giới hạn harness);
- `crash`: exception khác.
Một PUT lấy kind mạnh nhất trong các input bắt được nó: wrong_value > crash > resource.

### Bảng chính (đơn vị: PUT, mẫu số 1454 target PUT)

| Arm | Tổng detection | wrong_value | crash | resource | Không tính resource |
|---|---:|---:|---:|---:|---:|
| Naive cũ (sau packaging repair) | 82 | 53 | 3 | 26 | 56 |
| Direct batch | 68 | 46 | 3 | 19 | 49 |
| Soft BVA batch | 73 | 59 | 1 | 13 | 60 |

Direct vs Soft (matched): không tính resource, Soft hơn Direct 11 PUT (60 vs 49).
Shared 52; Direct-only 16 = 6 wrong_value + 2 crash + 8 resource; Soft-only 21 =
19 wrong_value + 2 resource.

### Vì sao naive cũ hơn Direct 14 PUT (82 − 68)

Old-only 30 PUT, Direct-only 16 PUT; 14 = 30 − 16.

| Nguyên nhân | Old-only | Direct-only | Ròng cho naive cũ |
|---|---:|---:|---:|
| Resource: input lớn gây timeout/RecursionError | 14 (task 13,31,41,53,55,63,83,97) | 7 (task 60, `2147483647`) | +7 |
| Mất input do interface/parser | 10 (task 151, Direct viết `True/False` trong JSON → cả response bị reject) | 5 (task 99, naive cũ viết `('14.5')` thiếu dấu phẩy singleton → 20/20 `invalid_literal`, repair không đổi) | +5 |
| Nội dung test idea (wrong_value) | 6 | 4 | +2 |
| Tổng | 30 | 16 | +14 |

Nội dung test idea, từng PUT:

| Task | Bên bắt | Input bắt lỗi | Input bên kia có gì |
|---|---|---|---|
| 10 make_palindrome (2) | Naive cũ | `'xyzz'`, `'abbaa'` (palindromic suffix ngắn hơn chuỗi) | Direct chỉ có palindrome trọn vẹn hoặc chuỗi đơn giản (`'abca'`, `'race'`) |
| 124 valid_date (1) | Naive cũ | `'02-29-2021'` (đúng biên 29 ngày tháng 2) | Direct có `02-30`, `02-31` (trên biên) nhưng không có `02-29` (tại biên) |
| 6 parse_nested_parens (1) | Naive cũ | `'( )'` (space bên trong group) | Direct có `'   '`, `'() () ()'`, không có space trong group |
| 140 fix_spaces (1) | Naive cũ | `' '`, `'  '` (chuỗi chỉ 1–2 space) | Direct có space-only từ 3 ký tự trở lên |
| 23 strlen (1) | Naive cũ | `'你好'`, `'café'`, `'🎉'` | Direct 20 chuỗi ASCII |
| 72 will_it_fly (3) | Direct | `([-1, -1], -2)` (tổng âm bằng đúng w) | Naive cũ có `([-1,0,-1], -1)`/`0`, không có tổng bằng w âm |
| 20 find_closest_elements (1) | Direct | `([3.0, 1.0, 2.0],)` (list chưa sort) | Naive cũ 20 list đều đã sort |

Kết luận:
- Không tính resource, naive cũ 56 vs Direct 49 (ròng 7). Hai lỗi interface (task 151
  của Direct, task 99 của naive cũ) tạo ròng +5; nội dung tạo ròng +2.
- Nếu bỏ cả resource lẫn hai task interface, naive cũ hơn Direct 2 PUT về nội dung
  (6 vs 4), trên 5 task với 1–2 PUT/task. Không đủ để nói prompt cũ sinh test idea tốt
  hơn; mỗi bên là một sample temperature 0.7.
- Resource +7 có tương quan với instruction mới về input nhỏ (xem Bổ sung 1), nhưng Direct
  vẫn sinh `2147483647` ở task 60. Chưa có prompt ablation nên chưa chứng minh nhân quả.
