# Thesis section (draft): concept packet trong agent kiểm thử — input tốt như nhau, evidence integration hỏng

Ngày 2026-10-22. Tổng hợp chuỗi v40 retry3 → Phase A (claim-role audit) → OBS-null probe → concept-binding ablation.
Không có run mới cho section này; mọi số liệu lấy từ các reports đã commit (mục "Nguồn").

## 1. Câu hỏi

Nếu đưa cho LLM testing agent một **concept** tường minh (catalog entry + binding vào spec + abstract coverage gap), agent
có (a) sinh được input expose bug tốt hơn, và (b) giữ/sửa hypothesis đúng hơn khi nhận tool feedback, so với cùng agent
không có concept packet không?

## 2. Setup (v40 retry3)

- 8 seen authored fixtures (E1–E8, HumanEval-style), 6 buggy, 1 correct (E7), 1 spec ambiguous (E8).
- 3 arms × 3 turns: **concept_adaptive (CA)**, **generic_adaptive (GA)** (cùng spec/code/base tests/initial hypothesis/raw
  observations nhưng không có packet), **concept_committed (CC)** (có packet, phải commit query batches từ T1).
- Concept packet = `concept` (catalog entry: intent, activation, dimensions), `concept_binding` (domain, condition,
  `allowed_outcome`, `spec_quote`), `abstract_gap`. Concepts do người viết cung cấp, không phải model extraction.
- Model Qwen2.5-Coder-32B-Instruct (AWQ, ctx 8192), temperature 0, seed cố định. Tool: `replay_input` chạy native PUT,
  trả về return value hoặc exception. Expected values chỉ tính sau generation freeze; `prediction` không phải oracle.

## 3. Kết quả 1: concept không tăng input yield

| | CA | GA | CC |
|---|---:|---:|---:|
| Buggy fixtures có revealing input | 6/6 | 6/6 | 6/6 |
| Fixtures chưa có supplied revealing row được expose (E1/E2/E4/E5) | 4/4 | 4/4 | 4/4 |
| Revealing final inputs (12 candidates) | 11/12 | 10/12 | 11/12 |
| False bug flags trên E7/E8 | 0 | 0 | 0 |

0 task win chỉ có ở CA. Trên fixtures này, input generation đã bão hòa ở arm không có concept, nên concept không có chỗ để
thêm giá trị ở tầng input. Kết quả này lặp lại pattern đã thấy từ v28 (ceiling, no concept gain) và v41 (sampling đã
chạm bug; bottleneck là oracle/selection).

## 4. Kết quả 2: evidence integration hỏng, và hỏng theo nhiều kiểu

Input đúng không kéo theo claim đúng. Phase A label lại toàn bộ 24 episode-arm rows (72 responses) với rubric cố định,
3 annotators độc lập (parent non-blind; reviewer 2 blind với v40 audits). Labels: SPEC (đọc sai spec), PRED (prediction/
discriminator sai), OBS (đọc sai observation), INTERFACE, ROLE (spec requirement thế vào implementation claim hoặc
prediction), FINAL (đổi stance không có replacement).

| Fixture | Failure | Arms | Label |
|---|---|---|---|
| E2 | T3 withdraw "strictly greater" (đúng, khớp chính predictions trước đó), keep "`>=` limit" = chữ của spec, trái `([2,2,2],2)→0` | CA, GA (CC giữ đúng) | ROLE high ×3 annotators |
| E3 | Binding cố ý sai (equality thay vì inclusion); model coi behavior khớp binding là spec-correct | CA, CC (GA final đúng) | SPEC |
| E4 | Sau hai ValueError observations, withdraw claim đúng "may raise ValueError", predict "will return None" | CA, CC (GA đúng) | ROLE vs OBS chưa tách |
| E6 | Withdraw/phủ nhận dedup trái `[2,2]→2`, `[2,2,2]→2` | CA, GA, CC | PRED (arithmetic sai từ T1) |

**Gate A = STOP** (đăng ký trước trong plan): high-confidence ROLE chỉ có ở 1 fixture (cần ≥2), và chỉ 2/7 eligible rows
không có upstream explanation (cần >1/2). Role confusion có tồn tại (E2 là instance sạch) nhưng **không phải giải thích
chính**: failures chia đều cho ROLE, SPEC, PRED và một case chưa phân định (E4).

## 5. Case study E4: packet và prediction slot

E4 là failure duy nhất mà **chỉ concept arms** mắc với binding đúng. Spec: "return the smallest strictly positive
integer, or None if no strictly positive integer exists". PUT gọi `min` trên tập rỗng nên raise `ValueError`. Ở T1 cả
ba arms đều predict đúng "will raise a ValueError" và observations xác nhận. Ở T2 CA/CC withdraw claim và predict
"will return None" cho `([0],)` — giá trị spec yêu cầu, không phải giá trị implementation trả.

Hai mechanism checks, mỗi cái PREREG + independent pre-run review trước mọi call, replay đúng T2 context đã đóng băng:

| Rendering của T2 context | CA | CC | GA |
|---|---|---|---|
| Verbatim (fresh replay, byte-identical với v40 ở cả 5 lần replay) | wrong | wrong | correct |
| Bỏ `"output": null` khỏi exception rows (H_obs) | wrong | wrong | correct |
| Bỏ `concept_binding.allowed_outcome` | wrong | wrong | — |
| Bỏ cả packet (`concept`, `concept_binding`, `abstract_gap`) | **correct** | wrong: **predict raise**, vẫn withdraw | — |

