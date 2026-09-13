# `learned/` — chạy sinh-test với CONCEPT HỌC-ĐƯỢC (ConceptCoder) thay vì tree-sitter

**Clone** của `magma/loop.py`, tách riêng để **không đụng** cache/kết quả bản tree-sitter.

| | tree-sitter (gốc) | learned (clone này) |
|---|---|---|
| items | `magma/items/*.jsonl` | `magma/items_learned/*.jsonl` |
| cache | `magma/loop_cache.jsonl` (1864 dòng) | `learned/loop_cache.jsonl` (riêng) |
| runner | `magma/loop.py` | `learned/loop_learned.py` |

Prompt template **giữ NGUYÊN** (`magma/prompts.py`), chỉ khác **nội dung `lines_concept`** → so sánh có kiểm soát
(controlled): biến duy nhất thay đổi là NGUỒN CONCEPT.

## Chạy
```bash
GROQ_API_KEY=gsk_... ROUNDS=3 .venv/bin/python learned/loop_learned.py
# mac dinh CONDS=magma_blind,magma_concept ; muon dung so sanh voi ban tree-sitter (4%):
CONDS=magma_concept_static GROQ_API_KEY=gsk_... ROUNDS=3 .venv/bin/python learned/loop_learned.py
```
Đối chiếu với `concept_static` trên tree-sitter = **TRIGGER 4% / REACHED 20%** (`magma/RESULTS.md` Bảng 3b).

## Cảnh báo chất lượng (đo trước khi chạy)
Concept học-được từ bản train rút gọn (LoRA 7.39M, 3 epoch, `concept_weight=0.2`) bị **collapse về nhãn phổ biến**:

| concept | learned | tree-sitter |
|---|---|---|
| ptr_deref / if_statement | 87 / 86 | 92 / 88 |
| buffer_access | 28 | 55 |
| null_check | 15 | 50 |
| **bound_check** | **1** | 35 |
| **buffer_allocation** | **0** | 38 |

Hệ quả thấy rõ ở PNG003 (bug OOB): prompt learned ra **`Loai: null_deref` (SAI họ)** và **không liệt kê được
buffer/sink/guard nào**, trong khi tree-sitter chỉ đúng `palette[...]` + sink `palette[i].red=...` + guard `length>3*...`.

→ **Dự đoán: learned < tree-sitter.** Nếu đúng, kết luận trung thực là *"concept học-được từ bản train YẾU thì hại
hơn công cụ tĩnh"* — **không** phải "phương pháp ConceptCoder sai" (paper dùng full-FT 10 epoch, ta dùng LoRA 3 epoch
vì Kaggle giới hạn ~29GB RAM / 12h session).
