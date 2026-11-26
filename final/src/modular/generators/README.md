# Injectable input generation

> Cập nhật18/11/2026: bộ chính giữ `ep_bva_v2`, `decision_table_v2`, `control_flow` gốc và `plain`. Đã gỡ VF3, reflection/catalogue→inputs, spec-obligation, LargeInput, Data-flow arms và HumanEval-X adapters khỏi đường chạy hiện tại. Shared pipeline, Pynguin thuần/tool pipeline, HumanEval Python/MBPP và historical outputs/checkpoints vẫn giữ. Nội dung bên dưới về các hướng đã gỡ chỉ là lịch sử; không dùng để launch mới.


`BenchmarkPipeline` nhận `input_generator: InputGenerator`. Core phụ thuộc vào
interface này để lấy input; mỗi phương pháp tự quản lý logic, LLM calls và evidence.

```text
load_cohort
  → InputGenerator.prepare_context (tùy chọn)
  → generate_task_inputs(input_generator)
  → lưu inputs của tất cả tasks
  → run_reference_oracle
  → InputGenerator.post_reference (tùy chọn)
  → evaluate_puts
  → InputGenerator.post_evaluation (tùy chọn)
  → Reporter
```

Default là `plain`. Registry còn `ep_bva_v2`, `decision_table_v2`,
`ep_bva_vf3_measured`, `decision_table_vf3_measured` và `control_flow`.
Các hướng EP/BVA/DT v1 và `boundary_value_analysis/` đã được gỡ bỏ.

## Inject phương pháp đã có

```python
from pathlib import Path
from final.src.modular.plain import PlainArm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings
from final.src.modular.generators import MethodInputGenerator
from final.src.modular.pipeline import BenchmarkPipeline

generator = MethodInputGenerator([PlainArm()])
pipeline = BenchmarkPipeline(
    Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"),
    ArtifactStore(Path("final/out/plain_injected")),
    input_generator=generator,
    calls=calls,  # ModelCalls backend đã cấu hình
    settings=PipelineSettings(target_programs=10, input_budget=20),
)
summary = pipeline.run(selected_tasks, metadata)
```

Có thể dùng `arms=(PlainArm(),)` như API ngắn hiện có; composition adapter sẽ
chuyển thành generator. Không truyền đồng thời `arms` và `input_generator`.

## Method mới có thể trực tiếp sinh input

Không cần inherit `InputGenerationMethod`, không cần `build_guidance`, concept packet hoặc
đăng ký tên vào orchestrator. Method chỉ cần có `name`, `configuration()` và
`run(context)` trả method batch:

```python
from final.src.modular.generators import MethodInputGenerator


class EquivalenceInputsMethod:
    name = "equivalence"

    def configuration(self):
        return {}

    def run(self, context):
        # Thay bằng logic riêng của phương pháp: mining, solver hoặc LLM.
        return {
            "inputs": [{"args": "([1, 2],)", "kwargs": "{}"}],
            "status": "generated",
            "rejected": [],
        }


generator = MethodInputGenerator(
    [EquivalenceInputsMethod()],
    prepare_packet=False,  # Method này chỉ cần frozen task/cohort context.
)
pipeline = BenchmarkPipeline(cohort_path, artifacts, input_generator=generator)
```

Mọi method trong adapter nhận cùng task input budget; nếu method dùng nhiều PUT
thì tự chia budget, như `BoundaryArm` đã làm. `configuration()` phải chứa tham số
có ảnh hưởng tới output. `uses_shared_prompt=True` chỉ dành cho method có `build_messages(packet)`
và cần prompt chung của PlainArm; method mới mặc định không cần prompt này.

## Inject toàn bộ generator riêng

Khi cần kiểm soát nhiều phương pháp hoặc stages phức tạp, implement abstraction:

```python
from final.src.modular.generators import InputGenerator


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

Các hooks tùy chọn: `prepare_context`, `validate_generation`, `post_reference`,
`post_evaluation`, `reporter`, `extend_summary`, `configuration`, `runtime_dependencies`.
Full generator nhận frozen cohort và tự quyết định eligibility/skip cho task;
core không buộc mọi phương pháp phải dùng cùng concept/visibility machinery.

## Output contract và validation

Mỗi input có `args` là literal list/tuple string, `kwargs` là literal dict string.
Có thể kèm `guidance_id`, boundary evidence hoặc dữ liệu provenance khác. Method
không tạo được input trả `inputs: []` và reason/status; nếu cả task bị bỏ qua thì
generator trả `{"task_id": "...", "skip": "reason"}` thay cho `arms`.

`input_contract.validate_generated_inputs()` kiểm task identity, tên methods,
batch shape, tổng records per method không vượt task budget và literal syntax
trước khi ghi `inputs.json`. Contract này chỉ kiểm format; input validity và output
correctness tiếp tục do reference/domain stage xử lý sau generation freeze.

Admission kiểm type trước reference execution cho mọi method, kể cả input literal
từ custom/frozen generators. `CallBuilder` enforce type hints đệ quy cho container,
phân biệt bool với int/float, chấp nhận int ở vị trí float và không ép kiểu input.
HumanEval và MBPP+ đọc kiểu từ chữ ký gốc. Tham số thiếu annotation được kiểm tra
hình dạng lời gọi và giá trị literal như các tham số khác. HumanEval kiểm tra thêm
contract khi chạy reference. Nếu caller truyền metadata kiểu tường minh,
`CallBuilder` chỉ dùng nó cho tham số chưa có annotation.
Unsupported annotation bị reject rõ ràng, không âm thầm bỏ check.

`run_reference_oracle` ghi `input_type_rejects` và detail cho input sai interface/type;
input đó không gọi reference hoặc PUT và không tính vào valid inputs/detections.
Raw input indices và catalogue survivor indices vẫn được giữ đúng sau khi lọc.
Type admission không thay thế value bounds/joint preconditions trong contract,
không tự rescore artifact cũ. Frozen runtime cũ giữ admission policy cũ.

Các validation của shared pipeline:

- `validate_generated_inputs()` và `validate_input_literal()` ở shared contract.

Chỗ gọi validation được đánh dấu `# VALIDATION START: ...` và
`# VALIDATION END: ...`. API arguments, budgets/cache identity và reference checks
cũng có block markers để dễ đọc. Đây là refactor cách tổ chức, không tắt checks.

## Checkpoint và replay

`generate_task_inputs` dùng input checkpoint khi resume/replay. Read-only mode
không gọi generator, model hoặc sandbox nếu thiếu artifact. Manifest ghi generator
class/config/source, runtime, task/spec/domain metadata và settings. Replay dùng
`modular_manifest.json` và `modular_summary.json`, không fallback sang
`manifest.json`/`summary.json` cũ.
Đổi source hoặc configuration cần output directory mới; historical artifacts
không được migrate hay ghi đè.

Optional input annotation là `guidance_id`. Frozen-input rescore giữ nguyên mọi
record đã lưu, kể cả annotation của schema trước. Source và executor identity mới
khiến execution cache cũ chỉ được reuse nếu toàn bộ key vẫn khớp.

Rescore dùng `FrozenInputsGenerator` như saved-input reader (tên class giữ cho caller cũ), không verify source/input hash hay budget generation. `methods_for_rescore` chỉ giữ labels và configuration, không khởi tạo implementation của arm cũ. Xem phần saved evaluation trong README modular.
