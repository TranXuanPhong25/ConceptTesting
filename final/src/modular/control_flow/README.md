# Control-flow concept discovery

Module tạo concept để thử C1/C2 gaps từ source và available base coverage.
LLM đặt tên scenario, mô tả input relation và construction instruction; tool
kiểm domain và đo actual target hit, sau đó trả feedback cho vòng sửa kế tiếp.
Concept luôn được lưu, kể cả chưa có witness. Source-bound không đồng nghĩa
semantic claim đã được chứng minh.

## Cơ chế

- `analysis.py`: coverage.py `PythonParser` lấy possible line arcs/executable
  lines. So với base traces để tìm C1/C2 gaps; BFS lấy một structural prefix,
  không tuyên bố path feasible. python-graphs `LAST_WRITE` cung cấp static may
  def-use; lỗi graph không chặn coverage analysis. Assignments và original
  source line labels đi cùng target để model đọc operation semantics.
- `schema.py`: concept gồm `id`, tool `target_id`, `name`, `input_relation`,
  `instruction`, `evidence_lines`, optional `predicate` (rỗng khi unsupported),
  và `strategies` (rỗng hoặc descriptors keyed theo signature). Source lines,
  target IDs, safe expression syntax và reference tới input parameter được kiểm;
  constant examples không được dùng làm predicate. Đây chưa phải semantic proof;
  prose semantics là hypothesis.
  `inputs` dùng named arguments/`concept_id`. Metadata sai không xóa valid
  direct attempts. Không thực thi model-written code.
- `arms/control_flow.py`: LLM discovery và Hypothesis constructors dùng chung
  candidate ledger; sandbox chạy original source, kiểm trusted admission rồi
  đo coverage.py. Feedback chỉ có domain/status/target hits và concept checks,
  không có actual output/reference. Input trùng merge provenance và reuse trace.
  Selection ưu tiên target hits rồi giữ các valid attempts còn budget.

Vì source original không bị rewrite, runtime giữ short-circuit semantics;
**chưa đo atomic-condition C3 hoặc MC/DC**. C2 không thay C3. Loop paths có thể
được model nhắm qua concept nhưng không có loop-count proof. Static may-flow
không chứng minh dynamic def-clear path hoặc intended semantics.

## Budget và artifacts

ControlFlow gửi mọi target đã phân tích từ PUT pass base tests, theo thứ tự
analysis, tối đa 6 target mỗi prompt mặc định. Phần chưa vừa chuyển sang batch
sau. Target chỉ bị bỏ khi prompt riêng của nó vượt context. Nếu còn lượt sau
khi gửi các batch, feedback dùng lại target và evidence của batch cuối.
Mặc định có ngân sách 2 round, hoặc một call cho mỗi batch nếu cần nhiều hơn.
Preview Prefect ghi tổng call và completion token là `pending`.

Mặc định mỗi concept/round có tối đa 32 draws và 2 giây sampling. Tổng quota
trace là 64 lượt input–PUT/task. Suite cuối dùng shared `input_budget` (20 mặc
định). Trace tối đa 1 giây/input trong singleton bwrap. Hard timeout ở native C
cho unknown/no coverage, lỗi infrastructure thật vẫn raise. Không suy
infeasible từ timeout/no witness.

Nếu thiếu cached coverage, replay toàn bộ recorded base calls tới300/PUT,
không cắt32calls. Quá cap hoặc replay thiếu measurement thì coverage unknown.
Đây là baseline của **available recorded calls**, không claim cover unrecorded
base-suite execution. Cached baseline và replay provenance/count được lưu.

Phân tích lấy target từ base evidence. `analysis.json` lưu target đã xếp batch,
target quá dài và PUT không có target nào vừa context. Coverage dùng tập
target đã xếp batch làm mẫu số. Kết quả ghi các PUT có target nhưng thiếu trace,
ví dụ khi không còn quota native. Observations đếm cặp input–PUT và unique
inputs đếm input.

Artifacts mỗi task: `control_flow/analysis.json`, `response_<round>.json`,
`base_<id-hash>.json` nếu cần, `generation.json`. Lưu raw response, errors,
concepts, strategy receipts, candidate ledger, native observations và target
coverage. Shared input freeze/reference/evaluation xử lý functional bugs sau.
Read-only replay đọc generation đã lưu, không gọi model hay chạy PUT.

## Sử dụng

CLI opt-in là `--arms control_flow` (có thể ghép `plain`). Default vẫn `plain`.
Completion default của comparison có control_flow là4096tokens/call. Đây là
adaptive generator, **chưa có preset trong Prefect batch runner một completion**.
Không tự chạy benchmark từ ví dụ dưới; mọi run cần lệnh người dùng.

```python
from final.src.modular.arms.control_flow import ControlFlowArm, ControlFlowSettings

arm = ControlFlowArm(ControlFlowSettings(rounds=2, candidate_limit=64))
# Truyền arms=(arm,) hoặc MethodInputGenerator([arm]) vào BenchmarkPipeline.
```

Reuse installed coverage.py, python-graphs, Hypothesis và Pydantic; optional
dependency group `control-flow` khai báo hai tool chưa thuộc base dependencies.
API `ModelCalls` giữ nguyên, nên endpoint hiện tại hoặc test adapter đều dùng
được. Không tự đổi model của benchmark.

## Grounding trong papers

Adaptation kết hợp [PANTA](https://arxiv.org/html/2503.13580v2) cho chọn missing
targets, [HITS](https://arxiv.org/html/2408.11324) cho scenario/concept và
[PALM](https://arxiv.org/html/2506.19287) cho execution checking. Module dùng
original-source tracing thay path-specific program rewriting của PALM.
Không reproduce full engines, không sửa author source. So với v11, thêm explicit
concept response và adaptive native feedback trên current inputs-only protocol;
v13/v57/VR15 đã có nhiều phần liên quan. Xem [research report](../../../../research/cfg-coverage-concepts-2026-11-10/REPORT.md).
