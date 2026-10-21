# Phase A label guide — claim-role confusion audit (v40 retry3)

Plan: [PLAN_CLAIM_ROLE_SEPARATION_20261021.md](../../../research/benchmark-papers-2025-2026/audit/PLAN_CLAIM_ROLE_SEPARATION_20261021.md) §3.
Zero inference: chỉ đọc saved records, không gọi model, PUT, scorer.

**Non-blind status (công khai).** Parent annotator (Claude) đã đọc REPORT/SEMANTIC_A/SEMANTIC_B của v40
và toàn bộ 72 trajectories trước khi viết guide này. Rubric và Gate A lấy nguyên từ plan (viết trước khi
audit); guide chỉ thêm adjudication rules cụ thể bên dưới. Hai reviewers label độc lập, không xem
`labels.csv`/`AUDIT.md` của parent; họ được phép đọc v40 audits (non-blind với audits đó).

## Material

- Root `R = trickcatcher_linefacts/out/pipelines/v40_concept_agent/humaneval/d1_retry3_20261021/`.
- Mỗi row = `E# × arm`. Đọc `R/requests/E#__arm__t.json` (context model thực sự thấy, gồm
  `earlier_turns`, `injected_observation`), `R/artifacts/…` (raw text), `R/events/…` (admission + feedback).
- `trajectories.txt` là bản render compact (stdlib, `render_trajectories.py`); khi cần exact rendering
  (vd. exception observation) đọc request JSON gốc. `input_hashes.sha256` khóa 216 input files.
- Fixture truth: spec của từng task (E3 binding cố ý sai; E7 program correct; E8 normative unknown).

## Unit và fields (`labels.csv`)

Primary unit = episode-arm row (24). Turn/claim chỉ là nested descriptive counts.

| Field | Ý nghĩa |
|---|---|
| episode, arm, relation | relation = concept catalog id của fixture |
| target_fact | implementation/normative fact cần giữ hoặc sửa ở row |
| initially_correct | model có nêu/predict đúng target fact ở một turn trước lỗi không (yes/no/na) |
| final_correct | final claims (T3) đúng target fact và không trái usable evidence (yes/no/partial) |
| eligible_target | yes nếu initially_correct=yes **và** final hoặc first unrecovered judgment trái usable evidence |
| first_error_turn / first_error_label | lỗi semantic đầu tiên (kể cả về sau recovered); `none` nếu không có |
| first_unrecovered_turn / first_unrecovered_label | lỗi đầu tiên còn tồn tại trong final turn; `none` nếu final đúng |
| secondary | các lỗi khác, `turn:LABEL` cách nhau `;` |
| role_confidence | high / medium / low / na cho mọi ROLE candidate trong row |
| rivals | rival explanations đã xét và verdict ngắn |
| evidence | file basenames + observation IDs cụ thể |

Thứ tự trong một turn: claims trước, rồi queries (prediction/why). Failed turn (INTERFACE) vẫn đọc raw text;
semantic content trong failed turn được ghi riêng, đánh dấu `(raw-invalid)`.

## Labels (nguyên từ plan)

SPEC, PRED, OBS, ROLE, FINAL, INTERFACE, UNKNOWN — định nghĩa ở plan §3. Adjudication rules thêm:

1. `keep/revise/withdraw` đọc cùng statement + kind; không chấm từ keyword. Stance `revise` không đổi
   statement = không có revision.
2. **ROLE** = required (spec) behavior hoặc normative judgment được đặt vào slot nói về actual implementation
   (implementation claim hoặc query prediction), trái usable observation. Hướng ngược (implementation/binding
   behavior được coi là spec-correct) là **SPEC**, không phải ROLE.
3. **FINAL** khi stance/polarity đổi trái evidence nhưng **không** có replacement claim/prediction mang nội dung
   normative cụ thể của spec.
4. **PRED** gồm cả arithmetic/set reasoning sai trong prediction hoặc discriminator (`why`) của chính model.
   Nếu một withdrawal sau đó khớp logic của discriminator sai đó, PRED là upstream explanation.
5. **OBS**: misread status/output/scope. Exception observation được render `"output": null` cạnh
   `execution_status=exception`; đọc null như `return None` là OBS candidate có thực (plan rubric ví dụ).

## High-confidence ROLE (cả bốn điều kiện plan + mọi rival bị loại)

(a) normative relation xác định (spec rõ, không phải E8); (b) actual observation usable và đã có trong context
**trước** turn đó; (c) raw text cho thấy substitution: replacement statement/prediction khớp nội dung spec,
không chỉ đổi stance; (d) rivals:

- polarity-label misuse: loại nếu model viết **nội dung mới** khẳng định normative behavior là implementation;
- scope error: loại nếu observation cùng scope với claim;
- arithmetic/set reasoning: loại nếu prediction/discriminator trước đó của chính model đúng cho cùng facts;
- observation parsing: loại nếu observation là literal output không thể đọc thành giá trị spec; **không loại
  được** khi observation là exception với `output: null` và substitution là `None`;
- generic final hallucination: không loại hoàn toàn được; ghi lại; nếu lỗi xuất hiện trước final turn thì yếu đi.

Một rival không loại được → tối đa medium. ROLE medium/low không tính cho Gate A.

## Gate A (nguyên plan, không đổi sau khi đọc labels)

GO sang B1 chỉ khi **cả hai**:

1. ≥2 distinct episodes thuộc ≥2 semantic relations (catalog ids) có ROLE high-confidence **agreed**:
   parent và cả hai reviewers đều gán ROLE high cho ít nhất một arm của episode đó. Disagreement ghi riêng,
   không ép consensus.
2. Trong eligible target rows, strictly more than half **không** có SPEC/PRED/OBS/INTERFACE upstream giải thích
   lỗi (OBS candidate chưa loại được tính là có upstream explanation). Denominator ghi đủ.

Ngược lại: stop H_role như giải thích chính, ghi failure distribution.
