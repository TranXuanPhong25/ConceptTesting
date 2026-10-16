# Flow hypothesis + concrete fuzz witness — audit và đề xuất

Ngày 2026-10-16. User đề xuất local CFG/control/data dependencies/path conditions → ranked evidence-backed fault hypotheses → input templates/constraints; khi fuzz tìm được input, đưa input cùng concept. Đây là audit code/results và thiết kế tiếp theo, chưa có pipeline mới hoặc model run.

## Đã thử đến đâu?

| Thành phần | Evidence trong repo | Giới hạn |
|---|---|---|
| Control/data relations | `pipelines/v12_rel/relations.py`: AST enclosing guards và observed def-use từ base/witness traces | Không phải CFG/control-dependence graph đầy đủ; enclosing guard không xử lý đủ early return, exception, loop history. Không có complete symbolic path conditions. |
| Spec-violation hypotheses và ranking | `pipelines/v13_hyp/hypotheses.py`, `hyp_worker.py`: Qwen đề xuất R/chain/T; 200 domain draws filtered by T; rank witnessed+mutant difference, witnessed, unwitnessed | T là model-proposed predicate. Kiểm source line tồn tại/T satisfaction không chứng minh chain/data propagation đúng. PUT–mutant difference không xác nhận spec violation. |
| Witness đi cùng concept | `pipelines/v7/prompts.py:section`, root `gen_prompts.py`, RESULTS §11.1 | `concept-toolinput` đã đưa từng fact cùng concrete input. Đây là flat fact+witness, chưa phải verified semantic hypothesis+path+trace package. |
| Hypothesis đi cùng witness | `pipelines/v13_hyp/hyp_prompts.py` | v13 cố ý chỉ render R/chain/T, không render concrete witness/search/mutant metadata. |

Kết quả frozen, không so chéo phiên bản như một controlled experiment:

- v3m2 `concept-toolinput`, dev113/K=3/ref: 57.0 detected tasks/run, `toolinput`60.0; paired11/16,p=.44 (RESULTS §11.1). Chỉ ghép fact+input chưa cho thấy gain.
- B4/v13: `hyp-hybrid`46.33, `flat-hybrid`62.67, `toolinput`63.00;133 shown hypotheses trên58/113 dev tasks,66 có witness. Calls/sample khác nhau nên không isolate hypothesis wording. Xem `b4_v13_hyp_results.md`.
- Kết quả này chưa đánh giá trọn chuỗi local flow → independently checked hypothesis activation → concept+concrete witness → new inputs.

## Cách tích hợp đề xuất

Giữ Qwen làm semantic extraction/alignment theo `PLAN_QWEN_REASONING_CHAIN.md`; tools cung cấp structural facts và kiểm evidence. Đây là addendum cho hướng đó, không thay bằng hardcoded fault-family matching.

1. Chọn suspect site từ existing facts, source review hoặc hypothesis; ghi provenance, không dùng canonical bug location. Cho phép site đã được base tests cover.
2. Tạo local flow slice có source IDs, branch edges, definitions/uses và guards dẫn tới site/output. Phân biệt static relations, observed relations, model-inferred conditions và unknown. Với missing branch, evidence nằm ở existing path thiếu guard/operation; không yêu cầu trace một branch không tồn tại. Loop/exception/alias ngoài support được ghi unknown.
3. Qwen gắn spec obligation với actual behavior, đề xuất boundary/missing-branch/inverted-condition/null-state hoặc hypothesis khác, kèm counterevidence/alternative. Fault classes là ví dụ, không phải semantic whitelist. Qwen xếp ưu tiên semantic; tool lưu riêng các evidence tiers (trace activation, local effect, output observation), không biến chúng thành xác suất bug.
4. Mỗi hypothesis chọn input template và constraint: boundary `b-1,b,b+1` khi domain cho phép; cặp input phân biệt nhánh; `None`/empty/nonempty chỉ khi spec cho phép; state sequence chỉ cho stateful API. Template là cách tạo input, không tự xác nhận hypothesis. Có thể dùng replayed fuzz witness có sẵn trước khi search mới. Không thu hẹp original input domain để làm hypothesis đúng.
5. Replay concrete input: kiểm domain theo validator với scope rõ ràng, observed path, local state/effect và output. `T(input)=True` chưa đủ xác nhận reach; reach chưa đủ xác nhận semantic failure. Shrink nếu giữ được các checks cần thiết. Unsupported effect/path claim vẫn unknown. Không tìm được witness trong budget không có nghĩa infeasible.
6. Đưa card vào prompt: **concept/obligation + suspected mismatch + source evidence + trigger + concrete witness + observed trace + uncertainty**. Qwen viết assertion theo spec và thêm input khác witness, giữ trigger hoặc tạo contrast để phân biệt alternative. PUT output được ghi observed, không dùng làm expected oracle.

Nếu witness đã được independent oracle xác nhận lỗi, ghi nhận detection trực tiếp; giá trị thêm của Qwen là new-input/new-task yield, không tính lại witness thành discovery của LLM.

## Phép thử cần thiết

Trong một phiên bản/preregistration mới, freeze cùng hypotheses, witness pool, source/spec và discovery costs trước generation. Trên tasks có witness, so cùng concrete inputs giữa `hypothesis+trace+witness`, `witness-only-prompt/toolinput`, `trace+witness` và `placebo+witness`; thêm `hypothesis-without-witness`, matched plain và executable witness-only. Full task denominator vẫn giữ tasks thiếu hypothesis/witness, báo missing coverage riêng. Ablation hypothesis+trace vs trace tách phần semantic package tốt hơn chỉ so với toolinput.

Match generation calls, output/input caps và execution budget; báo actual tokens. Đo riêng activation/effect verification, confirmed D_IO, false alarms, unique generated inputs và detections ngoài shared witnesses. Dùng cùng independent oracle sau freeze. Không kết luận concept gain chỉ từ branch coverage hoặc mutant difference.

Trước implementation, chốt bounded CFG/path support và audit addendum cùng chain plan theo workflow đã có. Hiện chưa chạy experiment, không có claim hiệu quả mới.
