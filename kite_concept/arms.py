"""Dependency-injected arm workflows.

Project-specific compilation and execution are callbacks so the same protocol can handle the five
different Defects4J build layouts while retaining one auditable state machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .injection import promotion_gate
from .models import ConceptRecord, MechanismRecord, TaskRecord
from .prompts import concept_prompt, direct_prompt, kite_prompt, mutgen_prompt

Generate = Callable[[str], tuple[str, int, int]]
CorrectCheck = Callable[[str], tuple[bool, str]]
TargetCheck = Callable[[str, Any], tuple[bool, str]]


@dataclass
class ArmWorkflows:
    generate: Generate
    correct_check: CorrectCheck
    target_check: TargetCheck
    charge: Callable[[int, int], None]

    def _ask(self, prompt: str) -> str:
        text, input_tokens, output_tokens = self.generate(prompt)
        self.charge(input_tokens, output_tokens)
        if not text.strip():
            raise ValueError("LLM returned an empty test suite")
        return text

    def direct(self, task: TaskRecord, context: str) -> dict[str, Any]:
        suite = self._ask(direct_prompt(task, context))
        passed, feedback = self.correct_check(suite)
        return {"suite": suite, "correct_pass": passed, "feedback": feedback}

    def mutgen(self, task: TaskRecord, summary: str, mutation_rounds: Callable[[str], list[dict]], budget: int) -> dict[str, Any]:
        suite = ""
        killed: set[str] = set()
        rounds = []
        for _ in range(budget):
            mutants = mutation_rounds(suite)
            actionable = [m for m in mutants if m["status"].upper() in {"SURVIVED", "NO_COVERAGE", "UNCOVERED"}]
            if suite and not actionable:
                break
            candidate = self._ask(mutgen_prompt(task, summary, actionable, suite))
            passed, feedback = self.correct_check(candidate)
            if passed:
                suite = candidate
            killed.update(str(m["id"]) for m in mutants if m["status"].upper() == "KILLED")
            rounds.append({"correct_pass": passed, "feedback": feedback, "actionable": len(actionable)})
        return {"suite": suite, "killed_mutant_ids": sorted(killed), "rounds": rounds}

    def kite(self, task: TaskRecord, targets: list[tuple[MechanismRecord, dict]], budget: int) -> dict[str, Any]:
        suite = ""
        detected: dict[str, bool] = {}
        rounds = []
        for mechanism, injection in targets:
            if len(rounds) >= budget:
                break
            already, feedback = self.target_check(suite, injection) if suite else (False, "empty suite")
            if already:
                detected[mechanism.id] = True
                continue
            candidate = self._ask(kite_prompt(task, mechanism, {**injection, "feedback": feedback}, suite))
            correct, correct_feedback = self.correct_check(candidate)
            current, target_feedback = self.target_check(candidate, injection) if correct else (False, "correct side failed")
            history = {key: self.target_check(candidate, old)[0] for key, old in
                       ((m.id, inj) for m, inj in targets if m.id in detected and detected[m.id])}
            promoted = promotion_gate(correct, current, history)
            if promoted:
                suite = candidate
            detected[mechanism.id] = promoted
            rounds.append({"mechanism_id": mechanism.id, "promoted": promoted,
                           "correct_feedback": correct_feedback, "target_feedback": target_feedback})
        return {"suite": suite, "detected_mechanisms": detected, "rounds": rounds}

    def concept(self, task: TaskRecord, concepts: list[ConceptRecord], budget: int) -> dict[str, Any]:
        suite = ""
        rounds = []
        for concept in concepts[:budget]:
            candidate = self._ask(concept_prompt(task, concept, suite))
            correct, feedback = self.correct_check(candidate)
            if correct:
                suite = candidate
            rounds.append({"mechanism_id": concept.mechanism_id, "correct_pass": correct, "feedback": feedback})
        return {"suite": suite, "rounds": rounds}

