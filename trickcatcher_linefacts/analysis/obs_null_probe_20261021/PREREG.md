# OBS-null probe — E4 exception rendering (PREREG, viết trước mọi model call)

Ngày 2026-10-21. User chọn probe này sau [Phase A](../claim_role_phaseA_20261021/AUDIT.md) (Gate A = STOP).

## Hypothesis

**H_obs:** ở E4 (concept_adaptive, concept_committed), model withdraw claim đúng "may raise ValueError" và predict
`return None` vì đọc exception observation được render `"output": null` như giá trị trả về `None`.

Đây là hypothesis khác H_role. **Kết quả probe không mở lại Gate A** và không được dùng để nâng E4 lên ROLE
high cho plan claim-role; muốn revive H_role phải có plan mới.

## Design

- Contexts: saved T2 requests (first-error turn) của `E4__concept_adaptive__2`, `E4__concept_committed__2`, và
  `E4__generic_adaptive__2` (negative control: arm gốc đọc đúng). Messages lấy từ frozen `wire_request.json`
  (đã kiểm tra trùng `requests/`).
- Hai renderings mỗi context:
  - **control**: messages verbatim.
  - **treatment**: chỉ xóa substring `"output": null, ` đứng trước `"output_capture": "unavailable"` trong user
    content (đúng 2 chỗ/context, đều là exception observations T1_1/T1_2). Giữ `execution_status=exception`,
    `exception_type=ValueError`, `output_capture=unavailable`. Không đổi gì khác.
- 6 completions tổng. Cùng params v40: model `qwen2.5-coder-32b-instruct`, temperature 0, top_p 1, max_tokens 1536,
  seed 20261021. Không retry nội dung/transport; lỗi transport = slot mất, ghi lại. Không chạy native/PUT.
- Endpoint: user-provided local Qwen32B, URL chỉ từ env (file chmod 600 ngoài repo), không log URL. Không paid fallback.

## Scoring (tự động, rules cố định)

Trên parsed JSON reply (parse fail = `invalid`, giữ trong denominator):

- `retained`: có ≥1 claim chứa "ValueError" với stance ∈ {candidate, keep, revise} **và** không claim nào chứa
  "ValueError" có stance withdraw.
- `none_pred`: có query prediction chứa "None" nhưng không chứa "ValueError"/"raise"/"exception" (case-insensitive).
- Context outcome = `retained and not none_pred` → **correct**; còn lại → **wrong** (hoặc invalid).

## Interpretation (cố định trước)

1. **Reproduction:** concept context được gọi là reproducing nếu control = wrong (giống original). Context
   control = correct → non-reproducing, loại khỏi inference, báo riêng.
2. **H_obs supported** nếu mọi reproducing concept context có treatment = correct, và GA treatment không thành wrong.
3. **H_obs not supported** nếu mọi reproducing concept context có treatment = wrong.
4. Còn lại (mixed, 0 reproducing context, GA regress, invalid) → **inconclusive**.
5. n = 2 concept contexts, temperature 0: đây là mechanism check trên seen data, không phải efficacy claim.
   Không thêm contexts/replicates/prompt variants sau khi xem outputs.

Manual reading của raw text được báo cáo cạnh automatic score; nếu khác nhau, ghi cả hai, automatic score giữ
làm verdict.

## Amendment 1 (2026-10-21, trước mọi model call; từ independent pre-run review)

Must-fixes đã áp vào `run.py`:

1. Kiểm tra `QWEN_BASE_URL` trước loop; thiếu env → exit, không consume slot.
2. Scorer: reply không phải dict, `claims` không phải list, hoặc `queries` sai kiểu → `invalid` (không crash).
   Bỏ ```json fences trước parse như v40 `decode()`.
3. Scorer chính xác hơn (thay rule cũ ở "Scoring"):
   - claim **affirmative** = statement chứa valueerror/raise/exception và không có negation (not/never/no longer/without
     trước các từ đó); claim **negated** = có negation đó.
   - `retained` = có affirmative claim stance ∈ {candidate, keep, revise}, không affirmative claim nào withdraw, và
     không negated claim nào stance ∈ {candidate, keep, revise}.
   - `none_pred` = chỉ xét `replay_input` predictions; match "return(s) None" không đứng sau "not"/"never", hoặc
     prediction chỉ là "None". ("return None instead of raising" → none_pred.)
4. Interpretation, thứ tự ưu tiên cố định:
   a. Concept context có control hoặc treatment invalid/transport error → loại context đó.
   b. Còn lại, reproducing = control wrong. Không còn reproducing context → inconclusive.
   c. Mọi reproducing context treatment wrong → **not supported** (không cần GA).
   d. Mọi reproducing context treatment correct **và** GA treatment valid + correct → **supported**.
   e. Mọi trường hợp khác (mixed; GA treatment invalid/wrong) → inconclusive.
5. Nếu manual reading khác automatic score ở context nào ảnh hưởng verdict → verdict = inconclusive (thay rule
   "automatic giữ làm verdict").

Nits đã áp: no proxy/no redirect, timeout 180s như v40, ghi `identical_to_original` cho control (determinism check).
