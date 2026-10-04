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

## So sánh với số trong bảng của paper (`PROTOCOL="paper"`, mặc định)

Eval chạy đúng quy trình `bashes/generate.sh` + `scripts/generate.py` + `scripts/eval.py` của HarnessLLM:

| | Paper | Notebook |
|---|---|---|
| thinking | bật (chat template mặc định) | bật (`THINK=1`) |
| mẫu / bài | 8 | 8 |
| decode | T=0.6, top_p=0.95, presence_penalty=1.5, max 32000 | giống |
| engine | sglang, tp=2 | vLLM 0.8.5, tp=2 (2×T4) |
| tập eval | 500 bài đầu mỗi dataset | 500 bài đầu, mặc định subset 100 cố định (`N_EVAL=0` = đủ 500) |
| judge | `compute_score`, 20 testcase / 5 generator / 20s | chính code đó |
| số báo cáo | mean ± std qua 8 mẫu (`print_stats`) | giống, kèm 95% CI theo bài |

**Anchor:** chạy `harness_rl` (checkpoint của paper) trước. Cell 10 kiểm tra số của paper có nằm trong 95% CI của số mình
tái lập hay không. `ANCHOR OK` thì số của `concept_aux`/`sft` so thẳng được với các dòng `SFT (Harness)`, `RL (Harness)`
của Table 1. `MISMATCH` thì chưa được so, phải tìm chỗ lệch protocol trước.

Số của paper trong `PAPER_TABLE` (Cell 2) **đã đối chiếu với PDF** arXiv 2511.01104v1 (04-10-2026). Metric là **TBR**
(True bug rate: % response mà bản đúng pass còn bản lỗi fail, tức `PassGoodFailBad`), trung bình 8 lần chạy. Seen và
MBPP+Fix(Hard) nằm ở Table 1, Unseen (bug do Qwen3-14B sinh) nằm ở Table 2:

| TBR % | MBPP+Fix(Hard) | LCB Seen | LCB Unseen | CF Seen | CF Unseen |
|---|---|---|---|---|---|
| SFT (I/O) | 44.6 | 42.9 | 17.3 | 59.5 | 23.1 |
| SFT (Harness) | 62.9 | 42.1 | 16.3 | 46.0 | 25.3 |
| RL (I/O) | 72.7 | 65.1 | 33.3 | 72.2 | 32.4 |
| RL (Harness) | 74.1 | **69.9** (anchor) | 37.2 | 74.4 | 37.9 |

- Bản snippet cũ sai: mỗi dataset trong bảng có 3 cột GI/ITR/TBR, snippet đọc 3 cột của MBPP thành 3 dataset (nên anchor
  LCB Seen cũ ghi 74.1, thực ra đó là TBR của MBPP).
- "MBPP+Fix" = split MBPP+Fix(Hard) của UTGen, 141 bài = `Shiyu-Lab/Testcase_MBPPHard` (141 dòng trên HF).
- Kích thước tập eval (Table 6, khớp số dòng trên HF): MBPP 141, LCB Seen 76, LCB Unseen 93, CF Seen 100, CF Unseen 84.
  Mọi tập đều < 100 bài trừ MBPP, nên `N_EVAL=100` lấy **đủ cả tập**, đúng như paper.
- Paper báo SFT model ở k=5 test case/response, RL model tự chọn (tối đa 20). Notebook chấm mọi variant bằng mặc định
  của `scripts/eval.py` (20 testcase, 5 generator). Với dòng SFT đây có thể là một chỗ lệch nhỏ.

**Phía train vẫn khác paper:** họ full-FT 15 epoch, cutoff 16k, bf16. Ở đây QLoRA r=16, 1 epoch, cutoff 8192 (ví dụ dài hơn
bị bỏ, dùng liger fused-CE để vừa T4), fp16. Đây là bất lợi cho model của mình, không làm mất tính hợp lệ của eval.

