# Plan hướng tiếp theo sau v48 (draft, chưa đăng ký) — 2026-10-22, Claude + Codex (Q2)

Chọn nhánh theo **failure decomposition của v48** (PREREG v48), không theo cảm tính. Mỗi nhánh nêu prior art trong repo.

## Điểm yếu đã thấy từ các phương pháp trước
1. Input reach không phải bottleneck chính (v41 pool 22/33); selection theo concept ≈ random nhiều lần (v7_mutref, v18,
   v35, v36, v41, v42, v44).
2. Oracle là bottleneck: in-head judge yếu (v45), DPP spec programs trên VibePass phần lớn invalid/memorized (v39:
   84 valid programs, 23/33 tasks < 3 valid, memorization 64%), mutant làm alternative hiếm khi đúng (v37 3/20).
3. TC-full (PUT-guided variants) mạnh nhất ở matched budget (v11), nhưng variants dẫn từ PUT dễ **copy bug của PUT**
   (common-mode). N-version literature: common-mode failures tập trung ở phần spec khó/mơ hồ (arXiv 2606.20158).
4. FA chủ yếu từ invalid inputs ở differential oracles (arXiv 2608.19626: 94% panel-disconfirmed inputs là invalid).

## Nhánh A (nếu v48 thất bại chủ yếu ở (b) common-mode hoặc (e) không có valid program): definitional concept oracle
- **Concept** = ngữ nghĩa định nghĩa của spec, viết thành chương trình **vét cạn (brute force)** trên input nhỏ — một
  executable spec, khác thuật toán tối ưu mà PUT/TC variants dùng (algorithm family khác → giảm common-mode; Codex Q2).
- **Nguồn**: ALGO (NeurIPS 2023): LLM-generated brute-force oracle đúng 88% trên CodeContests; dùng để verify program,
  không dùng để tìm bug trong plausible programs. TrickCatcher chỉ dùng PUT-guided variants.
- **Pipeline**: Qwen32B viết k = 5 brute-force programs/task từ spec (prompt yêu cầu enumerate theo định nghĩa, không tối
  ưu) → filter bằng public tests → input nhỏ từ concept classes (v47 kinds giới hạn kích thước) → PUT vs brute-force
  (và cross-family: chỉ emit khi brute-force group đồng ý với ≥ 1 TC variant, hoặc report riêng) → assertions (cap 20).
- **Controls**: TC-only (v48), DPP-only (v39), brute-force trên pool random cùng count, brute-force + random family
  assignment (Codex: cùng 10-program budget, random family labels).
- **Chi phí**: 33 × 5 = 165 calls (~1–2 giờ, 1 worker). Prior art trong repo: v38/v39 (stochastic spec programs, không
  yêu cầu vét cạn; fail vì invalid/memorized), v46 (mutant-edit guidance). Algorithm-family/brute-force: chưa có.

## Nhánh B (nếu thất bại chủ yếu ở FA trên invalid inputs): spec-precondition concept filter
- Concept = precondition từ spec (Constraints) thành predicate chạy được; lọc input trước oracle. Prior art: v7 mined
  validity (từ public examples, không từ spec), v24 obligations (Qwen contracts 0/9). Chỉ thử nếu FA-invalid chiếm đa số.

## Nhánh C (nếu thất bại chủ yếu ở (a) không có exposing input trong input đã chọn): không mở input-selection mới
- Đã thử nhiều lần (xem điểm yếu 1). Chỉ xét structure generators cho 11 unreachable tasks (v45_unreachable), và phải
  dùng fresh cohort vì v47 Part A đã nhìn hidden inputs.

## Gate chung
Mọi nhánh: correct assertions/confirmed tasks và FA tests so với TC-only cùng inputs/cap; independent review trước khi
chạy; PREREG trước output; không mở rộng n để vớt kết quả.
