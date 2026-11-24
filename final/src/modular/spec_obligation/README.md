# Spec obligations

## 17/11/2026 — Gỡ combined arm và evidence v5

`control_flow_obligation` đã gỡ khỏi source, registry, CLI/Prefect và preset.
`spec_obligation` vẫn dùng shared feedback v4 với evidence trước v5; giữ required
obligations, native treatment accounting, JSON-safe validation và useful direct inputs.
V5 guard-state snapshots/static return-dependency không còn trong đường generation.
Historical reports/checkpoints/frozen runtimes giữ nguyên; current console reject
run/resume combined arm đã retire.

## 16/11/2026 — Native feedback cho arm thuần

`spec_obligation` dùng chung `CoverageFeedbackArm`, với semantic scenarios bật và
structural targets tắt. Protocol `source-obligations-required-feedback-v1`, calls
`spec_obligation_round_0`/`_round_1`. Response contract yêu cầu `inputs` và
`obligations` trong cả hai round; nếu không có scenario phải trả explicit `reason`.
Vòng đầu trả seed inputs cùng obligations;
sampling/native observation diễn ra trước vòng sửa. `base_hit` chỉ là một witness,
không đóng scenario hoặc hủy lượt sinh inputs. Metadata hỏng vẫn cho phép fallback
sinh direct inputs ở vòng hai. Không khôi phục retired validated-v2 state checker.

Public response vòng trước được đưa lại vào context dưới role assistant, kể cả
metadata chưa parse được. Prompt yêu cầu control/contrast representatives trong
scenario/instruction hiện có, giữ earlier guards và xét khả năng contribution lan
đến return. Không có expected outputs, oracle outcomes hoặc hidden reasoning trong
feedback. Target diagnostics ghi arc nào chưa quan sát và exit thực tế; không suy
event order từ tập coverage. Budget mặc định vẫn tối đa2calls,20selectedinputs,
64candidate-PUT observations; vòng0 tối đa32 để giữ budget cho vòng sửa.

Historical completed generations vẫn đọc nguyên trạng; reproduce/resume run cũ
dùng frozen runtime của run đó. Các thay đổi này mới qua engineering checks, chưa
chứng minh PUT gain và không tự launch benchmark.

Arm `spec_obligation` đề xuất semantic scenarios từ spec/code. Default Plain
không đổi. Không retrieval hoặc prerequisite concolic engine.

## Pipeline

1. Đọc spec, trusted contract, original numbered PUT source, CFG và static may-DFG.
2. LLM đề xuất tối đa3obligations: requirement, program/line binding, scenario,
   instruction, correct-use counterexample, optional safe input predicate/strategies.
3. Đo recorded base inputs với predicate + native code reach: hit/miss/unknown.
   Partial/missing trace không được coi là miss. Covered code vẫn có semantic gap.
4. Sinh inputs cho missing/unknown scenarios và C1/C2 targets. Bounded Hypothesis
   descriptors và direct LLM inputs dùng chung ledger. Dedup toàn recorded base,
   kể cả calls của PUT không hiện trong prompt; metadata lỗi không bỏ valid inputs.
5. Freeze đúng persisted JSON inputs; shared reference/PUT evaluator xác nhận
   failure độc lập sau freeze. Không feed oracle outcomes vào generator.

Giới hạn/task/arm:2logicalcalls,20selectedinputs,3obligations,6structuraltargets,
64candidate-PUTobservations,300base replays;32Hypothesisdraws/obligation/2s.
Native trace tối đa1s; evaluation timeout lấy shared config. Input predicates có
syntax/resource limits và sandbox. Checksum/program/line binding giữ original source.

`treatment.status` phân biệt `applied`, `unknown`, `failed`; `applied` yêu cầu
ít nhất một native observation hợp lệ cho obligation. Inputs được giữ lại khi
treatment fail để chẩn đoán, nhưng pipeline không freeze/oracle một treatment
failed/unknown. `hit` v1 chỉ xác nhận input relation + site reach; requirement/applicability vẫn
hypothesis, không semantic proof hoặc bug verdict. Static CFG/DFG không chứng minh
feasibility. Trimming bỏ whole low-priority PUT packets khi quá context, giữ source
numbering và ghi supplied IDs; base reminder compact, dedup thực dùng full inventory.

## Integration và artifacts

CLI chọn `--arms spec_obligation`. Completion default4096; context/model/provider
phụ thuộc runner. Prefect normalize/preview và worker nhận standalone arm, với
preview2calls/task/arm. Preset full2 gồm `control_flow`/`spec_obligation`, cap628
logical calls trên157eligible tasks; chỉnh preset không tự launch/reload listener.

`tasks/<n>/<arm>/generation.json` giữ obligations, base/new membership, selected
structural targets, sampling receipts, candidate ledger và native observations.
Requests/responses/attempts/usage dùng shared checkpoint client. Summary tách call
ownership theo exact arm names và logical phases; không cộng hybrid calls vào CF.
Unsupported, pending và empty generations được giữ để report trung thực.

## 16/11/2026 — Context, native budget và coverage diagnostics

Feedback protocol `coverage-concept-spec-feedback-v3` ưu tiên PUT sở hữu target
chưa được đưa vào prompt ở vòng trước, rồi target chưa hit. Khi không có
`coverage_targets`, model trả `concepts: []`; semantic scenarios dùng obligations
và direct inputs, không dùng program/line number làm target ID. Metadata sai
vẫn giữ direct inputs và gửi danh sách target IDs hợp lệ về vòng sửa.

