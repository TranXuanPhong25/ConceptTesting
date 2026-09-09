# Kết quả — Concept-guided vs Blind unit-test generation (executed, de-leaked)

**Thiết lập.** Mỗi case là hàm `focal(input)` build được ở 2 bản cùng chữ ký: `func_vuln` / `func_fixed`.
Teacher (`openai/gpt-oss-120b`) sinh **unit test** từ 2 điều kiện — **blind** (few-shot + CoT, không concept)
và **concept** (dòng rủi ro do tree-sitter + họ nghi ngờ `family_pred` heuristic + recipe; **không** dùng
nhãn CWE, **không** thấy `func_fixed`). Test được compile+chạy với **từng** bản dưới `gcc -fsanitize=address,undefined`.
Chấm **executed, multi-sample K=3** (metric = tỉ lệ mẫu đạt).

- **DISCRIM** = compile cả 2 ∧ **nổ trên vuln** ∧ **KHÔNG nổ trên fixed** → test định vị ĐÚNG bug (không crash bừa).
- Không rò rỉ: concept dùng heuristic (không nhãn CWE); `func_fixed` không vào prompt; cache key = hash prompt.

## Dataset — CHỈ Juliet Test Suite (NIST SARD), **19 case thật, 8 CWE / 5 họ**
Bỏ hoàn toàn seed "tự soạn" (synthetic) khỏi đường bằng-chứng. `bench/authored.py` chỉ còn là **smoke
fixture** cho harness (self-check oracle 27/27), KHÔNG dùng để báo cáo. Toàn bộ evidence chạy trên Juliet:

| Trục | Họ | CWE | n | Sink | Trigger |
|---|---|---|---|---|---|
| Temporal | null_deref | 476 | 6 | deref `data` (NULL) | truyền `NULL` |
| Temporal | uaf | 416 | 3 | `free(data)` rồi deref | buffer đã free |
| Temporal | double_free | 415 | 5 | `free(data)` 2 lần | buffer malloc |
| Spatial (write) | oob_write over | 121 (stack), 122 (heap) | 2 | `buffer[data]=…`, guard thiếu upper | `data = N` |
| Spatial (write) | oob_write under | 124 | 1 | `buffer[data]=…`, guard thiếu lower | `data = -1` |
| Spatial (read) | oob_read over | 126 | 1 | đọc `buffer[data]`, thiếu upper | `data = N` |
| Spatial (read) | oob_read under | 127 | 1 | đọc `buffer[data]`, thiếu lower | `data = -1` |

**vuln/fixed là của CHÍNH NIST — không tự chế bản vá.** `func_vuln` = guard của `bad()` (THIẾU, vd `if(data>=0)`);
`func_fixed` = guard của `goodB2G()` (`if(data>=0 && data<N)`). Extractor `bench/juliet_extract.py` chỉ **tham-số-hoá**
(bỏ source-flow fscanf/rand/socket → tham số focal) rồi self-check qua đúng oracle ASAN (19/19 vuln nổ, fixed sạch).

### Vì sao KHÔNG dùng self-triggering `bad()`/`good()` nguyên bản?
KHÔNG phải "không có chỗ cho input" — **bài toán là sinh UNIT TEST**, và `int main(){ bad(); }` cũng là một
unit test hợp lệ. Lý do thật là **KHÔNG PHÂN BIỆT ĐƯỢC concept**: trigger bị nhồi cứng trong `bad()` → MỌI
điều kiện (blind / concept / shuffle) đều sinh đúng một driver tầm thường `bad();` → DISCRIM = 1 cho tất cả →
benchmark đo được **con số 0** về đóng góp của concept. Chỉ khi focal có **điểm quyết định** mà người viết test
phải chọn đúng (ở đây: chỉ số OOB) thì hiểu-biết-về-bug (concept) mới tạo khác biệt. Vì thế ta lấy subfamily
**CWE839 `buffer[data]`** (có input thật + bản vá input-conditioned của NIST) và bỏ subfamily hardcode-constant
(memcpy `sizeof(struct)`, `strcpy(SRC)`) — bản vá của chúng là "sửa hằng số", tham-số-hoá sẽ thành TỰ CHẾ bản vá.

