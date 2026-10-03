# concept_sft_harness

Fine-tune Qwen3-4B (QLoRA, chạy trên Kaggle) để sinh **test harness bắt bug**, có và không có **concept learning**.
So sánh với HarnessLLM (Liu et al., NeurIPS'25, [arXiv 2511.01104](https://arxiv.org/abs/2511.01104),
[repo](https://github.com/UCSB-NLP-Chang/HarnessLLM) pin `83a58d4b`).

Notebook: [`ConceptSFT_HarnessLLM_Kaggle.ipynb`](ConceptSFT_HarnessLLM_Kaggle.ipynb).

## Vì sao không dùng lại ConceptCoder trực tiếp

`ConceptCoder_org/` là **classifier** (vulnerability detection / branch prediction): `AutoModel` + `cbl` (Linear → 8 concept
per-line) + `classifier`. Model full-FT với DeepSpeed ZeRO-3 trên 2 GPU bf16, data C/C++ và repo không kèm data. Model này
không sinh test. `student/` đã thử chạy nó trên Kaggle bằng LoRA, nhưng đầu ra vẫn là nhãn phân loại.

Phần **mang sang được** là cơ chế học concept: mean-pool hidden state cuối theo từng dòng code, rồi
`cbl = Linear(hidden, K)`, BCE per-line, `loss = task + 0.2·concept` (`concept_weight=0.20` trong
`run_conceptcoder_fine_tuning.sh`). Notebook ghép cơ chế này vào causal-LM sinh harness:

```
loss = LM(harness | đề bài + chương trình lỗi) + 0.2 · BCE(cbl(pool_dòng(h_last)), nhãn concept của chương trình)
```

Lúc infer, prompt **giống hệt** baseline nên không cần annotator. Concept phải được model "học vào" representation.

## Thiết kế thí nghiệm

| VARIANT | Train | Vai trò |
|---|---|---|
| `base` | – | Qwen3-4B gốc, prompt của paper |
| `harness_rl` | – | checkpoint SFT+RL của paper (`Shiyu-Lab/HarnessLLM_RL_Qwen3_4B`), mốc trên |
| `sft` | QLoRA trên `Shiyu-Lab/HarnessLLM_SFT_Data` | baseline chính: stage-1 của paper chạy với budget Kaggle |
| `concept_aux` | `sft` + aux concept head | **phương pháp chính** |
| `placebo_aux` | `concept_aux` nhưng nhãn bị xáo giữa các dòng | kiểm soát "chỉ thêm loss" |
| `concept_prompt` | `sft` + concept hints trong prompt | concept phía input (tuỳ chọn) |

- **Concept**: 8 nhãn bug-prone cho Python, gán bằng AST: `boundary_compare, range_bound, index_arith, div_mod,
  special_case, extreme_init, order_select, io_parse_format`. Tương tự 8 nhãn tree-sitter của ConceptCoder VD.
- **Eval**: prompt `prompts/harness.py` và judge `custom_verl/testcase_judge.compute_score` của paper, **không sửa**, cùng
  tham số với `scripts/eval.py` (20 testcase, 5 generator, timeout 20s). Metric chính là `PassGoodFailBad` (harness pass bản
  đúng, fail bản lỗi). Mọi VARIANT chấm cùng subset (`EVAL_SUBSET_SEED=1234`).
- **So sánh**: paired theo bài: Δ tỉ lệ bắt bug + bootstrap 95% CI + McNemar exact.

## Khác paper (ghi rõ khi báo cáo)

Paper full-FT 15 epoch, cutoff 16k, bf16, có thinking. Ở đây: QLoRA r=16, 1 epoch, ≤3072 token (bỏ ví dụ dài hơn), fp16
trên T4, `THINK=0` (bỏ `<think>` khỏi target), decode ≤2048 token, eval subset `N_EVAL=100`. Số tuyệt đối không so được với
bảng của paper. Kết luận chỉ rút từ so sánh giữa các VARIANT dưới cùng budget.

Với `N_EVAL=100`, CI của Δ rộng khoảng ±12 điểm phần trăm. Muốn kết luận chắc chắn thì tăng `N_EVAL` (hoặc `0` = toàn bộ)
và chạy ≥2 `SEED`.

## Đã kiểm tra / chưa kiểm tra

- Đã chạy local (CPU): annotator, `to_triplet`/`extract_program`, map token→dòng (tokenizer giả có offset), judge gốc qua
  bộ chạy multiprocess của notebook (4 ca: bắt bug / test yếu / test sai / sai format đều cho đúng reward type), cell gộp kết
  quả và cell kiểm định paired.
- **Chưa chạy**: phần cần GPU và HuggingFace (load data/model, train QLoRA, generate). Schema của
  `HarnessLLM_SFT_Data` chưa xem được (mạng ở đây chặn HF), nên `to_triplet()` đoán nhiều format. Nếu Cell 4 báo
  "Không nhận ra schema" thì sửa hàm đó theo cột in ra.
- Ghi chú judge: `reliability_guard()` của paper đặt `os.getcwd=None`, làm `tempfile` hỏng nếu chưa cache. Notebook gọi
  `tempfile.gettempdir()` trước khi fork để xử lý. Nếu không build được `python-prctl` thì notebook dùng shim no-op.
