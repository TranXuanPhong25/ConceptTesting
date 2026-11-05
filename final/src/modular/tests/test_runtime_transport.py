"""Engineering-only transport tests: no remote API calls or benchmark outcomes."""
import io
import http.client
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import httpx

from final.src.core_model import ModelResponse
from final.src.runtime.artifacts import digest, save
from final.src.modular.cohort import call_usage
from final.src.runtime.checkpoint import CheckpointedModelClient, CompletionRetryLimit
from final.src.runtime.model import QwenModel, PreparedGeneration, TransportError


def streaming_event(payload):
    return b"data: " + json.dumps(payload).encode() + b"\n\n"


@pytest.fixture
def transport_model(monkeypatch, tmp_path):
    monkeypatch.setenv("FINAL_BASE_URL", "http://fixture.invalid/v1")
    monkeypatch.setenv("FINAL_MODEL", "fixture")
    monkeypatch.setenv("FINAL_ENDPOINT_ENV_FILE", str(tmp_path / "absent.env"))
    return QwenModel(expected_model="fixture")


@pytest.fixture
def completion_fixture(transport_model, monkeypatch):
    from final.src.runtime.model import _CompletionStream

    def install(pieces, *, failure=None, status=200):
        requests = []
        closed = []

        class FixtureBytes(httpx.SyncByteStream):
            def __iter__(self):
                for piece in pieces:
                    # Split across SSE framing and UTF-8 boundaries.
                    for offset in range(0, len(piece), 3):
                        yield piece[offset:offset + 3]
                if failure:
                    raise failure

            def close(self):
                closed.append(True)

        def factory(started_at):
            def handler(request):
                requests.append(request)
                response = httpx.Response(status, headers={"content-type": "text/event-stream"},
                                          stream=FixtureBytes())
                return response

            def bound_response(response):
                response.stream = _CompletionStream(response.stream, started_at)

            return httpx.Client(transport=httpx.MockTransport(handler),
                                event_hooks={"response": [bound_response]})

        monkeypatch.setattr(transport_model, "_completion_http_client", factory)
        return requests, closed

    return install


def test_streaming_collects_tokens_and_final_usage(transport_model, completion_fixture):
    provider_usage = {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16,
                      "completion_tokens_details": {"reasoning_tokens": 2}, "provider_extra": 7}
    pieces = [
        streaming_event({"choices": [{"delta": {"content": '{"inputs":'}, "finish_reason": None}]}),
        streaming_event({"choices": [{"delta": {"content": '[]}'}, "finish_reason": "stop"}]}),
        streaming_event({"choices": [], "usage": provider_usage}), b"data: [DONE]\n\n",
    ]
    requests, closed = completion_fixture(pieces)
    prepared = PreparedGeneration([{"role": "user", "content": "Việt 🧪"}], 10, 2048)
    result = transport_model.generate_prepared(prepared, temperature=.7, seed=314175)
    assert result.text == '{"inputs":[]}'
    assert result.usage["prompt_tokens"] == 10
    assert result.usage["completion_tokens"] == 6
    assert result.usage["total_tokens"] == 16
    assert result.usage["completion_tokens_details"]["reasoning_tokens"] == 2
    assert result.usage["provider_extra"] == 7
    assert result.usage["tokenizer_prompt_tokens"] == 10
    assert result.usage["requested_output_budget"] == 2048
    assert result.usage["usage_footer_complete"] is True
    assert len(requests) == 1
    assert json.loads(requests[0].content) == {
        "model": "fixture", "messages": prepared.messages, "stream": True,
        "stream_options": {"include_usage": True}, "temperature": .7,
        "seed": 314175, "max_tokens": 2048, "chat_template_kwargs": {"enable_thinking": False}}
    assert requests[0].headers["ngrok-skip-browser-warning"] == "1"
    assert closed


