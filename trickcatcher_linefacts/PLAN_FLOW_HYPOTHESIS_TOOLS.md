# Plan: hypothesis có source/spec/path evidence, concept/input và model gọi tool

Ngày 2026-10-16. **Trạng thái: chỉ lập plan**, theo yêu cầu mới nhất của user. Chưa copy pipeline, viết implementation hoặc gọi model. Yêu cầu endpoint trước đó không còn là điều kiện của task planning này.

## 1. Mục tiêu và điểm bắt đầu

Kiểm tra hai hướng:

1. Đưa hypothesis có source/spec/path evidence vào prompt, kèm abstract concept, concrete fuzz input, hoặc cả hai.
2. Cho Qwen chủ động gọi tool để kiểm structural/path claims và replay input, rồi dùng evidence để sửa hypothesis và sinh test.

Đây là extension của `PLAN_QWEN_REASONING_CHAIN.md`. Qwen làm semantic extraction/alignment; tools cung cấp/check facts. Không dùng static property-name matching để chọn semantic mismatch. Audit những phần đã thử nằm ở `analysis/flow_hypothesis_witness_direction_2026-10-16.md`: flat concept+input đã thử và chưa hơn toolinput; v13 có hypothesis nhưng giấu witness trong prompt. Kết quả cũ chưa đánh giá trọn package mới.

**Khi được yêu cầu implementation:** copy toàn bộ source của `pipelines/v7/` (best pipeline theo research-state hiện tại) sang `pipelines/v21_flowtools/`, trước mọi sửa đổi. Tạo parent manifest ghi source hashes, parent commit và file list; thêm CHANGELOG. Không copy output/cache làm kết quả mới. Fairness fixes từ v11_fair sẽ được port có liệt kê vào bản copy, không dùng v13/v19/v20 làm parent. Nếu best được cập nhật trước thời điểm implementation, xác minh lại research-state/results rồi ghi parent thực tế.

## 2. Chuỗi tạo evidence và hypothesis

| Bước | Qwen làm gì | Tool cung cấp/kiểm gì |
|---|---|---|
| S1 Spec concepts | Trích obligations, domain, eligibility, output/state relation và ambiguity | Exact quote/span và parameter references; quote đúng chưa chứng minh interpretation đúng |
| S2 Actual behavior | Abstraction của behavior từ executable code; nêu guards/state changes/output effects | Stable source IDs, local CFG, syntactic reads/writes, observations; S2 không nhận S1/spec-derived hints |
| S3 Hypotheses | Align S1–S2; đề xuất tối đa3 hypotheses, chọn tối đa2 để probe; ghi alternative/counterevidence | Check references; lưu evidence levels; không tự chọn fault theo keyword |
| Discovery | Chọn input template/constraint và dự đoán điều gì phân biệt các alternatives | Replay common frozen fuzz pool; xác nhận phần structural/execution được support |
| Generation | Dùng các package khác nhau hoặc tool feedback để sinh input/test | Cùng input domain filter, execution interface, caps và independent scoring |

Mỗi hypothesis có: `id`, obligation/spec span, source IDs, path/behavior claim, suspected mismatch, trigger, input template, constraints, predicted local/observable effect, alternative và uncertainty. Boundary/missing branch/inverted condition/null-state là ví dụ, không phải whitelist. `None` chỉ dùng khi original spec cho phép.

**Concept** là abstract relation cần giữ, ví dụ eligible duplicate occurrences phải được bảo toàn. **Hypothesis** là claim cụ thể rằng một code operation/path có thể vi phạm relation đó. **Witness** là concrete input có observed evidence được mô tả. Hypothesis vẫn chứa spec evidence khi không render concept riêng; ablation này đo lợi ích của việc trình bày concept rõ ràng, không thể xóa mọi semantic concept khỏi hypothesis.

Hypotheses gắn immutable source/spec/artifact IDs. Qwen chọn semantic priority trước replay; tool ghi riêng trigger/reach/effect support và contradictions. Thứ tự không được đổi bằng canonical feedback hoặc score của oracle. Không chỉ giữ hypotheses có witness; thiếu witness được ghi rõ và vẫn tính vào full-task coverage.

## 3. Structural/path support cần chốt

