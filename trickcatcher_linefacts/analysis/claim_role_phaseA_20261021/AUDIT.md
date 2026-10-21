# Phase A — claim-role confusion audit trên v40 retry3: Gate A = STOP

Ngày 2026-10-21. Plan: [PLAN_CLAIM_ROLE_SEPARATION_20261021.md](../../../research/benchmark-papers-2025-2026/audit/PLAN_CLAIM_ROLE_SEPARATION_20261021.md) §3.
**0 model calls, 0 native executions.** Chỉ đọc 216 frozen files (`input_hashes.sha256`).

**Kết luận: role confusion không phải giải thích chính của evidence-integration failures trong v40.**
ROLE high-confidence chỉ có ở **một episode (E2, eligible_contribution)**, được cả ba annotators đồng ý.
Trong 7 eligible target rows, chỉ **2/7** không có upstream explanation. Cả hai điều kiện Gate A đều fail.
Theo plan: dừng H_role như giải thích chính, **không chạy B1/B2**, không đổi rubric/threshold.

## Cách làm

- Unit = episode-arm row (24 rows = 8 episodes × 3 arms), đọc đủ 72 raw responses, gồm 7 failed turns.
- Rubric + adjudication rules: [LABEL_GUIDE.md](LABEL_GUIDE.md). Gate A lấy nguyên từ plan.
- Ba annotators label riêng: parent (`labels.csv`, non-blind: đã đọc v40 audits và trajectories trước khi viết guide),
  reviewer 1 (`labels_reviewer_1.csv`, được đọc v40 audits, cho biết audits không đổi label nào),
  reviewer 2 (`labels_reviewer_2.csv`, blind với v40 audits). Reviewers không xem labels của nhau hay của parent.
- `compute_gate.py` (stdlib) tính Gate A → `gate_a.json`. Rule "OBS candidate chưa loại được = upstream" cần đọc text,
  nên script báo hai bounds; adjudication thủ công ở dưới.

## Eligible target rows và failure distribution

Eligible = model đã giữ/predict đúng target fact, sau đó final hoặc first unrecovered judgment trái usable evidence.
Cả ba annotators chọn cùng **7 rows**.

| Row | Lỗi | Upstream explanation | Ba annotators |
|---|---|---|---|
| E2 CA, E2 GA | T3 withdraw "strictly greater", keep implementation claim "`>=` limit" (đúng chữ spec), trái `([2,2,2],2)→0`; predictions của chính model trước đó đều đúng | Không | ROLE **high** ×3 |
| E4 CA | T2 withdraw "may raise ValueError", predict "will return None" cho `([0],)`, `([-1,-2,0],)` sau hai exceptions | **OBS chưa loại được**: exception render `"output": null`, `output_capture: unavailable`; đọc null là `return None` giải thích được toàn bộ trajectory | parent UNKNOWN(ROLE\|OBS) medium; R1/R2 ROLE medium, ghi OBS not excluded |
| E4 CC | Cùng pattern ở raw T2 (invalid, không vào context T3); T3 withdraw lại, không có None replacement | OBS + INTERFACE | parent UNKNOWN medium; R1/R2 FINAL, ROLE low |
| E6 CA, GA, CC | Withdraw/phủ nhận deduplication trái `[2,2]→2`, `[2,2,2]→2`, `[3,3,3]→3` | **PRED**: discriminator/arithmetic T1 sai (vd. "5 (1+2+3)", "4, as deduplicated"), withdrawal khớp logic của discriminator sai | PRED (GA T3 ROLE medium/low) |

Gate A:

1. **Agreed high-ROLE episodes: 1 (E2), 1 relation** — cần ≥2 episodes, ≥2 relations. **Fail** với mọi annotator.
2. **Eligible rows không có upstream explanation: 2/7** cho cả ba annotators sau adjudication (E4 rows có OBS rival
   chưa loại, mọi annotator ghi rõ). Script bound lenient (coi E4 ROLE/UNKNOWN là không upstream): parent 4/7, R1 3/7,
   R2 4/7. Kể cả bound lenient, điều kiện 1 vẫn fail nên verdict không đổi.

First unrecovered labels trên 24 rows (parent / R1 / R2): none 15/15/14; ROLE 2/3/3; PRED 2/3/3; SPEC 2/0/2;
UNKNOWN 2/2/1; FINAL 1/1/1. Không có OBS/INTERFACE unrecovered.

## Rival mechanisms

- **E2 ROLE** là case sạch nhất: substitution có nội dung mới đúng chữ spec, observations literal, scope trùng,
  predictions trước đó đúng. Rival còn mở: **generic final-turn hallucination** — lỗi chỉ xuất hiện ở final turn
  (instruction final turn khác: "claims and up to2 final_inputs"). E2 CC giữ đúng ở final, nên không phải tất cả arms.
- **E4** không phân biệt được ROLE với OBS từ text. Đây là một interface/rendering finding riêng: exception observation có
  field `output: null` dễ đọc như Python `None`. GA đọc đúng cùng rendering, nên không phải lỗi bắt buộc.
- **E6** chủ yếu là reasoning error trong prediction/discriminator (arithmetic, eligibility × multiplicity), không phải
  role substitution. Final claims không tích hợp clean dedup discriminators đã thấy.
- **E3** (wrong binding) là **SPEC** ở concept arms: model coi implementation/binding behavior (False trên strict subset)
  là spec-correct — hướng ngược với ROLE. R1 gán UNKNOWN (polarity mơ hồ).
- Polarity-label misuse (stance `withdraw` dùng như "behavior này sai spec") xuất hiện rải rác (E5 GA/CC C3, E2 CC T2),
  không đủ evidence để thành mechanism riêng.

## Disagreements (giữ nguyên, không ép consensus)

E3 CA/CC: parent/R2 SPEC vs R1 UNKNOWN. E3 GA: R2 UNKNOWN vs parent/R1 none. E4 CA: parent UNKNOWN vs R1/R2 ROLE medium
(cùng nội dung: OBS chưa loại). E4 CC: parent UNKNOWN vs R1/R2 FINAL. E6 CA: parent FINAL vs R1/R2 PRED.
E6 GA: ROLE confidence parent medium, R1 medium, R2 low. Không disagreement nào ảnh hưởng Gate A.

## Ý nghĩa và giới hạn

- Gate A là engineering choice trên known data, không phải significance test. 24 rows từ seen authored fixtures.
- Kết quả không bác bỏ việc ROLE tồn tại: E2 là một instance rõ. Nó chỉ cho thấy ROLE không giải thích phần lớn failures;
  OBS rendering (E4) và prediction reasoning (E6) là các nguồn ngang hàng.
- Theo plan §3 và rule signal-not-more-data: **không chạy B1/B2**, không thêm dataset/K để cứu hypothesis.
  Scientific no-go của v40/v41 giữ nguyên.

## Files

`LABEL_GUIDE.md`, `labels.csv` (+ `write_parent_labels.py`), `labels_reviewer_1.csv`, `labels_reviewer_2.csv`,
`compute_gate.py` → `gate_a.json`, `render_trajectories.py` → `trajectories.txt`, `input_hashes.sha256`.
