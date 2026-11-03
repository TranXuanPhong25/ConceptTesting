"""Original V11 sampling including top_p, through the reviewed streaming transport."""

import contextvars
import fcntl
import json
import time
from contextlib import contextmanager
from pathlib import Path

from final.pipeline import digest, save, Settings
from final.experiments.concept_reference_v1_recovery.model import QwenModel
from final.experiments.concept_reference_v1_recovery.checkpoint import RecoveryPipeline

TOP_P = contextvars.ContextVar("v11_top_p", default=0.95)


class V11Model(QwenModel):
    def request(self, operation, body=None, **keywords):
        if operation == "completion":
            body = dict(body, top_p=TOP_P.get())
        return super().request(operation, body, **keywords)


class V11ModelCalls:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.model = V11Model(timeout=180)
        self.client = RecoveryPipeline(self.model, self.directory, Settings())

    def complete(self, messages, seed, *, temperature=0.7, top_p=0.95, max_tokens=1024):
        request = dict(
            model=self.model.model_id,
            messages=messages,
            seed=seed,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        request_hash = digest(request)
        directory = self.directory / "requests" / request_hash
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / ".call.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            cache_path = directory / "v11_response.json"
            if cache_path.exists():
                return dict(json.loads(cache_path.read_text()), cache_hit=True)
            save(directory / "sampling_request.json", request)
            token = TOP_P.set(top_p)
            started = time.monotonic()
            try:
                response = self.client.query(
                    directory,
                    "completion",
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    seed=seed,
                )
            finally:
                TOP_P.reset(token)
            result = dict(
                text=response.text,
                key=request_hash,
                params={
                    field_name: value
                    for field_name, value in request.items()
                    if field_name != "messages"
                },
                n_in=response.usage.get("prompt_tokens", 0),
                n_out=response.usage.get("completion_tokens", 0),
                seconds=time.monotonic() - started,
                finish_reason=response.finish_reason,
                usage=response.usage,
                cache_hit=False,
            )
            save(cache_path, result)
            return result
