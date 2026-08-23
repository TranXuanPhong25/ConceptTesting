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

## Chạy (3 bước) — seed
```bash
# 1) Build + TỰ KIỂM gold set (vuln nổ / fixed sạch) + điền concept  -> bench/items/gold.jsonl
.venv/bin/python bench/build_items.py

# 2) Sinh test teacher (Groq free, ~68 call, resumable). KEY đọc từ env, KHÔNG hardcode.
GROQ_API_KEY=gsk_... .venv/bin/python bench/gen.py

# 3) Chấm điểm executed: concept vs blind (DISCRIM, per-family, negative control)
.venv/bin/python bench/score.py
```

## Phase 2 — Juliet (CWE476 null-deref, Flow-01)
```bash
git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/arichardson/juliet-test-suite-c.git vendor/juliet   # (extractor tự sparse-checkout)
.venv/bin/python bench/juliet_extract.py                                    # -> bench/items/gold_juliet.jsonl
# gen/score chạy trên gold khác qua env GOLD + BENCH_CACHE:
GOLD=bench/items/gold_juliet.jsonl BENCH_CACHE=bench/juliet_cache.jsonl GROQ_API_KEY=... .venv/bin/python bench/gen.py
GOLD=bench/items/gold_juliet.jsonl BENCH_CACHE=bench/juliet_cache.jsonl .venv/bin/python bench/score.py
```
> **Hạn chế đã biết:** annotator gốc bỏ sót deref đơn `*data` → `family_pred=None` trên phần lớn case Juliet null-deref
> (chỉ `data->field` được nhận). Cần **concept augmenter** (nhận `*ptr`; `oob` phải có buffer thật) để concept
> hướng dẫn đúng — cũng vá luôn mislabel của seed (null_02/null_03).

## File
| file | vai trò |
|---|---|
| `authored.py` | 27 case tự soạn (vuln/fixed/ref_test/expect) |
| `run_diff.py` | harness vi-phân: assemble + compile_run (ASAN+UBSan) + run_diff |
| `concepts.py` | augmenter (`*ptr`→ptr_deref) + `family_of` (oob cần buffer thật) bench-local |
| `build_items.py` | tự kiểm oracle + annotate + augment concept → `items/gold.jsonl` |
| `prompts.py` | prompt blind/concept (không leak `func_fixed`); `prompt_key` = hash prompt → đổi prompt tự invalidate cache |
| `gen.py` | sinh test qua Groq → `bench_cache.jsonl` |
| `score.py` | bảng TP/FP/DISCRIM + per-family + negative control |

Phase sau: `juliet_extract.py` bơm Juliet Test Suite vào cùng schema (CWE121/190/369/476).
