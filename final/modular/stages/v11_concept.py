"""Extract V11 facts only. No V11 assertion, hybrid, or expected-output generation."""
from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from final.pipeline import digest, save
from final.v11_clean_runtimefix.cohort import V11ProgramView
from final.v11_clean_runtimefix.context import V11Context
from final.v11_clean_runtimefix.mining import V11MiningStage
from final.v11_clean_runtimefix.facts import V11FactsStage
from final.v11_clean_runtimefix.model_calls import V11ModelCalls
from final.v11_clean_runtimefix.sandbox import V11Sandbox, WorkerStalled
from final.experiments.concept_reference_v1_recovery.model import TransportError
from final.experiments.concept_reference_v1_recovery.checkpoint import CompletionRetryLimit
from .base import PipelineStage
from ..calls import V11PreparationCalls


REPOSITORY = Path(__file__).resolve().parents[3]
WORKER_PACKAGES = {"hypothesis": "6.169.0", "mutmut": "3.8.0",
                   "coverage": "7.16.2", "libcst": "1.9.0"}


def method_source_hashes():
    paths = [path for path in (REPOSITORY / "trickcatcher_linefacts/pipelines/v11_fair").iterdir()
             if path.is_file() and path.suffix in (".py", ".json")]
    adapter_directory = REPOSITORY / "final/v11_clean_runtimefix"
    for name in ("cohort.py", "context.py", "mining.py", "facts.py", "model_calls.py", "sandbox.py", "worker.py"):
        paths.append(adapter_directory / name)
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def original_line_numbers(raw_source, method_source):
    """Match unchanged AST nodes; leave ambiguous locations explicitly unmapped."""
    raw_nodes = defaultdict(list)
    method_nodes = defaultdict(list)
    for source, groups in ((raw_source, raw_nodes), (method_source, method_nodes)):
        for node in ast.walk(ast.parse(source)):
            if hasattr(node, "lineno"):
                groups[ast.dump(node, include_attributes=False)].append(node.lineno)
    candidates = defaultdict(set)
    for signature, method_lines in method_nodes.items():
        raw_lines = raw_nodes.get(signature, [])
        if len(raw_lines) == len(method_lines):
            for method_line, raw_line in zip(method_lines, raw_lines):
                candidates[method_line].add(raw_line)
    return {line: next(iter(matches)) for line, matches in candidates.items() if len(matches) == 1}


def concept_cards(bundle, program):
    """Expose only selected concepts; exclude tool inputs, witnesses and mutants."""
    line_numbers = original_line_numbers(program["code"], bundle["put"])
    cards = []
    for rank, fact in enumerate(bundle["concept_meta"]):
        def replace_line(match):
            method_line = int(match.group(1))
            if method_line in line_numbers:
                return f"line {line_numbers[method_line]}"
            return f"V11 method-view line {method_line} (original location unavailable)"

        text = re.sub(r"\bline (\d+)\b", replace_line, fact["text"])
        cards.append({
            "put_id": program["id"], "rank": rank, "kind": fact["kind"],
            "text": f"PUT {program['id']}: {text}"[:800],
            "original_v11_text": fact["text"],
            "method_line": fact.get("line"),
            "original_line": line_numbers.get(fact.get("line")),
            "fact_sha256": digest(fact),
        })
    return cards


def select_concept_cards(records, visible_programs, limit):
    """Take rank 0 from each visible PUT before rank 1; never select by outcomes."""
    by_identifier = {record["put_id"]: record for record in records}
    selected = []
    seen = set()
    maximum_rank = max((len(record["cards"]) for record in records), default=0)
    for rank in range(maximum_rank):
        for program in visible_programs:
            record = by_identifier[program["id"]]
            if rank >= len(record["cards"]):
                continue
            card = record["cards"][rank]
            identity = (card["kind"], card["original_v11_text"])
            if identity in seen:
                continue
            seen.add(identity)
            selected.append(dict(card, id=f"v11_c{len(selected)}"))
            if len(selected) == limit:
                return selected
    return selected


