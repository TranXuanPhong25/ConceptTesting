"""Audit existing source/cache only: no PUT execution and no model calls."""
import ast
import collections
import json
import statistics
from pathlib import Path

from final.src.runtime.contracts import fingerprint

REPOSITORY = Path(__file__).resolve().parents[3]


class PutQualityAudit:
    def json(self, relative_path):
        return json.loads((REPOSITORY / relative_path).read_text())

    def records(self, relative_directory):
        records = []
        for path in (REPOSITORY / relative_directory).glob("*.json"):
            if path.stem.isdigit():
                records.append(json.loads(path.read_text()))
        return records

    def entry_source(self, source, entry):
        for node in ast.parse(source).body:
            if isinstance(node, ast.FunctionDef) and node.name == entry:
                return ast.unparse(node)
        raise ValueError("Missing entry point")

    def complexity(self, source):
        statements = 0
        branches = 0
        for node in ast.walk(ast.parse(source)):
            statements += isinstance(node, ast.stmt)
            branches += isinstance(node, (ast.If, ast.For, ast.While, ast.IfExp, ast.comprehension))
        return statements, branches

    def run(self):
        bundle = self.json("trickcatcher_linefacts/out/tasks_v7hyb_v4.json")["tasks"]
        facts = self.records("trickcatcher_linefacts/out/facts_v3f")
        plus = self.records("trickcatcher_linefacts/out/offline")
        cohort = self.json("final/out/cohorts/qwen35_27b_humaneval164/cohort.json")
        dataset = {}
        for line in (REPOSITORY / "final/data/humaneval.jsonl").read_text().splitlines():
            task = json.loads(line)
            dataset[task["task_id"]] = task
        vendor = REPOSITORY / "vendor/TrickCatcher/Datasets/EvalPlus/PUTs"
        old_statements, old_branches = [], []
        source_matches = 0
        for record in bundle:
            source_matches += (vendor / f"HumanEval_{record['task']}/put0.py").read_text() == record["put"]
            statements, branches = self.complexity(record["put"])
            old_statements.append(statements)
            old_branches.append(branches)
        passing_count = 0
        module_matches = 0
        entry_matches = 0
        passing_tasks = 0
        new_statements, new_branches = [], []
        for task_cohort in cohort["tasks"]:
            task = dataset[task_cohort["task_id"]]
            reference = task["prompt"] + task["canonical_solution"]
            reference_hash = fingerprint(reference, task["entry_point"])
            reference_entry_hash = fingerprint(self.entry_source(reference, task["entry_point"]), task["entry_point"])
            task_passes = 0
            for program in task_cohort["programs"]:
                if program["base"]["status"] != "pass":
                    continue
                passing_count += 1
                task_passes += 1
                module_matches += fingerprint(program["code"], task["entry_point"]) == reference_hash
                entry_matches += fingerprint(self.entry_source(program["code"], task["entry_point"]), task["entry_point"]) == reference_entry_hash
                statements, branches = self.complexity(program["code"])
                new_statements.append(statements)
                new_branches.append(branches)
            passing_tasks += task_passes > 0
        known_errors = 0
        known_error_tasks = 0
        evaluated_count = 0
        for path in (REPOSITORY / "final/out/concept_reference_v1_recovery/tasks").glob("*/result.json"):
            result = json.loads(path.read_text())
            if result.get("skip"):
                continue
            evaluated_count += result["base_pass"]
            detected_count = sum(bool(outcome["failing"]) for outcome in result["outcomes"].values())
            known_errors += detected_count
            known_error_tasks += detected_count > 0
        return {
            "old": {
                "released_vendor_files": len(list(vendor.glob("HumanEval_*/put0.py"))),
                "method_pool_cached_base_passes": len(facts),
                "cached_base_pass_true": sum(record["base_ok"] is True for record in facts),
                "cached_plus_failure_tasks": sum(record["n_fail"] > 0 for record in plus),
                "zero_plus_failure_task_ids": sorted(record["task"] for record in plus if record["n_fail"] == 0),
                "docstring_example_mismatch_task_ids": sorted(record["task"] for record in facts if record["doc_fail"]),
                "v7_pool": len(bundle), "v7_source_matches_vendor": source_matches,
                "split_counts": dict(collections.Counter(record["split"] for record in bundle)),
                "median_ast_statements": statistics.median(old_statements),
                "median_branch_loop_nodes": statistics.median(old_branches),
            },
            "new": {
                "generated": sum(record["generated"] for record in cohort["tasks"]),
                "base_pass": passing_count, "tasks_with_base_pass": passing_tasks,
                "evaluated_base_pass": evaluated_count,
                "known_reference_disagreement_programs_lower_bound": known_errors,
                "tasks_with_reference_disagreement": known_error_tasks,
                "normalized_module_matches_canonical": module_matches,
                "normalized_entry_matches_canonical": entry_matches,
                "median_ast_statements": statistics.median(new_statements),
                "median_branch_loop_nodes": statistics.median(new_branches),
            },
            "scope": "Saved source and cached labels only; zero model or PUT execution; no cohort changes",
            "limitations": ["Different test sets: old plus labels and new generated-test disagreements are not comparable defect-rate estimates.",
                            "Historical labels were not revalidated on the current interpreter.",
                            "AST similarity is not semantic equivalence.",
                            "The old HumanEval pool has been used repeatedly for method development."],
        }


if __name__ == "__main__":
    summary = PutQualityAudit().run()
    output = REPOSITORY / "final/review/put_quality/SUMMARY.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
