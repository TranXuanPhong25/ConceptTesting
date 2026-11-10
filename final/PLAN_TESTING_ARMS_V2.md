# Testing arms v2 — behavioral/fault refinement + soft examples

User2026-11-09 đồng ý v2EP+BVA vàDT, rồi chọn **smoke6/4arms/tối đa24calls**,
chỉ chạy sau khi hai fullrun hiện tại completed evaluation/sourcechecks/replay.
V2 chưa có efficacy result; target Luna<90% chưa đo và không claim đã đạt.

## Thay đổi

- `ep_bva_v2`: bắt đầu từ specification behaviors/joint constraints/result kinds,
  dùng fault hypotheses quyết định tách/gộp class; chọn typical representatives,
  kiểm membership và bỏ redundancy trừ khi tests phân biệt faults khác nhau;
  normal BVA bổ sung ở class edges và giữ single-fault.
- `decision_table_v2`: interacting predicates/relations từ spec, không yêu cầu
  nhiều parameters; feasible/infeasible/unresolved riêng, fault hypotheses rà
  missing combination/condition/priority; ordered actions xác định trước merge,
  chỉ dùng don't-care khi condition không đổi behavior; kiểm coverage/membership.
- Optional `fault_hypothesis` trên class/rule, dùng existing covers để link input.
  Annotation không phải confirmed bug; semantic correctness tiếp tục pending.
- Mỗi v2arm nhận1soft example production-domain113words; v1không nhận examples
  hoặc hypothesis instruction. Shared schema chấp nhận optional annotation cho
  cả hai versions nhưng field không xuất ra khiNone,giữ shape v1 cũ.

Examples có provenance/commit/SHA256/nguồn license và engineering verification ở
[testing_arm_examples](research/testing_arm_examples/README.md). Không nhúng7bước
hoặc full solved table. Không tạo unsupportedinvalidbehavior,không execute model
predicates,không sinh expectedoutput bằngLLM. Một generationcompletion/task/arm.

## Comparison và budget

Cohort `boundary_smoke`:HumanEval0/5/18/81/99/120,1representativePUT/task,
4arms `ep_bva`, `ep_bva_v2`, `decision_table`, `decision_table_v2`.
20inputs/task/arm,completion4096tokens/call,context8192tokens,temperature0.7,
seed314159+tasknumber,reference271828+tasknumber,timeout8s/input.
Tối đa24logicaltester calls/480input records/98,304completiontokens cap.
Keepalive/physicalretryusage báo riêng. Cùng visibility jointlytrim cho cả4arms,
reference/scorer/parser/freeze/cache. V1-v2 chính theo technique;cross-technique
comparisons chỉdescriptive. Đây đo instruction+example package,không cô lập riêng
Fault Hypotheses/examples; không claim novelty chỉ vì thêm chữ “fault”.

Precedent:v31faulttemplate18vs15/33(p≈.38,mộtwin do schema),v34placebo rulekhông
đạt vàhypothesis accuracy không đượcchứngminh. V2 không reimplementpaper hoặc
mutation-ranking pipeline;chỉ là spec-based refinement có thể quan sát annotation.

## Thứ tự chạy

Predecessors43c7061b-38c6-4bbb-8c5a-6da366d337f9(Direct/Soft8s) và
d3a095ba-e5d2-46a4-bbe8-44deebdb6073(full3arms8s). Followup có mộtPrefectrecord,
prepare/source/config/cohort/exampleJSON/privateendpoint snapshot ngay trướcwait.
Chưa model/tokenizer/nativecalls trong lúcwait;chỉ launch frozenworker khi BOTH
APICompleted và savedstatuscomplete/nativeprogressfullyevaluated/resultdigest
sourcechecks+replayPASS. Failed/cancelled/crashed/missingfinalproof thìblock và
reportreason,không coi như “xong đểchạy”. Không sửahoặctakeovercurrentworkers.

Run cụ thể/các artifact được cập nhật khi prelaunch independent review/testsPASS.
Không tự nối fullv2 hoặc rerun sau smoke24calls.


Đăng ký thực tế: [Prefect followup](http://127.0.0.1:4200/runs/flow-run/117ba63b-4813-4663-88dc-f888a3e3d8fd).
Snapshot đã prepare, source guard và frozen example JSON được xác nhận;
0 model calls, chưa có worker_started marker trong lúc hai predecessors Running.
Independent final review GO;501 tests pass và11 orchestration checks pass riêng.
Không phải kết quả efficacy; không có benchmark/Luna inference ngoài24calls đã cho phép.
