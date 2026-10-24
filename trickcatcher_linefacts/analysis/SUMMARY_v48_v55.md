# Thesis summary v48–v55, kèm trạng thái Task B/v56

Ngày 2026-10-24. Các số dưới đây lấy từ reports đã lưu; phiên Codex này chưa
tạo model answer hoặc tính outcome mới. Task A/v55 bị chặn ở transport. Task
B/v56 mới có PREREG và infrastructure audit. Vì vậy đây là summary hiện trạng,
chưa phải báo cáo replication hoàn tất trên fresh cohort.

## Kết quả chính

Pipeline tốt nhất đã đo trên dev `vibepass_half` là strong writer Sonnet,
`defn` oracle k=3, `open` validity filter và `plain` LLM input generator:
**24/33 confirmed tasks, precision .96, FA 15 tests**. Khi dùng union với
universe: cũng 24/33, precision .97, FA 14. Đây là kết quả v53; chưa có
Codex-writer baseline của cấu hình này. Không dùng kết quả pilot hoặc dev để
khẳng định khả năng transfer sang fresh problems.

| Experiment | Kết quả | Ý nghĩa |
|---|---|---|
| [v48](v48_e2e_oracle/RESULTS.md) | LLM concept picks 6/33; random3 6.37; precision .25; FA 152 | Input selection không vượt controls khi oracle vẫn sai. |
| [v49](v49_defn_oracle/RESULTS.md) | Qwen defn 12/33, precision .59, FA 145; brute 10, .62, FA 100; plain 5; native TC-full 7, .23, FA 221 | Brute-force spec oracle là family effect đáng chú ý; concept gate NO-GO. |
| [v50](v50_binding_revision_20261023/RESULTS.md) | Binding/revision diagnostic: strict 2/8 mỗi arm, 0 tool-only semantic wins | Sửa interface không giải quyết normative-status errors. |
| [v51](v51_latent_concept/RESULTS.md) | CBM AUC .495; direct .476; intrinsic likelihood .650; MBPP+ CBM .627 vs placebo .631 | Latent discrepancy concepts không đạt gate; NO-GO. |
| [v52](v52_sonnet_defn/RESULTS.md) | Sonnet defn 5/6 vs brute 4/6; Qwen k-matched 1/6 vs 0/6; Sonnet FA 56/arm đều là invalid inputs | Strong writer cải thiện rõ trên pilot được chọn vì Qwen thất bại; chưa phải cohort estimate. |
| [v53 Stage 1](v53_validity_smallscope/RESULTS.md) | concept = lines = open: bắt 12,842/12,842 invalid, reject 0/19,469 valid và 0/4,084 exposing; numeric tool recall .144 | Extraction có giá trị, taxonomy không thêm gain trên fixed universe. |
| [v53 Stage 2](v53_validity_smallscope/RESULTS_STAGE2.md) | scope concept 18/33; plain LLM 24; typed 17; random_small 21; universe 22 | Small-scope concept thua plain 6 tasks; registered not promising. |
| [v54](v54_sonnet_mutconcept/RESULTS.md) | Sonnet tc = tc_concept 6/6; FA 3 vs 0; right programs 18 vs 16 | Pilot ở task ceiling; không đạt concept gate. |
| [v55 / Task A](v55_codex_interpretation/CHANGELOG.md) | PREREG, runner và 33-call manifest; 0/264 answers | Chưa có outcome hay verdict cho interpretation concept hoặc Codex baseline. |
| [v56 / Task B](v56_lcb_fresh/CHANGELOG.md) | PREREG và infrastructure audit; 0 PUT, 0 fresh hidden outcomes | Chưa có fresh cohort hoặc paired pipeline comparison. |

## Những phần có ích

**Writer strength.** v52 giữ prompt/scoring của v49, dùng k=3 trên sáu failure
tasks: Sonnet defn 5 vs Qwen 1, brute 4 vs 0. v54 cũng đạt 6/6 ở cả hai Sonnet
arms. Đây là bằng chứng trên selected pilots; contamination và selection
không cho phép gọi đó là generalization estimate. v55 được thiết kế để đo
Codex trên đủ 33 dev tasks nhưng transport chưa chạy được.

