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


from .round_one import V11RoundOneStage
from .hybrid import V11HybridStage


class V11Arm:
    """Expose V11 as one benchmark family with its required matched controls."""

    name = "v11"

    def run(self, context):
        first = V11RoundOneStage()
        hybrid = V11HybridStage()
        concept = hybrid.run(
            context, "concept-hybrid", first.run(context, "concept-hybrid")
        )
        plain = hybrid.run(
            context,
            "plain-hybrid",
            first.run(context, "plain-hybrid"),
            concept["round2_strategy_requests"],
        )
        placebo = hybrid.run(
            context,
            "placebo-hybrid",
            first.run(context, "placebo-hybrid"),
            concept["round2_strategy_requests"],
        )
        context.arm_results.update(
            v11_concept=concept, v11_plain=plain, v11_placebo=placebo
        )
        # Original V11 witness parser, retaining the first3valid tool inputs.
        from trickcatcher_linefacts.pipelines.v11_fair import gen_inputs

        candidates = [
            dict(input_repr=repr(tuple(ast.literal_eval(record["input_repr"]))))
            for record in gen_inputs.witness_candidates(context.bundle)
        ]
        flagged = hybrid.classify(
            context, context.directory / "tool_inputs", candidates=candidates
        )
        valid = [record for record in flagged["records"] if record["valid"]][:3]
        context.arm_results["v11_witness"] = dict(inputs=valid, llm_calls=0)
        response = context.calls.complete(
            gen_prompts.oracle_messages(context.bundle, valid),
            v4_prompts.seed(context.task["task"], "toolinput", 0, 2),
        )
        assertions = evaluate.extract_asserts(response["text"], limit=None)[:20]
        checked = hybrid.classify(
            context, context.directory / "tool_assertions", assertions=assertions
        )
        context.arm_results["v11_toolinput"] = dict(
            inputs=checked["records"],
            assertions=assertions,
            llm_calls=1,
            physical_request_keys=[response["key"]],
        )
        save(context.directory / "arm_results.json", context.arm_results)
