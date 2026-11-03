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


class V11FactsStage:
    name = "v11_facts"

    def run(self, context):
        path = context.directory / "facts.json"
        if path.exists():
            context.facts = json.loads(path.read_text())
        else:
            visible_spec = {
                key: context.human_eval[key]
                for key in ("prompt", "entry_point", "test")
            }
            context.facts = context.sandbox.execute(
                dict(mode="facts", task=context.task, he=visible_spec),
                context.directory / "fact_worker",
                timeout=3600,
            )
            if context.facts["base_ok"] is not True:
                raise ValueError("V11 base capture failed on program view")
            save(path, context.facts)
        selected = [context.facts["facts"][index] for index in context.facts["top3"]]
        placebo = context.facts["placebo3"]
        if not selected:
            from trickcatcher_linefacts.pipelines.v11_fair import spec_facts

            parameters = preconditions.specification(context.task)[2]
            specification_job = dict(
                mode="specfacts",
                entry=context.task["entry"],
                base=spec_facts.base_args(context.task["base"]),
                params=[
                    argument.arg
                    for argument in parameters.posonlyargs + parameters.args
                ],
                valid_src=context.task["mined_valid_src"],
            )
            specification_facts = context.sandbox.execute(
                specification_job,
                context.directory / "specification_facts",
                timeout=600,
            )
            if specification_facts["facts"]:
                selected = specification_facts["facts"][:3]
                placebo = specification_facts["placebo"][:3]
        context.bundle = dict(
            context.task,
            concept_meta=selected,
            concept_facts=[record["text"] for record in selected],
            placebo_meta=placebo,
            placebo_facts=[record["text"] for record in placebo],
            tool_inputs=list(
                dict.fromkeys(
                    record["witness_call"]
                    for record in selected
                    if record.get("witness_call")
                )
            ),
            doc_fail=context.facts["doc_fail"],
            facts_version="v4",
        )
        save(context.directory / "bundle.json", context.bundle)