- Local CFG phải có actual successor edges cho sequence, if/else, return/early return và loop break/continue trong subset đã support. Enclosing AST guards chỉ là một structural fact, không gọi là complete control dependence.
- Control dependence chỉ báo khi CFG/exit assumptions cho phép tính đúng; ghi normal/exceptional scope. Unsupported try/finally, dynamic dispatch, aliases hoặc helper semantics trả `unknown`, không đoán.
- Data facts phân biệt syntactic read/write, static reaching-definition relation nếu có, và observed def-use. Không biến shared variable name thành proven propagation.
- Path condition luôn có scope: model-proposed trigger, static bounded condition, hoặc observed predicate sequence. Loops dùng bounded trace và iteration IDs; chưa có unbounded symbolic completeness. Reach target không có nghĩa local effect đã thay đổi hoặc effect đến output.
- Missing-branch hypothesis được gắn với existing path thiếu operation/guard theo spec. Tool không thể trace một branch chưa tồn tại.

Ưu tiên thư viện có sẵn nếu đủ semantics; chọn dependency và support matrix trong design audit trước code. Không tự reimplement một paper.

## 4. Tool API cho model

| Tool | Input | Evidence trả về |
|---|---|---|
| `inspect_flow` | Source IDs và bounded neighborhood | Nodes/edges, guard labels, supported control/dependency facts, unsupported constructs |
| `inspect_data` | Source/variable IDs | Definitions/uses và provenance, phân biệt static/observed/unknown |
| `replay_input` | Full positional argument tuple + requested source IDs/observation kinds | Domain-filter status, native output/exception, statement/branch hits và supported state/effect observations |
| `check_path` | Existing trace ID + requested source/edge sequence | Sequence observed/not observed, incomplete trace/unknown; không suy ra global infeasibility |

Calls dùng structured JSON actions để chạy được với Qwen endpoint hiện có; native function calling không phải prerequisite. Model chỉ chọn trong API này; không nhận shell, arbitrary Python evaluator hoặc hidden reference tool. Mọi call/result được lưu và nối với hypothesis ID. Invalid calls vẫn tiêu budget và nhận typed error.

Model có thể keep/revise/withdraw/abstain sau feedback. Revision tạo version mới, giữ proposal cũ và contradiction. Không xóa failed predictions khỏi prompt/report. Tool xác nhận source/path/observation chỉ trong scope của nó; interpretation của spec vẫn cần semantic review.

## 5. Witness và input generation

Common discovery dùng frozen fuzz witnesses của parent trước, tối đa6 unique inputs/task theo selector cố định, không chọn theo oracle. Cost của parent mining/discovery được ghi riêng. Search mới nếu cần phải có budget và provenance riêng; không âm thầm thêm input khi treatment khó.

Replay witness trước generation để lưu domain-filter result, requested target hits và trace scope. Model-proposed trigger chưa có executable checker thì vẫn là unverified claim. Một input chỉ reach line được gọi reach witness; không gọi bug witness nếu chưa có independent oracle.

Generation yêu cầu input mới giữ trigger hoặc contrast input để phân biệt alternative; cho phép dùng lại seed witness nhưng gắn provenance. Expected result phải theo spec. Native PUT output được ghi observed, không làm expected oracle. Nếu input đã bắt bug trực tiếp, detection đó thuộc shared witness contribution.

## 6. Variants và controls

Mọi arm nhận cùng original spec/PUT/base tests. Fixed-package arms dùng cùng frozen hypotheses/discovery artifacts. Không lọc task theo witness/hypothesis success sau khi xem output.

| Arm | Guidance ngoài original context | Câu hỏi |
|---|---|---|
| `concept+hyp` | Abstract concept + hypothesis + source/spec/path evidence | Hướng chưa đưa input cụ thể |
| `input+hyp` | Hypothesis + evidence + common input/trace | Input có làm hypothesis dễ áp dụng hơn? |
| `concept+input+hyp` | Tất cả thành phần trên | Thêm concept presentation có ích so với input+hyp? |
| `agent-tools` | Full package; Qwen chọn tool/query trong budget | Active verification có thêm giá trị? |
| `fixed-tools` | Full package; tool requests theo schedule cố định, không theo model choice | Tách adaptive query policy khỏi thêm evidence/calls |
| `flow+input` | Cùng structural/trace facts + inputs, không explicit mismatch hypothesis | Hypothesis package có thêm giá trị? |
| `toolinput` | Cùng concrete inputs | Mốc đã mạnh trong các run cũ |
| `plain` | Testing instruction và feedback schedule tương đương | So với không guidance package |
| `placebo+input` | Truthful base-covered facts + cùng inputs | Control số request và việc nhận guidance/input |
| `witness-only` | Execute common witnesses; không generation LLM | Tool đã bắt được bao nhiêu? |