@pytest.mark.parametrize("finish, text", [(None, "partial"), ("stop", "")])
def test_incomplete_stream_is_never_accepted(transport_model, completion_fixture, finish, text):
    completion_fixture([streaming_event({"choices": [{"delta": {"content": text}, "finish_reason": finish}]})])
    with pytest.raises(TransportError) as failure:
        transport_model.generate_prepared(PreparedGeneration([], 10, 2048), temperature=.7, seed=1)
    assert failure.value.error_type == "IncompleteStream"
    assert failure.value.partial_text == text


@pytest.mark.parametrize("finished", [False, True])
@pytest.mark.parametrize("network_error", [httpx.ReadTimeout("private URL/key"),
                                           httpx.RemoteProtocolError("private URL/key")])
def test_stream_failure_before_and_after_finish(transport_model, completion_fixture, finished, network_error):
    requests, closed = completion_fixture([
        streaming_event({"choices": [{"delta": {"content": "text"},
                                      "finish_reason": "stop" if finished else None}]})], failure=network_error)
    prepared = PreparedGeneration([], 10, 2048)
    if finished:
        result = transport_model.generate_prepared(prepared, temperature=.7, seed=1)
        assert result.text == "text"
        assert result.usage["usage_footer_complete"] is False
    else:
        with pytest.raises(TransportError) as failure:
            transport_model.generate_prepared(prepared, temperature=.7, seed=1)
        assert failure.value.partial_text == "text"
        assert "private" not in str(failure.value)
        assert failure.value.completion_started
    assert len(requests) == 1
    assert closed


@pytest.mark.parametrize("finished", [False, True])
def test_generation_deadline_including_comment_footer(transport_model, completion_fixture, monkeypatch, finished):
    import final.src.runtime.model as model_module
    elapsed_seconds = [0]

    def pieces():
        elapsed_seconds[0] = 1
        yield streaming_event({"choices": [{"delta": {"content": "done"},
                                            "finish_reason": "stop" if finished else None}]})
        elapsed_seconds[0] = 1801
        yield b": keepalive\n\n"

    monkeypatch.setattr(model_module, "time", SimpleNamespace(monotonic=lambda: elapsed_seconds[0]))
    completion_fixture(pieces())
    if finished:
        assert transport_model.generate_prepared(PreparedGeneration([], 10, 32), temperature=0, seed=1).text == "done"
    else:
        with pytest.raises(TransportError) as failure:
            transport_model.generate_prepared(PreparedGeneration([], 10, 32), temperature=0, seed=1)
        assert failure.value.error_type == "GenerationDeadline"
        assert failure.value.partial_text == "done"


@pytest.mark.parametrize("status, retryable", [(401, False), (429, True), (503, True)])
def test_http_failure_is_sanitized_without_sdk_retry(transport_model, completion_fixture, status, retryable):
    requests, closed = completion_fixture([b'{"error":{"message":"private URL/key"}}'], status=status)
    with pytest.raises(TransportError) as failure:
        transport_model.generate_prepared(PreparedGeneration([], 10, 32), temperature=0, seed=1)
    assert failure.value.http_status == status
    assert failure.value.retryable is retryable
    assert "private" not in str(failure.value)
    assert len(requests) == 1
    assert closed


def test_nonzero_choice_cannot_supply_output(transport_model, completion_fixture):
    completion_fixture([streaming_event({"choices": [
        {"index": 1, "delta": {"content": "wrong"}, "finish_reason": "stop"}]})])
    with pytest.raises(TransportError) as failure:
        transport_model.generate_prepared(PreparedGeneration([], 10, 32), temperature=0, seed=1)
    assert failure.value.error_type == "IncompleteStream"
    assert failure.value.partial_text == ""


@pytest.mark.parametrize("finished", [False, True])
def test_malformed_json_before_and_after_finish(transport_model, completion_fixture, finished):
    completion_fixture([streaming_event({"choices": [{"delta": {"content": "text"},
                         "finish_reason": "stop" if finished else None}]}), b"data: {bad}\n\n"])
    if finished:
        assert transport_model.generate_prepared(PreparedGeneration([], 10, 32), temperature=0, seed=1).text == "text"
    else:
        with pytest.raises(TransportError) as failure:
            transport_model.generate_prepared(PreparedGeneration([], 10, 32), temperature=0, seed=1)
        assert failure.value.partial_text == "text"


