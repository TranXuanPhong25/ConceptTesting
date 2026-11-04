# Injectable input generation

`BenchmarkPipeline` nhận `input_generator: InputGenerator`. Core phụ thuộc vào
interface này để lấy input; mỗi phương pháp tự quản lý logic, LLM calls và evidence.

```text
FrozenCohortStage
  → optional preparation stages do generator khai báo
  → InputGenerationStage(input_generator)
  → freeze inputs của tất cả tasks
  → ReferenceOracleStage
  → PutEvaluationStage
  → ReportingStage
```

Core không import hoặc tạo `ConceptAnalysisStage`, `WitnessSamplingStage` hay V11
mining. Default mới là `plain`. `boundary` dùng chính module BoundaryValueAnalysis.
Modern context preparation chỉ kiểm cohort eligibility, chọn visibility order và
tạo prompt cho method nào cần. Không có bước tạo concept cũ trước input generation.

## Inject phương pháp đã có

```python
from pathlib import Path
from final.modular.arms.boundary import BoundaryArm
from final.modular.artifacts import ArtifactStore
from final.modular.context import PipelineSettings
from final.modular.generators import MethodInputGenerator
from final.modular.pipeline import BenchmarkPipeline

generator = MethodInputGenerator([BoundaryArm()])
pipeline = BenchmarkPipeline(
    Path("final/out/development_groups/boundary/smoke/cohort.json"),
    ArtifactStore(Path("final/out/boundary_smoke_injected")),
    input_generator=generator,
    calls=calls,  # ModelCalls backend đã cấu hình
    settings=PipelineSettings(target_programs=1, input_budget=20),
)
summary = pipeline.run(selected_tasks, metadata)
```

Có thể dùng `arms=(BoundaryArm(),)` như API ngắn hiện có; composition adapter sẽ
chuyển thành generator. Không truyền đồng thời `arms` và `input_generator`.

## Stage mới có thể trực tiếp sinh input

Không cần inherit `ExperimentArm`, không cần `build_guidance`, concept packet hoặc
đăng ký tên vào orchestrator. Stage chỉ cần có `name`, `configuration()` và
`run(context)` trả method batch:

```python
from final.modular.generators import MethodInputGenerator
from final.modular.stages.base import PipelineStage


class EquivalenceInputsStage(PipelineStage):
    name = "equivalence"

    def run(self, context):
        # Thay bằng logic riêng của phương pháp: mining, solver hoặc LLM.
        return {
            "inputs": [{"args": "([1, 2],)", "kwargs": "{}"}],
            "status": "generated",
            "rejected": [],
        }


generator = MethodInputGenerator(
    [EquivalenceInputsStage()],
    preparation_stages=(),  # Method này chỉ cần frozen task/cohort context.
)
pipeline = BenchmarkPipeline(cohort_path, artifacts, input_generator=generator)
```

Nếu method cần chuẩn bị riêng, truyền các `PipelineStage` vào `preparation_stages`.
Các stage này chạy qua orchestrator, có dependency checks và stage events. Stage
chuẩn bị truyền intermediate state qua `context.extensions`; method đọc state đó
để trả inputs. Method được gọi trong `InputGenerationStage`, không đăng ký lại
chính method vào preparation stages để tránh gọi hai lần.

Mọi method trong adapter nhận cùng task input budget; nếu method dùng nhiều PUT
thì tự chia budget, như `BoundaryArm` đã làm. `configuration()` phải chứa tham số
có ảnh hưởng tới output. `source_dependencies()` có thể khai báo helper files nằm
ngoài `final/modular`; source của generator/method/preparation stage được ghi vào
manifest. `uses_shared_prompt=True` chỉ dành cho method có `build_messages(packet)`
và cần prompt chung của PlainArm; method mới mặc định không cần prompt này.

## Inject toàn bộ generator riêng

Khi cần kiểm soát nhiều phương pháp hoặc stages phức tạp, implement abstraction:

```python
from final.modular.generators import InputGenerator


class MyInputGenerator(InputGenerator):
    def generate(self, context):
        return {
            "task_id": context.task["task_id"],
            "arms": {
                "my_method": {
                    "inputs": [{"args": "([1, 2],)", "kwargs": "{}"}],
                },
            },
        }
```

Đây là ví dụ contract cho task nhận một list; generator thật phải dùng interface/
spec của task. Key `arms` được giữ để tương thích reference/evaluation/artifacts
hiện có; nó chứa các named method batches và không bắt buộc subclass arm.

Các hooks tùy chọn: `preparation_stages`, `configuration`, `source_dependencies`,
`dependency_objects`, `reporting_stage`, `extend_summary`, `render_summary`.
Full generator nhận frozen cohort và tự quyết định eligibility/skip cho task;
core không buộc mọi phương pháp phải dùng cùng concept/visibility machinery.

## Output contract và validation

Mỗi input có `args` là literal list/tuple string, `kwargs` là literal dict string.
Có thể kèm `concept_id`, boundary evidence hoặc dữ liệu provenance khác. Method
không tạo được input trả `inputs: []` và reason/status; nếu cả task bị bỏ qua thì
generator trả `{"task_id": "...", "skip": "reason"}` thay cho `arms`.

`input_contract.validate_generated_inputs()` kiểm task identity, tên methods,
batch shape, tổng records per method không vượt task budget và literal syntax
trước khi ghi `inputs.json`. Contract này chỉ kiểm format; input validity và output
correctness tiếp tục do reference/domain stage xử lý sau generation freeze.

Các validation của BVA được gom vào hàm:

- `BoundarySelection.validate_response()` và `validate()`.
- `BoundaryInputGeneration.validate_response()` và `validate_input()`.
- `BoundaryArm.validate_task_input()`.
- `validate_generated_inputs()` và `validate_input_literal()` ở shared contract.

Chỗ gọi validation được đánh dấu `# VALIDATION START: ...` và
`# VALIDATION END: ...`. API arguments, budgets/cache identity và reference checks
cũng có block markers để dễ đọc. Đây là refactor cách tổ chức, không tắt checks.

## Checkpoint và legacy

`InputGenerationStage` dùng output checkpoint đã có khi resume/replay. Cache thiếu
ở read-only mode báo lỗi trước khi gọi generator. Manifest mới dùng protocol
`injectable-input-generator-v1`, khóa generator class/config/source cùng task,
model và settings; đổi generator/config phải dùng output directory mới.

Các experiments trước refactor giữ nguyên artifacts và source gốc. Adapter
`LegacyArmInputGenerator` duy trì flow concept/witness cho các methods cũ được
chọn tường minh. CLI yêu cầu `--legacy-generation` để chọn classical, contrastive,
placebo, toolinput, witness_only hoặc v11_concept. Không migrate manifest hay resume
run đang chạy bằng source mới một cách tự động.