- **H_obs not supported:** model không đọc `output: null` như `return None`.
- **Ablation verdict inconclusive** theo rule đăng ký (CA khớp "packet-level", CC khớp "không gỡ được ở T2").
- Đọc mô tả: bỏ packet làm "return None" predictions biến mất ở **cả hai** contexts (2/2 → 0/2). Bỏ riêng
  `allowed_outcome` không đủ; packet còn chứa "return None if no eligible item" trong `concept.activation` và
  `spec_quote`, nên A1 không cô lập được một field duy nhất (redundancy, không phải bằng chứng field đó vô hại).
- Lỗi E4 tách được thành hai phần: (1) **prediction slot bị điền normative value** — biến mất khi bỏ packet ở T2 (một call mỗi context);
  (2) **stance withdraw trên implementation claim mô tả bug** — còn ở CC khi không có packet, `why` ghi "raises ValueError
  ... contradicts the spec". Phần (2) giống polarity-label misuse (`withdraw` = "behavior này sai spec"), đã thấy rải rác
  ở E2 CC, E5 GA/CC trong Phase A.

## 6. Diễn giải

**Điều có thể claim (trên 8 seen fixtures, một model):**

1. Concept packet không tăng input yield khi generic agent đã đạt ceiling.
2. Bottleneck nằm sau input generation: agent không giữ tách bạch "spec nói gì" với "implementation làm gì" khi tích hợp
   feedback. Lỗi này xuất hiện cả ở GA (E2, E6), nên **không do concept gây ra**.
3. Concept packet **không sửa** lỗi đó. Ở hai fixtures, lỗi chỉ có ở concept arms và **trùng hướng** với nội dung
   packet: E3 (behavior khớp binding sai được coi là spec-correct), E4 (giá trị binding đúng xuất hiện trong prediction
   về implementation). Đây là quan sát tương quan, không phải causal claim: chỉ E4 có ablation và verdict inconclusive;
   E3 không có ablation.

**Giả thuyết post-hoc (chưa test, chỉ để định hướng):** normative content trong packet được model dùng như fact ở mọi
slot, kể cả descriptive slots (prediction, implementation claim). Concept hoạt động như **normative anchor rò sang kênh
evidence**, thay vì như một hypothesis về spec cần đối chiếu với observations.

**Điều không claim:**

- Không claim concept nói chung có hại hay vô ích. Concepts ở đây được cung cấp sẵn, fixtures đã thấy, n = 8.
- Không claim role confusion là mechanism chính (Gate A STOP).
- Không claim `allowed_outcome` là nguyên nhân E4 (ablation A1 âm tính, verdict inconclusive).

## 7. Threats to validity

- **External:** 8 authored fixtures đã thấy, một model 32B AWQ, temperature 0, một seed. Metadata endpoint không phải
  loaded-weight proof.
- **Internal (Phase A):** parent annotator non-blind (đã đọc v40 audits trước khi viết guide); giảm bằng reviewer 2 blind.
  Gate A là engineering threshold, không phải significance test.
- **Internal (E4):** E4 được chọn post-hoc sau Phase A. T2 history chứa T1 reply sinh ra khi có packet (carryover chưa
  loại trừ), nên A2 không tương đương GA context. Mỗi rendering một call; byte-identical replays cho thấy determinism
  của endpoint, không cho thấy robustness với paraphrase.
- **Construct:** scorer dùng regex (affirmative/negated ValueError claim, "return None" prediction); manual reading khớp
  automatic score ở mọi call.
- Theo rule signal-not-more-data, chuỗi E4 đã đóng: không thêm contexts, replicates hoặc fixtures để cứu kết quả.

## 8. Hàm ý cho hướng thesis (concept vẫn là trung tâm)

- Nếu giả thuyết ở mục 6 đúng, một thiết kế đáng thử là tách concept/binding khỏi kênh observations/predictions:
  concept giữ vai trò normative hypothesis, agent có slots riêng cho expected-per-spec và observed-from-PUT. Dữ liệu
  hiện tại chưa cho thấy thiết kế này giúp. Đây là nội dung B1/B2 của claim-role plan; Gate A đã chặn nó như *main explanation*, nên mọi bước tiếp phải là plan
  mới, đăng ký trước, và nêu rõ v40/Phase A đã thử gì.
- Giá trị của concept nên đo ở tầng mà generic agent chưa bão hòa (oracle/selection, theo v41/v42), không phải ở input
  yield trên fixtures nhỏ.

## Nguồn

| Bước | Folder | Commits | Model calls / tokens |
|---|---|---|---|
| v40 retry3 | `analysis/v40_retry3_20261021/` (REPORT, SEMANTIC_A/B, INTEGRITY_COST_AUDIT) | — | 72 responses; 220592 prompt + 21197 completion |
| Phase A | `analysis/claim_role_phaseA_20261021/` (AUDIT.md, LABEL_GUIDE.md, labels*.csv, gate_a.json) | 278804d | 0 |
| OBS-null probe | `analysis/obs_null_probe_20261021/` (PREREG, REPORT, responses/) | e71e04e, 54a8a1e, 0fb924a | 6; 19214 + 1434 |
| Binding ablation | `analysis/concept_binding_ablation_20261022/` (PREREG, REPORT, responses/) | cad0bf2, 4b54fb2, b2b67d0 | 6; 18745 + 1519 |

Plan: `research/benchmark-papers-2025-2026/audit/PLAN_CLAIM_ROLE_SEPARATION_20261021.md`. RESULTS.md §11.82 (v40).
