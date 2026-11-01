# Tiếp tục run với transport ổn định hơn

Đây là bản sửa kết nối cho experiment v1 đang dừng tại task16/classical. Giữ nguyên
cohort, prompts, seed, input budget, concept extraction và reference oracle.

Đã import18task inputs và91response từ run cũ, kiểm tra hash. Không sinh lại PUT.
Model trả token qua streaming; request lỗi được giữ lại và retry có giới hạn.
Số lần retry không reset khi restart. Partial output không được dùng làm test.
Log ghi rõ operation/HTTP status/error type, không ghi URL hoặc key.

Theo yêu cầu user, scheduler thử lại sớm nhất lúc **13:38:15 ngày31/10, giờ Việt Nam**.
Scheduler chỉ launch sau khi engineering tests và review thông qua, source hashes
khớp và `/models` xác nhận đúng model/context. Endpoint chưa lên thì chỉ poll
metadata mỗi60s, không gửi completion. Endpoint lấy từ env file riêng ngoài repo.

- Scheduler: `final/out/concept_reference_v1_recovery_schedule/status.json`
- Run tiếp: `final/out/concept_reference_v1_recovery/status.json`
- Cohort gốc: `final/out/cohorts/qwen35_27b_humaneval164/cohort.json`
- Import hashes: `final/out/concept_reference_v1_recovery/import_manifest.json`

```bash
final/.venv/bin/python -m pytest final/experiments/concept_reference_v1_recovery/tests -q
```

Không sửa v1 đang frozen hoặc ghi đè output gốc. Xem PREREG.md để đọc thay đổi
transport và accounting của các request chưa nhận được response.
