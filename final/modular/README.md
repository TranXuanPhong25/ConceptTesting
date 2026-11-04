# Pipeline theo class và module

Pipeline chính là khung điều phối với **injectable input generation**. Core nhận
`InputGenerator`, chạy preparation stages do generator khai báo, lấy input theo
contract chung rồi freeze → reference program → PUT evaluation → report.

Flow mặc định dùng `plain`; chọn `boundary` cho BoundaryValueAnalysis. Các bước
concept mining, CFG/DFG và witness sampling đã được bỏ khỏi flow hiện đại. Source/
checkpoints các experiments cũ vẫn có compatibility adapter riêng.

Xem [interface, ví dụ inject generator và stage mới](generators/README.md).
Full modular regression gần nhất: **93 checks pass**. Kết quả replay164task trước
đây thuộc refactor lịch sử; lần thay đổi này kiểm compatibility bằng fixtures,
chưa chạy live benchmark. Chi tiết ở [VALIDATION.md](VALIDATION.md).

## Mỗi loại chạy là một module

| Module | Class | Trách nhiệm |
|---|---|---|
| `arms/plain.py` | `PlainArm` | Sinh input không thêm guidance |
| `arms/classical.py` | `ClassicalArm` | Boundary, partition, CFG, def-use |
| `arms/contrastive.py` | `ContrastiveArm` | Khác biệt giữa các PUT pass base |
| `arms/placebo.py` | `PlaceboArm` | Covered facts làm control |
| `arms/toolinput.py` | `ToolInputArm` | Gợi ý input từ sampler |
| `arms/witness_only.py` | `WitnessOnlyArm` | Dùng witness trực tiếp, không gọi model |
| `arms/v11_concept.py` | `V11ConceptArm` | Concept v11, generator inputs-only của bản mới |
| `arms/boundary.py` | `BoundaryArm` | Hai bước LLM của BVA, chia input budget theo task |

`plain` và `boundary` là methods hiện đại. Các methods classical/contrastive/
placebo/toolinput/witness_only/v11_concept ở bảng là legacy, chỉ chạy khi chọn rõ.
Method mới có thể là stage trả inputs, không cần inherit `ExperimentArm`.
`MethodInputGenerator` ghép các method vào interface chung; core không dispatch
theo tên hay buộc chạy concept stages trước generation.

## Mỗi stage là một class

| Module trong `stages/` | Class | Đầu ra chính |
|---|---|---|
| `program_generation.py` | `ProgramGenerationStage` | Chương trình khác cấu trúc; chỉ khi chủ động tạo cohort mới |
| `base_tests.py` | `BaseTestFilterStage` | Base outcomes và cohort task |
| `frozen_cohort.py` | `FrozenCohortStage` | Nạp cohort đã có, không sinh lại |
| `input_preparation.py` | `InputPreparationStage` | Eligibility, visibility, optional shared prompt; không tạo concept |
| `input_generation.py` | `InputGenerationStage` | Gọi injected generator, validate shared output contract và checkpoint |
| `reference_oracle.py` | `ReferenceOracleStage` | Expected outputs và input hợp lệ |
| `put_evaluation.py` | `PutEvaluationStage` | Outcome matrix, PUT bị phát hiện |
| `reporting.py` | `ReportingStage` | Tổng hợp, matched comparison và Markdown report |

Benchmark mặc định bắt đầu ở **FrozenCohortStage**. Hai class tạo chương trình/lọc
base là công cụ riêng cho một cohort mới, không tự chạy lại trong benchmark.

`TaskContext` là dữ liệu truyền giữa stages. `ArtifactStore` quản lý checkpoint.
`ModelCalls` tách stage logic khỏi backend LLM. `BenchmarkPipeline` chỉ điều phối:

1. Chạy tất cả generation stages cho mọi task.
2. Đóng băng toàn bộ input.
3. Chạy reference/evaluation/reporting stages.

Mỗi stage có `name`, `requires` và `run(context)`. Input-producing stage có thể
trả `{"inputs": [...]}` để ghép qua MethodInputGenerator. Generator tùy ý cũng
có thể trả trực tiếp task batches mà không cần packet hay shared preparation.

## Inject stage sinh input mà không sửa orchestrator

