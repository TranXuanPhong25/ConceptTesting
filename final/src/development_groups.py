"""Course-based development subsets. Reads source/base caches, never calls a model.

Build the inventory once, then export small frozen cohorts for one testing method.
The running full benchmark is not modified by this offline development utility.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.metadata
import json
from collections import Counter, defaultdict
from pathlib import Path

from coverage.parser import PythonParser
from python_graphs import program_graph, program_graph_dataclasses

from final.src.modular.cohort import load_cohort
from final.src.runtime.artifacts import digest, save
from final.src.modular.dataset import load_tasks


REPOSITORY = Path(__file__).resolve().parents[2]
REVIEW = REPOSITORY / "final/review/development_groups"
DATA = REPOSITORY / "final/data/development_groups"
COHORT = REPOSITORY / "final/out/cohorts/qwen35_27b_humaneval164/cohort.json"
GROUPS = ("boundary", "equivalence", "statement", "def_use")
SLIDE_FILES = (
    "03. Kiem thu chuc nang.pdf", "04.Kiem_thu_dong_dieu_khien.pdf",
    "05.Kiem thu dong du lieu-2-2 (2).pdf",
)
PREFERRED_TASKS = {
    "boundary": {"smoke": [0, 18, 65, 81, 99, 120],
                 "development": [5, 47, 71, 115, 124, 140], "check": [2, 77, 138, 159]},
    "equivalence": {"smoke": [11, 22, 26, 51, 85, 137],
                    "development": [54, 78, 98, 104, 128, 151], "check": [7, 27, 116, 158]},
    "statement": {"smoke": [12, 31, 68, 88, 125, 141],
                  "development": [24, 43, 64, 90, 118, 161], "check": [40, 82, 95, 150]},
    "def_use": {"smoke": [1, 3, 9, 25, 46, 114],
                "development": [6, 8, 55, 61, 111, 123], "check": [13, 63, 106, 139]},
}


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_review():
    with (DATA / "task_review.tsv").open() as source:
        records = list(csv.DictReader(source, delimiter="\t"))
    if [int(record["task_number"]) for record in records] != list(range(164)):
        raise ValueError("Manual task review must contain each of the164tasks exactly once")
    for record in records:
        labels = [record["primary"], *record["secondary"].split(",")]
        if len(labels) != len(set(labels)) or not set(labels) <= set(GROUPS):
            raise ValueError("Invalid or duplicate course group labels")
    return records


class ProgramStructure:
    """Static library graphs and cached line coverage; no execution/bug labels."""

    def analyze(self, program):
        source = program["code"]
        syntax = ast.parse(source)
        parser = PythonParser(text=source)
        parser.parse_source()
        # Exclude import/definition execution at module load. C1 below is a
        # coverage.py executable-line proxy, not exact AST-statement coverage.
        excluded_lines = set()
        scopes = {}
        for node in ast.walk(syntax):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                excluded_lines.add(node.lineno)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for line in range(node.lineno, node.end_lineno + 1):
                    scopes[line] = f"{node.name}@{node.lineno}"
        executable_lines = sorted(set(parser.statements) - excluded_lines)
        coverage = program["base"].get("coverage")
        missing_lines = None
        if coverage is not None:
            missing_lines = sorted(set(executable_lines) - set(coverage["lines"]))
        loops = [node for node in ast.walk(syntax) if isinstance(node, (ast.For, ast.While, ast.AsyncFor))]
        updates = [node for node in ast.walk(syntax) if isinstance(node, ast.AugAssign)]
        augmented_reads = {(node.target.id, node.target.lineno, node.target.col_offset)
                           for node in updates if isinstance(node.target, ast.Name)}
        graph_error = None
        flow_edges = set()
        pairs = set()
        try:
            graph = program_graph.get_program_graph(source)
            for edge in graph.edges:
                if edge.type not in (program_graph_dataclasses.EdgeType.CFG_NEXT,
                                     program_graph_dataclasses.EdgeType.LAST_WRITE):
                    continue
                access = graph.nodes[edge.id1].ast_node
                previous = graph.nodes[edge.id2].ast_node
                access_line = getattr(access, "lineno", None)
                definition_line = getattr(previous, "lineno", None)
                if access_line is None or definition_line is None:
                    continue
                if edge.type == program_graph_dataclasses.EdgeType.CFG_NEXT:
                    flow_edges.add((access_line, definition_line))
                    continue
                variable = getattr(access, "id", None)
                is_read = type(getattr(access, "ctx", None)).__name__ == "Load"
                is_update_read = (variable, access_line, getattr(access, "col_offset", None)) in augmented_reads
                if isinstance(variable, str) and (is_read or is_update_read):
                    pairs.add((scopes.get(access_line), variable, definition_line, access_line))
        except Exception as error:
            graph_error = type(error).__name__
        incoming_definitions = defaultdict(set)
        for scope, variable, definition, use in pairs:
            incoming_definitions[(scope, variable, use)].add(definition)
        alternatives = [{"scope": scope, "variable": variable, "use_line": use,
                         "definition_lines": sorted(definitions)}
                        for (scope, variable, use), definitions in sorted(incoming_definitions.items(), key=str)
                        if len(definitions) > 1]
        loop_updates = []
        for node in updates:
            if any(loop.lineno <= node.lineno <= loop.end_lineno for loop in loops):
                loop_updates.append({"line": node.lineno, "expression": ast.unparse(node)})
        for node in ast.walk(syntax):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            assigned = {child.id for target in targets for child in ast.walk(target) if isinstance(child, ast.Name)}
            read_names = {child.id for child in ast.walk(node.value) if isinstance(child, ast.Name)} if node.value else set()
            if assigned & read_names and any(loop.lineno <= node.lineno <= loop.end_lineno for loop in loops):
                loop_updates.append({"line": node.lineno, "expression": ast.unparse(node)})
        return {
            "executable_line_count": len(executable_lines), "base_coverage_known": coverage is not None,
            "base_uncovered_lines": missing_lines, "static_cfg_edges": len(flow_edges),
            "static_def_use_pair_count": len(pairs), "alternative_reaching_definitions": alternatives,
            "loop_update_sites": loop_updates, "loop_count": len(loops),
            "graph_error": graph_error,
            "data_flow_status": "static-may-flow; dynamic def-clear coverage UNKNOWN",
        }


class DevelopmentGroups:
    def __init__(self):
        self.cohort = load_cohort(COHORT)
        self.tasks = {task["task_id"]: task for task in load_tasks()}
        self.reviews = read_review()

    def build(self):
        structure = ProgramStructure()
        task_records = []
        for review, cohort_task in zip(self.reviews, self.cohort["tasks"]):
            number = int(review["task_number"])
            task_id = f"HumanEval/{number}"
            if cohort_task["task_id"] != task_id:
                raise ValueError("Cohort task order changed")
            specification = self.tasks[task_id]
            labels = [review["primary"], *review["secondary"].split(",")]
            programs = []
            for program in cohort_task["programs"]:
                record = {"program_id": program["id"], "raw_source_sha256": hashlib.sha256(program["code"].encode()).hexdigest(),
                          "base_status": program["base"]["status"], "fit": {group: False for group in GROUPS}}
                if program["base"]["status"] == "pass":
                    evidence = structure.analyze(program)
                    record["structure"] = evidence
                    for group in labels:
                        if group in ("boundary", "equivalence"):
                            record["fit"][group] = True
                        elif group == "statement":
                            record["fit"][group] = (evidence["graph_error"] is None
                                and bool(evidence["base_uncovered_lines"]))
                        else:
                            record["fit"][group] = (evidence["graph_error"] is None
                                and evidence["static_def_use_pair_count"] > 0
                                and bool(evidence["alternative_reaching_definitions"] or evidence["loop_update_sites"]))
                programs.append(record)
            old_source = REPOSITORY / f"vendor/TrickCatcher/Datasets/EvalPlus/PUTs/HumanEval_{number}/put0.py"
            record = dict(review, task_id=task_id, entry_point=specification["entry_point"],
                          prompt_sha256=digest(specification["prompt"]), base_tests_sha256=digest(specification["test"]),
                          generated=cohort_task["generated"], programs=programs,
                          old_trickcatcher_source_available=old_source.is_file())
            task_records.append(record)
        inventory = {
            "schema": "course-development-groups-1", "selection_is_outcome_blind": True,
            "source_cohort_sha256": self.cohort["cohort_sha256"],
            "task_review_sha256": checksum(DATA / "task_review.tsv"),
            "builder_sha256": checksum(__file__), "task_records": task_records,
            "slides_sha256": {name: checksum(REPOSITORY / "test_slides" / name) for name in SLIDE_FILES},
            "library_versions": {name: importlib.metadata.version(name) for name in ("coverage", "python-graphs")},
            "limitations": [
                "Primary labels are manual development priorities, not exclusive bug categories.",
                "Statement fit needs a cached uncovered executable line and a supported static graph; feasibility remains unknown.",
                "Static def-use candidates do not establish uncovered def-clear paths; heap/alias mutation is not modeled.",
                "No reference source, plus tests, detected outcomes or model responses select tasks/PUTs.",
                "Check subsets are development checks, not a scientifically held-out dataset.",
                "Old TrickCatcher availability is source availability only; no current-runtime qualification is asserted.",
            ],
        }
        save(DATA / "inventory.json", inventory)
        self.write_plans(inventory)
        return inventory

    def verify_inventory(self, inventory):
        if inventory["source_cohort_sha256"] != self.cohort["cohort_sha256"]:
            raise ValueError("Inventory belongs to a different PUT cohort")
        if inventory["task_review_sha256"] != checksum(DATA / "task_review.tsv"):
            raise ValueError("Manual classification changed; rebuild inventory")
        if inventory["builder_sha256"] != checksum(__file__):
            raise ValueError("Inventory analysis code changed; rebuild inventory")
        for name, expected in inventory["slides_sha256"].items():
            if checksum(REPOSITORY / "test_slides" / name) != expected:
                raise ValueError("Course slides changed; review the classification")
        for name, expected in inventory["library_versions"].items():
            if importlib.metadata.version(name) != expected:
                raise ValueError("Graph/coverage library changed; rebuild inventory")

    @staticmethod
    def representative(task, group):
        candidates = [program for program in task["programs"] if program["fit"][group]]
        if not candidates:
            return None
        # Favor an observable structural obligation, then use source order. Never
        # rank by revealed bugs, generated suites, oracle outputs or model results.
        def priority(program):
            evidence = program["structure"]
            if group == "statement":
                return (-len(evidence["base_uncovered_lines"]), program["program_id"])
            if group == "def_use":
                return (-len(evidence["alternative_reaching_definitions"]), program["program_id"])
            return (0, program["program_id"])
        return min(candidates, key=priority)

    def make_plan(self, inventory, group):
        by_number = {int(task["task_number"]): task for task in inventory["task_records"]}
        available = [number for number, task in by_number.items()
                     if task["primary"] == group and self.representative(task, group) is not None]
        preferences = PREFERRED_TASKS[group]
        selected = {}
        used = set()
        # Reserve check tasks before filling smoke/dev so no task leaks between tiers.
        reserved_check = [number for number in preferences["check"] if number in available]
        for tier, desired, target in (("check", reserved_check, 4),
                                      ("smoke", preferences["smoke"], 6),
                                      ("development_extra", preferences["development"], 6)):
            blocked = used | (set(reserved_check) if tier != "check" else set())
            candidates = [number for number in desired + available if number in available and number not in blocked]
            chosen = []
            for number in candidates:
                if number not in chosen:
                    chosen.append(number)
                if len(chosen) == target:
                    break
            selected[tier] = chosen
            used.update(chosen)
        selected["development"] = selected["smoke"] + selected.pop("development_extra")
        selected["all"] = available
        return {"group": group, "primary_task_count": sum(task["primary"] == group for task in by_number.values()),
                "ready_task_count": len(available), "tiers": selected,
                "representatives": {str(number): self.representative(by_number[number], group)["program_id"]
                                    for number in available}}

    def write_plans(self, inventory):
        plans = {group: self.make_plan(inventory, group) for group in GROUPS}
        save(DATA / "subsets.json", {"inventory_sha256": digest(inventory), "groups": plans})
        lines = ["# Bốn nhóm development theo test_slides", "",
                 "Phân loại toàn bộ164task và source PUT, không chạy model/reference/plus tests.",
                 "Mỗi task có một nhóm chính và nhiều nhãn phụ. Đây là nhóm ưu tiên phát triển, không phải nhãn loại bug.", "",
                 "| Nhóm | Task chính | Task có PUT phù hợp | Smoke | Development | Check |",
                 "|---|---:|---:|---|---|---|"]
        for group, plan in plans.items():
            lists = [", ".join(map(str, plan["tiers"][tier])) for tier in ("smoke", "development", "check")]
            lines.append(f"| {group} | {plan['primary_task_count']} | {plan['ready_task_count']} | {' | '.join(lists)} |")
        lines += ["", "Smoke≤6PUT/group, development≤12, check≤4; default dùng một PUT/task.",
                  "Development bao gồm smoke; check tách theo task khỏi development của cả4nhóm.",
                  "PUT chọn từ source/base evidence, không chọn bằng kết quả phát hiện lỗi. Nhóm ít candidate có thể thiếu quota.", "",
                  "## Toàn bộ164task", "", "| Task | Entry point | Nhóm chính | Nhãn phụ | Obligation cần phát triển |",
                  "|---|---|---|---|---|"]
        for task in inventory["task_records"]:
            objective = task["development_obligation"].replace("|", "\\|")
            lines.append(f"| {task['task_number']} | {task['entry_point']} | {task['primary']} | {task['secondary']} | {objective} |")
        lines += ["", "## Giới hạn", ""] + [f"- {limitation}" for limitation in inventory["limitations"]]
        (REVIEW / "REPORT.md").write_text("\n".join(lines) + "\n")

    def export(self, group, tier, output, *, all_programs=False):
        inventory = json.loads((DATA / "inventory.json").read_text())
        self.verify_inventory(inventory)
        plan = self.make_plan(inventory, group)
        numbers = plan["tiers"][tier]
        if not numbers:
            raise ValueError("No ready tasks for this group/tier")
        by_identifier = {task["task_id"]: task for task in self.cohort["tasks"]}
        tasks = []
        owners = []
        for number in numbers:
            original = by_identifier[f"HumanEval/{number}"]
            if all_programs:
                selected_task = original
                selected_ids = [program["id"] for program in original["programs"] if program["base"]["status"] == "pass"]
            else:
                identifier = plan["representatives"][str(number)]
                program = next(program for program in original["programs"] if program["id"] == identifier)
                selected_task = dict(original, programs=[program], generated=1, base_pass=1, status="complete")
                selected_ids = [identifier]
            tasks.append(selected_task)
            owners.append({"task_id": original["task_id"], "program_ids": selected_ids})
        selection = {"group": group, "tier": tier, "task_ids": [task["task_id"] for task in tasks],
                     "selected_puts": owners, "target_programs": 10 if all_programs else 1,
                     "parent_cohort_sha256": self.cohort["cohort_sha256"],
                     "inventory_sha256": digest(inventory), "outcome_blind": True,
                     "purpose": "development; subset selection does not isolate generator guidance"}
        cohort = dict(self.cohort, tasks=tasks, cohort_sha256=digest(tasks), development_selection=selection)
        output = Path(output).resolve()
        if output.exists() and any(output.iterdir()):
            raise ValueError("Export requires an empty output directory; do not overwrite a run/checkpoint")
        output.mkdir(parents=True, exist_ok=True)
        save(output / "cohort.json", cohort)
        save(output / "selection.json", selection)
        return selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("build", "export"))
    parser.add_argument("--group", choices=GROUPS)
    parser.add_argument("--tier", choices=("smoke", "development", "check", "all"), default="smoke")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--all-programs", action="store_true")
    options = parser.parse_args()
    builder = DevelopmentGroups()
    if options.operation == "build":
        inventory = builder.build()
        print(json.dumps({"tasks_reviewed": len(inventory["task_records"]),
                          "primary_groups": dict(Counter(task["primary"] for task in inventory["task_records"])),
                          "report": str(REVIEW / "REPORT.md")}, ensure_ascii=False, indent=2))
    else:
        if options.group is None or options.output is None:
            parser.error("export requires --group and --output")
        print(json.dumps(builder.export(options.group, options.tier, options.output,
                                        all_programs=options.all_programs), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
