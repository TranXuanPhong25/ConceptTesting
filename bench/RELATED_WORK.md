# Related work & phương pháp chứng minh tác động của concept lên sinh test

Tổng hợp deep-research (2023–2026, 22 nguồn, 23/25 claim verify đối nghịch). Dùng cho phần
related-work + evaluation của luận văn. Kết luận lớn: **giá trị của guidance được chứng minh bằng
ablation on/off + negative/placebo control + kiểm định McNemar**, đo bằng **oracle vi-phân + metric
security-aware** (KHÔNG tin coverage/mutation thô). Guidance mạnh nhất là **artifact có cấu trúc**
(path-constraint, reachability, patch-derived), KHÔNG phải prompt dài.

## 1. Metric & thiết kế thí nghiệm (cách PROVE nhân-quả)
- **Coverage/mutation thô không đáng tin khi code có bug** — chỉ tương quan bắt-bug ở regression sạch
  (branch r≈0.861), yếu trên code có bug. [arXiv 2607.22880](https://arxiv.org/html/2607.22880v1).
- **Security → oracle vi-phân + metric security-aware**: [ExploitBench](https://arxiv.org/html/2605.14153v1)
  chấm exploit bằng *differential execution* (chạy trên cả bản vuln lẫn fixed, tín hiệu phải khác) — **y
  hệt oracle ASAN vi-phân của ta**. [SecMutBench](https://dl.acm.org/doi/10.1145/3805760.3814933): mutation
  thô thổi phồng năng lực **2.2×**; đề xuất Security Mutation Score phân loại kill.
- **Thiết kế nhân-quả chuẩn**: [AdverTest](https://arxiv.org/html/2602.08146) = ablation 5 biến thể có
  **negative control** + **McNemar** (p=0.00257) cho n nhỏ. → template cho ta.
- **Khoảng trống**: KHÔNG paper nào chạy **placebo/shuffle trên chính tín hiệu analysis** → cơ hội đóng góp.

## 2. Corroborate 2 kết quả ÂM của ta (không phải làm sai)
- Coverage-steering đơn độc kém: AdverTest coverage-only coverage cao hơn (80%) nhưng bắt lỗi thấp hơn
  (34% vs 40% mutation). [MultiFileTest](https://arxiv.org/pdf/2502.06556): bỏ yêu-cầu-coverage lại TĂNG
  coverage. → concept2 (spec dài) & coverage-steering thất bại của ta **khớp literature**.

## 3. Hướng kỹ thuật mới (có bằng chứng)
- **Patch-derived guidance** — [DIG](https://arxiv.org/abs/2606.13037): LLM đọc *patch* → suy điều-kiện
  kích-hoạt → **+40% CVE** (80 vs 57). Ta CÓ sẵn cặp vuln/fixed = patch → rút concept từ diff. ⭐
- **Path-constraint prompting** — [SymPrompt](https://arxiv.org/pdf/2402.00097) (FSE24): static (tree-sitter)
  liệt kê ràng buộc theo đường-chạy, giao chọn-nhánh cho analyzer, LLM chỉ viết test → **>2× coverage GPT-4**.
- **Trackable objectives** — [TATG](https://arxiv.org/html/2607.03194): theo dõi objective static đã-thoả/chưa;
  bỏ tầng static → sụp còn 26%.
- **Execution-feedback = đòn bẩy lớn nhất** — [PALM](https://arxiv.org/html/2506.19287) +14.2% path; AdverTest:
  bỏ loop mất nhiều nhất. → củng cố kết quả feedback của ta.
- **Reachability** — [VULEUT](https://arxiv.org/pdf/2409.16701): 64.5%→78.42% khi bật param-transfer analysis.

## 4. Student được ủng hộ
[SPA-guided](https://arxiv.org/pdf/2503.05394): guidance giúp **model yếu nhiều nhất**, GPT-4 chỉ nhích →
đúng giả thuyết student (model yếu cần spec tường minh).

## 5. Đóng góp mới ta có thể cắm cờ
1. **Placebo/shuffle control** trên tín hiệu concept — chưa ai làm.
2. **So đầu-đối-đầu** các tín hiệu static (tree-sitter concept vs patch-derived vs reachability) cho
   **memory-safety PoC** — chưa có.
3. "Coverage-steering không giúp model mạnh" cho **C/C++ ASAN differential** — ta là first.
4. Toàn literature là Java/regression → setting **C/C++ memory-safety + ASAN vi-phân** của ta là gap thật.

## Caveat
Gần như mọi bằng chứng là Java/regression, không phải C/C++ PoC; nhiều nguồn là preprint tự báo (TATG, DIG,
ExploitBench, AdverTest) — SymPrompt (FSE24) & VULEUT (FORGE25) là peer-reviewed. 2 claim bị BÁC BỎ (không
trích): "commercial-code 9-10x clean ablation" và "PALM 35% isolating analysis".
