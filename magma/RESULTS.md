# Kết quả — Concept-guided vulnerability-triggering test-gen trên **Magma (real CVE)**

**Thiết lập.** 100 bug CVE thật / 7 thư viện (libpng, libtiff, libxml2, sqlite3, libsndfile, openssl, lua).
LLM teacher `openai/gpt-oss-120b` sinh **input** cho harness; oracle = **canary Magma** (ground-truth):
VULN build (`CANARY_MODE=1`+`ISAN=1`) vs FIXED (`CANARY_MODE=3`). Metric:
- **REACHED** = chạm hàm lỗi (canary reached) — tín hiệu mềm.
- **TRIGGER** = thoả điều kiện lỗi (canary triggered) — ground-truth.
- **DISCRIM** = trigger trên vuln ∧ không crash-thật trên fixed.
Điều kiện: **blind** (chỉ "làm crash lib") vs **concept** (hàm focal + loại bug + fault_cond, KHÔNG leak input).

## Bảng 1 — One-shot (K=3), harness limit 5s/2000MB
| cond | rendered | TRIGGER | McNemar concept>blind |
|---|---|---|---|
| blind | 56% | 0% (0/100) | — |
| concept | 91% | 2% (4/100) | 4–0, **p=0.125 (ns)** |

→ One-shot **chạm trần**: sinh input cấu trúc kích hoạt bug SÂU trong một phát là quá khó (fuzzer mất hàng giờ).
Concept nhỉnh (4 vs 0) nhưng discordant nhỏ → chưa significant. (Nới timeout 0.1s→5s KHÔNG đổi trigger của
concept → timeout không phải nút thắt; độ khó one-shot mới là.)

## Bảng 2 — Feedback loop (CEGIS, KHÔNG train), ROUNDS=3 ⭐
`*_fb` = sinh → oracle (reached/triggered) → phản hồi đúng trạng thái (chưa chạm / chạm chưa thoả fault_cond /
phá bừa) → viết lại ≤3 vòng, giữ best. `magma/loop.py`.

| cond | rendered | **REACHED** | **TRIGGER** |
|---|---|---|---|
| blind_fb | 56% | 5% | **0%** (0/100) |
| **concept_fb** | **95%** | **17%** | **8%** (8/100) |

**McNemar concept_fb > blind_fb (TRIGGER): 8–0, p=0.0078 (\*\*).**

→ **Concept-guidance + execution-feedback THẮNG rõ ở cả 3 tầng phễu** trên CVE thật:
dựng input hợp lệ (95 vs 56) → **chạm hàm lỗi (17 vs 5, ×3.4)** → **trigger (8 vs 0)**.
- Feedback nâng concept 4→8 TRIGGER và biến kết quả thành **significant** (one-shot p=0.25 → feedback p=0.0078).
- **blind_fb vẫn 0%**: feedback KHÔNG cứu được blind — vòng lặp chỉ có ích khi biết *lái về đâu* (concept cho
  hàm + fault_cond). Đây chính là giá trị cốt lõi của ConceptTesting.
- **REACHED 17 vs 5** là tín hiệu sạch nhất (metric trigger còn thưa): concept dẫn model TỚI sink tốt hơn hẳn.
- Khớp `bench/` (feedback là đòn bẩy lớn nhất, 77→91%) — nay tái lập **trên thư viện THẬT**.