**Chi phí (ước lượng, chưa đo):** 8 mẫu × tối đa 32k token thinking trên 2×T4 rất chậm. 100 bài có thể mất vài giờ, đủ 500
bài thường vượt một phiên Kaggle 12h. File gens được ghi theo chunk 10 bài và tự resume, nên chạy lại cell 7 ở phiên sau
(Add Data = output phiên trước, rồi copy `gens_*.jsonl` vào `/kaggle/working`) sẽ chạy tiếp.

`PROTOCOL="fast"` (không thinking, 1 mẫu, 2048 token, HF generate) chỉ để thử nhanh, không so với paper. Kết quả hai protocol
được lưu và gộp riêng.

## Đã kiểm tra / chưa kiểm tra

- Đã chạy local (CPU): annotator, `to_triplet`/`extract_program`, map token→dòng (tokenizer giả có offset), judge gốc qua
  bộ chạy multiprocess của notebook (4 ca: bắt bug / test yếu / test sai / sai format đều cho đúng reward type), cell gộp kết
  quả và cell kiểm định paired.
- Đã chạy local với `vllm` giả: script sinh của vLLM (resume theo uid, ghi theo chunk), thống kê kiểu `print_stats` (mean ± std
  qua 8 mẫu) và logic anchor OK/MISMATCH.
- **Chưa chạy**: phần cần GPU và HuggingFace (load data/model, train QLoRA, vLLM thật trên T4). Schema của
  `HarnessLLM_SFT_Data` chưa xem được (mạng ở đây chặn HF), nên `to_triplet()` đoán nhiều format. Nếu Cell 4 báo
  "Không nhận ra schema" thì sửa hàm đó theo cột in ra.
- Ghi chú judge: `reliability_guard()` của paper đặt `os.getcwd=None`, làm `tempfile` hỏng nếu chưa cache. Notebook gọi
  `tempfile.gettempdir()` trước khi fork để xử lý. Nếu không build được `python-prctl` thì notebook dùng shim no-op.

## Lỗi Kaggle đã gặp

Chạy bằng `kaggle kernels push` (xem `student/KAGGLE_CLI.md`). `kernel-metadata.json` dùng:
`"machine_shape": "NvidiaTeslaT4"` (Kaggle cấp 2×T4) và
`"docker_image": "gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461"`.

| Lỗi | Nguyên nhân | Sửa |
|---|---|---|
| `No matching distribution found for vllm==0.8.5.post1` → Cell 7 `ModuleNotFoundError: vllm` | image Kaggle mặc định (10-2026) đã lên Python 3.13 / torch 2.11; vllm 0.8.x–0.10.1 yêu cầu Python <3.13 | pin `docker_image` ở trên trong kernel-metadata (image cũ, Python 3.12, cùng image kernel vLLM-T4 trước đó chạy được). Không đổi bản vLLM nên protocol giữ nguyên |
| Cell 6 `ImportError: cannot import name 'runtime_version' from 'google.protobuf'` (khi `import peft` → transformers → tensorflow) | cài vllm hạ protobuf, làm tensorflow có sẵn trong image bị vỡ; transformers tự import TF nếu thấy | Cell 1 đặt `os.environ["USE_TF"]="0"` trước khi import transformers (notebook không dùng TF) |
| Kernel `CANCEL_ACKNOWLEDGED` sau ~12h, `harness_rl` LCB Seen mới sinh 30/76 bài | giới hạn 12h/phiên của Kaggle. Trên 2×T4, 8 mẫu × tối đa 32k token mất ~4h cho mỗi chunk 10 bài, KV cache bị preempt liên tục (>700 lần) | resume: tải `gens_*.jsonl` qua `kaggle kernels output --file-pattern`, đưa lên dataset private `xunphongtrn/conceptsft-gens` (thêm vào `dataset_sources`), rồi push lại cùng RUN_CFG. Notebook glob `/kaggle/input/**/gens_*.jsonl` và sinh tiếp phần còn thiếu |
| `The following are not valid kernel sources: [<chính kernel đó>]` | Kaggle không cho một kernel dùng output của chính nó làm `kernel_sources` | resume qua dataset như dòng trên. `kernel_sources` chỉ dùng để lấy adapter/results từ kernel **khác** |
