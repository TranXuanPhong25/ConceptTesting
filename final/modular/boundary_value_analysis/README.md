# BoundaryValueAnalysis

Module riêng trong code hiện có, theo flow user yêu cầu ngày 2026-11-04:

```text
saved input calls + PUT/task signature
  → InputTypeExtraction
  → BoundaryTemplates
  → BoundarySelection (LLM lần 1)
  → BoundaryInputGeneration (LLM lần 2)
  → literal inputs + boundary evidence
```

Mỗi bước là một class với `run(context)`. `BoundaryValueAnalysis` điều phối,
lưu checkpoint và thực hiện skip. Public API: `extract`, `run`, `run_for_program`.
Module hoạt động độc lập theo từng PUT và đã có adapter `BoundaryArm` trong
pipeline chính, chọn bằng `--arms boundary`; không bật trong default arms.
Không cần CFG/DFG, mutation, fuzzing hoặc chạy PUT để trích type.
Core mới nhận injected generator; `MethodInputGenerator([BoundaryArm()])` nối
module vào cùng contract sinh input như mọi phương pháp khác, không có concept
mining/witness stages ban đầu. Xem [injection API](../generators/README.md).

## Type và templates

- Đọc concrete types từ `base_inputs`: `args`/`kwargs` là Python literal strings,
  hoặc `bound` là mapping parameter→literal string như cached base calls hiện tại.
  Nếu có cả hai thì bind args/kwargs vào PUT signature; tránh sai tên khi PUT đổi
  parameter name so với task signature.
- Bổ sung annotations từ PUT và task specification, giữ provenance riêng.
  Không import PUT, không evaluate annotations/default expressions bằng `eval`.
  Unknown type giữ unknown. Observed values không được biến thành semantic range.
- V1 có scalar numeric value, collection/string length, numeric list/tuple elements
  và numeric list/tuple sum. Model có thể chọn threshold là constant hoặc scalar/
  length/sum của parameter khác, ví dụ `sum(xs)=limit` hoặc `index=len(xs)`.
- Boolean-only, unknown/custom types không tạo numeric boundary candidate.
  Nested element paths, custom arithmetic, date objects và enum-specific order
  chưa hỗ trợ. Collection chứa type chưa hỗ trợ vẫn có length candidate.

## Hai bước LLM

Selection nhận specification, contract, PUT, type evidence và candidate templates.
Nó chọn characteristic, threshold, comparison, boundary kind, neighborhood,
target sides và constraints có source quotes. Có thể trả `no_boundary` với reason.

Schema validation kiểm template/parameter references, nonempty quotes thực sự
có trong spec/contract, numeric thresholds/steps, allowed sides và literal shape.
Quote tồn tại **không chứng minh semantic entailment**; selection được ghi rõ là
`llm_proposed_with_verified_quote_not_entailment_proof`.

Generation chỉ nhận selected boundaries và domains cùng templates. Model trả
`args`, `kwargs`, `boundary_id`, `side`; không sinh expected outputs/assertions.
Validator bind signature, kiểm finite supported literals, tính characteristic và
threshold trên chính input đó, kiểm đúng declared neighbor/side và loại duplicates.
`elements` cần ít nhất một element đạt target; `sum` dùng Python arithmetic.

`step` được tính theo Python arithmetic; `float_adjacent` dùng `math.nextafter`.
Nếu rounding làm neighbor trùng threshold hoặc nonfinite thì reject. Không dùng
tolerance tùy tiện để nhận một input không thực sự chạm target.

Constraints bằng prose vẫn là LLM proposals, **chưa được execute/verify**. Output
ghi `domain_constraints: unverified`, `oracle: not_run`. Cần external contract/
reference validation trước khi gọi input là valid test hoặc chấm bug detection.
V1 chỉ cho normal domain-boundary sides; input ngoài precondition không được đưa
vào chỉ vì muốn thêm robustness case. Behavior boundaries có thể xét hai phía.

## Skip, budget và cache

| Status | Ý nghĩa / số LLM calls |
|---|---|
| `unsupported_signature` | Signature chưa hỗ trợ; 0 calls |
| `no_templates` | Không có family hỗ trợ từ type evidence; 0 calls |
| `no_boundary` | LLM không chọn được boundary; 1 call, không sinh input |
| `invalid_selection` | JSON/schema/provenance invalid; 1 call, không giả làm no-boundary |
| `prompt_too_large` | Dừng trước request không vừa context; 0 hoặc 1 call trước đó |
| `invalid_generation` | Response sinh input malformed/truncated; 2 calls |
| `no_inputs` | Không sinh/không giữ được input; 2 calls, không claim infeasible |
| `generated` | Có input đã qua signature/target checks; 2 calls |

