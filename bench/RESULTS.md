# Kết quả — Concept-guided vs Blind unit-test generation (executed, de-leaked)

**Thiết lập.** Mỗi case là hàm `focal(input)` build được ở 2 bản cùng chữ ký: `func_vuln` / `func_fixed`.
Teacher (`openai/gpt-oss-120b`) sinh test từ 2 điều kiện — **blind** (few-shot + CoT, không concept)
và **concept** (dòng rủi ro do tree-sitter + họ nghi ngờ `family_pred` heuristic + recipe; **không** dùng
nhãn CWE, **không** thấy `func_fixed`). Test được compile+chạy với **từng** bản dưới `gcc -fsanitize=address,undefined`.
Chấm **executed, multi-sample K=3** (metric = tỉ lệ mẫu đạt).

- **DISCRIM** = compile cả 2 ∧ **nổ trên vuln** ∧ **KHÔNG nổ trên fixed** → test định vị ĐÚNG bug (không crash bừa).
- Không rò rỉ: concept dùng heuristic (không nhãn CWE); `func_fixed` không vào prompt; cache key = hash prompt.

## Bảng 1 — Seed (27 case tự soạn, 6 họ memory-safety), K=3
| cond | compile_v | FIRES_v | clean_fixed | **DISCRIM** |
|---|---|---|---|---|
| blind | 80% | 79% | 89% | **68%** |
| **concept** | **91%** | **89%** | 89% | **79%** |

DISCRIM theo họ (disc/n, TB qua 3 mẫu): oob_write 4.7→**5.0** · null_deref 0.3→**2.0** · uaf 2.0→**2.7** ·
double_free 2.0→**2.3** · oob 2.0=2.0 · oob_read **4.0**→3.3 (blind nhỉnh).
Negative control (sạch cả 2 = tốt): blind 1.0/5 · **concept 2.7/5** (concept ít báo động giả hơn).

## Bảng 2 — Juliet Test Suite / NIST SARD (14 case thật, 3 họ), K=3
| cond | compile_v | FIRES_v | clean_fixed | **DISCRIM** |
|---|---|---|---|---|
| blind | 90% | 90% | 67% | **57%** |
| **concept** | **93%** | 83% | **86%** | **69%** |

DISCRIM theo họ: null_deref 0.3→**3.7** · double_free **4.7**→4.3 · uaf **3.0**→1.7 (blind nhỉnh).
Blind `clean_fixed` chỉ 67% = **nổ trên bản fixed 33%** (crash bừa) → DISCRIM thấp; concept kỷ luật hơn (86%).

## Bảng 3 — Execution-feedback loop (hướng 1, KHÔNG train), K=1, ROUNDS=3
`concept_fb` = concept_1shot + oracle refine (compile/ASAN → feedback → viết lại, ≤3 vòng, giữ best).
Đơn-mẫu (K=1) nhưng feedback đơn điệu (concept_fb ≥ concept_1shot mọi họ). Xem `feedback/`.

| bộ | blind_1shot | concept_1shot | **concept_fb** |
|---|---|---|---|
| **Seed** (22) | 68% | 77% | **91%** (20/22) |
| **Juliet** (14) | 57% | 64% | **79%** (11/14) |

Feedback nâng concept **+14** (seed 77→91) / **+15** (Juliet 64→79); so blind là **+23 / +22**.
Per-family: mọi họ concept_fb ≥ concept_1shot. Điểm mềm: uaf/Juliet (concept_fb 2/3 < blind 3/3, n=3).
→ Oracle-in-the-loop là đòn bẩy lớn nhất của hướng concept, không cần finetune.

**Hướng A — concept lái feedback bằng coverage (gcov):** `concept_fb_cov` = `concept_fb` ĐÚNG BẰNG NHAU
(seed 91%/20-22, Juliet 86%/12-14, per-family y hệt) → **không lift**. Hàm nhỏ, một-đường-chạy → "đã chạm
dòng nguy hiểm" gần như luôn đúng → tín hiệu coverage trùng với plain feedback. **Kết luận:** với model mạnh +
hàm nhỏ, trần nằm ở `concept_fb`; concept giàu hơn (spec/coverage) chỉ có ý nghĩa với **hàm lớn/nhiều path
(real-world)** hoặc **model yếu (student)** — nơi tự-infer/tự-tìm-đường-tới-sink là khó.

## Bảng 4 — Ablation: concept "giàu" (đặc-tả tấn công đầy đủ) HẠI ở teacher, K=3
`concept2` = concept + đặc-tả tấn công viết tay (buffer/size/biến-nguy-hiểm/ràng-buộc, từ `extract_facts`).

| bộ | blind | concept | **concept2** |
|---|---|---|---|
| **Seed** (22) | 68% | **79%** | 65% (compile 91→76%) |

