import json

from final.src.runtime.contracts import fingerprint, parse_json
from ..program_prompts import programs as program_prompt
from .base import PipelineStage


class ProgramGenerationStage(PipelineStage):
    """Optional cohort-building stage; benchmark runs use FrozenCohortStage instead."""
    name = "program_generation"

    def run(self, context):
        if context.cohort_task is not None:
            context.generated_programs = context.cohort_task["programs"]
            return
        if context.calls is None:
            raise RuntimeError("Creating a new cohort requires explicitly supplied model calls")
        retained_programs = []
        fingerprints = set()
        rejections = []
        for round_index in range(context.settings.writer_rounds):
            missing_count = context.settings.target_programs - len(retained_programs)
            if missing_count == 0:
                break
            request_messages = program_prompt(context.task, retained_programs[-3:], min(5, missing_count))
            if len(retained_programs) > 3:
                earlier_approaches = []
                for program in retained_programs[:-3]:
                    earlier_approaches.append(program["approach"][:200])
                request_messages[-1]["content"] += "\nEarlier retained approaches (also avoid): " + json.dumps(earlier_approaches)
            response = context.calls.complete(
                context.task_number, f"programs_{round_index:02d}", request_messages,
                temperature=.9, max_tokens=3072,
                seed=context.settings.writer_seed + context.task_number * 100 + round_index,
            )
            try:
                candidates = parse_json(response.text)["programs"]
                if not isinstance(candidates, list) or len(candidates) > 30:
                    raise ValueError("Invalid programs array")
            except (ValueError, TypeError, KeyError):
                rejections.append({"round": round_index, "reason": "invalid_json"})
                continue
            for candidate in candidates:
                if len(retained_programs) == context.settings.target_programs:
                    break
                try:
                    if not isinstance(candidate, dict) or not isinstance(candidate.get("code"), str):
                        raise ValueError("Missing source")
                    if len(candidate["code"]) > 30000 or not isinstance(candidate.get("approach"), str):
                        raise ValueError("Invalid source or approach")
                    normalized_hash = fingerprint(candidate["code"], context.task["entry_point"])
                except (ValueError, SyntaxError, RecursionError, TypeError):
                    rejections.append({"round": round_index, "reason": "invalid_program"})
                    continue
                if normalized_hash in fingerprints:
                    rejections.append({"round": round_index, "reason": "duplicate"})
                    continue
                fingerprints.add(normalized_hash)
                retained_programs.append({
                    "id": len(retained_programs), "code": candidate["code"],
                    "approach": candidate["approach"], "fingerprint": normalized_hash,
                })
        context.generated_programs = retained_programs
        context.generation_rejections = rejections
