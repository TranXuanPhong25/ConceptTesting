"""Keep every transport attempt; retry transient completion failures at most twice."""
from __future__ import annotations

import json
import time
from dataclasses import asdict

from final.core_model import ModelResponse
from final.pipeline import Pipeline, digest, save
from .model import TransportError

RECOVERY_POLICY = "streaming-recovery-v1"
MAX_COMPLETION_ATTEMPTS = 3


class CompletionRetryLimit(RuntimeError):
    """Automatic completion attempts are exhausted; do not reset on controller restart."""


class RecoveryPipeline(Pipeline):
    def query(self, directory, name, messages, *, temperature, max_tokens, seed):
        call_directory = directory / "calls" / name
        request_record = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "seed": seed,
        }
        request_identifier = digest(request_record)
        attempt_path = call_directory / "attempt.json"
        response_path = call_directory / "response.json"
        if attempt_path.exists():
            previous_attempt = json.loads(attempt_path.read_text())
            if previous_attempt["request_id"] != request_identifier:
                raise RuntimeError("Cached request mismatch")
            if response_path.exists():
                return ModelResponse(**json.loads(response_path.read_text()))
            if previous_attempt.get("recovery_policy") == RECOVERY_POLICY:
                previous_error = previous_attempt.get("error", {})
                if previous_error.get("retryable") is False:
                    raise RuntimeError("Stored permanent transport failure; automatic replay disabled")
            self.archive_failed_attempt(call_directory)

        previous_completion_attempts = 0
        for archived_directory in call_directory.parent.glob(name + "_unknown_attempt_*"):
            if (archived_directory / "attempt.json").exists():
                previous_completion_attempts += 1

        for attempt_number in range(previous_completion_attempts, MAX_COMPLETION_ATTEMPTS):
            # Tokenizer/read-only errors happen before a completion attempt is recorded.
            prepared = self.model.prepare_generation(messages, max_tokens)
            save(call_directory / "request.json", request_record)
            save(attempt_path, {
                "request_id": request_identifier,
                "state": "started",
                "recovery_policy": RECOVERY_POLICY,
                "attempt_number": attempt_number + 1,
            })
            try:
                response = self.model.generate_prepared(prepared, temperature=temperature, seed=seed)
            except TransportError as error:
                save(attempt_path, {
                    "request_id": request_identifier,
                    "state": "unknown",
                    "recovery_policy": RECOVERY_POLICY,
                    "attempt_number": attempt_number + 1,
                    "error": error.details(),
                })
                if error.partial_text:
                    save(call_directory / "partial_response.json", {"text": error.partial_text})
                if not error.retryable:
                    raise
                if attempt_number + 1 >= MAX_COMPLETION_ATTEMPTS:
                    raise CompletionRetryLimit("Three completion attempts failed; history preserved") from None
                self.archive_failed_attempt(call_directory)
                time.sleep((5, 20)[attempt_number])
                continue
            save(response_path, asdict(response))
            save(attempt_path, {
                "request_id": request_identifier,
                "state": "received",
                "recovery_policy": RECOVERY_POLICY,
                "attempt_number": attempt_number + 1,
            })
            return response
        raise CompletionRetryLimit("Completion retry limit already reached; all attempts preserved")

    @staticmethod
    def archive_failed_attempt(call_directory):
        archive_number = 0
        while True:
            archive_directory = call_directory.with_name(
                call_directory.name + f"_unknown_attempt_{archive_number:04d}"
            )
            if not archive_directory.exists():
                call_directory.rename(archive_directory)
                return
            archive_number += 1
