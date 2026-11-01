# Pipeline theo class và module

Đây là entry point dễ đọc/mở rộng cho `final/`. Bản v1/recovery vừa chạy xong vẫn
được giữ nguyên source và kết quả để làm mốc đối chiếu. Không cần sinh lại PUT.

Đã qua **15 engineering checks**, review độc lập và replay đủ **164 task** khớp
toàn bộ kết quả cũ. Xem [VALIDATION.md](VALIDATION.md).

## Mỗi loại chạy là một module

| Module | Class | Trách nhiệm |
|---|---|---|
| `arms/plain.py` | `PlainArm` | Sinh input không thêm guidance |
| `arms/classical.py` | `ClassicalArm` | Boundary, partition, CFG, def-use |
| `arms/contrastive.py` | `ContrastiveArm` | Khác biệt giữa các PUT pass base |
| `arms/placebo.py` | `PlaceboArm` | Covered facts làm control |
| `arms/toolinput.py` | `ToolInputArm` | Gợi ý input từ sampler |
| `arms/witness_only.py` | `WitnessOnlyArm` | Dùng witness trực tiếp, không gọi model |

`ExperimentArm` quy định `build_guidance()` và `run()`. Cơ chế gọi model/parse
response dùng chung; không có chuỗi `if arm == ...` để dispatch từng loại chạy.
Muốn thêm arm: tạo subclass/module mới và truyền instance vào `BenchmarkPipeline`.
`arms/__init__.py` chỉ liệt kê các arm mặc định và lựa chọn cho CLI.

## Mỗi stage là một class

| Module trong `stages/` | Class | Đầu ra chính |
|---|---|---|
| `program_generation.py` | `ProgramGenerationStage` | Chương trình khác cấu trúc; chỉ khi chủ động tạo cohort mới |
| `base_tests.py` | `BaseTestFilterStage` | Base outcomes và cohort task |
| `frozen_cohort.py` | `FrozenCohortStage` | Nạp cohort đã có, không sinh lại |
| `concept_analysis.py` | `ConceptAnalysisStage` | Concept cards, code visibility, common prompt |
| `witness_sampling.py` | `WitnessSamplingStage` | Input pool và valid witnesses |
| `input_generation.py` | `InputGenerationStage` | Input cho các arm đã chọn |
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

Mỗi stage có `name`, `requires` và `run(context)`. Tên class và biến mô tả đầy đủ
trách nhiệm; không dùng các biến `a/b`, `da/db`, `fn/ns` trong code mới.

## Thêm pipe mà không sửa orchestrator

```python
from final.modular.stages.base import PipelineStage


class ConceptQualityStage(PipelineStage):
    name = "concept_quality"
    requires = ("concept_analysis",)

    def run(self, context):
        if context.packet.get("skip"):
            return
        cards = context.packet["analysis"]["classical"]
        context.extensions["concept_card_count"] = len(cards)


pipeline.insert_stage(ConceptQualityStage(), after="concept_analysis")
```

Thứ tự thiếu dependency hoặc trùng tên bị từ chối. Stage có cấu hình riêng phải
override `configuration()` để manifest nhận biết thay đổi. Arm có tham số riêng
cũng phải làm tương tự. Đổi stage/arm/config/model/metadata/task source thì dùng
output directory mới; frozen cohort tiếp tục được dùng lại.

## Chạy và track

Mặc định **replay chỉ đọc**, không tạo model và không chạy lại PUT:

```bash
final/.venv/bin/python -m final.modular.run
final/.venv/bin/python -m pytest final/modular/tests -q
```

Replay tái dựng prompt, parse lại response đã lưu, xác minh input/oracle/outcome và
toàn bộ summary kể cả accounting. Cache thiếu hoặc khác kết quả thì báo lỗi; không
tự gọi API hoặc execute thay thế. Original source/contracts/dependencies được kiểm
tra trước khi replay. Các artifacts cũ không bị ghi đè.

Để bắt đầu một run mới khi đã cấu hình backend, phải nêu rõ `--mode run` và thư mục
mới; ví dụ chỉ chạy hai arm:

```bash
final/.venv/bin/python -m final.modular.run --mode run \
  --artifacts final/out/modular_comparison --arms plain classical
```

CLI dùng adapter Qwen đã review. Python API nhận bất kỳ implementation `ModelCalls`
nào; `CoreModel` vẫn là interface backend ở `final/core_model.py`. Chọn arm khác là
cấu hình run khác, không sửa hay ghi đè kết quả của run vừa xong.

`pipeline.stage_events` chứa `task_id`, `stage`, `state` để track từng pipe. Run
thường ghi thêm `stage_events.jsonl`; replay chỉ giữ events trong memory.
`modular_manifest.json` khóa class/config/source/model/tasks/metadata/environment;
`generation_frozen.json` khóa input; `modular_summary.json` và `REPORT.md` là kết quả.
Chưa commit/push bản refactor này theo yêu cầu giữ pipeline mới ở local.

Chạy `--arms witness_only` không tạo model hay gọi tokenizer. Core analysis/sampler
và reference/PUT evaluation vẫn chạy trên CPU khi đây là một run mới.
