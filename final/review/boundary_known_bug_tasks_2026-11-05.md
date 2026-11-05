# 10 task có boundary value chạm bug đã xác nhận

Chọn ngày 2026-11-05. Không gọi model và không dùng hidden test input. Nguồn ứng viên:
disagreement đã lưu trong `final/out/v11_concept_inputs` và boundary corpora của
`final/src/audits/audit_boundary_witnesses.py`, quét trên mọi PUT base-pass của 44 task
trong group boundary. Mỗi input dưới đây được chạy lại 2 lần bằng HumanEval+ corrected
reference và contract; kết quả hai lần giống nhau. Chi tiết: file JSON cùng tên.

| Task | PUT | Boundary | Pass | Fail (bug) | Trong cohort 44 | Module biểu diễn được |
|---|---|---|---|---|---|---|
| 2 `truncate_number` | 6 | Sát dưới số nguyên | `1.0` | `0.9999999999999999` → 0.0 | Có | Có, `value` + `float_adjacent` |
| 11 `string_xor` | 1 | Độ dài 0 | `('0','1')` | `('','')` → error | Không | Có, `length` |
| 16 `count_distinct_characters` | 4 | Mã ký tự 256 | `'ÿ'` | `'Ā'` → 0 | Không | Không, thiếu characteristic |
| 23 `strlen` | 7 | Mã ký tự 128 | `'\x7f'` | `'\x80'` → 2 | Có | Không, thiếu characteristic |
| 72 `will_it_fly` | 4 | `sum(q) == w` | w=-3, w=-1 | `([-1,-1], -2)` → False | Có | Có, `sum` + threshold expression |
| 76 `is_simple_power` | 0 | `x == 0` | x=-1, x=1 | `(0, 2)` → timeout | Không | Có, `value` |
| 99 `closest_integer` | 1 | Phần lẻ 0.5 | `'0.5'` | `'0.49999999999999994'` → 1 | Có | Có, `parsed_float` |
| 124 `valid_date` | 0 | Năm đủ 4 chữ số | `'01-01-2000'` | `'01-01-200'`, `'01-01-20000'` → True | Có | Có, `length` 10 |
| 140 `fix_spaces` | 7 | Run 3 spaces, chuỗi toàn space | `'   '` | `' '`, `'  '` → `'-'` | Có | Có, nếu context chỉ gồm space |
| 157 `right_angle_triangle` | 3 | `c` đúng cạnh huyền | `(3.0,4.0,5.0)` | `c` liền kề 5.0 → True | Có | Một phần, threshold phụ thuộc a, b |

Nominal value của cả 10 task đều pass, nên bug không lộ ở giữa vùng.

## Giới hạn

- Đây là tập chọn theo kết quả, chỉ dùng làm diagnostic: "nếu chạm đúng biên thì có thấy
  bug không". Không dùng để báo cáo detection rate hay so sánh efficacy.
- PUT ở đây thường khác representative PUT của cohort 44 task; chạy pipeline cần cohort riêng.
- Mức tranh luận được: 157 (PUT cố ý dùng tolerance 1e-9), 72 (`w` âm), 11 (chuỗi rỗng).
  Contract cho phép các input này và corrected reference ra kết quả khác PUT.

## Đã loại

- Resource: recursion hoặc timeout (13 PUT3, 15, 24, 31, 41, 53, 60, 77, 83, 97, 100, 107, 129).
- Không phải boundary: 10 và 13 PUT2 (sai thuật toán), 45 (mọi float đều lỗi), 99 PUT0 (sai cả
  giữa vùng âm), 27 và 161 (lớp ký tự), 144 (rounding không có threshold rõ).
- Spec không phân xử được hoặc reference có quirk: 20 (tie), 91, 141, 151.

## Kết quả chạy prompt v4

Output `final/out/boundary_known_bug10_prompt_v4_20261105`: 14 calls, 10 inputs, 1 PUT
(task 124). PUT chọn theo kết quả nên đây không phải detection rate.

| Task | Bước mất bug | Chi tiết |
|---|---|---|
| 124 | Không mất | Chọn `date:length == 10`, input `'03-11-200'` lộ bug |
| 72 | Context | Chọn đúng `sum <= w`, nhưng context dùng số dương, không chạm partial sum âm |
| 140 | Context | Chọn đúng `run_length > 2`, nhưng context `'A  B'`, bug cần chuỗi toàn space |
| 76 | Selection | Chọn `n <= 1`, bỏ sót `x == 0` |
| 2, 11, 157 | Selection | `no_applicable_boundary`, lý do là spec không nêu threshold |
| 16, 23 | Selection | Như trên; module cũng chưa có characteristic mã ký tự |
| 99 | Selection | Response bị cắt ở `selection_tokens=2048` (`finish_reason=length`), thành `invalid_selection` |

## Chạy lại protocol5 sau sửa

User yêu cầu chạy lại trên cùng10PUT. Output:
`final/out/boundary_known_bug10_prompt_v5_20261105`:16calls,64input hợp lệ,
chạm bug ở76,99,124,140. So với v4, thêm76(selection có x=0),99(selection
không còn bị cắt),140(context có chuỗi toàn space).72vẫn thiếu số âm;
2/11vẫn abstain.16bind nhầm mã ký tự thành length rồi generation bị cắt;
23thiếu characteristic;157chọn a>0thay vì boundary cạnh huyền.

Đây vẫn là diagnostic chọn theo kết quả, không phải detection rate. Chi tiết,
cost và giới hạn replay do source runtime bị phiên khác sửa sau launch:
[protocol5 report](boundary_prompt_v5_diagnostic_2026-11-05.md).