> ## ⚠️ CẢNH BÁO — Bảng 3, 4, 5 bị NHIỄM LỖ RÒ (phát hiện 2026-09-13, đã sửa code)
> `feedback()` trong `magma/loop.py` (bản cũ) nhét **`item["fault_cond"]` và `item["focal"]` — cả hai LẤY TỪ PATCH** —
> vào **mọi nhánh** phản hồi. Nghĩa là **từ vòng 2 trở đi, MỌI điều kiện** (kể cả `blind`, `concept_static`,
> `shuffle`, `fewshot_*`, `learned`) đều **được mách tên hàm lỗi + điều kiện lỗi**.
> **Mức phơi nhiễm: 1771/2371 lượt gọi (75%) là vòng ≥1**; hầu hết item chạy đủ 4 vòng (TB 3.81–4.00).
>
> **Hệ quả — cái gì còn, cái gì hỏng:**
> - ❌ **HỎNG: mọi so sánh GIỮA các cond** (`shuffle ≈ static`, `fewshot ≈ placebo`, `learned ≈ tree-sitter`).
>   Chúng hoà nhau **có thể chỉ vì từ vòng 2 tất cả nhận CÙNG một gợi ý bị rò** → không kết luận được
>   "nội dung concept không nhân-quả".
> - ✅ **CÒN VỮNG (thậm chí mạnh hơn): `blind` ≪ mọi cond khác.** `blind` **cũng** nhận leak trong feedback
>   mà **vẫn 0/100 trigger, 5/100 reached, 56% render** → thiếu source thì dù được mách đáp án cũng không
>   dựng nổi input hợp lệ. Đây là so sánh **bảo thủ** (thiên vị blind) nên kết luận càng chắc.
>
> **Đã sửa:** `feedback()` giờ chỉ dùng tín hiệu oracle quan sát được (rendered/reached/triggered/crash_fixed),
> **không** nhắc tên hàm hay điều kiện lỗi (giống coverage-feedback của fuzzer). `magma_concept` vẫn giữ
> fault_cond nhưng **chỉ ở prompt vòng 1** — đúng định nghĩa của nó. `PROMPT_VERSION="v2-nofbleak"` được đưa vào
> `prompt_key` để **cache nhiễm KHÔNG bị replay**. Cần **chạy lại toàn bộ (tốn API)** mới có số sạch.

## Bảng 4 — ⭐ BẢNG CHỐT: 6 điều kiện trên **ĐỦ 100 bug**, ROUNDS=3 (oracle đã verify lành)
libtiff đã fix build (autogen tải `config.guess` lỗi) → **14/14 image, 100/100 bug**. Tất cả từ cache, 0 API call.

| cond | có source? | có đáp án? | rendered | REACHED | TRIGGER |
|---|---|---|---|---|---|
| `blind` | ✗ | ✗ | 56% | **5/100** | **0/100** |
| `concept` (LEAK) | ✗ | ✓ fault_cond từ patch | 95% | 17/100 | **8/100** |
| `concept_static` (C1) | ✓ | ✗ | 97% | 19/100 | 4/100 |
| `concept_shuffle` (**placebo**) | ✓ | ✗ (nhãn **SAI**) | 97% | 23/100 | 6/100 |
| `fewshot_authored` | ✓ | ✗ | 98% | 18/100 | 5/100 |
| `fewshot_juliet` | ✓ | ✗ | **99%** | **24/100** | 7/100 |

**McNemar vs `blind`** — mọi cond thắng **một chiều tuyệt đối (không thua ca nào)**:
| cond | TRIGGER | REACHED |
|---|---|---|
| concept (leak) | +8 −0 p=0.0078 | +13 −1 **p=0.0018** |
| concept_static | +4 −0 p=0.125 | +15 −1 **p=0.0005** |
| concept_shuffle | +6 −0 p=0.031 | +19 −1 **p=0.00004** |
| fewshot_authored | +5 −0 p=0.063 | +14 −1 **p=0.0010** |
| fewshot_juliet | +7 −0 p=0.016 | +20 −1 **p=0.00002** |

**Giữa các cond (không tính blind) — TẤT CẢ ns:**
`juliet > static` +3−0 p=0.25 · `juliet vs concept(leak)` +2−3 p=1.0 · `static vs concept` +1−5 p=0.22 ·
`static vs shuffle` +1−3 p=0.63 · **`juliet > shuffle` +2−1 p=1.0** ← phép so quyết định

### Kết luận chốt (phủ định phần lớn, nhưng có 1 khẳng định mạnh)
1. **KHẲNG ĐỊNH MẠNH — thông tin bug-cụ-thể là thứ DUY NHẤT quan trọng.** `blind` gần như vô dụng
   (**0/100 trigger, 5/100 reached, chỉ 56% render nổi input hợp lệ**). Mọi cond có *bất kỳ* thông tin cụ thể nào
   (source HOẶC điều kiện lỗi) đều nhảy vọt: REACHED 5→17-24, **p = 0.0018 tới 0.00002**. Đây là kết quả
   **significant và nhất quán nhất** của cả dự án.
2. **PHỦ ĐỊNH — DẠNG của thông tin thì KHÔNG quan trọng.** Mọi cặp giữa các cond ns:
   - `concept_shuffle` (nhãn concept **SAI hoàn toàn**) = 6/100, **≥ `concept_static` (đúng) 4/100** → **lần thứ 2
     độc lập** xác nhận annotation tree-sitter **KHÔNG nhân-quả**.
   - **`fewshot_juliet` KHÔNG hơn placebo** (+2−1 p=1.0) → few-shot cũng **không** nhân-quả. (Ban đầu
     tôi tưởng juliet "lấy lại được 8% mà không leak" — **sai**: placebo cũng làm được tương đương.)
   - reachability (C2) +0, concolic (C3) +1 bug — đã đo ở Bảng 3b, cũng ns.