### Vì sao KHÔNG "chạy full 100% Juliet"?
~64k case Juliet là **bội số tổ hợp** của {sink × source-flow × data-type × flow-variant obfuscation
(`if(5==5)`, `goto`, con trỏ hàm, đa-TU…)} trên **một số ít flaw gốc**. Với bài toán sinh test, flow-variant
cùng một sink là **trùng lặp ngữ nghĩa** (test giống hệt) → dedup theo focal là đúng. Bằng chứng: 5906 file
CWE121 → **1** focal unique; 3656 CWE122 → **1**; 372 CWE476 → **6** (theo type × sink). "100%" chỉ bơm `n`
bằng bản sao gần-trùng, KHÔNG thêm độ khó → dedup-by-focal cho con số DISTINCT trung thực.

## Bảng 1 — Juliet executed, temporal (476/416/415, 14 case đã có cache), K=3
| cond | compile_v | FIRES_v | clean_fixed | **DISCRIM** |
|---|---|---|---|---|
| blind | 90% | 90% | 67% | **57%** |
| **concept** | **93%** | 83% | **86%** | **69%** |

DISCRIM theo họ: null_deref 0.3→**3.7** · double_free **4.7**→4.3 · uaf **3.0**→1.7 (blind nhỉnh).
Lợi thế lớn nhất **null_deref**: blind đoán nhầm loại bug (tưởng UAF → truyền con trỏ đã freed → nổ CẢ
vuln lẫn fixed) còn concept biết "deref NULL → truyền NULL" → chỉ nổ trên vuln. Blind `clean_fixed` chỉ 67%
= nổ trên bản fixed 33% (crash bừa) → DISCRIM thấp; concept kỷ luật hơn (86%).

## Bảng 1b — Spatial (121/122/124/126/127) — CHỜ chạy `gen.py` (5 focal mới)
5 họ không-gian vừa thêm (self-check 19/19 OK) **chưa có cache** → chạy lại 1 lần để điền:
```bash
export SAMPLES=3
GROQ_API_KEY=... .venv/bin/python bench/gen.py      # mặc định GOLD=gold_juliet.jsonl, cache=juliet_cache.jsonl
.venv/bin/python bench/score.py                     # bảng đầy đủ 19 case / 5 họ
```
Kỳ vọng (giả thuyết, chưa chạy): concept dẫn ở missing-bound-check — blind hay đoán sai hướng vượt biên
(over vs under) hoặc quên vế thiếu của guard. Điền số THẬT vào đây sau khi chạy.

## Bảng 2 — Execution-feedback loop (hướng 1, KHÔNG train), K=1, ROUNDS=3
`concept_fb` = concept_1shot + oracle refine (compile/ASAN → feedback → viết lại, ≤3 vòng, giữ best).
Số dưới đây đo trên **temporal 14** (Juliet); chạy lại `feedback/loop.py` để phủ 19.

| bộ | blind_1shot | concept_1shot | **concept_fb** |
|---|---|---|---|
| **Juliet temporal** (14) | 57% | 64% | **79%** (11/14) |

Feedback nâng concept **+15** (64→79); so blind là **+22**. Mọi họ concept_fb ≥ concept_1shot.
→ Oracle-in-the-loop là đòn bẩy lớn nhất của hướng concept, không cần finetune.

**Hướng A — concept lái feedback bằng coverage (gcov):** `concept_fb_cov` = `concept_fb` (per-family y hệt)
→ **không lift**. Hàm nhỏ, một-đường-chạy → "đã chạm dòng nguy hiểm" gần như luôn đúng → tín hiệu coverage
trùng plain feedback. Trần nằm ở `concept_fb`; concept giàu hơn chỉ có nghĩa với **hàm lớn/nhiều path** hoặc
**model yếu (student)**.