Scenario feedback giữ status, witness indices, số unknown và error counts;
không lặp cả error object cho từng input. Native scheduling ưu tiên owner còn
target/obligation chưa hit, sau đó vẫn dùng phần budget còn lại cho representatives.
Caps về calls, inputs và observations không tăng.

`target_coverage.prompt_omitted` đếm targets chưa từng có trong prompt.
`target_measurements` ghi prompt rounds, số complete/unknown observations và
hit/miss/unknown cho từng target. Miss chỉ nói về inputs đã quan sát; không
chứng minh infeasible. Summary có `target_measurement_pending_tasks` cho cached
artifacts cũ thiếu diagnostics; không suy thành coverage bằng 0. Source run cũ
vẫn replay nguyên trạng, không tự chạy lại workload.

Audit artifact và giới hạn kết luận: [report](../../../review/cf_coverage_diagnosis_20261116.md).

## Source–target–feedback bundles và native budget diagnostic

Feedback protocol `coverage-concept-spec-feedback-v4` scope toàn bộ current IDs,
concepts, obligations, sampling và target diagnostics theo source packets còn
trong prompt. Mỗi supplied target giữ ít nhất một representative observed input
và native status/missed guard, hoặc lý do chưa có observation (`no_candidates`,
`native_budget_exhausted`, `owner_not_yet_observed`). Trimming chỉ xóa candidates
bổ sung, không xóa per-target diagnostics. Previous assistant proposal có thể
nhắc targets deferred, nhưng instruction yêu cầu chỉ hành động trên current IDs.

Concept có optional `feasibility: "suspected_infeasible"` để model giải thích
trong `instruction`; controller giữ `proof_status: "unverified"`, không xóa target
hay coi làhit. Sampling của claim tạm dừng, native routing ưu tiên objectives khác;
valid direct inputs vẫn được kiểm, nên witness có thể phản bác claim.

Default native cap vẫn64/task. CPU diagnostic riêng so prefix64/128 trên cùng
frozen candidate pool; không gọi LLM hoặc sửa selected input suite. Candidate
priority interleave queues của hai rounds cũ; không phải online feedback replay
hoặc kết quả của prompt mới. Run artifacts ghi cap, actual observations, pool
coverage, runtime và source hashes; không tự nối workload hoặc score PUT gain.

## Quyết định giữ v1 — 14/11/2026

Gemini full157eligible tasks/1454PUT: CF gốc35, v161, validatedv235PUT. Union EP+BVA
v2+DTv2 (không Plain) tương ứng79/84/81PUT. V2 không thêm PUT ngoài baseline+v1.
User yêu cầu gỡ v2 và commit v1; thời điểm đó registry giữ hai v1 arms. Ngày17/11
combined arm cũng đã retire. Frozen
runtime/checkpoints/results v2 được giữ, không thay đổi source run đã thực thi.

Chi tiết regressions và giới hạn causal: [report](../../../review/obligation_v1_vs_v2_20261114.md).

## 15/11/2026 — Mở rộng từ flow CF cũ (lịch sử, combined arm đã retire)

`control_flow_obligation` khi đó kế thừa `CoverageFeedbackArm`, core hai vòng của
CF trước thay đổi engine. `spec_obligation` thuần giữ flow v1 riêng. Arm CF đang
có engine vẫn giữ implementation riêng; không xóa engine hoặc đổi snapshot cũ.

Mỗi vòng trả concepts gắn C1/C2 + seed inputs; arm kết hợp thêm spec obligations.
Sau **vòng0**, code sampling và native-check rồi đưa remaining targets,
base/generated scenario membership, parse/encoding/domain/runtime errors vào
**vòng1** để sửa concepts/strategies/scenarios và inputs. Predicate/site reach
không là oracle; không có PUT return values/reference outputs trong feedback.
Code đã covered vẫn được đề xuất semantic scenario; broad base hit hoặc lỗi
metadata không làm bỏ lượt fallback sinh input/vòng sửa cuối.

Protocol mới `coverage-concept-spec-feedback-v1`, calls
`control_flow_obligation_round_0`/`_round_1`; không reuse old propose/construct
requests như thể cùng protocol. Cached completed generation artifacts vẫn được
đọc nguyên trạng; muốn reproduce run cũ phải dùng frozen runtime cũ.

Budgets: tối đa2calls,20selected inputs,64candidate-PUT observations (round0≤32,
round1 dùng phần còn lại),6structural targets; mỗi round≤6concepts+3obligations,
32Hypothesis draws/2s mỗi instance; full recorded-base dedup và300base replays.
Direct/concept/scenario queues interleave; giữ sources/round trong ledger và
observations, chưa quan sát giữ pending chứ không gán hit. Target hit và semantic
membership tách riêng; nghĩa spec/applicability vẫn hypothesis. Chưa hồi sinh
retired validated-v2 state checker, retrieval hoặc tự viết concolic engine.

Authoritative plan: `docs/plans/2026-11-15-extend-original-control-flow.md`.
115focused engineering checks pass, independent reviewclear; full workspace
checks còn lỗi missing legacy fixtures/reference changes ngoài scope, xem plan.
User đã cho phép một fullQwen extension run; control CF39/v153 vàEPDT113 chỉ
reuse saved artifacts, noPlain. Không tự gọi lại baseline để làm đẹp comparison.


CPU comparison hoàn tất: cap64/128 lần lượt hit194/197 trên407targets và
14/17 trên28obligations; sandbox seconds994,57/1710,77 (+72%). Giữdefault64.
Đây là pool coverage, không phải suite20inputs hoặc online feedback efficacy.
[Report](../../../out/cpu_cf_obligation_budget64_128_20261116_235056/REPORT.md).
