# Kết quả: DỪNG (không đủ tài nguyên Kaggle), 04-10-2026

Chưa có số liệu so sánh nào: anchor `harness_rl` trên LCB Seen chưa chạy xong, nên các variant base/sft/concept_aux/placebo_aux
**chưa chạy**.

## Đã làm
- `PAPER_TABLE` sửa theo PDF (commit `ed707f1`). Anchor LCB Seen RL(Harness) = **69.9** TBR (không phải 74.1).
- Kernel `xunphongtrn/conceptsft-harness-rl-lcbseen-s42` (2×T4, image pin, vLLM 0.8.5, PROTOCOL=paper, 76/76 bài):
  v3 sinh được 30/76 bài trong 12h rồi bị Kaggle dừng, v4 (resume qua dataset `xunphongtrn/conceptsft-gens`) bị hủy vì dừng dự án.
  Các lỗi Kaggle và cách sửa: xem README, mục "Lỗi Kaggle đã gặp".

## Số đo từ 30 bài đã sinh (240 mẫu, chưa chấm judge)
- Độ dài: trung vị 9,232 token/mẫu, trung bình 16,530, tổng 3.97M token. Throughput ~92 token/s trên 2×T4 (KV cache bị preempt >700 lần).
- **88/240 mẫu (37%) bị cắt ở 32k token.** Đây là một chỗ có thể lệch so với paper, cần kiểm tra trước khi tin số anchor nếu chạy lại.

## Vì sao dừng
Ước tính anchor cần ~30 giờ GPU (khoảng 3 phiên 12h). Cả kế hoạch 5 variant × 2 dataset theo protocol của paper cần khoảng 300 giờ GPU,
tức khoảng 10 tuần quota Kaggle (~30h/tuần). Muốn chạy lại cần GPU ≥ A100 (paper dùng sglang tp=2), hoặc chấp nhận
lệch protocol.
