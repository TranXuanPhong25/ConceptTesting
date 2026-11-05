from pathlib import Path

from ..cohort import load_cohort
from .base import PipelineStage


class FrozenCohortStage(PipelineStage):
    name = "frozen_cohort"

    def __init__(self, cohort_path: Path):
        self.cohort_path = cohort_path.resolve()
        self.cohort = load_cohort(self.cohort_path)
        self.task_records = {}
        for task_record in self.cohort["tasks"]:
            self.task_records[task_record["task_id"]] = task_record

    def run(self, context):
        context.cohort_task = self.task_records[context.task["task_id"]]

    def configuration(self):
        return {"cohort_sha256": self.cohort["cohort_sha256"]}