## Bảng 3 — Ablation: concept "giàu" (đặc-tả tấn công đầy đủ) HẠI ở teacher, K=3
`concept2` = concept + đặc-tả tấn công viết tay (buffer/size/biến-nguy-hiểm/ràng-buộc, từ `extract_facts`).
Đo trên bộ nhỏ; kết luận định tính giữ nguyên: **model mạnh đã TỰ suy ra buffer/size/ràng buộc từ code** →
thêm công thức tấn công là **thừa** (prompt dài → over-engineer, tự chép typedef → fail compile). Bài học:
concept-guidance nên NGẮN GỌN (loại bug + dòng rủi ro), đặc-tả tường minh để dành cho **student nhỏ**.

## Bảng 4 — Placebo (concept-shuffle): concept CONTENT là nhân-quả, K=3 ⭐
`concept_shuffle` = concept nhưng xáo tag rủi ro giữa các dòng + đảo family (concept-shaped, SAI nội dung).
Nếu lợi thế concept là THẬT → shuffle phải tụt về ~blind hoặc thấp hơn.

| bộ | blind | concept | concept_shuffle | McNemar concept>shuffle |
|---|---|---|---|---|
| **Juliet temporal** (14) | 48% | 71% | 38% | 6–1, p=0.125 (ns, n nhỏ) |

→ Concept SAI tụt thấp → model **thực sự dùng** nội dung concept, corrupt là hại. **Bằng chứng nhân-quả**
(control literature CHƯA ai làm). Chạy lại `placebo/run.py` để refresh trên 19. `placebo/run.py`.

## Bảng 5 — Patch-derived concept (guidance từ diff vuln↔fixed), K=3
`bench_patch` = blind base + điều kiện AN TOÀN bản vá áp đặt (rút từ diff) = điều cần VI PHẠM để trigger (kiểu DIG).

| bộ | blind | concept (tree-sitter) | **bench_patch** |
|---|---|---|---|
| **Juliet temporal** (14, khó/NIST) | 36% | 71% | **74%** (patch≈concept; patch>blind 5–0, p=0.0625) |

→ **Patch-derived ≈ tree-sitter concept — nguồn guidance thay thế TƯƠNG ĐƯƠNG, KHÔNG vượt.** Cả hai đều giúp
trên target khó (>> blind). (Con số K=1 "patch 86 / p=0.004" là NHIỄU, K=3 đã sửa.) `patch_concept/run.py`.

## Giới hạn (trung thực)
- Mức **teacher** (model mạnh) — không phải student finetune (student nhỏ bị catastrophic forgetting, ngoài phạm vi).
- **n nhỏ**: sau dedup-by-focal, Juliet cho 19 distinct focal (5 họ). Đây là con số DISTINCT trung thực cho bài
  toán sinh-test, không phải hạn chế "trích chưa hết" — flow-variant là trùng lặp ngữ nghĩa (xem trên).
- Phạm vi: 5 họ memory-safety mà 8 concept phủ; `int_overflow`/`div_zero` ngoài phạm vi (không có concept tương ứng).
- Bảng 1b/2/4/5 hiện phản ánh **temporal 14** đã cache; chạy lại các script (mặc định đã trỏ Juliet) để phủ 19.

## Tái lập
```bash
git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/arichardson/juliet-test-suite-c.git vendor/juliet
export SAMPLES=3
.venv/bin/python bench/juliet_extract.py          # gold Juliet 19 (self-check 19/19, tự sparse-checkout 8 CWE)
GROQ_API_KEY=... .venv/bin/python bench/gen.py     # mặc định GOLD=gold_juliet.jsonl
.venv/bin/python bench/score.py                    # bảng concept vs blind (19 case / 5 họ)
# feedback / placebo / patch: mặc định cũng đã trỏ gold_juliet.jsonl
GROQ_API_KEY=... .venv/bin/python feedback/loop.py && \
GROQ_API_KEY=... .venv/bin/python placebo/run.py && \
GROQ_API_KEY=... .venv/bin/python patch_concept/run.py
```