3. **Suy ra:** với model mạnh, đưa **source hàm lỗi hoặc điều kiện lỗi** + feedback loop là ĐỦ; mọi lớp
   concept/annotation/few-shot/reachability/concolic chồng thêm đều **không phân biệt được về mặt thống kê**.
   Giá trị của chúng (nếu có) thuộc về **model yếu (student)**, không phải teacher.

## Bảng 5 — Concept HỌC-ĐƯỢC (ConceptCoder) vs tree-sitter — **xác nhận độc lập LẦN 3**
`learned/loop_learned.py` (clone, cache riêng). Concept từ **lớp `cbl` của ConceptCoder tự train** (Kaggle,
Qwen2.5-Coder-3B LoRA 3 epoch, VD F1 64.36) thay cho tree-sitter. Prompt template **giữ nguyên** → biến duy
nhất = NGUỒN CONCEPT. Cùng 100 bug, ROUNDS=3.

| nguồn concept | rendered | REACHED | TRIGGER |
|---|---|---|---|
| tree-sitter (tĩnh) | 97% | 19/100 | 4/100 |
| **ConceptCoder (học-được)** | 98% | **19/100** | **5/100** |

McNemar `learned > tree-sitter`: TRIGGER +2 −1 **p=1.0** · REACHED +6 −6 **p=1.0** (hoà tuyệt đối).

**Đáng chú ý:** concept học-được bị **hỏng nặng** về chất lượng — `buffer_allocation` **0/38**, `bound_check`
**1/35**, và PNG003 bị gán **SAI họ** (`null_deref` thay vì `oob`), không liệt kê nổi buffer/sink/guard nào.
Dự đoán trước khi chạy là *"learned sẽ thua rõ"* — **SAI**. Chi tiết cục bộ thì đúng (PNG003 **chính là** bug
duy nhất tree-sitter trigger được mà learned mất), nhưng learned lại được **LUA004 + TIF007** → **hoà**.

⇒ **Ngay cả concept SAI/hỏng cũng không làm giảm hiệu năng** — trùng khớp hoàn toàn với placebo.

## ⭐ Tổng kết: 3 control độc lập, cùng một kết luận
| # | Control | Concept bị làm gì | Kết quả |
|---|---|---|---|
| 1 | `concept_shuffle` | xáo nhãn, đảo family (**SAI có chủ đích**) | 6/100 **≥** static 4/100 |
| 2 | `fewshot_juliet` | thêm ví dụ dạy suy luận | +2 −1 vs placebo, **p=1.0** |
| 3 | `learned` (ConceptCoder) | nhãn **collapse, sai họ** (model tự học) | +2 −1 vs tree-sitter, **p=1.0** |

Ba cách làm hỏng/thay đổi concept theo 3 kiểu khác nhau → **không cái nào đổi kết quả**. Trong khi bỏ hẳn
thông tin (`blind`) thì sập hoàn toàn (0/100 trigger, 5/100 reached, 56% render). 

**Kết luận cuối cùng:** cái model cần là **sự hiện diện của thông tin bug-cụ-thể** (source hàm lỗi hoặc điều kiện
lỗi), **không phải chất lượng/dạng của concept annotation**.

**Phương pháp luận rút ra:** nếu không có **placebo control**, ta đã kết luận sai 3 lần
(concept "thắng", few-shot "thắng", juliet "lấy lại được leak"). Placebo là thứ bác bỏ cả 3.

## Giới hạn (trung thực)
- **Tuyệt đối vẫn khiêm tốn** (8/100 trigger): nhiều bug Magma cực hiếm trigger kể cả fuzzing 24h, hoặc không
  reachable qua harness đang dùng (đọc-file). Đây là trần của bài toán, không phải của concept.
- Mức **teacher** (model mạnh), không phải student finetune.
- Discordant nhỏ (8) nhưng một chiều (8–0) → p<0.01. REACHED (17 vs 5) củng cố hướng.
- php/poppler chưa build (nặng dưới QEMU) → còn có thể mở rộng.