Đây là arm menu cho comparison sau feasibility gate; không chạy hết ngay. Chọn/freeze exact matrix trong preregistration trước outputs. Nếu triển khai đủ menu:9 LLM arms và1 executable control.

Proposed per-arm schedule:3 model calls, tối đa2 feedback/tool rounds, cuối cùng tối đa6 unique inputs. Fixed arms đề xuất input và nhận replay feedback theo fixed schedule; agent được chọn structural inspection hoặc replay trong cùng action budget; fixed-tools dùng predeclared query schedule. Mỗi round tối đa6 actions; một action là một API invocation với caps cố định về nodes/events/inputs, không giấu batch execution. Final-stage inputs có validation/execution nhưng không có thêm model revision.

Đây là comparison giữa adaptive systems: ceilings giống nhau không bảo đảm actual tool use/context/tokens giống nhau. Báo riêng discovery/extraction/generation, request/attempt/token counts, tool calls, PUT executions, failures và trace volume. So package quality trên common frozen evidence trước; active tools là contrast riêng, không gộp thành pure concept gain.

## 7. Thứ tự thử và tiêu chí đánh giá

1. **Design audit:** chốt structural subset, source IDs, tool semantics, action/resource accounting, parser/error/resume rules và variant contrasts. Review extension cùng chain plan trước implementation.
2. **Copy và CPU/interface checks:** lưu parent hashes; kiểm early return, loop/break/continue, unreachable/masked effects, exceptions, unsupported syntax, invalid tool calls, trace truncation, instrumented/native agreement và secret-free workers. Không dùng CPU fixtures để claim efficacy.
3. **Controlled semantic diagnostic:** giữ fixture suite/rubric và adjudication gate trong `PLAN_QWEN_REASONING_CHAIN.md`. Thêm tool queries cho claims đúng/sai/unknown. Mechanical checks, schema pass và semantic correctness báo riêng; model self-review không phải gold. Chưa qua gate thì chỉ báo diagnostic, chưa mở benchmark comparison.
4. **20-task dev pilot:** dùng frozen existing design cohort; full denominator giữ cả failed/abstained/missing-evidence tasks. Trước hết kiểm hypothesis usability, tool support và khả năng sinh discriminating input. Không held-out trong bước này.
5. **Matched generation comparison:** chỉ sau feasibility review, freeze arm matrix/config/source/prompts/cost ceilings, append PREREG rồi mới chạy. Shared references/canonical chỉ vào scoring sau generation freeze.

Metrics: source/spec reference validity; independently reviewed semantic hypothesis quality; supported/contradicted/unknown structural claims; trigger/reach/local-effect/output propagation coverage; tool-supported claims trước/sau feedback; admissible unique inputs; confirmed D_IO/false alarms; input/task detections ngoài shared witness pool; total cost. Report raw và random equal-input subsets, không dùng prefix matching.

Một input mới bắt cùng task mà shared witness đã bắt chỉ tăng input diversity/yield, chưa tăng task detection. Branch coverage hoặc mutant difference không thay independent oracle. Nếu agent-tools thắng fixed-tools, claim chỉ trong frozen scope/query budget đó. Nếu concept package không hơn toolinput/witness-only, báo negative result.

## 8. Deliverables khi implementation được yêu cầu

`pipelines/v21_flowtools/` sẽ chứa bản copy v7, parent manifest/CHANGELOG, source/flow services, stage schemas/prompts, tool dispatcher, bounded runner, audit export và scoring adapter. Protocol/run artifacts ghi đủ lineage và budgets; không sửa frozen versions. Hiện deliverable duy nhất là plan này; chưa tạo folder v21 hoặc chạy experiment.
