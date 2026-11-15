"""Recheck saved BVA bindings/targets offline, without any model or native execution."""
import argparse
import json
from collections import Counter
from pathlib import Path

from final.src.modular.dataset import load_tasks
from final.src.modular.boundary_value_analysis.legacy import BoundaryValueAnalysis, BoundarySettings
from final.src.modular.boundary_value_analysis.legacy.pipeline import BoundaryContext
from final.src.modular.boundary_value_analysis.legacy.stages import BoundarySelection
from final.src.modular.boundary_value_analysis.legacy.construction import TargetCompiler


def audit(source_run, cohort_path):
    cohort = json.loads(Path(cohort_path).read_text())
    tasks = {task["task_id"]: task for task in load_tasks()}
    metadata = json.loads(Path("final/data/contracts.json").read_text())
    counts = Counter()
    rows = []
    public_guards = []
    for record in cohort["tasks"]:
        task = tasks[record["task_id"]]
        number = int(task["task_id"].split("/")[-1])
        program = record["programs"][0]
        context = BoundaryContext(number, str(program["id"]), task["entry_point"], task["prompt"],
            metadata[task["task_id"]]["contract"], program["code"], program["base"].get("calls", []),
            BoundarySettings(), None, None)
        inspected = BoundaryValueAnalysis().extract(specification=context.specification,
            entry_point=context.entry_point, program_source=context.program_source,
            base_inputs=context.base_inputs, contract=context.contract)
        context.input_types = inspected["input_types"]
        context.templates = inspected["templates"]
        context.guidance = inspected["guidance"]
        path = Path(source_run) / "tasks" / str(number) / "boundary" / str(program["id"]) / "selection.json"
        selected = json.loads(path.read_text())
        accepted = []
        rejected = []
        for boundary in selected["boundaries"]:
            try:
                accepted.append(BoundarySelection.validate(boundary, context))
                counts["passed_new_structural_checks"] += 1
            except (ValueError, KeyError, TypeError) as error:
                reason = str(error) if type(error) is ValueError else type(error).__name__
                rejected.append({"id": boundary["id"], "reason": reason})
                counts[reason] += 1
        row = {"task_id": task["task_id"], "old_status": selected["status"],
               "old_boundaries": len(selected["boundaries"]), "supported_binding_checks": len(accepted),
               "rejected": rejected}
        if accepted:
            context.selection = {"boundaries": accepted}
            compiled = TargetCompiler().run(context)
            row.update(closed_scalar=compiled["closed_scalar"], closed_new_inputs=len(compiled["closed_inputs"]),
                       compiled_obligations=len(compiled["obligations"]), blocked=compiled["blocked"])
        rows.append(row)
        if number in (30, 52, 146):
            public_guards.append({"task_id": task["task_id"], "candidate_guards": context.guidance["candidate_guards"]})
    return {"scope": "Saved selections; no model, PUT, reference or benchmark execution",
            "original_artifacts_modified": False, "model_calls": 0, "counts": dict(counts), "tasks": rows,
            "previously_missed_public_guards": public_guards, "semantic_precision_claim": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, default=Path("final/out/boundary_all_plain_bva_20261105"))
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("final/review/boundary_repair_offline_2026-11-05.json"))
    options = parser.parse_args()
    result = audit(options.source_run, options.cohort)
    options.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result["counts"], indent=2))


if __name__ == "__main__":
    main()
