# LangChain thay được phần nào của model.py?

Historical feasibility report trước migration. User sau đó đã yêu cầu thay backend;
xem [migration](langchain_adapter_2026-11-05.md) cho implementation hiện tại.
JSON bên dưới giữ nguyên baseline cũ; probe source hiện so sánh runtime adapter với
plain ChatOpenAI và ghi ra `langchain_adapter_2026-11-05.json`.

Đã thử `ChatOpenAI.stream()` thật qua `httpx.MockTransport`, so sánh với
`final/src/runtime/model.py`. **LangChain có thể thay phần serialize completion
request và decode SSE. Chưa thể thay toàn bộ QwenModel bằng một ChatOpenAI call
mà giữ nguyên behavior.** Active backend hiện vẫn giữ nguyên.

Scope: engineering fixtures offline; 0 remote/model/benchmark calls. Không đọc
endpoint file, không dùng API key thật, không sửa checkpoint hay output của run.
LangChain tracing bị tắt trong probe. Đây không phải inference test với vLLM.

## Cách chạy lại

```bash
final/.venv/bin/python -m final.src.audits.probe_langchain_transport \
  --output final/review/langchain_adapter_2026-11-05.json
```

Source: [probe](../src/audits/probe_langchain_transport.py).
Evidence: [JSON](langchain_transport_2026-11-05.json).
Versions: langchain-openai 1.6.2, langchain-core 1.6.3, openai 3.14.0, httpx 0.28.1.

## Serialize

Default `ChatOpenAI(max_tokens=32)` gửi `max_completion_tokens=32`.
Dùng public config sau để request JSON bằng request hiện tại:

```python
model = ChatOpenAI(
    model=expected_model,
    base_url=base_url,
    api_key=api_key or "EMPTY",
    max_retries=0,
    timeout=180,
    temperature=temperature,
    seed=seed,
    stream_usage=True,
    use_responses_api=False,
    default_headers={"ngrok-skip-browser-warning": "1"},
    extra_body={
        "max_tokens": prepared.output_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    },
)
for chunk in model.stream(prepared.messages):
    ...  # adapter collects text, finish_reason and usage
```

Probe xác nhận equality của parsed JSON gồm messages/system/user/Unicode,
model, temperature, seed, max_tokens, stream, stream_options và
chat_template_kwargs. Không cần dùng private LangChain API. JSON equality
không có nghĩa serialized bytes giống hệt. Header trong snippet được cấu hình;
probe không dùng nó để claim header equivalence với urllib.

## Decode SSE và behavior

LangChain dùng OpenAI SDK để parse SSE, rồi đổi event thành `AIMessageChunk`.
Probe chia HTTP body mỗi 3 bytes để kiểm tra cả UTF-8 và SSE boundary.

| Fixture | QwenModel hiện tại | ChatOpenAI.stream() |
| --- | --- | --- |
| Text + finish + usage | Nhận đủ | Text/finish/token counts bằng nhau |
| EOF thiếu finish | Reject, giữ partial text | Kết thúc bình thường, trả partial chunks |
| Timeout trước finish | Reject, giữ partial text | Raise, đã yield partial chunks |
| Timeout sau finish | Accept, thiếu usage footer | Raise, đã yield finish |
| Text rỗng có finish | Reject | Kết thúc bình thường |
| Malformed JSON trước finish | Reject | Raise |
| Malformed JSON sau finish | Accept text đã xong | Raise |
| CRLF | Accept | Accept |
| Multiline SSE data | Reject | Decode đúng SSE, accept |
| Chỉ có choice index=1 | Ignore, reject | Dùng choice đầu tiên, accept |
| SSE error event | Reject thành IncompleteStream | Raise APIError |
| HTTP 503 | Sanitized TransportError | OpenAIAPIError; 1 request khi max_retries=0 |

7 executable checks pass: normal text, finish, compatible request JSON, token
counts, không retry ngầm trên toàn bộ 12 case, partial text trước timeout,
và finish đã được yield trước footer timeout.

`usage_metadata` dùng `input_tokens`/`output_tokens`, thay vì
`prompt_tokens`/`completion_tokens`. `reasoning_tokens` đổi thành
`output_token_details.reasoning`; fixture `provider_extra=7` bị mất. Có thể map
các token count chuẩn về format hiện tại, nhưng public chunk API trong phiên bản
đã thử không bảo toàn toàn bộ raw provider usage. Probe chỉ apply lại policy
finish/nonempty để so sánh; đó chưa phải một production adapter và chưa xử lý
choice index hay resource limit.

## Khuyến nghị

Thay completion serialization/SSE parsing bằng library là khả thi. Cần giữ một
adapter nhỏ thuộc runtime để:

- Require finish + nonempty text; giữ partial text khi failure; accept completed
  output nếu chỉ mất footer.
- Map usage và quyết định có cần bảo toàn raw provider fields; tắt SDK retries
  để checkpoint là nơi duy nhất quản lý completion retry.
- Sanitize exceptions, map HTTP status/retryable/completion_started.
- Giữ deadline 1800s, response cap 16 MiB và lựa chọn choice index=0.
- Giữ refresh configuration/model pinning, `/models`, `/tokenize`, context budget
  và tokenizer retry. `ChatOpenAI` không cung cấp vLLM `/tokenize` này.

Nếu cần giữ raw usage/choice index và kiểm tra byte limit, dùng trực tiếp OpenAI
SDK dưới adapter sẽ hợp hơn public LangChain chunk API: SDK cũng đã phụ trách SSE
cho LangChain. Đây là hướng đề xuất từ code inspection; chưa có probe riêng để
claim SDK adapter tương đương toàn bộ runtime.

Chưa chuyển active backend: probe đã chỉ ra các khác biệt ảnh hưởng acceptance và
accounting, nên không thể claim drop-in equivalence. Không có kết luận về tốc độ,
memory footprint hay output model thực tế từ fixture test này.

## Verification

Probe hoàn tất 12 fixtures/7 checks. Existing targeted suite: 16 passed, 1 failed.
Failure ở `test_current_modules_import_with_historical_packages_blocked`: `.venv`
thiếu dependency `python_graphs` khi import `development_groups.py`, trước khi
chạy transport. Không sửa dependency/code ngoài scope của probe.
