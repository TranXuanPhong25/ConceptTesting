"""The original V11 round1/strict hybrid recipe as explicit, reusable classes."""

import ast
import random

from final.pipeline import save
from trickcatcher_linefacts.pipelines.v11_fair import (
    prompts,
    gen_prompts,
    v4_prompts,
    v4_strategies,
    fair_generation,
    evaluate,
)


class V11HybridStage:
    name = "v11_strict_hybrid"

    def classify(
        self, context, directory, *, assertions=None, candidates=None, shown=()
    ):
        job = dict(mode="classify", task=context.bundle, shown=list(shown))
        if assertions is not None:
            job["assertions"] = assertions
        else:
            job.update(candidates=candidates or [], requested_draws=100)
        try:
            return context.sandbox.execute(job, directory, timeout=600)
        except RuntimeError as error:
            count = len(assertions if assertions is not None else candidates or [])
            summary = dict(
                candidates=count,
                valid=0,
                removed=count,
                raw_candidates=count,
                raw_valid=0,
                oversize=0,
                trace_errors=0,
                shown_hit_counts=[0] * len(shown),
                concept_hit_counts=[0] * len(context.bundle.get("concept_meta", [])),
                concept_hit_rates=[0.0] * len(context.bundle.get("concept_meta", [])),
                requested_draws=100 if candidates is not None else count,
                raw_valid_rate=0.0,
                first_contract_message=f"classification failed: {error}",
                classification_error=str(error),
            )
            return dict(records=[], summary=summary)

    def run(self, context, arm_name, round_one, matched_requests=None):
        directory = context.directory / "arms" / arm_name
        directory.mkdir(parents=True, exist_ok=True)
        assertions = round_one["assertions"]
        shown = (
            context.bundle["concept_meta"]
            if arm_name == "concept-hybrid"
            else context.bundle["placebo_meta"]
            if arm_name == "placebo-hybrid"
            else []
        )
        first_inputs = self.classify(
            context, directory / "round1_inputs", assertions=assertions, shown=shown
        )
        missed = [
            index
            for index, hits in enumerate(first_inputs["summary"]["shown_hit_counts"])
            if not hits
        ]
        matched = arm_name in ("plain-hybrid", "placebo-hybrid")
        budget = matched_requests if matched else len(missed)
        budget = min(budget, max(0, 8 - len(round_one["calls"]) - 1))
        calls = list(round_one["calls"])
        selected = []
        attempts = []
        request_count = 0
        for request_index in range(budget):
            if matched and request_count >= budget:
                break
            if len(calls) >= 7:
                break
            if arm_name == "placebo-hybrid":
                available = missed or list(range(len(shown)))
                fact_index = (
                    available[request_index % len(available)] if shown else None
                )
            else:
                fact_index = (
                    None if arm_name == "plain-hybrid" else missed[request_index]
                )
            fact = shown[fact_index] if fact_index is not None else None
            messages = v4_prompts.hybrid_messages(context.bundle, fact, assertions)
            for retry_index in range(1 if arm_name == "plain-hybrid" else 2):
                if matched and request_count >= budget:
                    break
                if len(calls) >= 7:
                    break
                response = context.calls.complete(
                    messages,
                    v4_prompts.seed(
                        context.task["task"], arm_name, 0, 1, request_index, retry_index
                    ),
                    temperature=0,
                    top_p=1,
                    max_tokens=4096,
                )
                calls.append(response)
                request_count += 1
                attempt_directory = directory / f"request_{request_index}_{retry_index}"
                generated = None
                flagged = None
                error_text = None
                good = []
                try:
                    code = v4_strategies.checked(response["text"])
                    generated = context.sandbox.execute(
                        dict(
                            mode="draw",
                            task=context.bundle,
                            code=code,
                            seed=v4_prompts.seed(
                                context.task["task"],
                                arm_name,
                                0,
                                3,
                                request_index,
                                retry_index,
                            ),
                            n=100,
                            cap=500,
                            exclude=[],
                        ),
                        attempt_directory / "draw",
                        timeout=180,
                    )
                    flagged = self.classify(
                        context,
                        attempt_directory / "classify",
                        candidates=generated["candidates"],
                        shown=[fact] if fact else [],
                    )
                    good = [
                        record
                        for record in flagged["records"]
                        if record["valid"] and (fact is None or record["shown_hits"][0])
                    ]
                    if not good:
                        error_text = (
                            "No valid input exercised the fact."
                            if fact
                            else "No valid inputs returned."
                        )
                    if (
                        generated["nonliteral"]
                        or generated["wrong_arity"]
                        or generated["errors"]
                    ):
                        import json

                        error_text = json.dumps(
                            {
                                key: generated[key]
                                for key in ("nonliteral", "wrong_arity", "errors")
                            }
                        )
                except (SyntaxError, ValueError, RuntimeError) as error:
                    error_text = f"{type(error).__name__}: {error}"
                picked = (
                    random.Random(
                        v4_prompts.seed(
                            context.task["task"],
                            arm_name,
                            0,
                            3,
                            request_index,
                            retry_index,
                        )
                    ).sample(good, min(2, len(good)))
                    if not error_text
                    else []
                )
                selected += picked
                attempts.append(
                    dict(
                        request=request_index,
                        retry=retry_index,
                        fact_index=fact_index,
                        error=error_text,
                        selected=picked,
                    )
                )
                if not error_text or retry_index == 1 or arm_name == "plain-hybrid":
                    break
                messages += [
                    dict(role="assistant", content=response["text"]),
                    dict(
                        role="user", content=v4_prompts.RETRY.format(error=error_text)
                    ),
                ]
        selected = list({record["input_repr"]: record for record in selected}.values())
        selected = fair_generation.unseen_inputs(
            selected, assertions, context.task["entry"]
        )
        selected = selected[: max(0, 20 - len(assertions))]
        injected = []
        if selected:
            response = context.calls.complete(
                gen_prompts.strict_oracle_messages(context.bundle, selected),
                v4_prompts.seed(context.task["task"], arm_name, 0, 2),
            )
            calls.append(response)
            injected = evaluate.extract_asserts(response["text"], limit=None)
        final, missing = fair_generation.strict_assertions(
            assertions, selected, injected, context.task["entry"]
        )
        final, dropped = fair_generation.cap_assertions(final)
        classified = self.classify(
            context, directory / "final_inputs", assertions=final
        )
        result = dict(
            arm=arm_name,
            assertions=final,
            inputs=classified["records"],
            round1_assertions=assertions,
            round1_input_summary=first_inputs["summary"],
            missed_fact_indices=missed,
            round2_strategy_requests=request_count,
            generator_attempts=attempts,
            strict_missing_expected=missing,
            llm_calls=len(calls),
            physical_request_keys=[response["key"] for response in calls],
            dropped_assertions=dropped + round_one["dropped_assertions"],
        )
        if matched:
            result["matched_strategy_requests"] = matched_requests
        if matched and request_count != matched_requests:
            raise RuntimeError("V11 matched strategy request count mismatch")
        save(directory / "result.json", result)
        return result