```python
from final.modular.stages.base import PipelineStage
from final.modular.generators import MethodInputGenerator


class MyInputStage(PipelineStage):
    name = "my_method"

    def run(self, context):
        return {"inputs": [{"args": "([1, 2],)", "kwargs": "{}"}]}


generator = MethodInputGenerator([MyInputStage()], preparation_stages=())
pipeline = BenchmarkPipeline(cohort_path, artifacts, input_generator=generator)
```

Ví dụ trên dành cho task nhận một list; logic method thật cần dùng spec/interface
của task. Stage chuẩn bị riêng có thể inject bằng `preparation_stages`, hoặc thêm
qua `insert_stage(stage, after=...)`. Thứ tự thiếu dependency hoặc trùng tên bị
từ chối. Generator/method/stage có tham số cần khai báo `configuration()` để
manifest khóa đúng cấu hình. Đổi source/config thì dùng output directory mới.

## Chạy và track

Mặc định **replay chỉ đọc**, không tạo model và không chạy lại PUT:

```bash
final/.venv/bin/python -m final.modular.run
final/.venv/bin/python -m pytest final/modular/tests -q
```

Replay đọc stage checkpoints, xác minh input/oracle/outcome và
toàn bộ summary kể cả accounting. Cache thiếu hoặc khác kết quả thì báo lỗi; không
tự gọi API hoặc execute thay thế. Original source/contracts/dependencies được kiểm
tra trước khi replay. Các artifacts cũ không bị ghi đè.

Để bắt đầu một run mới khi đã cấu hình backend, phải nêu rõ `--mode run` và thư mục
mới; ví dụ chỉ chạy hai arm:

```bash
final/.venv/bin/python -m final.modular.run --mode run \
  --artifacts final/out/modular_comparison --arms plain boundary
```

CLI dùng adapter Qwen đã review. Python API nhận bất kỳ implementation `ModelCalls`
nào; `CoreModel` vẫn là interface backend ở `final/core_model.py`. Chọn arm khác là
cấu hình run khác, không sửa hay ghi đè kết quả của run vừa xong.

`pipeline.stage_events` chứa `task_id`, `stage`, `state` để track từng pipe. Run
thường ghi thêm `stage_events.jsonl`; replay chỉ giữ events trong memory.
`modular_manifest.json` khóa class/config/source/model/tasks/metadata/environment;
`generation_frozen.json` khóa input; `modular_summary.json` và `REPORT.md` là kết quả.
Chưa commit/push bản refactor này theo yêu cầu giữ pipeline mới ở local.

Default artifacts path là `final/out/modular_pipeline`; replay cần run đã hoàn
thành với đúng generator/settings/source. Chạy legacy `--legacy-generation --arms
witness_only` không tạo model hay gọi tokenizer, nhưng vẫn chạy sampler/reference.

## Legacy compatibility: concept v11

Phần này mô tả experiment cũ, được chọn tường minh qua `--legacy-generation`.
`LegacyArmInputGenerator` chứa các bước concept/witness cũ, không nằm trong core
hoặc flow mặc định. Giữ source và artifacts để đối chiếu lịch sử.

User đổi workflow: sửa trên code hiện có, không copy thêm folder version và
không commit trước khi user review. Arm mới được thêm ngay trong `final/modular/`:

`frozen PUTs → V11 concept extraction → common prompt + concept cards →
1 call/task sinh inputs-only → freeze toàn bộ inputs → reference → tất cả PUT pass base`.

V11 chỉ cung cấp B5 mining, coverage/mutation/fuzz facts, ranking/G-prime và spec
fallback qua đúng kernels gốc. Không chạy V11 round1, hybrid, assertions, expected
output hay retry sinh test. `V11ConceptArm` kế thừa nguyên `ConceptArm.run()` nên
cùng prompt nền, parser, seed, temperature, input/output budget và oracle với các
arm mới. Guidance chỉ có id/kind/text; không truyền witness, tool input, mutant
source, strategy code hoặc output của reference. Sáu arm cũ lấy qua `legacy_arms()`
khi replay lịch sử; default hiện tại chỉ có plain.

Concept được tạo cho từng PUT. Từ top3 gốc của các PUT thấy trong prompt, lấy tối
đa4card theo rank rồi round-robin theo thứ tự PUT đang hiển thị; không chọn dựa
trên output/lỗi. Vị trí line được đối chiếu AST về raw source, vị trí không ánh xạ
được ghi rõ là line của V11 view. Đây là adaptation từ per-PUT sang prompt chung
theo task, không phải toàn bộ V11 hybrid. Xem [PREREG.md](PREREG.md).

