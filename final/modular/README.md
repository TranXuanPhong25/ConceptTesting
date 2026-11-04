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
| `arms/v11_concept.py` | `V11ConceptArm` | Concept v11, generator inputs-only của bản mới |

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
| `v11_concept.py` | `V11ConceptStage` | Chỉ B5 mining và facts/top3/spec fallback của v11 |
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

## Concept v11 + generator của bản mới

User đổi workflow: sửa trên code hiện có, không copy thêm folder version và
không commit trước khi user review. Arm mới được thêm ngay trong `final/modular/`:

`frozen PUTs → V11 concept extraction → common prompt + concept cards →
1 call/task sinh inputs-only → freeze toàn bộ inputs → reference → tất cả PUT pass base`.

V11 chỉ cung cấp B5 mining, coverage/mutation/fuzz facts, ranking/G-prime và spec
fallback qua đúng kernels gốc. Không chạy V11 round1, hybrid, assertions, expected
output hay retry sinh test. `V11ConceptArm` kế thừa nguyên `ConceptArm.run()` nên
cùng prompt nền, parser, seed, temperature, input/output budget và oracle với các
arm mới. Guidance chỉ có id/kind/text; không truyền witness, tool input, mutant
source, strategy code hoặc output của reference. Các arm mặc định vẫn là sáu arm
cũ để replay không thay đổi; chọn `v11_concept` một cách tường minh.

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
  --artifacts final/out/v11_concept_inputs --arms plain v11_concept
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
