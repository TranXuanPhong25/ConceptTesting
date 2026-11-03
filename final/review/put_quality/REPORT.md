# Chất lượng PUT: TrickCatcher và cohort mới — 2026-11-01

**Khuyến nghị:** dùng pool TrickCatcher đã kiểm tra làm benchmark phát triển chính
cho câu hỏi concept có giúp tìm bug; giữ cohort Qwen mới làm benchmark bổ sung về
các chương trình pass base nói chung. Không thay đổi hồi tố kết quả run đã hoàn thành,
không chọn PUT theo thắng/thua của concept, và không hứa đổi pool sẽ tạo concept gain.

## Số liệu đã kiểm tra

| Thuộc tính | TrickCatcher/LineFacts | Cohort mới |
|---|---|---|
| Nguồn | PUT gốc trong artifact TrickCatcher | qwen3.5-27b-awq, sinh từ spec |
| Quy mô local | 151 file vendor; pool method139 | 1634 chương trình đã sinh |
| Pass base | Cache139/139method PUT | 1465PUT trên159task |
| Bằng chứng lỗi | Cache138/139fail ít nhất một HumanEval+ input | Run hiện tại tìm171PUT bất đồng reference trên40task |
| Số bản/problem | Một PUT/task | Tối đa10bản khác AST/task |
| Pool v7/v11 | 133PUT =113dev+20pilot | 1454PUT/157task thực sự được chấm |
| Median AST statements | 9, trên133PUT | 10, trên1465PUT |
| Median branch/loop nodes | 3 | 3 |

**Hai cột bằng chứng lỗi dùng test sets khác nhau.** 171 là lower bound của lỗi đã
phát hiện, không phải tổng số PUT có bug; không được gọi phần còn lại là correct.
Không so138/139 với171/1465 như hai defect-rate measurements cùng protocol.

Kiểm tra provenance: cả133source trong bundle v7 khớp byte-for-byte với
`vendor/TrickCatcher/Datasets/EvalPlus/PUTs/HumanEval_<id>/put0.py`. Old source không
bị sửa. Tất cả số base/plus ở đây là **cache cũ**, chưa revalidate bằng current
Python3.11.14 trong audit này. Không chạy model hay native PUT mới.

## Vì sao pool cũ phù hợp hơn cho concept targeting

Pool cũ có một target đã biết có lỗi cho gần mọi problem, nên test generator có cơ
hội thực sự tìm lỗi ở nhiều task. Với pool mới, pass base chỉ chứng minh qua base;
chưa biết từng task có PUT sai nào. Một task không phát hiện gì có thể vì chương
trình đúng, vì input không tới lỗi, hoặc vì pipeline tạo/giữ input thất bại.

Ví dụ PUT0 dùng `abs(numbers[i]-numbers[j]) <= threshold` trong khi spec yêu cầu
khoảng cách **nhỏ hơn** threshold. Input `[1.0,2.0],1.0` phân biệt equality boundary:
spec yêu cầu False; code PUT suy ra True. Đây là kiểu target rõ nghĩa để kiểm tra
boundary concept, không cần model phải tự đoán expected output.

Bộ mới vẫn có giá trị: nhiều cách cài đặt theo cùng spec, giữ riêng selection khỏi
test outcomes, và cho thấy hành vi trên cohort sinh tự nhiên. Tuy nhiên10bản khác
cấu trúc không tự đảm bảo10algorithm hay10loại bug. AST audit chỉ có21/1465module
(22entry functions) trùng canonical sau normalizing; **không có bằng chứng phần lớn
là bản chép AST của canonical**. AST khác cũng không chứng minh sai hay độc lập.

## Chất lượng pool cũ có giới hạn

- Task66 có0/1007failing plus inputs trên toolchain của cache. Đánh dấu zero-known-
  failure, không tính nó là target chắc chắn có bug.
- PUT69,108,116,131,152 không khớp một số ví dụ docstring. Đây là PUT/example
  mismatch; không tự suy ra docstring sai. Báo cáo riêng vì có thể là lỗi dễ lấy
  thẳng từ ví dụ, khác bài toán target subtle failures.
- Task50 từng được protocol cũ đánh dấu spec-ambiguous. Cần semantic review trước
  khi đưa vào clean core; không áp dụng sự loại bỏ dựa vào concept performance.
- Trước khi chuyển cohort, revalidate base và một valid plus witness/task trên
  đúng interpreter/contract/reference comparator mới; oracle mới giữ nguyên.
- Pool này đã dùng cho phát triển v7/v11 và nhiều variant.113dev/20pilot là split
  lịch sử; không được gọi pool này là một held-out mới chưa từng thấy.

## Điều kiện sử dụng trong pipeline mới

1. Nạp các PUT đã có thành frozen cohort riêng, một program/task, lưu provenance
   và source hash. Không yêu cầu hay tự sinh10bản mới cho pool cũ.
2. Các arm cùng nhận spec/base/PUT; HumanEval+ labels/witness chỉ dùng qualification/
   evaluation, không đưa plus input/reference source vào concept/generation prompt.
3. Cùng input budget, reference oracle, parser và matched comparison giữa các arm.
   Báo raw/valid yield và control như hiện tại. Không ghép số liệu hai cohort.
4. Bản modular hiện hard-code target10trong settings và skip khi không đủ10. Adapter
   pool một-PUT phải đặt target_programs=1 ở **run mới** và dùng manifest/output riêng.
   Không sửa cohort gốc hoặc kết quả cũ. Đây là điều kiện tích hợp, chưa triển khai/run.
5. Run hiện tại còn83/157primary pairs có zero valid-input budget và258graph failures.
   Đổi cohort không tự chứng minh đã sửa schema/domain/analysis losses này. Giữ chúng
   là limitation riêng; kết quả concept cũ vẫn là no demonstrated gain.

Reproduction: `final/.venv/bin/python -m final.review.put_quality.audit`.
Evidence: `SUMMARY.json`. Audit không thay cohort/pipeline/result và không gọi model.