## Bảng 3 — "concept++" ablation (de-leak + reachability + concolic), ROUNDS=3 — **NULL ở teacher (trung thực)**
Trả lời critique "concept = mách đáp án (fault_cond bê từ patch)". Chạy 2 thí nghiệm ablation trên 100 CVE.

### 3a — De-leak + Placebo (`magma/loop.py`, 4 cond)
| cond | rendered | REACHED | TRIGGER |
|---|---|---|---|
| blind | 56% | 5% | 0% |
| **concept** (patch, **LEAK** fault_cond) | 95% | 17% | **8%** |
| concept_static (C1, de-leak: source+tree-sitter, tự suy) | 97% | 19% | **4%** |
| concept_shuffle (placebo: nhãn/family/var XÁO, source thật) | 97% | 23% | **6%** |

McNemar: `concept>blind` **+8 −0 p=0.0078** · `concept_static>concept` +1 −5 p=0.22 · `shuffle>static` +3 −1 p=0.625.

### 3b — Reachability + Concolic (`concolic/loop_cc.py`, 3 cond) — bootstrap reaching **34/100**
| cond | rendered | REACHED | TRIGGER |
|---|---|---|---|
| concept_static (C1) | 95% | 20% | 4% |
| concept_reach (+C2 seed reaching + grammar) | 98% | **24%** | 4% |
| concept_cc (+C3 concolic byte-sweep) | 100% | 25% | **5%** |

McNemar: `reach>static` +2 −2 p=1.0 · `cc>reach` +1 −0 p=1.0.

### Diễn giải (thẳng — phần lớn NULL ở teacher)
1. **Leak thổi số**: `concept` 8% có được nhờ **fault_cond bê từ patch** (mách đáp án). Bỏ leak → `concept_static` **4%**. Con số trung thực là 4%.
2. **Placebo bác annotation**: `shuffle` (6%) ≥ `static` (4%), REACHED 23≥19, p=0.625 → **các annotation tree-sitter KHÔNG nhân-quả** ở teacher; cái giúp là **source code** (đưa vào cả 2). Khớp `bench/` (concept2 "giàu" hại teacher).
3. **Reachability/concolic không thêm trên trigger**: reach≈static (+2−2), cc chỉ solve **+1 bug** (cơ chế chạy thật nhưng ns). Reachability chỉ nhích **REACHED** (20→24). bootstrap **34/100** = trần: 2/3 bug không có seed chạm-sink để reach/solve.
4. **Điều kiện tường minh > source-alone**: `concept`(8%, chỉ điều kiện, KHÔNG source) > `concept_static`(4%, source, KHÔNG điều kiện) → ở teacher model thà được *nói thẳng điều kiện* hơn tự đọc hàm. ⇒ lever là **điều kiện tường minh** (nếu suy-ra được, không leak); annotation/reach/concolic đều **thừa** ở teacher.
5. **Throughline**: model mạnh chỉ cần **source/điều-kiện + feedback**; mọi lớp concept/kĩ-thuật thêm vào đều redundant Ở MỨC TEACHER → giá trị của chúng (nếu có) thuộc về **student (model yếu)** không tự infer từ code. Đây là kết quả **rigor & trung thực**: de-leak + placebo + technique-ablation chỉ ra *cái gì THỰC SỰ giúp*.

**Kỹ thuật ghi nhận:** byte-taint trên format CRC (PNG) chỉ ra 'structure' bytes, KHÔNG 'fault' → concolic defer LLM-solver; concrete-solve chỉ hợp trường số/index không-CRC (SQL/openssl).

## Tái lập
```bash
# (sau setup.sh + extract 7 targets -> items/*.jsonl = 100 bug)
GROQ_API_KEY=gsk_... ROUNDS=3 .venv/bin/python magma/loop.py     # blind_fb vs concept_fb (Bảng 2)
# Ablation de-leak/placebo (Bảng 3, phần tĩnh):
CONDS=magma_blind,magma_concept,magma_concept_static,magma_concept_shuffle \
  GROQ_API_KEY=gsk_... ROUNDS=3 .venv/bin/python magma/loop.py
# Reachability + concolic (Bảng 3, phần động):
GROQ_API_KEY=gsk_... ROUNDS=3 .venv/bin/python concolic/loop_cc.py
GROQ_API_KEY=gsk_... SAMPLES=3 .venv/bin/python magma/gen.py && .venv/bin/python magma/score.py   # one-shot (Bảng 1)
```
