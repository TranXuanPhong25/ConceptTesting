"""Engineering-only transport tests: no remote API calls or benchmark outcomes."""
import io
import http.client
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

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


def test_streaming_collects_tokens_and_final_usage(transport_model, monkeypatch):
    response_bytes = b"".join([
        streaming_event({"choices": [{"delta": {"content": '{"inputs":'}, "finish_reason": None}]}),
        streaming_event({"choices": [{"delta": {"content": '[]}'}, "finish_reason": "stop"}]}),
        streaming_event({"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16}}),
        b"data: [DONE]\n\n",
    ])
    captured_requests = []

    def open_fixture(operation, request_body):
        captured_requests.append(request_body)
        return io.BytesIO(response_bytes)

    monkeypatch.setattr(transport_model, "request", open_fixture)
    prepared = PreparedGeneration([], 10, 2048)
    result = transport_model.generate_prepared(prepared, temperature=.7, seed=314175)
    assert result.text == '{"inputs":[]}'
    assert result.usage["total_tokens"] == 16
    assert result.usage["usage_footer_complete"] is True
    request_body = captured_requests[0]
    assert request_body["stream"] is True
    assert request_body["temperature"] == .7
    assert request_body["seed"] == 314175
    assert request_body["max_tokens"] == 2048


def test_incomplete_stream_is_never_accepted(transport_model, monkeypatch):
    partial_response = streaming_event({"choices": [{"delta": {"content": '{"inputs":'}, "finish_reason": None}]})
    monkeypatch.setattr(transport_model, "request", lambda *args: io.BytesIO(partial_response))
    with pytest.raises(TransportError) as failure:
        transport_model.generate_prepared(PreparedGeneration([], 10, 2048), temperature=.7, seed=1)
    assert failure.value.error_type == "IncompleteStream"
    assert failure.value.partial_text == '{"inputs":'


def test_finished_output_survives_lost_usage_footer(transport_model, monkeypatch):
    class FooterTimeout:
        def __enter__(self):
            return self

        def __exit__(self, *arguments):
            return False

        def __iter__(self):
            yield streaming_event({"choices": [{"delta": {"content": "complete"}, "finish_reason": "stop"}]})
            raise TimeoutError()

    monkeypatch.setattr(transport_model, "request", lambda *args: FooterTimeout())
    result = transport_model.generate_prepared(PreparedGeneration([], 10, 32), temperature=0, seed=1)
    assert result.text == "complete"
    assert result.usage["usage_footer_complete"] is False


@pytest.mark.parametrize("finished", [False, True])
def test_truncated_chunked_stream_before_and_after_finish(transport_model, monkeypatch, finished):
    class TruncatedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *arguments):
            return False

        def __iter__(self):
            yield streaming_event({"choices": [{"delta": {"content": "text"},
                                                "finish_reason": "stop" if finished else None}]})
            raise http.client.IncompleteRead(b"truncated")

    monkeypatch.setattr(transport_model, "request", lambda *args: TruncatedResponse())
    prepared = PreparedGeneration([], 10, 2048)
    if finished:
        assert transport_model.generate_prepared(prepared, temperature=.7, seed=1).text == "text"
    else:
        with pytest.raises(TransportError) as failure:
            transport_model.generate_prepared(prepared, temperature=.7, seed=1)
        assert failure.value.error_type == "IncompleteRead"
        assert failure.value.partial_text == "text"


def test_finished_output_survives_generation_deadline_in_footer(transport_model, monkeypatch):
    import final.src.runtime.model as model_module
    elapsed_seconds = [0]

    class SlowFooter:
        def __enter__(self):
            return self

        def __exit__(self, *arguments):
            return False

        def __iter__(self):
            elapsed_seconds[0] = 1
            yield streaming_event({"choices": [{"delta": {"content": "done"}, "finish_reason": "stop"}]})
            elapsed_seconds[0] = 1801
            yield b"\n"

    monkeypatch.setattr(model_module, "time", SimpleNamespace(monotonic=lambda: elapsed_seconds[0]))
    monkeypatch.setattr(transport_model, "request", lambda *args: SlowFooter())
    assert transport_model.generate_prepared(PreparedGeneration([], 10, 2048), temperature=.7, seed=1).text == "done"


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
