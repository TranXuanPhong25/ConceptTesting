"""Explicit source-bound resource exclusions, applied before any task generation."""
import hashlib
import json
from pathlib import Path


class ResourceExclusionPlan:
    def __init__(self, path):
        self.path = Path(path).resolve()
        content = self.path.read_bytes()
        self.sha256 = hashlib.sha256(content).hexdigest()
        self.plan = json.loads(content)
        if self.plan.get("schema") != "v11-resource-exclusions-1":
            raise ValueError("Unknown resource exclusion plan schema")
        if self.plan.get("scope") != "preparation_prompt_and_evaluation":
            raise ValueError("Resource exclusions must consistently omit preparation, prompts and evaluation")
        self.records = {}
        for record in self.plan["records"]:
            key = (record["task_id"], record["put_id"])
            if key in self.records or record.get("decision") != "exclude_put":
                raise ValueError("Duplicate or invalid resource exclusion decision")
            if not record.get("reason"):
                raise ValueError("A resource exclusion requires a recorded reason")
            self.records[key] = record

    def configuration(self):
        return {"path": str(self.path), "sha256": self.sha256,
                "scope": "preparation_prompt_and_evaluation"}

    def apply(self, context, identify_program):
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != self.sha256:
            raise ValueError("Resource exclusion plan changed during the run")
        manifest_path = context.artifacts.path("modular_manifest.json")
        if not manifest_path.is_file():
            raise ValueError("Resource exclusions require a frozen run manifest")
        manifest = json.loads(manifest_path.read_text())
        if manifest["cohort_sha256"] != self.plan["cohort_sha256"]:
            raise ValueError("Resource exclusion plan belongs to another cohort")
        retained = []
        excluded = []
        for program in context.cohort_task["programs"]:
            key = (context.task["task_id"], program["id"])
            record = self.records.get(key)
            if record is None:
                retained.append(program)
                continue
            identity = identify_program(context, program)
            for field in ("raw_source_sha256", "specification_sha256"):
                if record[field] != identity[field]:
                    raise ValueError(f"Resource exclusion PUT/spec mismatch: {field}")
            if program["base"]["status"] != "pass":
                raise ValueError("Resource exclusion expected an originally base-passing PUT")
            excluded.append(dict(identity, reason=record["reason"], plan=self.configuration(),
                                 source_expressions=record.get("source_expressions", [])))
        context.extensions["resource_exclusions"] = excluded
        if not excluded:
            return
        marker_path = context.task_directory + "/resource_exclusions.json"
        if not context.artifacts.exists(marker_path):
            completed_paths = ("packet.json", "inputs.json", "oracle_0.json", "oracle_1.json", "result.json")
            if any(context.artifacts.exists(context.task_directory + "/" + name) for name in completed_paths):
                raise ValueError("Cannot apply new exclusions after task generation or evaluation")
        context.artifacts.write(marker_path, excluded)
        context.cohort_task = dict(context.cohort_task, programs=retained,
                                   base_pass=sum(program["base"]["status"] == "pass" for program in retained),
                                   resource_exclusions=excluded)