def test_multiline_sse_and_crlf(transport_model, completion_fixture):
    completion_fixture([b'data: {"choices":\r\ndata: [{"index":0,"delta":{"content":"ok"},"finish_reason":"stop"}]}\r\n\r\n'])
    assert transport_model.generate_prepared(PreparedGeneration([], 10, 32), temperature=0, seed=1).text == "ok"


def test_wire_size_guard_counts_comments(monkeypatch):
    from final.src.runtime.model import _CompletionStream
    stream = _CompletionStream(iter([b":" * (16 * 1024 * 1024), b"x"]), 0)
    monkeypatch.setattr("final.src.runtime.model.time.monotonic", lambda: 1)
    iterator = iter(stream)
    assert len(next(iterator)) == 16 * 1024 * 1024
    with pytest.raises(TransportError) as failure:
        next(iterator)
    assert failure.value.error_type == "ResponseTooLarge"


def test_tokenizer_read_failure_retries_without_completion(transport_model, monkeypatch):
    class BrokenRead(io.BytesIO):
        def read(self, *arguments):
            raise http.client.IncompleteRead(b"partial")

    responses = iter([BrokenRead(), io.BytesIO(b'{"count": 27}')])
    operations = []

    def open_fixture(operation, *arguments, **keywords):
        operations.append(operation)
        return next(responses)

    monkeypatch.setattr(transport_model, "request", open_fixture)
    monkeypatch.setattr("final.src.runtime.model.time.sleep", lambda seconds: None)
    assert transport_model.tokens([]) == 27
    assert operations == ["tokenize", "tokenize"]


def test_metadata_read_failure_is_sanitized_transport_error(transport_model, monkeypatch):
    class BrokenRead(io.BytesIO):
        def read(self, *arguments):
            raise http.client.IncompleteRead(b"partial")

    monkeypatch.setattr(transport_model, "request", lambda *args, **kwargs: BrokenRead())
    with pytest.raises(TransportError) as failure:
        transport_model.check_endpoint()
    assert failure.value.operation == "models"
    assert failure.value.retryable


class FixtureTransportModel:
    def __init__(self, failures=0, permanent=False):
        self.failures = failures
        self.permanent = permanent
        self.completion_calls = 0
        self.received_parameters = []

    def prepare_generation(self, messages, max_tokens):
        return PreparedGeneration(messages, 10, max_tokens)

    def generate_prepared(self, prepared, *, temperature, seed):
        self.completion_calls += 1
        self.received_parameters.append((prepared.messages, prepared.output_tokens, temperature, seed))
        if self.completion_calls <= self.failures:
            raise TransportError("completion", "TimeoutError", retryable=not self.permanent,
                                 completion_started=True, partial_text="partial")
        return ModelResponse('{"inputs":[]}', {"total_tokens": 12}, "stop")


QUERY_ARGUMENTS = {"messages": [{"role": "user", "content": "fixture"}],
                   "temperature": .7, "max_tokens": 2048, "seed": 314175}


def test_prior_attempt_retry_preserves_unknown_and_reuses_saved_response(tmp_path, monkeypatch):
    monkeypatch.setattr("final.src.runtime.checkpoint.time.sleep", lambda seconds: None)
    task_directory = tmp_path / "tasks" / "16"
    call_directory = task_directory / "calls" / "plain"
    save(call_directory / "request.json", QUERY_ARGUMENTS)
    save(call_directory / "attempt.json", {"request_id": digest(QUERY_ARGUMENTS), "state": "unknown"})
    model = FixtureTransportModel(failures=1)
    pipeline = CheckpointedModelClient(model)
    result = pipeline.query(task_directory, "plain", **QUERY_ARGUMENTS)
    assert model.completion_calls == 2
    assert model.received_parameters[0] == model.received_parameters[1]
    accounting = call_usage(tmp_path)
    assert accounting["invocations"] == 3
    assert accounting["received"] == 1
    assert accounting["unknown"] == 2
    assert pipeline.query(task_directory, "plain", **QUERY_ARGUMENTS) == result
    assert model.completion_calls == 2
    assert len(list((task_directory / "calls").glob("plain_unknown_attempt_*"))) == 2


