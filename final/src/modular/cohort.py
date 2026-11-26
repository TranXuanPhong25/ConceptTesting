"""Frozen program cohort validation and recorded model-call accounting."""
import ast
import json
from pathlib import Path

from final.src.runtime.contracts import bound_call_key


def base_call_keys(cohort_task, signature):
    saved = set(cohort_task['base_input_keys'])
    recorded = set()
    for program in cohort_task.get('programs', []):
        for call in program.get('base', {}).get('calls', []):
            try:
                bound = signature.bind(*ast.literal_eval(call['args']), **ast.literal_eval(call['kwargs']))
            except (ValueError, TypeError, KeyError, SyntaxError, RecursionError):
                continue
            bound.apply_defaults()
            saved.discard(bound_call_key(bound.arguments, legacy=True))
            recorded.add(bound_call_key(bound.arguments))
    return saved | recorded


def load_cohort(path: Path):
    return json.loads(path.read_text())


def call_usage(directory):
    attempts = list(directory.glob("tasks/*/calls/*/attempt.json"))
    responses = list(directory.glob("tasks/*/calls/*/response.json"))
    totals = {key: 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    for path in responses:
        usage = json.loads(path.read_text()).get("usage", {})
        for key in totals:
            value = usage.get(key, 0)
            if type(value) in (int, float):
                totals[key] += value
    return dict(
        invocations=len(attempts),
        received=len(responses),
        unknown=len(attempts) - len(responses),
        known_usage=totals,
    )