**Brute-force definitional oracle.** Trong v49, brute/defn spec-only đạt 10–12
tasks, còn plain implementation 5. So với native TC-full, precision tăng từ .23
lên khoảng .6. Common-mode share theo định nghĩa cũ, mọi finishing program
bằng PUT trên exposing inputs, là defn 3.0%, brute 4.9%, tc 28.2%. Tuy vậy
registered family gate thất bại do absolute FA; phải ghi đây là descriptive
family effect. Các con số giữa native TC-full và primary quorum không phải
matched-rule causal comparison.

**Validity filter.** Trên fixed universe, bất kỳ strong-writer filter nào
trong concept/lines/open đều phân loại giống nhau, và loại toàn bộ 56 invalid
Sonnet FA của pilot mà không mất confirmed task. Đây là lợi ích của spec
constraint extraction; không phải bằng chứng typed concept tốt hơn open.
Finite-pool agreement cũng không chứng minh validator đúng trên mọi input mới.

**LLM input generation.** v53 Stage 2 plain xác nhận 24 tasks so với universe
22; hai task mới 168/171 được cả plain lẫn scope đạt. Plain còn giữ được
size/value diversity giúp oracle gặp các lỗi mà tiny exhaustive scopes bỏ
lỡ. Union universe∪plain vẫn 24, cho thấy coverage bổ sung ở đây đến từ LLM
generation; chưa có fresh-cohort evidence.

## Những concept chưa giúp được

Validity taxonomy: margin concept−open = 0. Input-side scope concept:
18−24 = −6. Oracle defn headings: v49 có 93 vs 78 valid programs, nhưng trên
tasks mà cả defn/brute đều eligible, kết quả là 10 vs 10; +2 chỉ đến từ
valid-program yield và không đạt gate. v52 có một defn-only win ở task 65 do
enumeration space khả thi hơn, song pilot chỉ sáu tasks. Mutant concept v54:
confirmed tasks 6 vs 6, không có task gain. Interpretation concept của v55
**chưa được đo**, nên không được liệt kê là một negative result đã xác lập.

## Các vấn đề còn mở

- **Common-mode spec interpretation:** v53 problem dùng chung bởi 161/73/74
  có cả ba programs cùng trả giá trị sai trên valid inputs lớn, ví dụ
  `(200,120)` cho 450 thay vì reference 530. Quorum không bảo vệ được lỗi chung.
- **Abstention:** task 141 có exposing inputs nhưng brute-force oracle timeout.
- **Reach:** sáu tasks 6/39/48/58/69/70 vẫn không được các v53 arms tiếp cận.
- **Transfer và contamination:** cần fresh LCB cohort không trùng toàn bộ
  VibePass; chỉ gọi post-cutoff khi cutoff của writer đã được xác minh.
- **Operational blockers:** isolated `codex exec` preflight thất bại với
  `workspace routing discovery failed`; hai GPU probes không kết nối được
  trong sandbox. `.git` read-only làm `git add` không tạo được index.lock,
  nên phiên này chưa có commit hash hay push mới.

Task A đã đăng ký rule: interpretation phải hơn cả defn và placebo ít nhất
hai confirmed tasks trên ít nhất hai problems, FA không tăng, precision ≥.95
và giảm số problems có common-mode. Task B chỉ được freeze treatment theo
rule đó, không chọn arm từ fresh outcomes, không tăng cohort để cứu kết quả.
VibePass held-out không được chạy hoặc chỉnh sửa trong phiên này.

## Handoff và provenance

v55 [PREREG](v55_codex_interpretation/PREREG.md),
[runner](v55_codex_interpretation/experiment.py),
[manifest](v55_codex_interpretation/MANIFEST.json),
[transport record](v55_codex_interpretation/TRANSPORT_PREFLIGHT.json).
v56 [PREREG](v56_lcb_fresh/PREREG.md) yêu cầu source/manifest và adapter freeze
trước mining; chưa đủ điều kiện kích hoạt run. Chưa dùng Sonnet answers trong
bất kỳ arm mới nào. Không có outcome mới để báo cáo precision/FA hoặc paired
wins/losses của A/B. Không suy ra concept NO-GO từ transport failure.
