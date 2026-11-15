"""Recorded test calls using synthetic model responses, without network access."""
from dataclasses import asdict
from final.src.runtime.artifacts import digest, save
from final.src.models.core_model import ModelResponse


class FixtureCalls:
    def __init__(self, model, directory):
        self.model = model
        self.directory = directory

    @property
    def model_id(self):
        return self.model.model_id

    def token_count(self, messages):
        return self.model.tokens(messages)

    def complete(self, task_number, call_name, messages, **parameters):
        directory = self.directory / f"tasks/{task_number}/calls/{call_name}"
        request = dict(messages=messages, **parameters)
        response_path = directory / "response.json"
        if response_path.exists():
            import json
            if json.loads((directory / "request.json").read_text()) != request:
                raise ValueError("Cached request mismatch")
            return ModelResponse(**json.loads(response_path.read_text()))
        save(directory / "request.json", request)
        save(directory / "attempt.json", {"request_id": digest(request), "state": "started"})
        response = self.model.generate(messages, **parameters)
        save(response_path, asdict(response))
        save(directory / "attempt.json", {"request_id": digest(request), "state": "received"})
        return response
