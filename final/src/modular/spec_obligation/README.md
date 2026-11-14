# Spec obligations v1

Hai opt-in arms: `spec_obligation` đề xuất semantic scenarios từ spec/code;
`control_flow_obligation` kết hợp scenarios với C1/C2 coverage gaps. Default Plain
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

`hit` v1 chỉ xác nhận input relation + site reach; requirement/applicability vẫn
hypothesis, không semantic proof hoặc bug verdict. Static CFG/DFG không chứng minh
feasibility. Trimming bỏ whole low-priority PUT packets khi quá context, giữ source
numbering và ghi supplied IDs; base reminder compact, dedup thực dùng full inventory.

## Integration và artifacts

CLI chọn `--arms spec_obligation control_flow_obligation`. Completion default4096
khi chọn arm; context/model/provider phụ thuộc runner. Prefect normalize/preview,
worker và meaningful run names nhận cả hai arms; preview tính2calls/task/arm.
Preset full3 gồm control_flow/spec_obligation/control_flow_obligation được chuẩn bị,
không tự launch hoặc reload listener khi chỉnh code/preset.

`tasks/<n>/<arm>/generation.json` giữ obligations, base/new membership, selected
structural targets, sampling receipts, candidate ledger và native observations.
Requests/responses/attempts/usage dùng shared checkpoint client. Summary tách call
ownership theo exact arm names và logical phases; không cộng hybrid calls vào CF.
Unsupported, pending và empty generations được giữ để report trung thực.

## Quyết định giữ v1 — 14/11/2026

Gemini full157eligible tasks/1454PUT: CF gốc35, v161, validatedv235PUT. Union EP+BVA
v2+DTv2 (không Plain) tương ứng79/84/81PUT. V2 không thêm PUT ngoài baseline+v1.
User yêu cầu gỡ v2 và commit v1; active registry/source chỉ giữ hai v1 arms. Frozen
runtime/checkpoints/results v2 được giữ, không thay đổi source run đã thực thi.

Chi tiết regressions và giới hạn causal: [report](../../../review/obligation_v1_vs_v2_20261114.md).
