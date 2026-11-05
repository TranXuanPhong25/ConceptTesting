"""Compare the runtime LangChain adapter to plain ChatOpenAI, entirely offline.

Run: final/.venv/bin/python -m final.src.audits.probe_langchain_transport --output PATH
Only httpx.MockTransport is used; no endpoint, credentials or model are contacted.
The runtime adapter is the active backend; this probe makes no real model calls.
"""
from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import httpx
from langchain_openai import ChatOpenAI
from langsmith import tracing_context

from final.src.runtime.model import PreparedGeneration, QwenModel, TransportError, _CompletionStream


MESSAGES = [{"role": "system", "content": "Return JSON."},
            {"role": "user", "content": "Tiếng Việt: 🧪"}]
PREPARED = PreparedGeneration(MESSAGES, 10, 32)
USAGE = {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16,
         "completion_tokens_details": {"reasoning_tokens": 2}, "provider_extra": 7}


def event(content=None, finish=None, *, index=0, usage=None):
    payload = {"id": "fixture", "object": "chat.completion.chunk", "model": "fixture",
               "choices": [{"index": index, "delta": {"content": content},
                            "finish_reason": finish}]}
    if usage is not None:
        payload.update(choices=[], usage=usage)
    return b"data: " + json.dumps(payload, ensure_ascii=False).encode() + b"\n\n"


def fixtures():
    complete = event('{"text":"Việt 🧪"}', "stop")
    footer = event(usage=USAGE)
    return {
        "complete_usage": ([complete, footer, b"data: [DONE]\n\n"], None, 200),
        "missing_finish": ([event("partial")], None, 200),
        "timeout_before_finish": ([event("partial")], "timeout", 200),
        "timeout_after_finish": ([complete], "timeout", 200),
        "empty_finished": ([event("", "stop")], None, 200),
        "malformed_json_before_finish": ([event("partial"), b"data: {bad}\n\n"], None, 200),
        "malformed_json_after_finish": ([complete, b"data: {bad}\n\n"], None, 200),
        "crlf": ([complete.replace(b"\n", b"\r\n"), footer, b"data: [DONE]\r\n\r\n"], None, 200),
        "multiline_sse": ([b'data: {"choices":\ndata: [{"index":0,"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\n'], None, 200),
        "nonzero_choice": ([event("wrong choice", "stop", index=1)], None, 200),
        "error_event": ([b'data: {"error":{"message":"fixture failure","type":"server_error"}}\n\n'], None, 200),
        "http_503": ([b'{"error":{"message":"fixture failure"}}'], None, 503),
    }


class FixtureStream(httpx.SyncByteStream):
    def __init__(self, pieces, failure):
        self.pieces = pieces
        self.failure = failure

    def __iter__(self):
        # Deliberately split UTF-8 and SSE boundaries; the SDK must reassemble them.
        for piece in self.pieces:
            for offset in range(0, len(piece), 3):
                yield piece[offset:offset + 3]
        if self.failure:
            raise httpx.ReadTimeout("fixture timeout")


def run_runtime(pieces, failure, status):
    # Avoid configuration files/environment: inject only a fake HTTP endpoint.
    model = QwenModel.__new__(QwenModel)
    model.expected_model = "fixture"
    model.base_url = "http://fixture.invalid/v1"
    model.api_key = "fixture-not-a-secret"
    model.timeout = 180
    model.refresh_configuration = lambda: None
    requests = []

    def factory(started_at):
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(status, headers={"content-type": "text/event-stream"},
                                  stream=FixtureStream(pieces, failure))

        def bound_response(response):
            response.stream = _CompletionStream(response.stream, started_at)

        return httpx.Client(transport=httpx.MockTransport(handler),
                            event_hooks={"response": [bound_response]})

    model._completion_http_client = factory
    try:
        result = model.generate_prepared(PREPARED, temperature=.7, seed=123)
        outcome = {"accepted": True, "text": result.text, "finish_reason": result.finish_reason,
                   "usage": result.usage}
    except TransportError as error:
        outcome = {"accepted": False, "error_type": error.error_type,
                   "partial_text": error.partial_text, "details": error.details()}
    return dict(outcome, requests=requests)