def test_completion_retry_limit_persists_across_controller_restarts(tmp_path, monkeypatch):
    monkeypatch.setattr("final.src.runtime.checkpoint.time.sleep", lambda seconds: None)
    model = FixtureTransportModel(failures=10)
    pipeline = CheckpointedModelClient(model)
    task_directory = tmp_path / "tasks" / "16"
    with pytest.raises(CompletionRetryLimit):
        pipeline.query(task_directory, "plain", **QUERY_ARGUMENTS)
    assert model.completion_calls == 3
    with pytest.raises(CompletionRetryLimit):
        pipeline.query(task_directory, "plain", **QUERY_ARGUMENTS)
    assert model.completion_calls == 3
    assert call_usage(tmp_path)["unknown"] == 3


def test_legacy_unknown_counts_toward_three_total_attempts(tmp_path, monkeypatch):
    monkeypatch.setattr("final.src.runtime.checkpoint.time.sleep", lambda seconds: None)
    task_directory = tmp_path / "tasks" / "16"
    call_directory = task_directory / "calls" / "plain"
    save(call_directory / "request.json", QUERY_ARGUMENTS)
    save(call_directory / "attempt.json", {"request_id": digest(QUERY_ARGUMENTS), "state": "unknown"})
    model = FixtureTransportModel(failures=10)
    pipeline = CheckpointedModelClient(model)
    with pytest.raises(CompletionRetryLimit):
        pipeline.query(task_directory, "plain", **QUERY_ARGUMENTS)
    assert model.completion_calls == 2
    assert call_usage(tmp_path)["invocations"] == 3
    with pytest.raises(CompletionRetryLimit):
        pipeline.query(task_directory, "plain", **QUERY_ARGUMENTS)
    assert model.completion_calls == 2


def test_permanent_failure_is_not_replayed_on_restart(tmp_path):
    model = FixtureTransportModel(failures=10, permanent=True)
    pipeline = CheckpointedModelClient(model)
    task_directory = tmp_path / "tasks" / "16"
    with pytest.raises(TransportError):
        pipeline.query(task_directory, "plain", **QUERY_ARGUMENTS)
    with pytest.raises(RuntimeError, match="permanent"):
        pipeline.query(task_directory, "plain", **QUERY_ARGUMENTS)
    assert model.completion_calls == 1


def test_tokenizer_failure_records_no_completion_attempt(tmp_path):
    model = FixtureTransportModel()

    def fail_preparation(messages, max_tokens):
        raise TransportError("tokenize", "HTTPError", http_status=503, retryable=True)

    model.prepare_generation = fail_preparation
    pipeline = CheckpointedModelClient(model)
    with pytest.raises(TransportError):
        pipeline.query(tmp_path / "tasks" / "16", "plain", **QUERY_ARGUMENTS)
    assert model.completion_calls == 0
    assert call_usage(tmp_path)["invocations"] == 0


def test_endpoint_configuration_can_refresh_without_recording_url(transport_model, tmp_path):
    private_configuration = tmp_path / "endpoint.env"
    private_configuration.write_text("export FINAL_BASE_URL='http://replacement.invalid/v1'\nexport FINAL_MODEL='fixture'\n")
    transport_model.endpoint_file = private_configuration
    transport_model.refresh_configuration()
    assert transport_model.base_url == "http://replacement.invalid/v1"


def test_startup_environment_cannot_silently_change_expected_model(monkeypatch, tmp_path):
    monkeypatch.setenv("FINAL_BASE_URL", "http://fixture.invalid/v1")
    monkeypatch.setenv("FINAL_MODEL", "different-model")
    monkeypatch.setenv("FINAL_ENDPOINT_ENV_FILE", str(tmp_path / "absent.env"))
    with pytest.raises(TransportError) as failure:
        QwenModel()
    assert failure.value.error_type == "ModelChanged"
