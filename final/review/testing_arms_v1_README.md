# Prompt và kết quả testing arms v1

Full v1: Plain **68**, EP+BVA **89**, Decision Table **74** detected PUTs trên **1454 eligible PUTs**. Chênh lệch EP+BVA chủ yếu là resource; wrong-value tương ứng **54/55/57**. Matched-valid-input-budget chưa cho thấy khác biệt rõ. Catalogue structural-valid không chứng minh kỹ thuật đã được thực hiện đúng về semantic.

## Prompt được lưu

- [Plan và prompt v1](../PLAN_TESTING_ARMS.md).
- [EP guidance](../src/modular/equivalence_partitioning/prompts.py).
- [BVA và EP+BVA guidance](../src/modular/boundary_value_analysis/classical.py).
- [DT và combined guidance](../src/modular/decision_table/prompts.py).
- [Guidance/config snapshot từ full run](testing_arms_v1_prompt_snapshot.json). EP+BVA và DT guidance trong snapshot đã được đối chiếu đúng bytes với constants tương ứng. Plain guidance nằm trong source đã track.

Phạm vi commit này là prompt/plan và reports v1, không gồm runtime integration đang làm dở, prompt/examples v2 hay hướng solver mới. Snapshot không phải task-specific request export; checkpoints, shared packets và raw responses vẫn giữ nguyên ở output local. Prompt combined được lưu nhưng các report dưới đây không phải kết quả combined-arm generation.

## Reports

| Run/analysis | Nội dung |
|---|---|
| [Smoke6](ep_bva_smoke6_results_2026-11-09.md) | Plain và EP+BVA cùng 1/6 PUT; timeout 3s |
| [Catalogue audit smoke6](ep_bva_smoke6_catalogue_audit_2026-11-08.md) | Giới hạn schema và semantic của catalogue |
| [Full v1](full_testing_arms_timeout8_2026-11-09.md) | 157 eligible tasks, 1454 PUTs; 20 inputs/task/arm; timeout 8s |
| [Direct/Soft control](direct_soft_full_timeout8_2026-11-09.md) | Comparator lịch sử, config khác full v1 |
| [Direct77 vs Plain68 audit](direct77_vs_plain68_audit_2026-11-09.md) | Phân tích baseline và khác biệt config |
| [Plain-guidance rerun](plain_guidance_rerun_results_2026-11-09.md) | 71/1454 PUTs; completion cap 2048, không thay thế baseline Plain68 trong full v1 |
| [Union inputs v1](union_inputs_results_2026-11-09.md) | Union 109/1454; budget tối đa 60 thay vì 20 inputs/task, không phải một combined generation arm |

JSON cùng tên đi kèm các report kết quả. Đây là artifact có sẵn; không chạy lại generation/evaluation để commit. Mỗi report ghi config, chi phí và giới hạn riêng; không trộn các cohort/budget thành một comparison.
