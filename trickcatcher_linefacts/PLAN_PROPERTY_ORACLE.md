# Plan: concept làm oracle (property / metamorphic) thay cho exact expected value

Ngày 2026-10-18. User đồng ý ("ừ, làm đi") sau kết quả v21_flowtools (`analysis/v21_flowtools_results.md`).

## Vì sao

v21_flowtools: input đã chạm bug ở nhiều task (witness-only thấy PUT ≠ reference ở 8/20 pilot task), nhưng
Qwen 7B đoán sai expected value → 1–4 task confirmed, 19–38 false alarm. Bottleneck là oracle, không phải input.
Câu hỏi: nếu concept được viết thành property/relation có thể chạy (kiểm trên output thật của PUT), có tách bug
thật khỏi false alarm tốt hơn exact expected không?

## Thiết kế (inputs cố định, chỉ oracle thay đổi)

- Folder: `pipelines/v26_proporacle/` (copy của `v21_flowtools` để dùng lại client/executor/scoring; best-on-dev vẫn là v7).
- Cohorts: `pilot20` (chính) và `diag16` (phụ, ceiling đã biết).
- Input pool / task (không model, không chọn theo outcome): frozen witnesses + public base calls trước, sau đó
  các final-test input của mọi arm v21 (đã freeze) sắp theo sha256 của literal; tối đa 12; chỉ input admissible
  (mined validator) vào oracle.
- 4 oracle arm, mỗi arm 1 Qwen call / task:
  1. `exact_spec`: expected value cho từng input, chỉ từ spec + base tests.
  2. `exact_code`: như trên, thấy thêm code (mốc giống v21 final call).
  3. `property`: ≤3 `check(args, output, error) -> bool` viết từ spec (concept dạng property); tool chạy trên output thật của PUT.
  4. `metamorphic`: ≤2 cặp `follow(args)` + `relation(args, output, args2, output2)`; tool chạy PUT trên follow-up input.
- Model code chạy trong sandbox (unshare -rn, timeout, memory cap). Lỗi property = unknown, không phải bug.
- Scoring sau freeze, reference độc lập (HumanEval+ canonical / fixture oracle):
  input-level TP / false alarm / missed / unknown, precision, task-level confirmed và false-alarm tasks.
  Property soundness (property có fail trên output của reference không) chỉ ở evaluator.
- Secondary (đăng ký trước): consensus `exact_code ∧ property`, union.

## Quy tắc kết luận

Property hoặc metamorphic "promising" nếu precision cao hơn cả hai exact arm và số task confirmed không thấp
hơn `exact_code` trên pilot20. n nhỏ, K=1 → chỉ mô tả; không claim generalization, không promote tự động.