class V11ConceptStage(PipelineStage):
    name = "v11_concept_extraction"
    requires = ("frozen_cohort",)

    def __init__(self, cache_directory=None, *, cache_only=False):
        self.cache_directory = Path(cache_directory).resolve() if cache_directory is not None else None
        self.cache_only = cache_only
        self.calls = None
        self.sandbox = None

    def source_dependencies(self):
        return tuple(Path(filename) for filename in method_source_hashes())

    def configuration(self):
        return {
            "cache_directory": str(self.cache_directory) if self.cache_directory is not None else None,
            "cache_only": self.cache_only,
            "method": "V11MiningStage+V11FactsStage;original-top3-with-spec-fallback",
            "worker_packages": WORKER_PACKAGES,
            "coverage_core": "pytrace",
        }

    def run(self, context):
        cohort_task = context.cohort_task
        passing_programs = [program for program in cohort_task["programs"] if program["base"]["status"] == "pass"]
        if cohort_task["generated"] != context.settings.target_programs or not passing_programs:
            context.extensions["v11_concepts"] = []
            return
        records = []
        for program in passing_programs:
            relative_path = context.task_directory + f"/v11_concepts/{program['id']}/concepts.json"
            if context.artifacts.exists(relative_path):
                record = context.artifacts.read(relative_path)
                self.verify_record(context, program, record)
            else:
                if context.artifacts.read_only:
                    raise FileNotFoundError(f"Read-only replay requires {relative_path}")
                record = self.extract(context, program)
                context.artifacts.write(relative_path, record)
            records.append(record)
        context.extensions["v11_concepts"] = records

    @staticmethod
    def identity(context, program):
        visible_spec = {key: context.task[key] for key in ("task_id", "prompt", "entry_point", "test")}
        return {
            "put_id": program["id"], "task_id": context.task["task_id"],
            "raw_source_sha256": hashlib.sha256(program["code"].encode()).hexdigest(),
            "specification_sha256": digest(visible_spec),
            "seed_alias": context.task_number * 10 + program["id"],
        }

    def verify_record(self, context, program, record):
        for field, expected in self.identity(context, program).items():
            if record.get(field) != expected:
                raise ValueError(f"V11 concept checkpoint identity mismatch: {field}")
        if record["method_source_hashes"] != method_source_hashes():
            raise ValueError("V11 concept extraction source changed")
        if not context.artifacts.read_only and record["model"] != context.calls.model_id:
            raise ValueError("V11 concept extraction model changed")

    def import_bundle(self, context, program, view):
        if self.cache_directory is None:
            return None
        case_id = context.task_number * 10 + program["id"]
        directory = self.cache_directory / "cases" / str(case_id)
        required = (directory / "bundle.json", directory / "program_view.json",
                    directory / "mining.json", self.cache_directory / "manifest.json")
        if not all(path.is_file() for path in required):
            return None
        manifest = json.loads(required[-1].read_text())
        if manifest["model"] != context.calls.model_id:
            raise ValueError("Imported V11 model does not match this run")
        if manifest["worker_packages"] != WORKER_PACKAGES:
            raise ValueError("Imported V11 worker versions do not match")
        for filename, checksum in method_source_hashes().items():
            if manifest["source_hashes"].get(filename) != checksum:
                raise ValueError(f"Imported V11 extraction source mismatch: {filename}")
        bundle = json.loads(required[0].read_text())
        program_view = json.loads(required[1].read_text())
        mining = json.loads(required[2].read_text())
        expected = {"task": case_id, "entry": context.task["entry_point"], "put": view, "base": context.task["test"]}
        if any(bundle.get(field) != value for field, value in expected.items()):
            raise ValueError("Imported V11 bundle belongs to another PUT/specification")
        if program_view["raw_source_sha256"] != hashlib.sha256(program["code"].encode()).hexdigest():
            raise ValueError("Imported V11 raw source mismatch")
        return bundle, {
            "origin": "imported", "directory": str(directory),
            "artifact_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in required[:3]},
            "historical_mining_request_keys": mining["physical_request_keys"],
            "manifest_sha256": hashlib.sha256(required[-1].read_bytes()).hexdigest(),
        }

    def extract(self, context, program):
        identity = self.identity(context, program)
        view = V11ProgramView().build(context.task, program)
        imported = self.import_bundle(context, program, view)
        common = dict(identity, model=context.calls.model_id, method_source_hashes=method_source_hashes())
        if imported is not None:
            bundle, provenance = imported
            return dict(common, state="complete", cards=concept_cards(bundle, program), provenance=provenance)
        if self.cache_only:
            raise FileNotFoundError(f"No matching V11 concepts for {context.task['task_id']}/PUT {program['id']}")
        if self.calls is None:
            self.calls = V11ModelCalls(context.artifacts.path("v11_concept_preparation"))
        if self.calls.model.model_id != context.calls.model_id:
            raise ValueError("Concept extraction and test generation must use the registered model")
        if self.sandbox is None:
            self.sandbox = V11Sandbox()
        directory = context.artifacts.path(context.task_directory + f"/v11_concepts/{program['id']}")
        directory.mkdir(parents=True, exist_ok=True)
        preparation = V11Context(
            task={"task": identity["seed_alias"], "entry": context.task["entry_point"], "put": view,
                  "base": context.task["test"], "split": "fixed_cohort"},
            human_eval={key: context.task[key] for key in ("prompt", "entry_point", "test")},
            original_program={"id": program["id"], "code": program["code"]},
            directory=directory, calls=V11PreparationCalls(self.calls), sandbox=self.sandbox,
        )
        try:
            for stage in (V11MiningStage(), V11FactsStage()):
                save(directory / "progress.json", {"stage": stage.name, "state": "running"})
                stage.run(preparation)
                save(directory / "progress.json", {"stage": stage.name, "state": "complete"})
        except (TransportError, CompletionRetryLimit, WorkerStalled):
            raise
        except (RuntimeError, ValueError, SyntaxError, KeyError, TypeError, StopIteration, AttributeError) as error:
            save(directory / "progress.json", {"stage": "v11_concept_extraction", "state": "failed", "error_type": type(error).__name__})
            return dict(common, state="preparation_failed", cards=[], error_type=type(error).__name__,
                        provenance={"origin": "computed", "directory": str(directory)})
        return dict(common, state="complete", cards=concept_cards(preparation.bundle, program),
                    provenance={"origin": "computed", "directory": str(directory),
                                "mining_request_keys": preparation.mining["physical_request_keys"]})
