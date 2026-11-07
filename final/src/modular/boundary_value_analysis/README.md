# Boundary value analysis — soft BVA

Arm `boundary` dùng soft BVA làm flow chính từ 2026-11-07, theo quyết định của user.
Một completion cho mỗi PUT được cấp budget, output trực tiếp concrete inputs.

```text
spec + domain contract + một PUT + existing base calls
  → soft BVA guidance
  → JSON named arguments
  → CallBuilder encode và deduplicate
  → freeze toàn bộ task inputs
  → shared reference/domain checks → PUT evaluation
```

Spec và contract định nghĩa correct behavior. PUT là nguồn tìm test locations.
Guidance nhắc below/at/above, zero/sign, empty/singleton, integer crossings và
context để khác biệt ảnh hưởng kết quả. Model vẫn được sinh các test hữu ích khác.
Không có selection API, template eligibility gate, worksheet hay target compiler.

## Files

| File | Trách nhiệm |
|---|---|
| `prompts.py` | Soft guidance và single-PUT packet |
| `pipeline.py` | Settings, một completion, context budget, identity/checkpoint/lock |
| `inputs.py` | Strict JSON decoder và shared CallBuilder |
| `../arms/boundary.py` | Chia task input budget, gộp input và accounting |
| `legacy/` | Typed selection/context/compiler, literal mode, checked grounding |

Default settings:20inputs,2048completion tokens,8192context tokens,temperature0.7,
seed314159+task,tối đa12base calls. Với20inputs, request messages và decoder khớp
byte-for-byte/hành vi với arm `soft_bva` trong prompt-style diagnostic.

Khi có nhiều visible PUT, arm chia tổng task input budget đều giữa các PUT, giữ
thứ tự visibility hiện có. Nếu budget nhỏ hơn số PUT, các PUT còn lại có status
`input_budget_exhausted`. Share không dùng hết không được phân phối lại. Mỗi PUT
được cấp share có tối đa một completion; multi-PUT flow chưa được kiểm chứng bằng
diagnostic10task,mỗi task chỉ có một PUT.

Output phải là `{"inputs":[{"arguments":{"parameter_name":value}}]}`.
Truncated response, sai envelope hoặc vượt budget bị từ chối, không repair/retry
semantic. Model values chỉ được encode, không tự điều chỉnh target. Domain checks
và base-duplicate filtering vẫn do shared oracle thực hiện sau freeze.

## Chạy

```bash
final/.venv/bin/python -m final.src.modular.run --mode run \
  --cohort <cohort.json> --artifacts <new-output-directory> \
  --arms boundary --target-programs 1 --input-budget 20
```

Giữ tên CLI `boundary`; `plain` vẫn là control hiện có. Import API:

```python
from final.src.modular.boundary_value_analysis import BoundarySettings, BoundaryValueAnalysis

analysis = BoundaryValueAnalysis(BoundarySettings(input_budget=20))
result = analysis.run_for_program(
    task, program, contract=metadata["contract"], artifacts=artifacts, calls=calls,
)
```

Artifacts mới ở `tasks/<task>/boundary/soft_bva/<program>/`; call key
`bva_<program>_soft_inputs`. Identity chứa packet,settings,model,source hashes.
Read-only replay chỉ đọc checkpoint, không tokenize hoặc gọi model. Đổi source/
settings cần output directory mới; không migrate hay sửa manifest/results cũ.
Frozen-input rescore chọn accounting đúng theo protocol trong manifest cũ.

## Legacy và bằng chứng

Flow cũ chỉ còn dưới [legacy/](legacy/README.md), dùng explicit imports:

```python
from final.src.modular.boundary_value_analysis.legacy import BoundarySettings, BoundaryValueAnalysis
from final.src.modular.boundary_value_analysis.legacy.arm import BoundaryArm
```

`--arms boundary` không chọn flow legacy. Các audits/tests của flow cũ import
legacy tường minh; không tự fallback từ soft sang legacy.

Diagnostic10known-bug PUT:soft7/direct6/worksheet7. Đây là tập outcome-selected đã
dùng trong development,mỗi task/arm có một response; quyết định dùng soft là lựa
chọn engineering của user,chưa chứng minh superiority tổng quát. Xem
[input analysis](../../../review/boundary_soft_vs_direct_inputs_2026-11-07.md).
Offline promotion kiểm exact request/decoder parity cho cả10saved soft responses,
không gọi model hay chạy PUT mới.
