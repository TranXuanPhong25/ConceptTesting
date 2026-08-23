# Benchmark executed vi-phân (concept vs blind)

Chứng minh **concept-guided test generation** bắt lỗi bộ nhớ tốt hơn blind, bằng **thực thi**
(compile + AddressSanitizer/UBSan) trên bộ **gold build được, có cặp vuln/fixed**. Chạy 100% local, không GPU.

Mỗi case có `focal(input)` ở 2 bản cùng chữ ký. Test do LLM sinh được link với **từng** bản:
- test + `func_vuln`  → sanitizer **phải nổ** (bắt bug)
- test + `func_fixed` → **phải sạch** (nổ = báo động giả)
- **DISCRIM** = compile cả 2 ∧ nổ trên vuln ∧ không nổ trên fixed → bằng chứng test *định vị đúng* bug.

## Phạm vi
6 họ memory-safety mà 8 concept của ConceptCoder phủ: `oob_write, oob_read, oob, uaf, double_free,
null_deref` + 5 negative control. `int_overflow`/`div_zero` chưa có concept tương ứng → ngoài phạm vi seed.

## Chạy (3 bước)
```bash
# 1) Build + TỰ KIỂM gold set (vuln nổ / fixed sạch) + điền concept  -> bench/items/gold.jsonl
.venv/bin/python bench/build_items.py

# 2) Sinh test teacher (Groq free, ~68 call, resumable). KEY đọc từ env, KHÔNG hardcode.
GROQ_API_KEY=gsk_... .venv/bin/python bench/gen.py

# 3) Chấm điểm executed: concept vs blind (DISCRIM, per-family, negative control)
.venv/bin/python bench/score.py
```

## File
| file | vai trò |
|---|---|
| `authored.py` | 27 case tự soạn (vuln/fixed/ref_test/expect) |
| `run_diff.py` | harness vi-phân: assemble + compile_run (ASAN+UBSan) + run_diff |
| `build_items.py` | tự kiểm oracle + annotate concept → `items/gold.jsonl` |
| `prompts.py` | prompt blind/concept (tái dùng `pipeline_v3/common.py`, không leak `func_fixed`) |
| `gen.py` | sinh test qua Groq → `bench_cache.jsonl` |
| `score.py` | bảng TP/FP/DISCRIM + per-family + negative control |

Phase sau: `juliet_extract.py` bơm Juliet Test Suite vào cùng schema (CWE121/190/369/476).
