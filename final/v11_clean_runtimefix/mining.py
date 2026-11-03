"""Class-based preparation stages, preserving V11 prompts and tool kernels."""

import ast
import json
import re
from pathlib import Path

from final.pipeline import save
from trickcatcher_linefacts.pipelines.v11_fair import (
    preconditions,
    precond_prompts,
    v4_prompts,
    v4_strategies,
)


class V11MiningStage:
    name = "v11_b5_mining"

    def run(self, context):
        path = context.directory / "mining.json"
        if path.exists():
            context.mining = json.loads(path.read_text())
            context.task.update(
                mined_valid_src=context.mining["valid_source"],
                strategy_src=context.mining["strategy_source"],
            )
            return
        specification, docstring, parameters = preconditions.specification(context.task)
        seed = 20261010 + context.task["task"]
        responses = []

        def query(stage, conditions=None):
            messages = precond_prompts.messages(stage, specification, conditions)
            response = context.calls.complete(
                messages, seed, temperature=0, top_p=1, max_tokens=4096
            )
            responses.append(response["key"])
            return response["text"]

        failure = None
        dropped = []
        try:
            candidates = preconditions.json_list(query("observation"))
            identifiers = [candidate.get("id") for candidate in candidates]
            if any(
                not isinstance(identifier, str)
                or not re.fullmatch(r"P[1-9][0-9]*", identifier)
                for identifier in identifiers
            ):
                raise ValueError("Invalid condition identifiers")
            if len(identifiers) != len(set(identifiers)) or any(
                not isinstance(candidate.get("condition"), str)
                or not candidate["condition"].strip()
                for candidate in candidates
            ):
                raise ValueError("Invalid conditions")
            confirmations = (
                preconditions.json_list(query("confirmation", candidates))
                if candidates
                else []
            )
            if len(confirmations) != len(identifiers) or {
                record.get("id") for record in confirmations
            } != set(identifiers):
                raise ValueError("Confirmation identifiers mismatch")
            kept = []
            for candidate in candidates:
                decision = next(
                    record
                    for record in confirmations
                    if record["id"] == candidate["id"]
                )
                evidence = decision.get("evidence", "")
                if type(decision.get("keep")) is not bool or not isinstance(
                    evidence, str
                ):
                    raise ValueError("Invalid confirmation schema")
                record = dict(candidate, evidence=evidence)
                if decision["keep"]:
                    kept.append(record)
                else:
                    dropped.append(dict(record, reason="confirmation_false"))
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            candidates, kept, dropped = [], [], []
            failure = type(error).__name__
        code, dropped_code = (
            preconditions.predicates(
                query("code", kept), [record["id"] for record in kept], parameters
            )
            if kept
            else ({}, [])
        )
        verification = context.sandbox.execute(
            dict(mode="verify", task=context.task, code=code, doc=docstring),
            context.directory / "predicate_verification",
            timeout=600,
        )
        valid_source = "\n".join(
            code[identifier] for identifier in verification["survivors"]
        )
        valid_source += (
            "\ndef valid(*args, **kwargs):\n    return "
            + (
                " and ".join(
                    f"{identifier}(*args, **kwargs) is True"
                    for identifier in verification["survivors"]
                )
                or "True"
            )
            + "\n"
        )
        surviving_conditions = [
            record["condition"]
            for record in kept
            if record["id"] in verification["survivors"]
        ]
        context.task["mined_valid_src"] = valid_source
        messages = v4_prompts.domain_messages(context.task, surviving_conditions)
        attempts = []
        fallback = False
        for retry_index in range(2):
            response = context.calls.complete(
                messages, seed, temperature=0, top_p=1, max_tokens=4096
            )
            responses.append(response["key"])
            try:
                strategy_source = v4_strategies.checked(response["text"])
                draws = context.sandbox.execute(
                    dict(
                        mode="draw",
                        task=context.task,
                        code=strategy_source,
                        seed=seed,
                        n=100,
                        cap=500,
                        exclude=[],
                    ),
                    context.directory / f"domain_attempt_{retry_index}",
                    timeout=180,
                )
                if (
                    draws["nonliteral"]
                    or draws["wrong_arity"]
                    or not draws["candidates"]
                    or draws["errors"]
                ):
                    raise ValueError(
                        json.dumps(
                            {
                                key: draws[key]
                                for key in (
                                    "nonliteral",
                                    "wrong_arity",
                                    "valid",
                                    "errors",
                                )
                            }
                        )
                    )
                break
            except (SyntaxError, ValueError, RuntimeError) as error:
                error_text = str(error)
                attempts.append(error_text)
                messages += [
                    dict(role="assistant", content=response["text"]),
                    dict(
                        role="user", content=v4_prompts.RETRY.format(error=error_text)
                    ),
                ]
        else:
            fallback = True
            strategy_source, missing_annotations = v4_strategies.fallback_source(
                context.task
            )
            draws = context.sandbox.execute(
                dict(
                    mode="draw",
                    task=context.task,
                    code=strategy_source,
                    seed=seed,
                    n=100,
                    cap=500,
                    exclude=[],
                ),
                context.directory / "domain_fallback",
                timeout=180,
            )
        context.task.update(strategy_src=strategy_source)
        context.mining = dict(
            valid_source=valid_source,
            strategy_source=strategy_source,
            candidates=candidates,
            kept=kept,
            dropped=dropped,
            dropped_code=dropped_code,
            verification=verification,
            fallback=fallback,
            domain_attempt_errors=attempts,
            mining_failure=failure,
            physical_request_keys=responses,
        )
        save(path, context.mining)
