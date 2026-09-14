# `byte_sweep/` — C3: dò byte + oracle verify (ĐỔI TÊN từ `concolic/`)

## ⚠️ Vì sao đổi tên
Tên cũ **`concolic` là phóng đại**. Code ở đây **KHÔNG** có:
- symbolic execution · path constraint · SMT solver · instrument chương trình

Nó chỉ là: XOR-flip cửa sổ 2 byte (lấy mẫu ~20 vị trí) để đoán byte nào điều khiển lỗi, rồi thử
**4 giá trị hardcode** `0xFF/0x7F/0x01/0x00`, oracle xác nhận. **~36 lần chạy.**
Tên đúng: *mutational byte-sweep / black-box sensitivity analysis*.

Kết quả cũng đúng mức độ ngây thơ đó: **+1 bug** (5 vs 4), p=1.0 (ns).

## Concolic THẬT — chưa làm
Magma **ship sẵn**: `fuzzers/symcc_afl` (clone SymCC + **Z3**), `fuzzers/klee`, `fuzzers/parmesan`.
```bash
FUZZER=symcc_afl TARGET=libpng bash vendor/magma/tools/captain/build.sh
```
→ instrument chương trình, thu path constraint, Z3 giải ra input lật nhánh tới `fault_cond`.

**Chi phí/rủi ro:** build LLVM + SymCC + Z3 dưới QEMU amd64 — vài giờ, và dễ vấp như `libfuzzer` lúc trước
(apt repo chết, torch/Pascal...). **Chưa quyết định làm hay không.**
