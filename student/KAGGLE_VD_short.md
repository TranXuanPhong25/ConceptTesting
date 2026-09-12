# Student concept finetune (VD) — bản RÚT GỌN cho Kaggle (≤10h)

Tái lập tín hiệu ConceptCoder ở **model nhỏ** (nơi concept THẮNG, khác với teacher bão hoà). Dùng **script gốc**
của ConceptCoder, chỉ rút epoch 10→3 + accelerate config cho Kaggle 2×T4.

## Kỳ vọng (paper, arXiv 2603.23470, Qwen-3B, VD concept F1)
| | SFT (regular) | ConceptCoder | Δ |
|---|---|---|---|
| Qwen2.5-Coder-3B | 65.15 | **73.44** | **+8.3** |

Mục tiêu: tái hiện **Δ > 0** (concept > regular). Số tuyệt đối có thể lệch (epoch 3 vs 10, fp16 vs bf16) nhưng
DẤU của Δ là thứ cần.

## Chuẩn bị trên Kaggle
1. Dataset: upload `ConceptCoder/` + `data/VD/` (giữ đúng layout — script trỏ `../../../data/VD/`).
2. GPU: **T4 ×2** (Settings → Accelerator). Quota ~30h/tuần, 1 session ~9–12h.
3. Cài: `pip install -r ConceptCoder/requirements.txt accelerate deepspeed` (+ `huggingface-cli login` nếu model gated như Llama).

## Chạy (2 phiên, mỗi phiên ≤ ~6h)
```bash
# Phiên 1 — CONCEPT (quan trọng nhất):
VARIANT=conceptcoder EPOCH=3 bash student/run_short.sh
# Phiên 2 — BASELINE để so:
VARIANT=regular      EPOCH=3 bash student/run_short.sh
```
Đọc F1 ở `data/logs/concept_learning/VD/concept/Qwen2.5-Coder-3B/...`.

## Thời gian (ước lượng, 2×T4, full-FT 3B, ZeRO-3 + CPU offload)
- ~23k mẫu, batch hiệu dụng ~16–32, block 512.
- **~1–1.6h/epoch → epoch 3 ≈ 3–5h/variant.** → mỗi phiên (train+test 1 variant) **≤ ~6h, vừa 1 session**.
- Chạy cả 2 variant trong 1 phiên ≈ 6–10h (sát trần) → **khuyến nghị tách 2 phiên** cho an toàn.

## Knobs nếu vướng
- **OOM trên T4**: giảm `train_batch_size 16 → 4/8` trong `run_*_fine_tuning.sh`; giữ `offload_*_device: cpu`.
- **fp16 overflow (loss NaN)**: giảm `learning_rate 2e-5 → 1e-5`, hoặc đổi `mixed_precision: bf16` (chậm hơn trên T4).
- **Muốn nhanh hẳn (bỏ full-FT)**: chuyển LoRA (sửa script thêm PEFT) → 3B fit 1×T4 không offload, ~2–3× nhanh,
  cả 2 variant trong 1 phiên. **Lưu ý**: LoRA ≠ full-FT của paper → số tuyệt đối khác, nhưng Δ concept-vs-regular
  vẫn đo được (đủ cho luận điểm).
- **Chỉ đủ 1 GPU** (P100/Colab): `num_processes: 1` trong `student/accelerate_kaggle.yaml`.

## Hướng A — dùng ConceptCoder làm BỘ CẤP CONCEPT cho generator (sinh test)
ConceptCoder là **classifier** (không sinh test). Nhưng model dự đoán **concept per-line** (lớp `cbl` → sigmoid),
đúng format `lines_concept` của tree-sitter → drop thẳng vào prompt sinh-test hiện có. Pipeline:
```bash
# 1) (Kaggle) train xong -> co checkpoint (VARIANT=conceptcoder EPOCH=3 bash student/run_short.sh)
# 2) (Kaggle) du doan concept HOC-DUOC cho ham target (Magma/bench):
python student/predict_concepts.py \
   --ckpt data/saved_models/VD/concept/Qwen2.5-Coder-3B/checkpoint-best-f1/statement_level_sequential/Qwen2.5-Coder-3B \
   --base Qwen/Qwen2.5-Coder-3B --model_type qwen \
   --in magma/items/libpng.jsonl --out magma/items_learned/libpng.jsonl --func_key func_vuln
# 3) (local) sinh test SO: concept tree-sitter vs concept ConceptCoder (cung generator Groq)
GOLD=magma/items/libpng.jsonl        ... magma/loop.py   # tree-sitter
GOLD=magma/items_learned/libpng.jsonl ... magma/loop.py  # learned (lines_concept da thay)
```
`predict_concepts.py` thay `lines_concept` = concept học-được (giữ bản cũ ở `lines_concept_treesitter`).
Prompt builder `concept`/`concept_static` đọc `lines_concept` → KHÔNG cần code sinh-test mới.

**Kỳ vọng trung thực:** ConceptCoder học TRÊN nhãn tree-sitter → learned ≈ static về nội dung. Điểm có thể hơn:
concept học-được **định vị root-cause** tốt hơn (semantic) so với tree-sitter (gắn cờ MỌI sink theo cú pháp).
Ở teacher có thể vẫn null (placebo đã bác annotation); giá trị rõ hơn khi cấp cho **student generator**.

## Vì sao đáng làm
Mọi kết quả teacher phiên trước = NULL (concept bão hoà). Paper cho thấy **ở 3B concept +8.3 F1**. Đây là bằng
chứng "concept có giá trị ở model YẾU" — mảnh còn thiếu để đóng khung: *teacher không cần concept, student thì có*.
