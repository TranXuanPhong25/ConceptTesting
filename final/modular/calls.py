"""Cached calls and a transport adapter shared by every experiment arm."""
from final.core_model import ModelResponse
from final.pipeline import digest
from final.experiments.concept_reference_v1_recovery.checkpoint import RecoveryPipeline
from final.pipeline import Settings
from .artifacts import ArtifactStore


class CachedModelCalls:
    """No network or model construction; verify exact request identity before replay."""

    def __init__(self, artifacts: ArtifactStore):
        self.artifacts = artifacts

    @property
    def model_id(self):
        if self.artifacts.exists("manifest.json"):
            return self.artifacts.read("manifest.json")["model"]
        return "cache-only"

    def token_count(self, messages):
        raise RuntimeError("Tokenization is unavailable during read-only replay")

    def complete(self, task_number, call_name, messages, *, temperature, max_tokens, seed):
        directory = f"tasks/{task_number}/calls/{call_name}"
        request = dict(messages=messages, temperature=temperature, max_tokens=max_tokens, seed=seed)
        if self.artifacts.read(directory + "/request.json") != request:
            raise ValueError(f"Cached request mismatch: {directory}")
        attempt = self.artifacts.read(directory + "/attempt.json")
        if attempt["request_id"] != digest(request):
            raise ValueError(f"Request checksum mismatch: {directory}")
        response = self.artifacts.read(directory + "/response.json")
        return ModelResponse(**response)


class RecoveryModelCalls:
    """Uses the reviewed streaming/retry transport without changing request policy."""

    def __init__(self, model, artifacts: ArtifactStore):
        if artifacts.read_only:
            raise ValueError("Live model calls cannot use a read-only artifact store")
        self.model = model
        self.artifacts = artifacts
        self.client = RecoveryPipeline(model, artifacts.directory, Settings())

    @property
    def model_id(self):
        return self.model.model_id

    def token_count(self, messages):
        return self.model.tokens(messages)

    def complete(self, task_number, call_name, messages, *, temperature, max_tokens, seed):
        return self.client.query(
            self.artifacts.path(f"tasks/{task_number}"), call_name, messages,
            temperature=temperature, max_tokens=max_tokens, seed=seed,
        )
