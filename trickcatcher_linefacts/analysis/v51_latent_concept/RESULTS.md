# v51 latent concept oracle — kết quả (2026-10-23, CPU, $0)

Registration: [PREREG.md](PREREG.md) (+ Amendment 1 sau independent review, trước khi fit). Số liệu:
[fit_report.json](fit_report.json) (MBPP+ validation), [results.json](results.json) (VibePass, score một lần).
Code: [build.py](build.py), [extract.py](extract.py), [probe.py](probe.py).

Câu hỏi: hidden state của Qwen2.5-Coder-1.5B frozen có cho biết input nào làm PUT trả output sai không (bottleneck
oracle/selection của v41), và đi qua discrepancy concept (concept bottleneck) có thêm thông tin so với direct probe
không.

## Dữ liệu

- Train (MBPP+, tool label): 291 task, 13,810 example (6,644 wrong). Features: last-token residual 7 layer.
- Eval (pool v41 VibePass đã lưu): 4,187 example, 22 PUT evaluable, 17 problem.
- Extraction: cache check đạt (relative diff 5.7e-6). Features đủ cho mọi example, không có NaN/inf.

## MBPP+ validation (58 task held-out, chọn layer + C)

| | direct (A) | CBM (B) | placebo (C, seed 0) | verbal | intrinsic | surface |
|---|---:|---:|---:|---:|---:|---:|
| macro AUC | .626 | .627 | **.631** | .590 | .591 | .526 |

- Layer 28 (cuối), C = 0.01 cho cả ba arm.
- Concept probe AUC (one-vs-rest trên mọi row validation): TYPE .95, BOOL_FLIP .97, SIZE .92, CONTENT .95,
  NUM_NEAR .78, NUM_FAR .79. ORDER không có trong validation.
- Ngay trong phân phối train, B không hơn placebo type-matched (−.004). Tức là danh tính concept không thêm gì, kể cả
  trước khi chuyển sang VibePass.

## VibePass (score một lần)

| | direct (A) | CBM (B) | placebo (C, mean 3 seed) | verbal | intrinsic | surface |
|---|---:|---:|---:|---:|---:|---:|
| macro AUC (17 problem) | .476 | .495 | .385 | .441 | **.650** | .496 |
| pooled AUC | .460 | .445 | .397/.469/.394 | .416 | .596 | .506 |

So sánh theo problem (sign test):

- B vs A: +.019, 10/7, p = .63.
- B vs C: +.111, 11/6, p = .33.
- B vs best D (intrinsic): −.155, 5/12, p = .14.
- A vs intrinsic: −.174, 3/14, **p = .013**.

## Quyết định: **NO-GO** (theo luật đã đăng ký)

Cả A lẫn B đều không đạt .60, và cả hai đều thua intrinsic likelihood, một baseline không cần train. Theo PREREG,
không có lý do viết plan 7B hay HumanEval confirmation.

## Cơ chế (mô tả, không phải gate)

1. **Concept shift.** Wrong output của VibePass gồm NUM_NEAR 409/791 (52%), NUM_FAR 241, CONTENT 134, ORDER 7, và
   0 TYPE/BOOL_FLIP/SIZE. Những concept probe đọc tốt (≥ .92) chủ yếu là concept về dạng output, nên gần như không
   xuất hiện ở eval. Concept eval cần nhất (NUM_NEAR, số sai lệch nhỏ) lại là probe yếu nhất (.78), và AUC đó tính trên
   cả row đúng nên phần lớn chỉ đọc "output là số". Concept head đặt top-1 đúng concept do tool tính cho 153/791 wrong
   row (19%).
2. **Spec shift.** Spec VibePass dài trung bình 1,414 ký tự, MBPP+ chỉ 148. Wrong rate là 19% so với 48%. Muốn biết
   một số nguyên có lệch 1 so với đáp án hay không thì model phải tự giải bài; một residual readout của model 1.5B
   không làm thay được việc đó.
3. **B − C = .11 không phải tín hiệu concept.** B ≈ chance (.495). Khoảng cách đến từ placebo rơi dưới chance (.385),
   không phải từ B. Điều kiện B − C trong luật GO đạt về mặt số học nhưng không mang nghĩa ngữ nghĩa.
4. **Per-PUT AUC phân cực.** Ví dụ vp87: verbal .00, placebo .01, CBM .92, intrinsic .98, surface .98. Ví dụ vp161:
   direct .17, surface 1.00. Trong một PUT, nhãn tương quan với độ lớn hoặc độ dài output, và các score bắt đặc trưng
   đó theo chiều ngẫu nhiên. Đây không phải đánh giá spec.
5. **Intrinsic likelihood là score duy nhất trên .60** (.650 macro, thắng direct 14/3). Score này không có concept,
   nên không phải phương pháp concept-centric.

Top-3 (mô tả):

- Có artifact khi score bằng nhau. Eval row được xếp exposing trước, nên khi hòa score, stable sort đặt exposing lên
  đầu. Surface có 97% row hòa, nên con số 16/22 đã ghi là artifact.
- Phá hòa ngẫu nhiên (200 lần): surface 9.2.
- Các arm khác không có hòa: intrinsic 11, CBM 10, direct 7, verbal 7.
- Chọn 3 input ngẫu nhiên trung bình được 11.7/22. Không arm nào hơn chọn ngẫu nhiên.

## Hàm ý

Probe trên hidden state, có hay không có concept bottleneck, không chuyển được từ MBPP+ mutant sang bug VibePass. Ngay
trong MBPP+, concept bottleneck cũng không hơn placebo type-matched. Đây không phải vấn đề kích thước dữ liệu: các
concept học được (dạng output) không phải loại bug của eval (số lệch nhỏ). Theo luật đã đăng ký, hướng này đóng ở
dạng hiện tại; không chạy 7B, không mở rộng train.

Giới hạn:

- Model 1.5B fp32 CPU.
- Chỉ dùng last-token residual, không thử mean pooling.
- Concept label do rule tính, "first matching" nên mỗi wrong row chỉ có một concept.
- 17 problem nên sign test yếu.
- Top-3 không phải gate.
