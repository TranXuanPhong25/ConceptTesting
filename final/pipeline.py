"""Model-independent orchestration and checkpointed experiment artifacts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import prompts
from .contracts import fingerprint, parse_json, validate_test
from .core_model import CoreModel, ModelResponse
from .execution import execute


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


@dataclass(frozen=True)
class Settings:
    programs: int = 10
    generation_rounds: int = 5
    tests: int = 30
    generation_tokens: int = 16000
    test_tokens: int = 8000
    generation_temperature: float = 0.9
    test_temperature: float = 0.6
    timeout: float = 3.0
    seed: int = 20261030


class UnknownInvocation(RuntimeError):
    """A recorded invocation has no durable response; never silently call again."""


class Pipeline:
    def __init__(self, model: CoreModel, out: Path, settings: Settings):
        self.model, self.out, self.settings = model, Path(out), settings

    def query(self, directory, name, messages, *, temperature, max_tokens, seed):
        directory = directory / "calls" / name
        request = dict(messages=messages, temperature=temperature, max_tokens=max_tokens, seed=seed)
        request_id = digest(request)
        response_path, attempt_path = directory / "response.json", directory / "attempt.json"
        if attempt_path.exists():
            attempt = json.loads(attempt_path.read_text())
            if attempt["request_id"] != request_id:
                raise RuntimeError("Cached request mismatch; use a new output directory")
            if response_path.exists():
                return ModelResponse(**json.loads(response_path.read_text()))
            raise UnknownInvocation(f"{directory.name}: prior invocation has no saved response; usage unknown")
        save(directory / "request.json", request)
        save(attempt_path, dict(request_id=request_id, state="started"))
        try:
            response = self.model.generate(messages, temperature=temperature, max_tokens=max_tokens, seed=seed)
        except Exception as exc:
            # Keep only the exception class; arbitrary providers may embed URLs/keys in str(exc).
            save(attempt_path, dict(request_id=request_id, state="unknown", error_type=type(exc).__name__))
            raise RuntimeError(f"Model invocation failed ({type(exc).__name__}); response/usage unknown") from None
        save(response_path, asdict(response))
        save(attempt_path, dict(request_id=request_id, state="received"))
        return response

    def run_task(self, task: dict) -> dict:
        task_number = int(task["task_id"].split("/")[1])
        directory = self.out / "tasks" / str(task_number)
        result_path = directory / "result.json"
        if result_path.exists():
            return json.loads(result_path.read_text())
        settings = self.settings
        reference = task["prompt"] + task["canonical_solution"]
        base_job = dict(mode="base", entry=task["entry_point"], base=task["test"],
                        context=task["prompt"], timeout=settings.timeout, seed=settings.seed + task_number)
        reference_path = directory / "reference_base.json"
        if reference_path.exists():
            reference_base = json.loads(reference_path.read_text())
        else:
            reference_base = execute(dict(base_job, source=reference))
            save(reference_path, reference_base)
        if reference_base["status"] != "pass":
            raise RuntimeError(f"{task['task_id']}: canonical solution does not pass base tests")

        programs, rejected, seen = [], [], set()
        for generation_round in range(settings.generation_rounds):
            if len(programs) == settings.programs:
                break
            response = self.query(directory, f"programs_{generation_round:02d}",
                                  prompts.programs(task, programs, settings.programs - len(programs)),
                                  temperature=settings.generation_temperature,
                                  max_tokens=settings.generation_tokens,
                                  seed=settings.seed + task_number * 100 + generation_round)
            try:
                candidates = parse_json(response.text)["programs"]
                if not isinstance(candidates, list) or len(candidates) > 100:
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                rejected.append(dict(round=generation_round, reason="invalid_response"))
                continue
            for candidate in candidates:
                if len(programs) == settings.programs:
                    break
                try:
                    if not isinstance(candidate, dict) or not isinstance(candidate.get("code"), str):
                        raise ValueError()
                    if not isinstance(candidate.get("approach"), str) or not candidate["approach"].strip():
                        raise ValueError()
                    if len(candidate["code"]) > 60000:
                        raise ValueError()
                    key = fingerprint(candidate["code"], task["entry_point"])
                except (ValueError, SyntaxError, TypeError, RecursionError):
                    rejected.append(dict(round=generation_round, reason="invalid_program"))
                    continue
                if key in seen:
                    rejected.append(dict(round=generation_round, reason="structural_duplicate"))
                    continue
                seen.add(key)
                programs.append(dict(id=len(programs), approach=candidate["approach"],
                                     code=candidate["code"], fingerprint=key))
        save(directory / "programs.json", dict(programs=programs, rejected=rejected))
        result = dict(task_id=task["task_id"], generated=len(programs), base_pass=0,
                      valid_tests=0, evaluated_programs=0, detected_programs=0,
                      unstable_programs=0, status="generation_shortfall", programs=[])
        if len(programs) != settings.programs:
            save(result_path, result)
            return result

        passing = []
        base_keys = set(reference_base["input_keys"])
        for program in programs:
            path = directory / "base" / f"{program['id']}.json"
            if path.exists():
                outcome = json.loads(path.read_text())
            else:
                outcome = execute(dict(base_job, source=program["code"]))
                save(path, outcome)
            base_keys.update(outcome.get("input_keys", []))
            result["programs"].append(dict(id=program["id"], base=outcome))
            if outcome["status"] == "pass":
                passing.append(program)
        result["base_pass"] = len(passing)
        if not passing:
            result["status"] = "no_base_pass"
            save(result_path, result)
            return result

        # Exactly one invocation shared by ALL base-passing implementations.
        response = self.query(directory, "tests", prompts.tests(task, passing, settings.tests),
                              temperature=settings.test_temperature, max_tokens=settings.test_tokens,
                              seed=settings.seed + task_number * 100 + 99)
        candidates, test_rejections = [], []
        try:
            raw_tests = parse_json(response.text)["tests"]
            if not isinstance(raw_tests, list):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raw_tests = []
            test_rejections.append(dict(reason="invalid_response"))
        for index, record in enumerate(raw_tests[:settings.tests]):
            try:
                candidates.append(dict(validate_test(record), original_index=index))
            except (ValueError, SyntaxError, TypeError, RecursionError):
                test_rejections.append(dict(index=index, reason="invalid_test"))
        if len(raw_tests) > settings.tests:
            test_rejections.append(dict(reason="exceeds_test_cap", count=len(raw_tests)-settings.tests))

        case_job = dict(mode="cases", entry=task["entry_point"], timeout=settings.timeout,
                        context=task["prompt"], seed=settings.seed + task_number)
        reference_runs = []
        for repeat in range(2):
            path = directory / f"reference_tests_{repeat}.json"
            if path.exists():
                checks = json.loads(path.read_text())
            else:
                checks = execute(dict(case_job, source=reference, tests=candidates))
                save(path, checks)
            reference_runs.append(checks["tests"])
        new_keys, valid = set(), []
        for index, record in enumerate(candidates):
            checks = [run[index] for run in reference_runs]
            if not all(check["status"] == "pass" for check in checks):
                reason = "reference_rejects"
            elif checks[0]["input_key"] in base_keys:
                reason = "base_input_duplicate"
            elif checks[0]["input_key"] in new_keys:
                reason = "new_input_duplicate"
            else:
                new_keys.add(checks[0]["input_key"])
                valid.append(record)
                continue
            test_rejections.append(dict(index=record["original_index"], reason=reason, reference=checks))
        save(directory / "tests.json", dict(valid=valid, rejected=test_rejections,
                                             note="Reference checks do not prove domain validity or full oracle soundness."))
        result.update(valid_tests=len(valid), test_rejections=test_rejections)
        if not valid:
            result["status"] = "no_valid_new_tests"
            save(result_path, result)
            return result

        for program in passing:
            runs = []
            for repeat in range(2):
                path = directory / "new_tests" / f"{program['id']}_{repeat}.json"
                if path.exists():
                    checks = json.loads(path.read_text())
                else:
                    checks = execute(dict(case_job, source=program["code"], tests=valid))
                    save(path, checks)
                runs.append(checks["tests"])
            fail_indices = [i for i in range(len(valid))
                            if all(run[i]["status"] in ("fail", "error", "timeout") for run in runs)]
            unstable = any(runs[0][i]["status"] != runs[1][i]["status"] for i in range(len(valid)))
            row = result["programs"][program["id"]]
            row.update(new_tests=runs, failed_test_indices=fail_indices, detected=bool(fail_indices), unstable=unstable)
            result["detected_programs"] += bool(fail_indices)
            result["unstable_programs"] += unstable
        result.update(evaluated_programs=len(passing), status="complete")
        save(result_path, result)
        return result


def summarize(out: Path, expected_tasks: int) -> dict:
    results = [json.loads(path.read_text()) for path in sorted((out / "tasks").glob("*/result.json"))]
    calls = list((out / "tasks").glob("*/calls/*/attempt.json"))
    received = list((out / "tasks").glob("*/calls/*/response.json"))
    usage = {}
    for path in received:
        for key, value in json.loads(path.read_text()).get("usage", {}).items():
            if type(value) in (int, float):
                usage[key] = usage.get(key, 0) + value
    totals = {key: sum(r[key] for r in results) for key in (
        "generated", "base_pass", "valid_tests", "evaluated_programs", "detected_programs", "unstable_programs")}
    totals.update(expected_tasks=expected_tasks, finished_tasks=len(results),
                  complete_generation_tasks=sum(r["generated"] == 10 for r in results),
                  tasks_with_detection=sum(r["detected_programs"] > 0 for r in results),
                  tasks_without_valid_tests=sum(r["status"] == "no_valid_new_tests" for r in results),
                  model_invocations=len(calls), received_responses=len(received),
                  unknown_invocations=len(calls) - len(received), known_usage=usage,
                  detected_fraction_of_base_pass=(totals["detected_programs"] / totals["base_pass"]
                                                  if totals["base_pass"] else None),
                  tested_fraction_of_base_pass=(totals["evaluated_programs"] / totals["base_pass"]
                                                if totals["base_pass"] else None),
                  statuses={status: sum(r["status"] == status for r in results)
                            for status in sorted({r["status"] for r in results})})
    save(out / "summary.json", totals)
    fraction = totals["detected_fraction_of_base_pass"]
    text = f"""# HumanEval incremental test detection

- Finished tasks: {len(results)}/{expected_tasks}; full sets of 10: {totals['complete_generation_tasks']}.
- Structurally distinct generated programs: {totals['generated']}.
- Programs passing base tests: {totals['base_pass']}.
- Programs evaluated with valid new tests: {totals['evaluated_programs']}.
- Programs failing new tests on both repeats: {totals['detected_programs']} ({'n/a' if fraction is None else f'{fraction:.2%}'} of base-pass programs).
- Tasks with a detected failure: {totals['tasks_with_detection']}.
- Valid novel tests: {totals['valid_tests']}; tasks with no valid new tests: {totals['tasks_without_valid_tests']}.
- Model invocations: {len(calls)}; responses: {len(received)}; unknown: {len(calls)-len(received)}.

This measures additional failures among base-pass programs, not recall of all real bugs.
Canonical acceptance is a reference check, not proof of input-domain validity or a sound
oracle for all valid alternative outputs. The tester is prompted to use properties for
non-unique outputs. Inspect per-task tests before making a spec-correctness claim.
Structural deduplication does not prove different algorithms. Generation shortfalls and
tasks without valid tests are reported explicitly, never counted as successful survival.
"""
    (out / "REPORT.md").write_text(text)
    return totals
