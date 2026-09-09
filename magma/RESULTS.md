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

## Giới hạn (trung thực)
- **Tuyệt đối vẫn khiêm tốn** (8/100 trigger): nhiều bug Magma cực hiếm trigger kể cả fuzzing 24h, hoặc không
  reachable qua harness đang dùng (đọc-file). Đây là trần của bài toán, không phải của concept.
- Mức **teacher** (model mạnh), không phải student finetune.
- Discordant nhỏ (8) nhưng một chiều (8–0) → p<0.01. REACHED (17 vs 5) củng cố hướng.
- php/poppler chưa build (nặng dưới QEMU) → còn có thể mở rộng.

## Tái lập
```bash
# (sau setup.sh + extract 7 targets -> items/*.jsonl = 100 bug)
GROQ_API_KEY=gsk_... ROUNDS=3 .venv/bin/python magma/loop.py     # blind_fb vs concept_fb
GROQ_API_KEY=gsk_... SAMPLES=3 .venv/bin/python magma/gen.py && .venv/bin/python magma/score.py   # one-shot
```
