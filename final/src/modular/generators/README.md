# Batch input generation

CLI và Prefect chọn các arm có sẵn. Plain, EP/BVA VF3, DT VF3, ControlFlow và CF Obligation chạy qua batch generation. Tool sampling và Pynguin nhận cấu hình từ entry point tương ứng. Rescore đọc các batch đã lưu.

Pipeline chuẩn bị context, chốt input cho tất cả task rồi chạy reference oracle. Catalogue measurement chạy cho VF3 trước khi chấm PUT. Tool sampling có thêm audit sau khi chấm.

## Output contract và validation

Mỗi input có `args` là literal list/tuple string, `kwargs` là literal dict string.
Có thể kèm `guidance_id`, boundary evidence hoặc dữ liệu provenance khác. Method
không tạo được input trả `inputs: []` và reason/status; nếu cả task bị bỏ qua thì
generator trả `{"task_id": "...", "skip": "reason"}` thay cho `arms`.

`input_contract.validate_generated_inputs()` kiểm task ID và tên arm trước khi lưu `inputs.json`.
Arm áp input budget khi sinh. Reference oracle kiểm literal, kiểu và contract trên input đã chốt.

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
`# VALIDATION END: ...`. API arguments, budgets và reference checks
cũng có block markers để dễ đọc. Đây là refactor cách tổ chức, không tắt checks.

## Checkpoint và replay

Resume dùng lại `inputs.json` và request/response đã lưu. Manifest ghi task ID,
arm, settings và runtime. Replay đọc `result.json` và đối chiếu `modular_summary.json` khi có.
Đổi source hoặc configuration cần output directory mới; historical artifacts
không được migrate hay ghi đè.

Optional input annotation là `guidance_id`. Frozen-input rescore giữ nguyên mọi
record đã lưu, kể cả annotation của schema trước.

Rescore dùng `FrozenInputsGenerator` như saved-input reader (tên class giữ cho caller cũ), không verify source/input hash hay budget generation. `methods_for_rescore` chỉ giữ labels và configuration, không khởi tạo implementation của arm cũ. Xem phần saved evaluation trong README modular.