Mặc định đọc lại concept cache từ `final/out/v11_clean_runtimefix/`. Kiểm tra raw
source, view, spec/base, model, tool versions và source hashes trước khi import;
không đọc file result/oracle của run cũ. Thiếu cache thì chỉ chạy mining/facts
và checkpoint riêng ở output mới. `--v11-cache-only` cấm tính lại concept.
Reference và PUT evaluation giữ nguyên. Giữ cả quy tắc skip shortfall của bản mới:
164 task records,157 task eligible/1454 PUT trong cohort hiện tại; khác run full
V11 vốn giữ cả các task shortfall. Không so raw count hai protocol như cùng budget.

Lệnh cho run **sau khi review**, chưa chạy benchmark trong lần sửa này:

```bash
final/.venv/bin/python -m final.modular.run --mode run \
  --artifacts final/out/v11_concept_inputs --legacy-generation --arms plain v11_concept
```

Output directory mới là nơi giữ kết quả cấu hình mới, không phải một version
source mới. `v11_concept_extraction` có stage events và từng PUT có progress riêng;
`v11_concept_preparation` trong summary tách chi phí mining khỏi tester calls.
Concept import có lịch sử request đã dùng, không được gọi là concept miễn phí.

## Resource exclusions đã được user chọn

`--v11-resource-exclusions <plan.json>` áp dụng danh sách PUT được loại khỏi
**preparation, prompt của cả hai arm và evaluation**. Plan gắn source/spec/cohort
hash và lý do từng PUT; per-task marker phải được ghi trước khi task sinh inputs.
Không dùng tùy chọn này để đổi task đã có kết quả. Cohort nguồn/checkpoint cũ giữ
nguyên; report phân biệt số base-pass gốc, số bị loại và số thực sự được chấm.
Nếu loại hết base-pass của task thì task được ghi skip rõ ràng.

## BoundaryValueAnalysis

Module độc lập theo từng PUT: [boundary_value_analysis/](boundary_value_analysis/README.md).
`BoundaryValueAnalysis.extract()` trích type và templates offline;
`run_for_program()` dùng saved task/PUT records và backend hiện có để chạy hai bước
LLM: chọn boundary/domain, sau đó sinh input. Có early skip và resumable checkpoints.

Đã tích hợp qua `BoundaryArm`, chọn bằng `--arms boundary` hoặc inject
`MethodInputGenerator([BoundaryArm()])`. Output đi qua generation freeze → reference/domain validation → PUT
evaluation → report như các arm hiện có. Report giữ task/PUT skip reasons và số
logical calls của cả selection lẫn generation.

Input budget là tổng **per task**, chia đều cho các visible PUT có templates;
phần dư theo thứ tự visibility hiện có. PUT không có template nhận0budget. Nếu
số PUT vượt input budget thì phần còn lại có status `input_budget_exhausted`.
Share của PUT no-boundary/invalid không chuyển cho PUT khác. Gộp inputs, deduplicate
và namespace concept IDs theo PUT trước khi chấm trên mọi retained PUT của task.
Vì mỗi PUT có thể dùng2calls, so sánh với one-call plain hiện chỉ là descriptive,
không tự claim matched-call efficacy.

Chạy boundary smoke subset đã có, khi backend và run được cấu hình:

```bash
final/.venv/bin/python -m final.modular.run --mode run \
  --cohort final/out/development_groups/boundary/smoke/cohort.json \
  --artifacts final/out/boundary_smoke_pipeline \
  --arms boundary --target-programs 1 --input-budget 20 \
  --task-ids HumanEval/0 HumanEval/5 HumanEval/18 HumanEval/81 HumanEval/99 HumanEval/120
```

`--arms plain boundary` thêm plain vào cùng run. Với boundary-only, không chạy
classical CFG/DFG hoặc witness sampler; empty suite không execute reference/PUT.
`--mode replay` đọc lại cùng artifacts/settings/task IDs mà không gọi model.
Đây là lệnh sử dụng, chưa launch live smoke/benchmark trong lần tích hợp này.

Inputs qua literal/signature/boundary-target checks vẫn có constraints dạng prose
chưa được verify. Reference stage áp dụng trusted contract hiện có; không biến
mọi LLM constraint thành proven fact. Xem module README cho schema và giới hạn V1.
