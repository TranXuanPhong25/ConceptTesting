# Magma — vulnerability-triggering test-gen benchmark (real CVE, oracle vi-phân)

Chứng minh **concept-guided input generation** trên thư viện THẬT (Magma, SIGMETRICS'21) — dataset thoả cả 3
tiêu chí: **có input tự nhiên** (harness đọc file), **lỗ hổng thật** (CVE), **có bản fixed** (macro biên dịch).
Khác `bench/` (Juliet synthetic, LLM viết C gọi `focal`), ở đây **LLM sinh INPUT (bytes)** kích hoạt bug.

## Oracle vi-phân (ground-truth = canary Magma)
- **VULN build** = `CANARY_MODE=1` (fixes EXCLUDED, bug hiện diện) + `ISAN=1` (`-DMAGMA_FATAL_CANARIES`:
  canary trigger → abort). `magma-<t>-vuln`.
- **FIXED build** = `CANARY_MODE=3` (fixes INCLUDED, bug đã vá). `magma-<t>-fixed`.
- **TRIGGERED** = canary của đúng bug mục tiêu bật trên vuln (đọc qua `monitor --dump human`, `magma/runonce.sh`
  in `exit_code N bug <BUGID>`). **DISCRIM** = triggered(vuln) ∧ clean(fixed).

## Trạng thái
- ✅ **Milestone 0 (oracle)**: `oracle.py --selftest PNG003` → VULN `bug=PNG003`, FIXED sạch, **DISCRIM=1**
  trên CVE thật (oversized-PLTE, `png_handle_PLTE`, fault `num > max_palette_length`).
- ✅ **Milestone 1 plumbing**: gen→render_input→oracle→score→McNemar chạy đủ (validate bằng cache giả).
- ✅ **Scale: 100 bug real-CVE / 7 libs** — libpng7 lua4 libtiff14 libxml2 17 sqlite20 libsndfile18 openssl20
  (family: oob48 null31 df13 uaf3). php/poppler build nặng bị kill dưới QEMU (VM RAM) — để sau nếu cần thêm.
- ⏳ Cần `GROQ_API_KEY` để sinh test thật (blind vs concept) → điền bảng.

## Files
- `setup.sh` — build libpng vuln+fixed (Docker, `--platform linux/amd64`, fuzzer=`vanilla`=gcc standalone).
- `oracle.py` — `run_input(bytes,bug)` chạy 2 build trong container; `render_input(model_text)` exec `build()`→bytes;
  `--selftest PNG003`.
- `extract.py` — parse `targets/<t>/patches/bugs/*.patch` → item {bug_id, focal, fault_cond, fix_hint,
  func_vuln, concepts, family_pred}; nguồn hàm vuln lấy từ image, concept qua tree-sitter (`load_annotator`).
- `prompts.py` — blind (chỉ "làm crash <lib>") vs concept (focal + loại bug + fault_cond + fix_hint, KHÔNG leak input).
- `gen.py` / `score.py` — one-shot: sinh qua Groq (resumable) / chấm TRIGGER+DISCRIM + McNemar.
- `loop.py` — **Milestone 2 feedback (CEGIS)**: sinh → oracle (REACHED/triggered) → phản hồi → viết lại ≤ROUNDS,
  giữ best. Oracle giờ trả cả `reached` (chạm hàm lỗi, mềm hơn) lẫn `triggered` (thoả fault_cond, ground-truth).
- `patched_runonce.sh` — nới harness limit 0.1s/50MB → 5s/2000MB (bind-mount, khỏi rebuild).
- `items/*.jsonl` — 100 bug / 7 libs (gen.py & score.py tự gộp mọi file items/*.jsonl).

## Tái lập
```bash
git clone --depth 1 --branch v1.2.1 https://github.com/HexHive/magma.git vendor/magma
T="libpng lua libtiff libxml2 sqlite3 libsndfile openssl"
TARGETS="$T" bash magma/setup.sh                      # build vuln+fixed moi target (Docker amd64/QEMU, one-time)
.venv/bin/python magma/oracle.py --selftest PNG003    # gate: DISCRIM=1
for t in $T; do .venv/bin/python magma/extract.py --target $t; done   # -> items/*.jsonl (100 bug + concept)
GROQ_API_KEY=gsk_... SAMPLES=3 .venv/bin/python magma/gen.py          # gop het items/*.jsonl
.venv/bin/python magma/score.py                       # bang blind vs concept + McNemar
```

## Ghi chú kỹ thuật (đã xử lý)
- macOS host GID 20 (staff) đụng group Ubuntu → build args `USER_ID/GROUP_ID=1000`.
- libfuzzer kéo clang-11 từ `apt.llvm.org/bionic` (đã gỡ) → dùng `vanilla` (gcc + StandaloneFuzzTargetMain).
- Apple Silicon arm64: libpng build `arm/*.S`, Magma ép `-include canary.h` vào assembler → lỗi → `--platform linux/amd64` (QEMU).
- Bảo mật: `gen.py` đọc `GROQ_API_KEY` từ env, KHÔNG hardcode.

## Scale
Đã có **100 bug / 7 libs**. Thêm nữa: php (PHP001–016), poppler (PDF001–022) — build C/C++ nặng, dưới QEMU
hay bị kill (VM RAM); tăng RAM Docker Desktop rồi `TARGETS="php" bash magma/setup.sh` từng cái.
Input khó one-shot → **Milestone 2 = feedback loop** (reached/triggered → refine), nơi concept lợi thế nhất.
