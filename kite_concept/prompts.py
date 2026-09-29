from __future__ import annotations

from .models import ConceptRecord, MechanismRecord, TaskRecord

SYSTEM = """You are a research unit-test generator. Return one complete compilable JUnit test class only.
Tests must assert documented behavior of the fixed program. Do not mock the focal method, modify production
state outside normal APIs, use sleeps, network, randomness, or weaken/delete prior assertions."""


def direct_prompt(task: TaskRecord, context: str) -> str:
    return f"""Generate a focused JUnit test suite for {task.focal_class}#{task.focal_method}.
The suite must exercise important boundaries and assert externally observable behavior.

Fixed focal source:
{task.source}

Repository context:
{context}
"""


def mutgen_prompt(task: TaskRecord, summary: str, mutants: list[dict], prior_tests: str = "") -> str:
    feedback = "\n".join(
        f"{m['id']}. {m['operator']} at line {m.get('line', '?')}, {m['status']}:\n{m['mutated_statement']}"
        for m in mutants if m["status"].upper() in {"SURVIVED", "NO_COVERAGE", "UNCOVERED"}
    )
    return f"""Generate diverse JUnit tests that kill each live or uncovered mutant. Preserve useful prior tests.

## Summary
{summary}

## Source code without comments
{task.source}

## Mutation Feedback
{feedback or 'No live mutants were reported.'}

## Prior passing tests
{prior_tests}
"""


def kite_prompt(task: TaskRecord, mechanism: MechanismRecord, injection: dict, prior_tests: str = "") -> str:
    return f"""Enhance the suite so it passes on the fixed method and exposes the injected behavior.
Preserve every previously detected injected behavior.

Focal source:
{task.source}

Bug mechanism (what): {mechanism.what}
Applicability (where): {mechanism.where}
Injection intent (how): {mechanism.how}
Local patch: {injection.get('before')} -> {injection.get('after')}
Trigger recipe: {injection.get('trigger_recipe')}
Observed injected-side feedback: {injection.get('feedback', '')}
Prior passing tests:
{prior_tests}
"""


def concept_prompt(task: TaskRecord, concept: ConceptRecord, prior_tests: str = "") -> str:
    concept.validate()
    return f"""Enhance the suite using the executable concept below. Use the trigger relation to construct inputs,
and use the expected oracle to construct assertions. The result must pass on the fixed method.

Focal source:
{task.source}

Violated constraint: {concept.violated_constraint}
Applicability condition: {concept.applicability_condition}
Trigger input relation: {concept.trigger_input_relation}
Expected oracle: {concept.expected_oracle}
Prior passing tests:
{prior_tests}
"""

