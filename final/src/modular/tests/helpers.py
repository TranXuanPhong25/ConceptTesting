"""Recorded test calls using synthetic model responses, without network access."""
import json
from dataclasses import asdict
from final.src.runtime.artifacts import digest, save
from final.src.models.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext


SPECIFICATION = 'def choose(xs: list[int]):\n    """Return the sum. xs has at least two elements."""\n'
TASK = {"task_id": "HumanEval/7", "entry_point": "choose", "prompt": SPECIFICATION,
        "test": "def check(candidate):\n    assert candidate([0, 0]) == 0\n",
        "canonical_solution": "    # REFERENCE_ONLY_MARKER\n    return sum(xs)\n"}
META = {"contract": "\n    assert isinstance(xs, list) and len(xs) >= 2\n    assert all(type(x) is int for x in xs)\n",
        "atol": 0}


def program(identifier):
    return {"id": identifier, "code": "def choose(xs):\n    return 0\n",
            "base": {"status": "pass", "calls": [{"args": "([0, 0],)", "kwargs": "{}"}],
                     "coverage": {"lines": [1, 2], "arcs": []}}}


def make_context(tmp_path, calls, count=2, budget=5):
    context = TaskContext(TASK, META, ArtifactStore(tmp_path),
                          PipelineSettings(input_budget=budget), calls)
    context.cohort_task = {"task_id": TASK["task_id"], "generated": count, "base_pass": count,
                           "programs": [program(index) for index in range(count)], "base_input_keys": []}
    context.packet = {"visible_put_ids": list(range(count))}
    return context


def write_cohort(path, tasks=None, *, boolean=False):
    records = []
    for task in tasks or [TASK]:
        item = program(0)
        if boolean:
            item["code"] = "def choose(flag: bool):\n    return flag\n"
            item["base"]["calls"] = [{"args": "(True,)", "kwargs": "{}"}]
        records.append({"task_id": task["task_id"], "generated": 1, "base_pass": 1,
                        "programs": [item], "base_input_keys": []})
    save(path, {"tasks": records, "cohort_sha256": digest(records), "dataset_sha256": "fixture-dataset"})
    return path


class PlainFixtureModel:
    model_id = "plain-pipeline-fixture"

    def __init__(self):
        self.requests = []

    def tokens(self, messages):
        return max(1, len(json.dumps(messages)) // 4)

    def generate(self, messages, **settings):
        self.requests.append(messages)
        assert "REFERENCE_ONLY_MARKER" not in json.dumps(messages)
        record = {"inputs": [{"args": "([7, 8],)", "kwargs": "{}", "guidance_id": None}]}
        return ModelResponse(json.dumps(record), {"prompt_tokens": 50, "completion_tokens": 50,
                                                  "total_tokens": 100}, "stop")


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