Default tối đa4boundaries,20input records,2048completion tokens cho mỗi call,
context8192, selection temperature0 và generation temperature0.7. Không có model
retry/fallback ở module này; transport adapter giữ retry policy riêng của nó.
Prompt generation hiển thị tối đa12base calls đầu tiên; duplicate validation vẫn
so với toàn bộ base calls. Type evidence được gộp theo type, giữ observation count
và tối đa8example indices. Không dùng observed extrema làm threshold.

Artifact ở `tasks/<task_number>/boundary/<program_id>/`: identity, input_types,
templates, select/inputs prompts, selection, generation, result. Identity ràng buộc
source/spec/contract/base inputs/settings/model và module source hashes; mismatch
fail trước inference. Calls dùng keys `bva_<program_id>_select` và
`bva_<program_id>_inputs`, tương thích `RecoveryModelCalls` và token accounting.
Lock riêng cho từng PUT ngăn hai controller chạy cùng checkpoint.

Transport failure propagate, giữ selection đã hoàn thành để resume ở generation;
không chuyển API failure thành skip. Read-only replay cần đầy đủ stage artifacts,
không tokenize/gọi model/chạy PUT. Dùng output directory riêng cho protocol này;
không ghi vào completed runs hoặc checkpoint của arm khác.

## Sử dụng

Chỉ inspect candidates offline:

```python
from final.modular.boundary_value_analysis import BoundaryValueAnalysis

analysis = BoundaryValueAnalysis()
candidates = analysis.extract(
    specification=task["prompt"],
    entry_point=task["entry_point"],
    program_source=program["code"],
    base_inputs=program["base"]["calls"],
    contract=metadata["contract"],
)
```

Chạy hai bước LLM khi backend/run đã được cấu hình:

```python
from pathlib import Path
from final.modular.artifacts import ArtifactStore
from final.modular.calls import RecoveryModelCalls
from final.modular.boundary_value_analysis import BoundarySettings, BoundaryValueAnalysis

artifacts = ArtifactStore(Path("final/out/boundary_development"))
calls = RecoveryModelCalls(model, artifacts)  # model dùng backend/env hiện có
analysis = BoundaryValueAnalysis(BoundarySettings(input_budget=12))
result = analysis.run_for_program(
    task, program, contract=metadata["contract"], artifacts=artifacts, calls=calls,
)
```

Adapter chỉ lấy prompt/entry point, PUT source và saved base inputs; không đọc
canonical solution/plus inputs/base expected outputs. Nó không tự tạo PUT,
không chạy reference và không tự launch benchmark. Inputs có thể đưa vào bước
reference validation hiện có sau khi freeze toàn bộ generation của run.
Budget của API này là **per PUT**. Adapter `BoundaryArm` đã chia total task budget
cho các visible PUT có template, gộp/deduplicate inputs rồi dùng reference oracle
và PUT evaluation của pipeline chính. Mỗi allocated PUT có tối đa2logical calls;
không gọi đây là one-call/task arm. Xem [pipeline usage](../README.md#boundaryvalueanalysis)
cho CLI chạy smoke subset và cách giữ các arm khác trong cùng run.

## Verification

Engineering fixtures dùng scripted model responses, không phải mô phỏng paper.
Kiểm early exits, source provenance, malformed/truncated responses, relational/
float targets, literal safety, duplicates, transport resume và immutable replay.
Chạy: `final/.venv/bin/python -m pytest final/modular/tests/test_boundary_value_analysis.py -q`.

Module41checks + integration11checks; toàn bộ modular regression suite85checks
pass. Integration dùng scripted responses và tiny synthetic programs để kiểm
generation freeze, real sandbox reference/evaluation, checkpoint resume/replay,
task budget và báo cáo skip. Chưa chạy live model hoặc benchmark cohort.

Sau refactor dependency inversion: full suite93checks pass. Các validation được
tách thành `validate_response`, `validate_input`, `validate_task_input` và shared
`validate_generated_inputs`/`validate_input_literal`; chỗ gọi có comment blocks
`VALIDATION START`/`VALIDATION END`. API/cache/budget/reference checks có markers.

Xem [research basis](../../review/boundary_applicability_2026-11-04.md).
