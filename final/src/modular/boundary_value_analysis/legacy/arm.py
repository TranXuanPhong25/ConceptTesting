"""Adapt per-PUT BVA to the shared task budget and reference-oracle pipeline."""
from __future__ import annotations

from dataclasses import replace

from ...arms.base import InputGenerationMethod
from .pipeline import BoundarySettings, BoundaryValueAnalysis
from .stages import frozen_value
from .types import entry_function, input_signature, literal_arguments


class BoundaryArm(InputGenerationMethod):
    name = "boundary"
    uses_shared_prompt = False

    def __init__(self, *, boundary_budget=4, selection_tokens=4096, base_example_limit=12, construction_mode="compiled", grounding_mode="off"):
        # Validate the arm-specific settings using the module's public contract.
        BoundarySettings(boundary_budget=boundary_budget, selection_tokens=selection_tokens,
                         base_example_limit=base_example_limit, construction_mode=construction_mode, grounding_mode=grounding_mode)
        self.boundary_budget = boundary_budget
        self.selection_tokens = selection_tokens
        self.base_example_limit = base_example_limit
        self.construction_mode = construction_mode
        self.grounding_mode = grounding_mode

    def configuration(self):
        configuration = {"boundary_budget": self.boundary_budget, "selection_tokens": self.selection_tokens,
                "base_example_limit": self.base_example_limit,
                "construction_mode": self.construction_mode,
                "pipeline_contract": "typed-target-context-v3",
                "allocation": "equal-fixed-shares-over-template-eligible-visible-PUTs",
                "input_budget": "shared-task-budget-no-redistribution",
                "generator": "up-to-two-calls-per-allocated-PUT", "plain_fallback": False}
        if self.grounding_mode != "off":
            configuration["grounding_mode"] = self.grounding_mode
        return configuration

    def build_guidance(self, packet):
        return "Boundary selection and construction use their own per-PUT prompts."

    def settings_for_context(self, context):
        return BoundarySettings(
            boundary_budget=self.boundary_budget, input_budget=context.settings.input_budget,
            base_example_limit=self.base_example_limit, selection_tokens=self.selection_tokens,
            input_tokens=context.settings.input_tokens, input_temperature=context.settings.input_temperature,
            context_tokens=context.settings.context_tokens, seed=context.settings.input_seed,
            construction_mode=self.construction_mode,
            grounding_mode=self.grounding_mode,
        )

    def run(self, context):
        if context.packet is None or context.cohort_task is None:
            raise RuntimeError("Boundary arm requires the frozen cohort and visibility packet")
        settings = self.settings_for_context(context)
        analysis = BoundaryValueAnalysis(settings)
        programs_by_id = {program["id"]: program for program in context.cohort_task["programs"]
                          if program["base"]["status"] == "pass"}
        visible_programs = [programs_by_id[identifier] for identifier in context.packet["visible_put_ids"]]
        inspections = {}
        eligible_identifiers = []
        for program in visible_programs:
            inspection = analysis.extract(
                specification=context.task["prompt"], entry_point=context.task["entry_point"],
                program_source=program["code"], base_inputs=program["base"].get("calls", []),
                contract=context.metadata["contract"],
            )
            inspections[program["id"]] = inspection
            if inspection["input_types"]["status"] == "extracted" and inspection["templates"]["candidates"]:
                eligible_identifiers.append(program["id"])
        allocated_identifiers = eligible_identifiers[:settings.input_budget]
        allocations = {}
        if allocated_identifiers:
            quotient, remainder = divmod(settings.input_budget, len(allocated_identifiers))
            for index, identifier in enumerate(allocated_identifiers):
                allocations[identifier] = quotient + (index < remainder)
        plan = {
            "task_id": context.task["task_id"], "task_input_budget": settings.input_budget,
            "visible_put_ids": context.packet["visible_put_ids"],
            "programs": [{"program_id": program["id"], "input_budget": allocations.get(program["id"], 0),
                          **inspections[program["id"]]} for program in visible_programs],
        }
        context.artifacts.write(context.task_directory + "/boundary_plan.json", plan)
        task_signature = input_signature(entry_function(context.task["prompt"], context.task["entry_point"]))
        accepted = []
        rejected = []
        program_results = []
        seen = set()
        for program in visible_programs:
            identifier = program["id"]
            inspection = inspections[identifier]
            allocation = allocations.get(identifier, 0)
            if not allocation:
                status = inspection["input_types"]["status"]
                if status == "extracted":
                    status = "input_budget_exhausted" if identifier in eligible_identifiers else "no_templates"
                result = {"status": status, "inputs": [], "rejected": [], "boundaries": [],
                          "logical_calls": {"selection": False, "generation": False}}
            else:
                module = BoundaryValueAnalysis(replace(settings, input_budget=allocation))
                result = module.run_for_program(context.task, program, contract=context.metadata["contract"],
                                                artifacts=context.artifacts, calls=context.calls)
            record = {"program_id": identifier, "input_budget": allocation, "status": result["status"],
                      "selected_boundaries": len(result["boundaries"]), "generated_inputs": len(result["inputs"]),
                      "retained_inputs": 0, "logical_calls": result["logical_calls"]}
            program_results.append(record)
            for rejection in result["rejected"]:
                rejected.append({"program_id": identifier, **rejection})
            for input_index, input_record in enumerate(result["inputs"]):
                # VALIDATION START: task signature and duplicates across PUTs.
                try:
                    identity = self.validate_task_input(input_record, task_signature)
                except (ValueError, SyntaxError, TypeError, RecursionError):
                    rejected.append({"program_id": identifier, "index": input_index,
                                     "reason": "task_signature_mismatch"})
                    continue
                if identity in seen:
                    rejected.append({"program_id": identifier, "index": input_index,
                                     "reason": "duplicate_across_programs"})
                    continue
                # VALIDATION END: task signature and duplicates across PUTs.
                seen.add(identity)
                accepted.append({**input_record, "program_id": identifier,
                                 "guidance_id": f"bva_{identifier}_{input_record['boundary_id']}"})
                record["retained_inputs"] += 1
        statuses = {record["status"] for record in program_results}
        status = "generated" if accepted else (next(iter(statuses)) if len(statuses) == 1 else "no_inputs")
        if status == "generated" and not accepted:
            status = "no_inputs"
        arm_result = {
            "status": status, "skip": None if accepted else status, "inputs": accepted, "rejected": rejected,
            "programs": program_results, "task_input_budget": settings.input_budget,
            "domain_validation": "pending_shared_reference_oracle",
        }
        context.artifacts.write(context.task_directory + "/boundary_arm.json", arm_result)
        return arm_result

    @staticmethod
    def validate_task_input(input_record, task_signature):
        """Bind a PUT-generated call to the shared task interface for deduplication."""
        arguments, keywords = literal_arguments(input_record)
        bound = task_signature.bind(*arguments, **keywords)
        bound.apply_defaults()
        return frozen_value(dict(bound.arguments))

    def extend_summary(self, contexts, summary, reporting):
        accounting = {"task_statuses": {}, "program_statuses": {}, "allocated_programs": 0,
                      "selected_boundaries": 0, "retained_inputs": 0,
                      "logical_calls": {"selection": 0, "generation": 0},
                      "budget_policy": self.configuration()["allocation"],
                      "comparison_scope": "descriptive; calls not matched to one-call plain"}
        for context in contexts:
            arm_result = (context.inputs or {}).get("arms", {}).get(self.name)
            if arm_result is None:
                continue
            reporting.increment(accounting["task_statuses"], arm_result["status"])
            for program in arm_result["programs"]:
                reporting.increment(accounting["program_statuses"], program["status"])
                accounting["allocated_programs"] += program["input_budget"] > 0
                accounting["selected_boundaries"] += program["selected_boundaries"]
                accounting["retained_inputs"] += program["retained_inputs"]
                for phase, used in program["logical_calls"].items():
                    accounting["logical_calls"][phase] += int(used)
        summary["boundary_analysis"] = accounting
