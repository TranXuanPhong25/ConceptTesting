"""Prepare input-method context: cohort eligibility, visibility and optional prompt."""
from __future__ import annotations

import hashlib

from .input_prompts import structured_input_prompt


def _overflow_packet(task_id: str, *, empty_context_on_overflow: bool, extra: dict | None = None) -> dict:
    if empty_context_on_overflow:
        return {
            "task_id": task_id,
            "visible_put_ids": [],
            "common": "",
            "prompt_tokens": {},
            "empty_context": True,
        }
    return {"task_id": task_id, "skip": "prompt_too_large", **(extra or {})}


def prepare_task_packet(
    context,
    methods=(),
    *,
    prior_stage_inputs=(),
    empty_context_on_overflow: bool = False,
) -> dict:
    """Select eligible visible PUTs and build the shared prompt fitting context limits."""
    cohort = context.cohort_task
    passing_programs = [program for program in cohort["programs"] if program["base"]["status"] == "pass"]
    if not passing_programs:
        return {"task_id": context.task["task_id"], "skip": "no_base_pass"}
    programs = sorted(
        passing_programs,
        key=lambda program: hashlib.sha256(f"{context.task_number}:{program['id']}".encode()).hexdigest(),
    )
    prompt_methods = [method for method in methods if getattr(method, "uses_shared_prompt", False)]
    while programs:
        packet = {
            "task_id": context.task["task_id"],
            "visible_put_ids": [program["id"] for program in programs],
            "common": "",
            "prompt_tokens": {},
        }
        if prompt_methods:
            if context.calls is None:
                raise RuntimeError("Shared-prompt input methods require tokenization")
            packet["common"] = structured_input_prompt(
                context.task,
                programs,
                context.metadata["contract"],
                context.settings.input_budget,
                prior_stage_inputs=prior_stage_inputs,
                extra_base_tests=cohort.get("extra_base_tests", ""),
            )
            for method in prompt_methods:
                packet["prompt_tokens"][method.name] = context.calls.token_count(method.build_messages(packet))
        limit = context.settings.context_tokens - context.settings.input_tokens - 128
        # VALIDATION START: all shared prompts fit the configured context budget.
        if max(packet["prompt_tokens"].values(), default=0) <= limit:
            return packet
        if any(getattr(method, "preserve_prompt_context", False) for method in prompt_methods):
            return _overflow_packet(
                packet["task_id"],
                empty_context_on_overflow=empty_context_on_overflow,
                extra={
                    **packet,
                    "reason": "full_prompt_exceeds_context",
                    "required_prompt_tokens": max(packet["prompt_tokens"].values()),
                    "available_prompt_tokens": limit,
                },
            )
        # VALIDATION END: all shared prompts fit the configured context budget.
        programs.pop()
    return _overflow_packet(context.task["task_id"], empty_context_on_overflow=empty_context_on_overflow)


def load_or_prepare_packet(
    context,
    methods=(),
    *,
    prior_stage_inputs=(),
    empty_context_on_overflow: bool = False,
) -> dict:
    """Load saved task packet or compute and persist it."""
    path = context.task_directory + "/packet.json"
    context.packet = context.artifacts.load_or_compute(
        path,
        lambda: prepare_task_packet(
            context,
            methods,
            prior_stage_inputs=prior_stage_inputs,
            empty_context_on_overflow=empty_context_on_overflow,
        ),
    )
    return context.packet
