---
name: test-slides-arm-module-plan
description: Plan chỉ còn EP/BVA/DT theo slide 03;weak EP+normal BVA single-fault mặc định;catalogue bắt buộc;chưa implement/run
metadata:
  type: project
---

Kế hoạch: [PLAN_TESTING_ARMS.md](../final/PLAN_TESTING_ARMS.md).

User 2026-11-08 thu hẹp scope: chỉ arm equivalence, BVA, decision table (slide
`03. Kiem thu chuc nang.pdf`); control-flow/data-flow/special value bỏ khỏi plan.

Quyết định trong plan:
- Mỗi arm ứng với biến thể có tên trong slide. Mặc định weak EP (p.25) và normal
  BVA single-fault 4n+1 (p.9–11). `ep_bva` là cấu hình chính; `equivalence`,
  `bva_normal` là ablation; `decision_table` riêng (8 bước p.36). Biến thể sau:
  `ep_strong`, `bva_robust` (chỉ khi spec định nghĩa out-of-domain), `bva_worst_case`,
  `ep_dt_bva`. Comparator: `plain`, `boundary` (soft BVA, không đổi).
- Catalogue (classes/boundaries/rules + `covers`) bắt buộc trong cùng call, để kỹ
  thuật kiểm tra được; catalogue sai không reject input. Chung completion cap 4096.
- EP chia cả output domain. Coverage DT tính trên feasible rules gốc.
- Lỗi của slide được ghi làm fixture: bảng DT p.43 có combination infeasible,
  gộp cột cần action trước bước 7, ví dụ điểm chữ p.21 overlap tại 4.

**Why:** đánh giá trước đó: plan cũ dùng "below/at/above" không khớp biến thể nào,
thiếu single-fault/weak/output partition, DT 8 bước không kiểm chứng được khi chỉ
xuất inputs, prompt quá dài/nhiều câu viết cho người report.
**How to apply:** implement chỉ khi user yêu cầu; theo lộ trình đợt 0–4; không tự
chạy smoke/dev/check.

Update 2026-11-08: user yêu cầu bỏ dead weight/không ép prompt. Guidance mỗi arm
≤~8 dòng, viết khẳng định, theo kiểu soft BVA (gợi ý, cho phép test hữu ích khác),
không lặp shared prompt. Ràng buộc (invalid/robust, infeasible proof, overlap,
budget priority) chuyển sang domain check/checker/audit — bảng ở mục 11 plan.
Catalogue tối giản, `covers` optional; có thể ablation `catalogue=off`.
