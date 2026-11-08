# Tỷ lệ boundary input trong các input làm fail: Direct vs Soft BVA

Nguồn: `final/out/bva_batch_matched164_reparse_20261108_192012/evaluation` (parser đã sửa).
Tool: `final/src/audits/boundary_share.py`; 0 model call, không chạy PUT, chỉ chạy reference đã instrument.
Dữ liệu từng input: `boundary_share_direct_soft_2026-11-08.json`.

Định nghĩa heuristic (đơn vị: input hợp lệ trong oracle union):
- natural_edge: có container/chuỗi rỗng, container 1 phần tử, chuỗi 1 ký tự, hoặc số 0/1/−1;
- reference_threshold: chạy reference, có phép so sánh số rơi đúng ngưỡng hoặc cách ngưỡng 1 (int).
"Input làm fail" = input làm ít nhất một PUT fail ở cả hai lần chạy.

| Nhóm input | Số input | natural_edge | reference_threshold | Boundary (một trong hai) |
|---|---:|---:|---:|---:|
| Fail chung (cả hai arm sinh ra) | 25 | 52% | 76% | 84% |
| Fail chỉ Direct | 52 | 17% | 46% | 48% |
| Fail chỉ Soft | 57 | 30% | 37% | 44% |
| Tất cả input fail của Direct | 77 | 29% | 56% | **60%** |
| Tất cả input fail của Soft | 82 | 37% | 49% | **56%** |
| Mọi input hợp lệ của Direct (base rate) | 2962 | 42% | 47% | **68%** |
| Mọi input hợp lệ của Soft (base rate) | 2951 | 46% | 48% | **71%** |

Theo PUT: Direct 55/78 PUT bị bắt bởi ít nhất một boundary input (23 PUT chỉ bị bắt bởi input không phải boundary);
Soft 62/73 (11 PUT chỉ bị bắt bởi input không phải boundary).

Kết luận:
- Khoảng 60% input làm fail của Direct (naive) là boundary theo heuristic; Soft 56%.
- Cả hai arm đều có tỷ lệ boundary trong input làm fail thấp hơn base rate của chính arm đó (60 vs 68%, 56 vs 71%):
  boundary input không chiếm tỷ trọng cao bất thường trong số input bắt được lỗi.
- Input chỉ Soft bắt được không mang tính boundary hơn input chỉ Direct bắt được (44% vs 48%).

Giới hạn: heuristic rộng và có sai cả hai chiều. Ví dụ dương tính giả: chuỗi ngoặc của task 1 chạm `depth == 0`
trong reference với hầu hết input. Âm tính giả: `0.999999999` (ngay dưới 1, integer crossing) không được tính.
Heuristic không nói boundary là nguyên nhân gây fail.

## Gán nhãn tay (3 subagent Haiku, mù arm và heuristic)

Mỗi input làm fail có cờ `boundary_manual` + `boundary_manual_reason` trong file JSON. Định nghĩa: giá trị tại/sát
điểm hành vi theo spec thay đổi (ngưỡng/biên khoảng, ngưỡng quan hệ như `sum == w`, rỗng/1 phần tử/0/đổi dấu/integer
crossing, giới hạn độ dài/số lượng). Không đối chiếu người gán thứ hai (người dùng không yêu cầu).

| Nhóm input làm fail | Boundary (tay) | Heuristic |
|---|---:|---:|
| Chung | 18/25 = 72% | 84% |
| Chỉ Direct | 25/52 = 48% | 48% |
| Chỉ Soft | 35/57 = 61% | 44% |
| Tất cả của Direct | **43/77 = 56%** | 60% |
| Tất cả của Soft | **53/82 = 65%** | 56% |

Theo PUT: Direct 56/78 PUT bị bắt bởi ít nhất một input boundary (tay); Soft 56/73.

Độ nhạy: task 43 có 12 nhãn yếu (số 0 có mặt nhưng không tham gia cặp tổng 0). Bỏ task 43: chỉ Direct 24/51 = 47%,
chỉ Soft 27/49 = 55%.

Kết luận theo nhãn tay: Soft nghiêng về boundary hơn Direct ở input làm fail (65% vs 56%; riêng phần không trùng 61% vs 48%,
55% vs 47% nếu bỏ task 43). Nhưng số PUT bắt được bởi boundary input bằng nhau (56 vs 56): guidance làm input boundary
nhiều hơn nhưng không bắt thêm PUT. Nhãn do một model gán, chưa đối chiếu người gán thứ hai.
