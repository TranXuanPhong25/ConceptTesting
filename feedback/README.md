# Execution-feedback loop (hướng 1)

Cải tiến concept **không cần train**: thay vì sinh test one-shot, dùng chính oracle vi-phân
(`bench/run_diff`) làm **phản hồi** để model tự sửa test qua ≤`ROUNDS` vòng.

```
concept-prompt ─► LLM ─► test ─► run_diff (compile+ASAN vuln|fixed)
                          ▲                    │
                          └── feedback ◄────────┘   (nếu chưa discriminate)
```
Feedback theo 3 lỗi:
- **không compile** → trả lỗi compile;
- **không nổ trên vuln** → "chưa trigger, input độc hại hơn / đi đúng điểm lỗi";
- **nổ trên fixed** (báo động giả) → "test tự crash, chỉ được kích hoạt lỗi trong focal".

So 3 điều kiện trên cùng gold: `blind_1shot` · `concept_1shot` · **`concept_fb`** (concept + feedback).
So sánh chính: **concept_fb vs concept_1shot** = tác dụng của vòng phản hồi.

## Chạy (từ repo root)
```bash
export GROQ_API_KEY=<KEY>      # rotate key đã lộ
export ROUNDS=3

# SEED (27 case tự soạn)
.venv/bin/python feedback/loop.py

# JULIET (14 case NIST)
GOLD=bench/items/gold_juliet.jsonl FB_CACHE=feedback/fb_juliet.jsonl .venv/bin/python feedback/loop.py
```
Env: `ROUNDS` (mặc định 3) · `GROQ_MODEL` (gpt-oss-120b) · `GROQ_RPM=30` · `GOLD` · `FB_CACHE`.
Resumable (cache kết quả cuối mỗi item). ~110 call (seed) / ~70 (Juliet), free, one-time.

> Tái dùng `bench/run_diff` (oracle) + `bench/prompts` (blind/concept, không leak `func_fixed`).
> Không finetune. Đây là trần "concept + kiểm chứng" của hướng hiện tại.

## Hướng A — concept lái feedback bằng coverage (`loop_cov.py`)
Thêm tín hiệu **concept-coverage** (gcov): test có CHẠM dòng thao tác nguy hiểm mà concept đánh dấu không?
→ feedback cụ thể hơn: *"chưa chạm dòng `free(..)`/`*p` → lái execution tới đó"* vs *"chạm rồi nhưng input chưa đủ độc hại"*.
So **concept_fb** (feedback thường) vs **concept_fb_cov** (có coverage) → đo coverage-steering thêm được bao nhiêu.
```bash
export ROUNDS=3
.venv/bin/python feedback/loop_cov.py                                                        # seed
GOLD=bench/items/gold_juliet.jsonl FB_CACHE=feedback/fb_juliet.jsonl .venv/bin/python feedback/loop_cov.py   # juliet
```
Tái dùng cache của `loop.py` cho 3 cột đầu → chỉ sinh mới `concept_fb_cov`. Cần `gcov` (macOS/Linux có sẵn).
