# LangChain completion migration

Theo yêu cầu user sau feasibility probe, `QwenModel.generate_prepared()` hiện dùng
LangChain `ChatOpenAI` và OpenAI SDK để serialize request và decode SSE.
Không còn parser SSE/JSON completion tự viết. `/models`, `/tokenize`, model pinning,
refresh configuration và context/output budget giữ trong runtime.

Adapter giữ các policy hiện tại:

- Require finish reason và nonempty text; giữ partial text nếu stream fail.
- Accept text đã finish nếu usage footer bị timeout hoặc malformed.
- SDK `max_retries=0`: checkpoint tiếp tục sở hữu completion retry/accounting.
- Sanitized TransportError với HTTP status/retryable/completion_started.
- Bound wire response 16 MiB và elapsed deadline 1800s, gồm cả SSE comments.
- Không export tracing; đóng stream và HTTP client sau mỗi invocation.

`_QwenChatOpenAI` chỉ override decoded-chunk conversion để filter choice index=0,
validate content và chuyển raw provider usage vào chunk metadata. LangChain vẫn
phụ trách message/request conversion; OpenAI SDK phụ trách HTTP và SSE decoding.
Nhờ hook này, field riêng của provider cũng được giữ, không cần map usage ngược
từ `usage_metadata`. SDK có thể thêm optional fields giá trị null; token counts,
reasoning details và unknown provider fields trong fixtures vẫn được giữ.

Đây là một private hook được cover bởi transport regression tests. Dependency
versions pin trong `final/src/runtime/requirements.txt`: langchain-openai 1.6.2,
langchain-core 1.6.3, openai 3.41.0, httpx 0.28.1. Đã cài vào `final/.venv`.
New manifests ghi thêm versions này; không sửa manifest/checkpoint cũ.

## Verification

Full current suite trong `final/.venv`: **258 passed**. Root `.venv` thiếu các
dependency của pipeline (`evalplus`, `python_graphs`), nên kết quả verification
chính dùng environment được ghi trong runbook.

Transport suite: 26 tests pass. HTTP fixtures chạy qua LangChain/OpenAI SDK thật,
không mock output chunks. Bao gồm serialized JSON/headers, usage/custom fields,
EOF thiếu finish, empty output, timeout/protocol failure trước/sau finish, deadline,
byte cap, HTTP 401/429/503 không retry ngầm, malformed JSON, choice index và
multiline SSE/CRLF. HTTP body bị chia thành các đoạn 3 bytes.

Probe riêng: 12 fixtures, 12 executable checks pass. Evidence:
[JSON](langchain_adapter_2026-11-05.json). Command:

```bash
final/.venv/bin/python -m final.src.audits.probe_langchain_transport \
  --output final/review/langchain_adapter_2026-11-05.json
final/.venv/bin/python -m pytest -q final/src/modular/tests final/tests
```

Không có remote model/tokenizer calls hoặc benchmark inference; không sửa các
artifacts cũ. Các khác biệt protocol có chủ ý: SDK decode đúng multiline SSE và
raise explicit API error cho SSE error event. Chưa kiểm chứng inference trên live
vLLM endpoint.

## Subsequent live smoke, user-authorized

2026-11-05 16:21 UTC: `/models` xác nhận `qwen3.5-27b-awq`, context 8192.
`/tokenize` trả 42 prompt tokens. Một completion qua active LangChain adapter
trả đúng `{"ok":true,"message":"Tiếng Việt"}`, finish=`stop`, usage footer đầy đủ:
42 prompt + 12 completion = 54 tokens. Tổng thời gian 2.885s, không có transport
hoặc SSE decode error. Evidence: [JSON](langchain_live_smoke_2026-11-05.json).
Không chạy benchmark; endpoint chỉ truyền qua process environment, không lưu URL.