→ **Model mạnh (gpt-oss-120b) đã TỰ suy ra buffer/size/ràng buộc từ code.** Thêm công thức tấn công viết tay
là **thừa**: prompt dài hơn → model over-engineer (tự chép typedef/scaffold → fail compile), vài đặc-tả chưa
chuẩn còn misdirect. **Bài học:** concept-guidance nên NGẮN GỌN (loại bug + dòng rủi ro), KHÔNG phải recipe
đầy đủ. Đặc-tả tường minh để dành cho **student nhỏ** (không tự infer được) khi làm finetune.

## Bảng 5 — Placebo (concept-shuffle): concept CONTENT là nhân-quả, **K=3** ⭐
`concept_shuffle` = concept nhưng xáo tag rủi ro giữa các dòng + đảo family (concept-shaped, SAI nội dung).

| bộ | blind | concept | concept_shuffle | McNemar concept>shuffle |
|---|---|---|---|---|
| **Seed** (22) | 70% | 77% | **33%** | **14–0, p=0.0001 (\*\*\*)** |
| **Juliet** (14) | 48% | 71% | 38% | 6–1, p=0.125 (ns, n nhỏ) |

→ Concept SAI tụt còn **33% — THẤP HƠN cả blind (70%)**: model **thực sự dùng** nội dung concept, corrupt là hại.
**Bằng chứng nhân-quả mạnh** (control literature CHƯA ai làm). concept-vs-blind trending (seed 6–1, Juliet 4–0)
nhưng ns ở n=22/14 — hạn chế small-n. `placebo/run.py`.

## Bảng 6 — Patch-derived concept (guidance từ diff vuln↔fixed), **K=3**
`bench_patch` = blind base + điều kiện AN TOÀN bản vá áp đặt (rút từ diff) = điều cần VI PHẠM để trigger (kiểu DIG).

| bộ | blind | concept (tree-sitter) | **bench_patch** |
|---|---|---|---|
| **Seed** (22, dễ) | 61% | 76% | 59% (≈ blind; concept nhỉnh) |
| **Juliet** (14, khó/NIST) | 36% | 71% | **74%** (patch≈concept; patch>blind 5–0, p=0.0625) |

→ **Patch-derived ≈ tree-sitter concept — nguồn guidance thay thế TƯƠNG ĐƯƠNG, KHÔNG vượt.** Cả hai đều giúp
trên target khó (Juliet, >> blind), đều bão hoà trên seed dễ. (Con số K=1 "patch 86 / p=0.004" là NHIỄU do blind
rơi thấp lần đó — K=3 đã sửa.) `patch_concept/run.py`.

## Diễn giải
- **Concept +11 (seed) / +12 (Juliet) điểm DISCRIM**, ổn định qua K=3 (hết dao động ±9 của 1-mẫu).
- Lợi thế lớn nhất ở **null_deref**: blind đoán nhầm loại bug (tưởng use-after-free → truyền con trỏ đã freed →
  nổ CẢ vuln lẫn fixed), còn concept biết "deref NULL → truyền NULL" → chỉ nổ trên vuln. Đây là giá trị cốt lõi
  của concept-guidance: **định hướng đúng LOẠI lỗi** để sinh input phù hợp.
- Concept cũng cải thiện **specificity** (ít false-fire trên hàm an toàn / bản fixed).
- Điểm mềm: oob_read (seed) & uaf (Juliet) — blind nhỉnh hơn chút, biên nhỏ; và `[buf_access+ptr_deref]` không
  buffer_alloc thì 8 concept không tách được oob_read vs null_deref (hạn chế của BỘ concept).

## Giới hạn (trung thực)
- Mức **teacher** (model mạnh) — không phải student finetune (student nhỏ bị catastrophic forgetting, ngoài phạm vi).
- n nhỏ (seed 22 pos, Juliet 14) → tin cột **tổng DISCRIM** hơn per-family. K=3 đã giảm nhiễu.
- Phạm vi: 6 họ memory-safety mà 8 concept phủ; `int_overflow`/`div_zero` ngoài phạm vi. Juliet: chỉ họ
  executable-triggerable + có input DOF (CWE476/416/415); bỏ CWE690/122/124.

## Tái lập
```bash
export SAMPLES=3
.venv/bin/python bench/build_items.py            # gold seed (self-check 27/27)
.venv/bin/python bench/juliet_extract.py         # gold Juliet (self-check 14/14)
GROQ_API_KEY=... .venv/bin/python bench/gen.py && .venv/bin/python bench/score.py
GOLD=bench/items/gold_juliet.jsonl BENCH_CACHE=bench/juliet_cache.jsonl GROQ_API_KEY=... .venv/bin/python bench/gen.py
GOLD=bench/items/gold_juliet.jsonl BENCH_CACHE=bench/juliet_cache.jsonl .venv/bin/python bench/score.py
```
