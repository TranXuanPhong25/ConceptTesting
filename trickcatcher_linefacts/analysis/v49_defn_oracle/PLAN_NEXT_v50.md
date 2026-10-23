# Plan hướng tiếp theo sau v48/v49 (draft, chưa đăng ký) — 2026-10-23, Claude

Viết **trước khi** có output của v48 execute/score và v49 execute/score (generation còn chạy: v49 193/495, v46 tc
112/310). Luật chọn nhánh cố định ngay bây giờ, tính từ các field đã có trong `e2e.py score` (v48) và
`oracle.py score` (v49) trên decisive universe; không đổi sau khi đọc kết quả. Codex quota 5h < 15% → Claude viết.

## Điểm yếu đã thấy (tóm tắt, chi tiết ở `../v48_e2e_oracle/PLAN_NEXT_v49.md`)
1. Concept-guided input selection ≈ random nhiều lần (v7_mutref, v18, v35, v36, v41, v42, v44, v47); reach không phải
   bottleneck chính (v41 pool 22/33).
2. Oracle là bottleneck: TC-full variants copy bug của PUT (common-mode; smoke v49 task 3: 9 valid tc variants, 0 test),
   spec programs trên VibePass invalid/memorized (v39), in-head judge yếu (v45), property oracle unsound (v26).
3. Brute-force oracle (v49) chỉ đúng/kịp trên input nhỏ: timeout = abstention, nên exposing input lớn bị bỏ.
4. FA chủ yếu do invalid input ở differential oracle (2608.19626).

## Bằng chứng ngoài (đọc 2026-10-23)
- **AutoCode** (ICLR 2026, arXiv 2510.12803): Validator–Generator–Checker. Brute force là ground truth trên input
  **small-data exhaustion**; bỏ exhaustive hoặc random/extreme làm FPR tăng (1.7% / 1.6%). Validator: LLM viết 40 case
  (10 valid, 30 near-valid), sinh 3 validator, giữ cái phân loại đúng nhiều nhất. Model o3/GPT-5 (mạnh hơn Qwen32B nhiều).
- **CodeHacker** (arXiv 2602.20213): hack agent cho solution AC trên test yếu; oracle = standard solution đã verify
  (setting của ta không có). Ablation: bỏ refinement loop của Validator/Checker giảm nhiều nhất (51.40 → 46.60 HSR);
  bỏ stress test chỉ 50.12; bỏ anti-hash 51.00.
- **DePro** (arXiv 2603.19399): brute-force reference + stress test trên input random/edge nhỏ + LLM repair.
- **HardTests** (arXiv 2505.24098): LLM validator + hacking inputs, nhưng output oracle do người viết.
- **B4** (ASE 2024, arXiv 2409.08692): chọn solution/test plausible bằng posterior Bayes (4 Beta), hơn CodeT 6–12% —
  liên quan nếu v48 thất bại ở vote (c/d).
- Small scope hypothesis (Jackson; Andoni et al. 2003): phần lớn bug lộ ra trên input nhỏ.
Khác biệt của ta: không có reference, model yếu (Qwen2.5-Coder-32B), PUT plausible (pass public tests).

## Luật chọn nhánh (bản đầu — đã được thay bằng Revision 1 ở cuối file)
Ký hiệu trên decisive universe, chỉ các task có ≥ 2 valid `defn` programs ("defn-eligible").
- **R1 — v49 GO** (PREREG v49 amendment 2) → **v50-H**: chạy lại pipeline đã đóng băng trên held-out cohort
  (`memory/heldout-final-readiness.md`), không đổi gì.
- **R3 — không viết được executable spec**: số task defn-eligible < 17/33, hoặc trong test `defn` emit, tỉ lệ sai giá trị
  (FA `put_wrong_wrong_value` + `put_right`) ≥ 50% → Qwen32B là giới hạn; đóng họ program-oracle trên model này. Chỉ đi
  tiếp với model mạnh hơn (Vertex ≈ $25 còn lại) **sau khi hỏi user**.
- **R2 — abstention-bound**: tổng `exposing_no_finishing` của `defn` (pooled trên task defn-eligible) ≥ 50%
  `exposing_inputs` → **v50-S shrink-then-judge**: input lộ bug quá lớn cho brute force.
  - Lấy input mà PUT ≠ tc majority (differential disagreement, không cần reference), shrink bằng **Hypothesis shrinker**
    (library, không tự viết delta debugging) với predicate “PUT ≠ tc majority vẫn giữ”, rồi `defn` brute force phân xử
    trên input đã shrink; cộng thêm small-data exhaustion inputs (AutoCode) từ v41 strategies giới hạn kích thước.
  - CPU ceiling trước (không gọi model mới, dùng lại programs v46/v49): bao nhiêu task có exposing input sau shrink mà
    `defn` finish. Control: cùng inputs không shrink; random small inputs cùng count.
  - Prior art trong repo: v41 (Hypothesis sampling, không shrink, không brute force), v13/v21 fuzz witness (không có
    brute-force oracle). Shrink-then-brute-force: chưa có.
- **R5 — FA do invalid input**: trong FA tests của v48 `llm_code` và v49 `defn`, `invalid_input` ≥ 50% → **v50-V validator
  concept**: precondition từ spec Constraints thành predicate chạy được, chọn best-of-3 trên case valid/near-valid tự
  sinh (AutoCode). Prior art: v7 mined validity (từ public examples), v24 obligations (Qwen contracts 0/9) — khác ở chỗ
  chọn bằng case tự sinh có thể chạy được. Gate: FA giảm mà confirmed không giảm, so với không validator cùng inputs.
