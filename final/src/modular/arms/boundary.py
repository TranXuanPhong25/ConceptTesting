"""Allocate the task input budget to direct soft-BVA calls for visible PUTs."""
from dataclasses import replace

from .base import InputGenerationMethod
from ..boundary_value_analysis import BoundarySettings, BoundaryValueAnalysis


class BoundaryArm(InputGenerationMethod):
    name = "boundary"
    uses_shared_prompt = False

    def __init__(self, *, base_example_limit=12):
        BoundarySettings(base_example_limit=base_example_limit)
        self.base_example_limit = base_example_limit

    def configuration(self):
        return {"pipeline_contract": "soft-bva-v1", "base_example_limit": self.base_example_limit,
                "allocation": "equal-fixed-shares-over-visible-PUTs",
                "input_budget": "shared-task-budget-no-redistribution",
                "generator": "one-direct-input-call-per-allocated-PUT"}

    def build_guidance(self, packet):
        from ..boundary_value_analysis.prompts import GUIDANCE
        return GUIDANCE

    def settings_for_context(self, context):
        settings = context.settings
        return BoundarySettings(input_budget=settings.input_budget, base_example_limit=self.base_example_limit,
            input_tokens=settings.input_tokens, input_temperature=settings.input_temperature,
            context_tokens=settings.context_tokens, seed=settings.input_seed)

    def run(self, context):
        if context.packet is None or context.cohort_task is None:
            raise RuntimeError("Boundary arm requires the frozen cohort and visibility packet")
        settings = self.settings_for_context(context)
        programs_by_id = {program["id"]: program for program in context.cohort_task["programs"]
                          if program["base"]["status"] == "pass"}
        visible_programs = [programs_by_id[identifier] for identifier in context.packet["visible_put_ids"]]
        allocated_programs = visible_programs[:settings.input_budget]
        allocations = {}
        if allocated_programs:
            quotient, remainder = divmod(settings.input_budget, len(allocated_programs))
            for index, program in enumerate(allocated_programs):
                allocations[program["id"]] = quotient + (index < remainder)
        context.artifacts.write(context.task_directory + "/boundary_plan.json", {
            "task_id": context.task["task_id"], "pipeline_contract": "soft-bva-v1",
            "task_input_budget": settings.input_budget, "visible_put_ids": context.packet["visible_put_ids"],
            "programs": [{"program_id": program["id"], "input_budget": allocations.get(program["id"], 0)}
                         for program in visible_programs],
        })
        accepted, rejected, program_results, seen = [], [], [], set()
        for program in visible_programs:
            identifier = program["id"]
            allocation = allocations.get(identifier, 0)
            if allocation:
                module = BoundaryValueAnalysis(replace(settings, input_budget=allocation))
                result = module.run_for_program(context.task, program, contract=context.metadata["contract"],
                    artifacts=context.artifacts, calls=context.calls)
            else:
                result = {"status": "input_budget_exhausted", "inputs": [], "rejected": [],
                          "logical_calls": {"generation": False}}
            record = {"program_id": identifier, "input_budget": allocation, "status": result["status"],
                      "generated_inputs": len(result["inputs"]), "retained_inputs": 0,
                      "logical_calls": result["logical_calls"]}
            program_results.append(record)
            rejected.extend({"program_id": identifier, **item} for item in result["rejected"])
            for index, item in enumerate(result["inputs"]):
                identity = item["args"], item["kwargs"]
                if identity in seen:
                    rejected.append({"program_id": identifier, "index": index, "reason": "duplicate_across_programs"})
                    continue
                seen.add(identity)
                accepted.append({**item, "program_id": identifier, "guidance_id": f"soft_bva_{identifier}"})
                record["retained_inputs"] += 1
        statuses = {record["status"] for record in program_results}
        status = "generated" if accepted else (next(iter(statuses)) if len(statuses) == 1 else "no_inputs")
        result = {"status": status, "skip": None if accepted else status, "inputs": accepted,
                  "rejected": rejected, "programs": program_results, "task_input_budget": settings.input_budget,
                  "domain_validation": "pending_shared_reference_oracle"}
        context.artifacts.write(context.task_directory + "/boundary_arm.json", result)
        return result

    def extend_summary(self, contexts, summary, reporting):
        accounting = {"pipeline_contract": "soft-bva-v1", "task_statuses": {}, "program_statuses": {},
                      "allocated_programs": 0, "retained_inputs": 0, "logical_calls": {"generation": 0},
                      "budget_policy": self.configuration()["allocation"],
                      "comparison_scope": "one call per allocated PUT; multi-PUT costs may differ from plain"}
        for context in contexts:
            result = (context.inputs or {}).get("arms", {}).get(self.name)
            if result is None:
                continue
            reporting.increment(accounting["task_statuses"], result["status"])
            for program in result["programs"]:
                reporting.increment(accounting["program_statuses"], program["status"])
                accounting["allocated_programs"] += program["input_budget"] > 0
                accounting["retained_inputs"] += program["retained_inputs"]
                accounting["logical_calls"]["generation"] += int(program["logical_calls"]["generation"])
        summary["boundary_analysis"] = accounting
