# Concept-binding ablation — E4 T2 (PREREG, viết trước mọi model call)

Ngày 2026-10-22. Follow-up của [OBS-null probe](../obs_null_probe_20261021/REPORT.md) (H_obs not supported). User
đồng ý test.

## Hypothesis

**H_bind:** ở E4, concept arms (CA, CC) withdraw claim đúng "may raise ValueError" và predict `return None` vì concept
packet đưa normative outcome vào context; GA (không có packet, cùng exception observations) đúng.

Post-hoc từ một fixture. Đây là mechanism check, không phải efficacy hoặc generalization claim. Không mở lại Gate A
của claim-role plan.

## Design

- Contexts: saved T2 requests `E4__concept_adaptive__2`, `E4__concept_committed__2` (frozen `wire_request.json`).
- Control = probe trước: replay verbatim đã cho reply byte-identical với v40 original (wrong ở cả hai). Không gọi lại.
- Hai ablations, mỗi context một call (tổng **4 calls**):
  - **A1 `no_allowed_outcome`:** chỉ xóa key `context.concept_binding.allowed_outcome` (`"return None"`). Giữ
    `spec_quote` vì nó là trích dẫn spec (spec đầy đủ vẫn có trong `context.spec`).
  - **A2 `no_packet`:** xóa ba keys `context.concept`, `context.concept_binding`, `context.abstract_gap` (đúng các keys
    GA không có). Mọi thứ khác giữ nguyên.
- Serialization: `json.dumps(..., ensure_ascii=False)` với default separators; assert round-trip của bản gốc khớp từng byte.
- Không thay instruction, history, observations. **Caveat:** `earlier_turns` vẫn chứa T1 của chính concept arm (vd. why
  "contradicts the spec which requires returning None"), sinh ra khi có packet. A2 vì vậy không phải GA context.
- Params như v40: `qwen2.5-coder-32b-instruct`, temperature 0, top_p 1, max_tokens 1536, seed 20261021. Không retry;
  transport error = slot mất. Không native/PUT. URL chỉ từ env, không log.

## Scoring

Dùng nguyên `score()` của `../obs_null_probe_20261021/run.py` (amendment 1): `correct` = giữ affirmative ValueError
claim, không withdraw, không negated claim live, không replay prediction "return None". Invalid giữ trong denominator.

## Interpretation (cố định)

Bỏ context có ablation invalid khỏi rule tương ứng. Trên các context valid:

1. A1 correct ở mọi context → **binding value đủ gây lỗi** (H_bind supported, cụ thể `allowed_outcome`).
2. A1 wrong, A2 correct ở mọi context → **packet-level** (H_bind supported, không quy riêng cho `allowed_outcome`).
3. A2 wrong ở mọi context → **H_bind not supported** (lỗi tồn tại không cần packet; history/spec đủ).
4. Còn lại (mixed giữa contexts, A1 correct nhưng A2 wrong, không context valid) → **inconclusive**.

Manual reading báo cạnh automatic score; khác nhau ở điểm ảnh hưởng verdict → inconclusive. Không thêm contexts,
replicates hoặc prompt variants sau khi xem outputs.

## Amendment 1 (2026-10-22, trước mọi model call; từ independent pre-run review)

Thay toàn bộ phần "Interpretation" ở trên:

- Thêm **fresh control** (verbatim replay) mỗi context: tổng **6 calls**. Context chỉ **valid** nếu fresh control
  byte-identical với v40 original reply, reported model = `qwen2.5-coder-32b-instruct`, và cả A1, A2 đều parse-valid.
  Không có context valid → **inconclusive**.
- Trên các valid contexts (≥1), rules loại trừ nhau:
  a. A1 correct **và** A2 correct ở mọi context → `allowed_outcome` là **cần thiết** cho lỗi ở T2 (H_bind supported,
     binding value). Lưu ý `concept.activation` vẫn còn "return None if no eligible item" trong A1.
  b. A1 wrong **và** A2 correct ở mọi context → packet-level cần thiết, không quy riêng cho `allowed_outcome`.
  c. A1 wrong **và** A2 wrong ở mọi context → lỗi **không gỡ được bằng cách bỏ packet ở T2**; T1 carryover (history sinh
     ra khi có packet) chưa loại trừ. H_bind không được support ở mức T2 context.
  d. Mọi trường hợp khác (A1 correct + A2 wrong, mixed giữa contexts) → inconclusive.
- Manual-vs-automatic disagreement ảnh hưởng verdict → inconclusive (giữ nguyên).

Runner: kiểm tra overwrite cho cả 6 files trước call đầu tiên; bỏ backtick trước khi score (`None` trong backticks).
Ctrl-C giữa call không để lại file: không chạy lại slot đó, ghi là lost.