- **R4 — common-mode cả với brute force**: `defn` `common_mode_share` ≥ 50% → bug nằm ở phần spec mơ hồ (2606.20158);
  không có nhánh chạy ngay — viết báo cáo và nhờ Opus subagent phản biện để tìm hướng.
- **Không luật nào bật** → đóng hướng definitional oracle cho cohort này; tổng kết; nhờ Opus/Codex phản biện.

## Gate chung
PREREG trước output; independent read-only review trước khi tính outcome; control cùng inputs/cap; không mở rộng n để
vớt kết quả (signal-not-more-data); kiểm tra version tree trước khi đề xuất; concept bắt buộc có mặt
(thesis-concept-requirement): ở v50-S concept = định nghĩa ENUMERATE/CHECK/AGGREGATE dùng làm oracle; ở v50-V concept =
precondition của spec.

## Revision 1 (2026-10-23 19:45, sau independent read-only Opus review; vẫn trước mọi output execute/score)
Review tìm 3 must-fix và 8 should-fix; luật mới (cài trong `plan_rules.py`, 7 tests), thứ tự cố định
**R1 > R1b > R6 > R3 > plurality (R2/R3v/R4/R7) > R5**, trên toàn decisive universe:
- **Exposure (M3):** official reach nơi score đã tính (menu ∪ `llm_code`), các input pool còn lại dùng proxy
  valid ∧ ref ≠ PUT (bản đầu chỉ đếm menu ∪ `llm_code` nên lệch về input lớn).
- **Phân loại theo task (S1, S2):** mỗi task defn-eligible (≥ 2 valid) chạy v48 `decomposition` qua adapter (vote = v49
  `primary`, label = v49 label) → primary class. Common-mode chỉ khi *mọi* valid program trả giá trị của PUT; một
  program finish bằng PUT còn lại timeout = `variants_failed` (abstention).
- **R1 (M1):** v49 GO → v50-H chỉ sau manual audit (defn-only wins đã audit vẫn phải đủ margin ≥ 3 trên ≥ 3 problems);
  `status = pending_manual_audit`. v50-H không phải rerun “không đổi gì” (S8): held-out cohort cần v41 pool, v47 menus,
  v46 tc trước; universe và arms phải viết trong PREREG riêng.
- **R1b (M2):** margin và span đạt nhưng `fa_no_worse` fail → v50-FA (FA control trên cùng inputs: defn∧tc, validator).
- **R6 (M2):** secondary (brute vs plain) GO hoặc defn_vs_tc GO → family effect không có concept effect → v50-F: re-score
  $0 CPU các arm của v48 (inputs concept-guided) bằng defn/brute primary oracle (mechanism check; v47 reach null dự báo
  null), rồi hỏi user. Concept vẫn nằm ở phía input (thesis rule).
- **R3:** < 12/24 problems có valid + `rejected_resource_only` ≥ 2, hoặc tỉ lệ test sai giá trị (put_right +
  put_wrong_wrong_value) ≥ 50% **chỉ trên test có input valid và reference resolved** (S3).
- **Plurality:** trong các task defn-eligible chưa confirmed, class nhiều task nhất với ≥ 3 tasks trên ≥ 3 problems:
  `b2_variants_failed`→R2 (v50-S), `c/d vote wrong`→R3v, `b_common_mode`→R4, `a_no_exposing_input`→R7 (không mở input
  selection mới; small-scope exhaustion chỉ trên fresh cohort). Hòa: R2 > R3v > R4 > R7.
- **R5 (S4):** chỉ trên FA của `defn` (≥ 10 FA tests, `invalid_input` ≥ 50%); FA của v48 tc (`llm_code`) chỉ report.
- **Guard (S5):** mỗi task, số test và FA tính lại phải bằng `score.json`; output ghi bằng `immutable` kèm sha256 của
  hai score.json.
- **v50-V (S6):** trùng B5/F1b (RBCTest-style precondition miner, verify trên input valid đã biết, FA giảm ~½) và F4/F4b
  (concept-guided mining, tệ hơn vì Qwen biến output condition thành input condition), RESULTS §11.3. Nếu R5 bật:
  baseline = B5/F1b miner; concept = vocabulary của người + instance đã verify bằng execution (LLM-inferred precondition
  một mình đã bị loại làm concept ngày 2026-10-09).
- **v50-S (S7):** predicate “PUT ≠ tc majority” không bao giờ đúng ở task common-mode (task 3: tc 0 test), và Hypothesis
  không shrink được input nó không tự sinh → dùng small-scope exhaustion (size-bounded strategy / `hypothesis.find`)
  phán xử bằng `defn` trực tiếp, ddmin library cho input có sẵn; giữ arm `brute` (concept vẫn chưa được chứng minh).

## Note (2026-10-23 23:40, after the run)
v50 (`analysis/v50_binding_revision_20261023`, `pipelines/v50_binding_revision`) and v51 (`analysis/v51_latent_concept`)
were taken by other sessions meanwhile. The branch labels `v50-*` here (and in `plan_rules.py` output) mean "the next
experiment of this line"; its folder will be the next free number (v52). Outcome: R7 fired (see `RESULTS.md`).
