"""Cached calls and a transport adapter shared by every experiment arm."""
from final.src.models.core_model import ModelResponse
from final.src.runtime.artifacts import digest
from final.src.models.checkpoint import CheckpointedModelClient
from .artifacts import ArtifactStore


def structured_format(schema):
    return {'type': 'json_schema', 'json_schema': {'name': 'tool_preparation', 'strict': True, 'schema': schema}}


class CachedModelCalls:
    """No network or model construction; verify exact request identity before replay."""

    def __init__(self, artifacts: ArtifactStore):
        self.artifacts = artifacts

    @property
    def model_id(self):
        return "cache-only"

    def token_count(self, messages):
        raise RuntimeError("Tokenization is unavailable during read-only replay")

    def complete_structured(self, task_number, call_name, messages, *, schema, temperature, max_tokens, seed):
        return self.complete(task_number, call_name, messages, temperature=temperature,
                             max_tokens=max_tokens, seed=seed, response_format=structured_format(schema))

    def complete(self, task_number, call_name, messages, *, temperature, max_tokens, seed, response_format=None):
        directory = f"tasks/{task_number}/calls/{call_name}"
        request = dict(messages=messages, temperature=temperature, max_tokens=max_tokens, seed=seed)
        if response_format is not None:
            request['response_format'] = response_format
        if self.artifacts.read(directory + "/request.json") != request:
            raise ValueError(f"Cached request mismatch: {directory}")
        attempt = self.artifacts.read(directory + "/attempt.json")
        if attempt["request_id"] != digest(request):
            raise ValueError(f"Request checksum mismatch: {directory}")
        response = self.artifacts.read(directory + "/response.json")
        return ModelResponse(**response)


class RecordedModelCalls:
    """Uses the reviewed streaming/retry transport without changing request policy."""

    def __init__(self, model, artifacts: ArtifactStore):
        if artifacts.read_only:
            raise ValueError("Live model calls cannot use a read-only artifact store")
        self.model = model
        self.artifacts = artifacts
        self.client = CheckpointedModelClient(model)

    @property
    def model_id(self):
        return self.model.model_id

    def token_count(self, messages):
        return self.model.tokens(messages)

    def complete_structured(self, task_number, call_name, messages, *, schema, temperature, max_tokens, seed):
        return self.complete(
            task_number,
            call_name,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            response_format=structured_format(schema),
        )

    def complete(self, task_number, call_name, messages, *, temperature, max_tokens, seed, response_format=None):
        structured = {} if response_format is None else {'response_format': response_format}
        return self.client.query(
            self.artifacts.path(f"tasks/{task_number}"),
            call_name,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            **structured,
        )