def run_langchain(pieces, failure, status, *, preserve_max_tokens=False):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(status, headers={"content-type": "text/event-stream"},
                              stream=FixtureStream(pieces, failure))

    fragments = []
    usage = {}
    finish_reason = None
    error_type = None
    extra_body = {"chat_template_kwargs": {"enable_thinking": False}}
    if preserve_max_tokens:
        # Use the public vLLM extra_body escape hatch, avoiding LangChain's rename.
        extra_body["max_tokens"] = PREPARED.output_tokens
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        model = ChatOpenAI(model="fixture", api_key="fixture-not-a-secret",
            base_url="http://fixture.invalid/v1", http_client=client,
            max_retries=0, timeout=180, temperature=.7, seed=123,
            max_tokens=None if preserve_max_tokens else PREPARED.output_tokens,
            stream_usage=True, use_responses_api=False, extra_body=extra_body,
            default_headers={"ngrok-skip-browser-warning": "1"})
        try:
            with tracing_context(enabled=False):
                for chunk in model.stream(MESSAGES):
                    if isinstance(chunk.content, str):
                        fragments.append(chunk.content)
                    if chunk.usage_metadata:
                        usage = dict(chunk.usage_metadata)
                    if chunk.response_metadata.get("finish_reason") is not None:
                        finish_reason = chunk.response_metadata["finish_reason"]
        except Exception as error:
            # Record only class names, never exception strings containing URLs/keys.
            error_type = type(error).__name__
    text = "".join(fragments)
    return {"stream_raised": error_type, "text": text, "finish_reason": finish_reason,
            "usage_metadata": usage, "requests": requests,
            "accepted_with_existing_finish_policy": finish_reason is not None and bool(text.strip())}


def probe():
    rows = {}
    for name, arguments in fixtures().items():
        rows[name] = {"runtime": run_runtime(*arguments),
                      "langchain": run_langchain(*arguments)}
    compatible = run_langchain(*fixtures()["complete_usage"], preserve_max_tokens=True)
    runtime = rows["complete_usage"]["runtime"]
    ordinary = rows["complete_usage"]["langchain"]
    checks = {
        "normal_text_equal": runtime["text"] == ordinary["text"],
        "normal_finish_equal": runtime["finish_reason"] == ordinary["finish_reason"],
        "compatibility_request_equal": runtime["requests"] == compatible["requests"],
        "no_implicit_retries": all(len(row[backend]["requests"]) == 1
                                   for row in rows.values() for backend in ("runtime", "langchain")),
        "usage_counts_equal": ordinary["usage_metadata"].get("total_tokens") == USAGE["total_tokens"],
        "partial_text_preserved": rows["timeout_before_finish"]["langchain"]["text"] == "partial",
        "finish_visible_before_footer_failure": rows["timeout_after_finish"]["langchain"]["finish_reason"] == "stop",
        "runtime_rejects_missing_finish": not rows["missing_finish"]["runtime"]["accepted"],
        "runtime_preserves_partial": rows["timeout_before_finish"]["runtime"]["partial_text"] == "partial",
        "runtime_accepts_finished_timeout": rows["timeout_after_finish"]["runtime"]["accepted"],
        "runtime_ignores_nonzero_choice": not rows["nonzero_choice"]["runtime"]["accepted"],
        "runtime_keeps_provider_usage": runtime["usage"].get("provider_extra") == USAGE["provider_extra"],
    }
    assert all(checks.values()), checks
    return {"scope": "Offline fixtures only; no remote/model/benchmark calls; runtime uses LangChain",
            "versions": {name: version(name) for name in ("langchain-openai", "langchain-core", "openai", "httpx")},
            "checks": checks, "cases": rows, "compatible_serialization": compatible}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = probe()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"cases": len(result["cases"]), "checks": result["checks"]}))


if __name__ == "__main__":
    main()
