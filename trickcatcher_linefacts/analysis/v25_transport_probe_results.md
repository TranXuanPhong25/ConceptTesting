# v25 delayed transport probe — endpoint offline (2026-10-17)

Probe chạy đúng lịch21:08:06Vietnam/14:08:06UTC và dừng ở metadata preflight:
**GET /v1/models → HTTP404, ERR_NGROK_3200**. Ngrok error body báo endpoint offline.
Không có tokenizer/plain/guided request nào. Vì vậy không diễn ra paired comparison
hay semantic/schema test. Không retry, reset attempts, sửa frozen utility/run cũ,
chạy diagnostic5 hoặc gửi thêm network/model calls trong terminal audit.

## Actual evidence và latency

|Stage|Attempt|Kết quả|Latency|
|---|---:|---|---:|
|Models metadata|1|HTTP404; ngrok endpoint offline|0.217735796s|
|Pinned Qwen model/context|0 verified|Blocked vì không có model-list JSON|NA|
|Tokenizer|0|Blocked preflight|NA|
|Plain metadata completion|0|Blocked preflight|NA|
|Guided metadata completion|0|Blocked preflight|NA|

Scheduled due14:08:06; status started14:08:06.051909UTC, delay0.051909s. Terminal
status preflight_failed/ValueError lúc14:08:06.271434UTC, wall0.219525s. Frozen decode
raises transport_unavailable khi metadata record không received; đây là gateway
HTTP error, không phải tokenizer/model schema hoặc JSON/usage mismatch.

Body2,374bytes, không truncated; recorded original body SHA có trong analysis JSON.
Unredacted body không được giữ đầy đủ vì privacy redaction, nên không thể independently
reconstruct original-body SHA từ sanitized text. Hash của toàn bộ persisted record
được tính lại ở analysis time. Chỉ trích safe excerpt:
"The endpoint <redacted-host> is offline. (ERR_NGROK_3200)".

## Usage và coverage

- 1 HTTP request, metadata GET only.0 completion attempts,0 model responses,0 model
usage reports,0 PUT/predicate workers. Không có unknown-usage completion attempt trong
probe này. Models artifact dùng generic state http_error_usage_unknown; tên state đó
không có nghĩa đã gửi completion hoặc phát sinh unknown generation usage.
- Planned cap2 completions/1attempt mỗi slot và max2metadata không bị vượt.2 completion
slots chưa dùng không phải failed model outputs. results.json/plain/guided artifacts
không được tạo vì preflight đã dừng.
- Không có fresh echo, schema satisfaction, code envelope, contract, hypothesis hay
input để đánh giá. Không lấy prior capability echo làm kết quả probe này.8 unknown-usage
completion attempts của diagnostic5 cũ vẫn riêng biệt, không reset hay recredit.

Endpoint offline là điều ngrok thông báo tại timestamp trên; không có server logs để
xác định vì sao tunnel/upstream ngừng hoạt động. Không thể kết luận GPU crash, model
hang hay guided decoder lỗi. Cả plain và guided đều chưa chạy; kể cả một paired run thành
công trong fixed sequential order cũng chịu confounding từ thời điểm/load/warmup.

## Frozen integrity, privacy và independent review

Read-only verifier đối chiếu script SHA với frozen probe protocol, exact old f02
payloads (chỉ khác guided_json),74 v25 source hashes, prepared-data hash, old snapshot
identity và770 artifact hashes. Original diagnostic5 transport/status/report hashes
cũng khớp analysis-time audit trước đó. Không sửa original artifacts, utility hoặc
source; no calls/workers trong audit. New analysis-time hashes của probe records
không được mô tả là một original completion-output freeze.

Clean-context v25_probe_audit independently xác nhận kết quả/coverage/cost limits và
integrity. Audit phát hiện frozen redactor bỏ sót hostname không có scheme trong ngrok
HTML. Không copy body/hostname vào analysis hay tracked files; originals giữ nguyên
đúng yêu cầu. Root đã vô tình hiển thị hostname khi kiểm tra body; không lặp lại trong
analysis. Future hardening cần xử lý bare hostname, nhưng không repair frozen utility
hoặc reset run này. Không link trực tiếp error-body artifact.

**Disposition:** callback handled, probe completed its bounded preflight and endpoint
was unavailable. No diagnostic5/full comparison/benchmark/paid/new calls tự động.
Cần endpoint online trở lại hoặc endpoint mới trước một lần thử được authorize riêng.
[Read-only verifier](v25_transport_probe_results.py),
[sanitized evidence JSON](v25_transport_probe_results.json).
