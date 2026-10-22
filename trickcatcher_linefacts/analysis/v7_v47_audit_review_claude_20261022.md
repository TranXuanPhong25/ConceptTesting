# Review của audit v7→v47 (Codex, `d89d0bd`): những điểm bị bỏ sót

Ngày 2026-10-22, Claude. Đọc `codex-session-v7-46.md`, `analysis/v7_to_v47_implementation_audit_20261022.md`, v46/v47
source/PREREG, RESULTS/v11 report, v41/v44 results. Chỉ CPU checks tool-side (không reference, không model call).
Script: `analysis/v7_v47_audit_review_claude_20261022_checks.py`.

## Kết luận ngắn

Audit của Codex đúng về fidelity từng nhánh. Phần bị bỏ sót nằm ở **khuyến nghị hướng đi** (concept selection để phân bổ
input) và ở **v46/v47 trong bối cảnh toàn pipeline**: hướng được khuyến nghị đã thử ít nhất 6 lần, “signal” dựa trên một
gap có sẵn theo cách tính (max vs mean), metric bỏ qua oracle/false alarm, và trong repo method thắng ở matched budget
là TC-full (program-variant oracle), không phải input selection.

## Điểm bỏ sót

| # | Điểm | Bằng chứng |
|---|---|---|
| R1 | **Prior art của “concept selection” bị nói thiếu** (rule check-version-tree). Codex chỉ nêu v18/v43/v47. | v7 `facts.pick` (kind priority), v7_mutref rank-2 13/10 no gain; v18 LLM 11 vs lexical 12; v31/v35 template ranking ≈ random, concept trỏ đúng bug 11/33; v36 LLM localization hit@3 6/14, revealing 3/33; v41 relation selection lift .38; v42 mutant-disagreement selection lift .62. Cả 6 lần đều null/no-go. Mới ở v47: menu trộn kinds + covered@3. |
| R2 | **“Perfect 20 vs random instance 10.1” không phải signal**: max-over-instances luôn ≥ mean khi các instance khác nhau. | v44 RESULTS: class ideal 20, matched random by reach **20.0**; tức là chạy hết inputs của class (~195) đã reach 20 tasks, không cần chọn. Gap chỉ tồn tại khi tự đặt budget ≤ 32 inputs. |
| R3 | **Hướng khuyến nghị tối ưu phần không phải bottleneck.** Execution inputs gần như free; chi phí thật là oracle (expected value) và false alarm. covered@3 không đo hai thứ này. | v41: sampling reach 22/33, bottleneck là nhận ra input nào sai. v47 metric = picked instance có chứa exposing input (theo reference), không có oracle. |
| R4 | **Matched-budget winner trong repo là TC-full**, nên pipeline hoàn chỉnh phải dựa trên program-variant oracle và so với TC-full cùng cost. Codex chỉ nêu số này như một fairness note. | v11 report: concept-hybrid vs tc_full_v2 random matched detection **29.75 vs 42.99, W/L 2/25, p=6e-6** (3.47 calls/sample); tc_full precision .99. TC-full chưa từng chạy end-to-end trên VibePass33. |
| R5 | **Gate v47 có thể “promising” trong khi thua chính controls của nó.** Tiêu chí #2 của Codex (hơn heuristic + kind-matched) không có trong gate. | Gate = covered@3 ≥ random3+3 và ≥ 0.5×perfect. first3, per-kind random3, kind-matched chỉ report. Không có non-LLM heuristic (fixed kind priority, kiểu v7 pick). |
| R6 | **Contamination hidden-input ảnh hưởng cả Part B**, không chỉ Part A. | Menu Part B có spec_range/value_biased (thiết kế sau khi xem hidden inputs ở v45_unreachable) → perfect_menu và covered@3 tuyệt đối bị ảnh hưởng; so với random3 trên cùng menu thì ít hơn. |
| R7 | **v46 và v47 rời nhau**: v46 oracle chỉ chạy trên 607 mutant-disagreement inputs; khi xong cũng không nói được oracle có đúng trên concept-selected inputs không. Nhưng program `tc` của v46 là code chạy được trên mọi input → ghép end-to-end chỉ cần CPU. | `oracle.py jobs()`: programs per task, không phụ thuộc question. |
| R8 | **v46 không khả thi về throughput** trên endpoint hiện tại; judge chiếm 75% calls và v45 đã cho thấy in-head judge yếu. | vLLM metrics 22:55: running 1, waiting 8, ~10 output tok/s (serial). v46 = 620 program + 1821 judge calls (max_tokens 2048); 25 records sau ~3 giờ. v47 chung queue. |
| R9 | **tc_concept của v46 gần như circular**: concept block = đúng mutant edit định nghĩa câu hỏi; variant chép edit sẽ đồng ý với mutant trên đúng các input đó. | v42: trên package inputs mutant đúng 52, PUT 335, neither 46 → chép mutant dự đoán precision thấp. Gate (precision ≥ .5, FA ≤) chặn được, nhưng arm này đo “bỏ qua hint sai”, không đo concept giúp oracle. |

## Các caveat Codex để mở — đã kiểm tra (CPU, tool-side)

- v47 cached calls: **50/50 prompt_sha256 khớp prompt hiện tại** → không có stale cache.
- Menu dedupe theo thứ tự: **5/33 tasks** (39, 58, 73, 74, 161) có 1 cặp item cùng input set khác thứ tự, mỗi arm.
- pool_max chặn range của argument khác: **0/33**. `10**9`/`len()` bounds: 0/33 (Codex đã kiểm).
→ Các lỗi parser/range là lỗi generality, không giải thích kết quả trên current33.

## Hệ quả cho bước tiếp theo

Pipeline hoàn chỉnh nên là: tool pool + concept menu → LLM chọn (v47 picks) → **program-variant oracle (v46 `tc`)** →
vote → assertions; chấm confirmed bugs **và** false alarms; so với: random-3, first-3, kind-matched, fixed-kind heuristic,
toàn bộ menu (không chọn), và matched-input random từ pool (TC-full-style, không concept). Toàn bộ chạy CPU trên outputs
đã lưu; chỉ cần v46 `tc` programs và v47 calls hoàn tất.

## Codex xác minh (2026-10-22, read-only)

R3, R5, R6, R7: **đồng ý**. R1, R2, R4, R8, R9: **đồng ý một phần**, sắc thái được sửa như sau:
- R1: “6 lần null” quá mạnh — v31 qua gate yếu ban đầu; v34 8–2 detection nhưng fail FA rule. Ý chính (prior art bị cite thiếu) giữ.
- R2: selection vẫn có thể có ích khi có resource constraint thật; số v44 không biện minh cho budget 32 inputs.
- R4: 3.47 là distinct candidate-input calls, không phải LLM calls/total cost; precision .9907 dưới shared-ref.
  TC-full là comparator bắt buộc, chưa chứng minh native program oracle phải là kiến trúc.
- R8: repo không tự chứng minh queue behavior; sau đó đã xác nhận live: owner v46 chạy lại 1 worker/timeout 3600 s,
  probe 1-token từ > 60 s xuống 12 s (livelock do client timeout hủy request trên server serial).
- R9: là endogenous guidance, không phải leakage; vẫn kiểm được concept có giúp dựng oracle không, nhưng bias mạnh
  về mutant answers.
CPU checks C1–C3 tái hiện được. Must-fix của Codex cho v48 → PREREG v48 Amendment 1.
