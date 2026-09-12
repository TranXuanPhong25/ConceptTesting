# Chạy ConceptCoder trên Kaggle bằng **CLI** (đã chạy được, ghi lại nguyên trạng)

MCP Kaggle báo `Unauthenticated` (token bị từ chối) → dùng `kaggle` CLI, nó tự đọc `~/.kaggle/access_token`.

```bash
.venv/bin/pip3 install -q kaggle
.venv/bin/kaggle kernels list --mine        # verify auth
```

## 1. Đóng gói & upload (2 dataset: data nặng + code nhẹ để iterate nhanh)
```bash
# pkg.tgz = ConceptCoder + data/VD + student + magma/items   (~22MB)
#   LUU Y: data release bi typo `teest_concept.jsonl` -> phai doi thanh `test_concept.jsonl`
kaggle datasets create -p /tmp/kgup        # id: xunphongtrn/conceptcoder-vd-pkg
# code.tgz = ConceptCoder + student (~0.5MB) -> sua code chi can day lai cai nay
kaggle datasets create -p /tmp/kgcode      # id: xunphongtrn/conceptcoder-code
kaggle datasets status xunphongtrn/conceptcoder-vd-pkg   # PHAI doi "ready" truoc khi chay kernel
```

## 2. Kernel metadata (bản chạy được)
```json
{ "id": "xunphongtrn/conceptcoder-vd-train", "code_file": "train.py",
  "language": "python", "kernel_type": "script", "is_private": true,
  "enable_gpu": true, "enable_internet": true,
  "machine_shape": "NvidiaTeslaT4",
  "dataset_sources": ["xunphongtrn/conceptcoder-vd-pkg","xunphongtrn/conceptcoder-code"] }
```
```bash
kaggle kernels push -p /tmp/kgk
kaggle kernels status  xunphongtrn/conceptcoder-vd-train
kaggle kernels output  xunphongtrn/conceptcoder-vd-train -p /tmp/kgout   # log = JSON
```

## 4 lỗi đã gặp & cách sửa (ghi để khỏi vấp lại)
| Lỗi | Nguyên nhân | Sửa |
|---|---|---|
| `pkg.tgz: No such file` | push kernel khi dataset còn đang xử lý | chờ `datasets status` = `ready`; script tự `glob("/kaggle/input/**/pkg.tgz")` |
| `ImportError: cannot import name 'AdamW'` | code họ viết cho transformers 4.48; bản mới **gỡ** `AdamW`/`WEIGHTS_NAME` | shim trong `kaggle_train.py` trước khi `exec_module` |
| `Found an incompatible version of torchao 0.10` | `peft` mới kỵ torchao có sẵn của Kaggle | `pip uninstall -y torchao` trong kernel |
| `CUDA error: no kernel image` | Kaggle cấp **P100 (sm_60)**, torch mới đã **bỏ hỗ trợ Pascal** | `"machine_shape": "NvidiaTeslaT4"` (⚠ cờ `--accelerator gpu-t4x2` bị **bỏ qua**) |

Mẹo tìm `machine_shape` hợp lệ: `kaggle kernels pull <kernel-cu-tung-chay-GPU> -m` rồi đọc metadata.

## Vì sao dùng LoRA (`student/kaggle_train.py`) thay vì script gốc
Full-FT 3B ≈ params fp32 12G + grads 6G + Adam 24G ≈ **42GB** → cần ZeRO-3 + CPU offload, mà Kaggle chỉ ~29GB RAM
→ OOM. LoRA: base fp16 6GB, fit 1×T4/P100. **Vẫn train `cbl` (concept bottleneck) + `classifier`** nên giữ nguyên
multitask `loss = CE(vuln)*1 + BCE(concept per-line)*0.2`. Khác paper (full-FT) → số tuyệt đối lệch, nhưng Δ
concept-vs-baseline và `cbl` (dùng cho hướng A) vẫn đo được.
