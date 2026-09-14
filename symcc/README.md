# `symcc/` — Concolic THẬT (SymCC + Z3) trên Magma

Baseline **program-analysis** để đặt cạnh LLM. Đây là thứ thay thế cho `byte_sweep/` — cái mà trước đây
tôi gọi sai là "concolic" (thực chất chỉ XOR-flip dò byte + thử 4 giá trị hardcode, không symbolic,
không path-constraint, không SMT).

## Tại sao làm cái này

Micro-experiment trên **PNG001** (= `AAH001` trong paper Magma gốc, CVE-2018-13785) định vị chính xác
nút thắt:

| PNG001 | render | REACHED | TRIGGER |
|---|---|---|---|
| `blind` | ✗ | ✗ | ✗ |
| `concept_static` (source + concept, **không** có fault_cond) | ✓ | **✓** | **✗** |
| `fewshot_authored` | ✓ | **✓** | **✗** |
| *(run cũ bị rò — feedback mách `row_factor_l == 1<<32`)* | ✓ | ✓ | **✓ giải ra `width=0x55555553`** |

⇒ LLM **giải** ràng buộc rất tốt (được cho phương trình → ra nghiệm ngay vòng 1) nhưng **không suy ra
được phương trình từ source** (có cả source trong prompt vẫn chỉ chạm, không nổ).

Paper Magma nói đúng về lớp bug này: magic value `0x55555555` *"không được mã hoá ở đâu trong target,
dễ tính ra bằng giải ràng buộc `row_factor == 0`, nhưng fuzzer đột biến thì vật lộn"* — chỉ 3/7 fuzzer
trigger nổi, và **SymCC-AFL nhanh nhất**. Tức SymCC làm đúng vế mà LLM thủng.

## Thiết kế: `symcc_std` = `vanilla` + SymCC (tối giản)

Bản gốc `vendor/magma/fuzzers/symcc_afl` build **4 thứ**; ta chỉ cần **2**:

| thành phần | symcc_afl gốc | ở đây | lý do |
|---|---|---|---|
| Z3 (nguồn, ghim `897cbf3`) | ✓ | **✓ bắt buộc** | repo 18.04 chỉ có 4.4.1, SymCC cần API C++ 4.8.x |
| SymCC (pass LLVM + runtime, QSYM backend) | ✓ | **✓ bắt buộc** | phần lõi |
| AFL + llvm_mode | ✓ | ✗ | không chạy chiến dịch fuzzing, chỉ giải ràng buộc |
| libc++ từ `llvm-project` | ✓ | ✗ | chỉ cần cho target **C++**; target ta dùng đều là **C**. Đây là cuốc build **đắt nhất** |
| `cargo` symcc_fuzzing_helper | ✓ | ✗ | chỉ để ghép vòng lặp AFL↔SymCC |

Hai thay đổi nữa, để tránh đúng các lỗi đã gặp:
- **Không dùng `apt.llvm.org`.** `clang-10`/`llvm-10-dev` có sẵn trong repo Ubuntu 18.04 chính thức
  (đã kiểm tra). Chính `apt.llvm.org/bionic-11` bị gỡ là thứ làm build `libfuzzer` chết (exit 100).
- **Không `pip install lit`.** Bản gốc dùng `python-pip` (python2); PyPI đã bỏ python2 → `set -e` giết
  build. `lit` chỉ cần cho test-suite LLVM, mà ta không build LLVM.

## Chạy

```bash
bash symcc/setup.sh                             # build magma-libpng-symcc  (2-4h dưới QEMU, MỘT LẦN)
TARGETS="libpng libxml2 lua" bash symcc/setup.sh

# LƯU LẠI kẻo mất khi docker prune (đã bị 1 lần, mất 14 image):
docker save magma-libpng-symcc | gzip > ~/magma-libpng-symcc.tgz

.venv/bin/python symcc/loop_symcc.py            # concolic + chấm điểm bằng oracle vi-phân
GOLD=/tmp/png001.jsonl ROUNDS=2 .venv/bin/python symcc/loop_symcc.py     # 1 bug
```

## Vòng lặp đo

```
seed CHẠM hàm lỗi (reach/taint.py bootstrap)
   --SymCC: thu path constraint, Z3 phủ định từng nhánh--> input mới
   --oracle canary (magma/oracle.py, cặp image vuln/fixed)--> reached / triggered
   input nào CÒN chạm hàm lỗi --> làm seed vòng sau (BFS, ROUNDS vòng)
```

Chấm bằng **đúng** oracle của bảng LLM → so trực tiếp được (`lab.mcnemar` trên `results_symcc.json`).

**Giới hạn biết trước:** SymCC cần một seed **đã chạm** hàm lỗi. `bootstrap_reaching` chỉ đạt **34/100**
bug → 2/3 bug SymCC không có chỗ bắt đầu. Đây là trần của thiết kế, sẽ báo trung thực trong kết quả
(`co seed` là một dòng riêng trong bảng).

## Ghi chú build

- `vendor/` bị gitignore ⇒ script tự viết nằm ở `symcc/fuzzer/` (có track), `setup.sh` **copy** vào
  `vendor/magma/fuzzers/symcc_std/` rồi build. Idempotent.
- `canaries=1` nhưng **không** `isan`: muốn binary **chạy tiếp** sau khi chạm bug để SymCC đi hết đường
  dẫn; nếu `-DMAGMA_FATAL_CANARIES` thì trigger → abort ngay → mất phần đường còn lại.
- `runonce.sh` nới `TIMELIMIT` 0.1s→30s và `MEMLIMIT` 50MB→4000MB: binary có instrument SymCC + Z3
  chậm và ngốn RAM; giới hạn gốc giết solver trước khi nó trả lời.
