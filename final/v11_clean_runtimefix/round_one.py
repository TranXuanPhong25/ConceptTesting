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


class V11RoundOneStage:
    name = "v11_round_one"

    def run(self, context, arm_name):
        kind = {
            "concept-hybrid": "concept",
            "plain-hybrid": "plain",
            "placebo-hybrid": "placebo",
        }[arm_name]
        messages = gen_prompts.messages(*prompts.build(kind, context.bundle))
        seed_arm = (
            "concept"
            if kind == "concept"
            else "plain"
            if kind == "plain"
            else "placebo-hybrid"
        )
        response = context.calls.complete(
            messages, v4_prompts.seed(context.task["task"], seed_arm, 0, 0)
        )
        parsed = evaluate.extract_asserts(response["text"], limit=None)
        assertions, dropped = fair_generation.cap_assertions(parsed)
        return dict(assertions=assertions, calls=[response], dropped_assertions=dropped)
