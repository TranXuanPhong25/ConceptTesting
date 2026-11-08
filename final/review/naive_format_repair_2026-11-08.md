# Naive cũ sau khi sửa format: 87 PUT

Kết quả: naive cũ sau packaging repair + sửa format bắt **87 PUT** (trước 82), trên 1454 PUT vượt base tests.
Giới hạn kết luận: cùng response lịch sử, chỉ sửa format input; không phải sample mới, vẫn khác Direct/Soft về prompt và thời điểm sinh.

Run: `final/out/naive_packaging_audit_format_repair_20261108_201016` (tool `final/src/audits/format_repair_naive.py`).
0 model call. Scorer lịch sử full-two-repeat, corrected reference HumanEval+ v0.1.10, timeout 3 s/input.
Immutable replay và hash source/input khớp.

## Sửa format (123 input trên 10 task)

| Lỗi format | Input sửa |
|---|---:|
| Thiếu tuple wrap cho hàm 1 tham số (`'a'` → `('a',)`) | 60 |
| Chép kwargs vào args (`(')()(', 'kwargs': '{}')`) | 18 |
| Quote key JSON lỗi (`{"args':'...','kwargs"...}`) | 12 |
| Tách record khi JSON hỏng một chỗ (task 14) | 19 |
| Thừa quote cuối | 3 |
| Ký tự xuống dòng thật trong chuỗi | 2 |

Không sửa: expression (`2*3`, `'a'*1000`), `inf/nan`, record đa nghĩa, response bị truncation (task 22, 27, 69).
Input mới hợp lệ: 2876 (trước 2758).

## Detection theo kind (đơn vị PUT)

| Arm | Tổng | wrong_value | crash | resource | Không tính resource |
|---|---:|---:|---:|---:|---:|
| Naive sau sửa format | **87** | 58 | 3 | 26 | **61** |
| Naive repaired (trước) | 82 | 53 | 3 | 26 | 56 |
| Direct (batch, parser sửa) | 78 | 56 | 3 | 19 | 59 |
| Soft BVA (batch, parser sửa) | 73 | 59 | 1 | 13 | 60 |

5 PUT mới so với naive repaired, đều wrong_value: task 99 (PUT 0, 7, 8, 9) và task 124 (PUT 1). Không mất PUT nào.

So với Direct: chung 65; chỉ naive 22 (8 wrong_value, 14 resource); chỉ Direct 13 (6 wrong_value, 7 resource).
So với Soft: chung 65; chỉ naive 22 (5 wrong_value, 2 crash, 15 resource); chỉ Soft 8 (6 wrong_value, 2 resource).

Kết luận: khi cả ba arm không còn mất input do interface, không tính resource thì naive 61, Soft 60, Direct 59 —
tương đương. Naive cao hơn ở tổng chủ yếu nhờ resource (26 vs 19/13), từ input lớn mà prompt mới dặn tránh.
