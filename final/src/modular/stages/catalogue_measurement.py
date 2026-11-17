"""Measure frozen catalogues after domain/reference checks, before PUT execution."""
from .base import PipelineStage
from ..catalogue import measure_catalogue
from ..arm_names import retained_input_budget


class CatalogueMeasurementStage(PipelineStage):
    name = "catalogue_measurement"
    requires = ("reference_oracle",)

    def __init__(self, methods):
        self.names = tuple(method.name for method in methods if getattr(method, "measures_catalogue", False))

    def configuration(self):
        return {"arms": list(self.names), "protocol": "testing-catalogue-membership-v2"}

    def run(self, context):
        if context.inputs.get("skip"):
            return
        measurements = {}
        for name in self.names:
            batch = context.inputs["arms"][name]
            indices = context.oracle.get("catalogue_valid_input_indices", {}).get(name, [])
            try:
                measurements[name] = measure_catalogue(batch, context.task, indices,
                                                       arm_name=name, input_budget=retained_input_budget(name,context.settings.input_budget))
            except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
                # Catalogue metadata may fail validation; valid calls still reach PUT evaluation.
                measurements[name] = {"status": "catalogue_invalid", "errors": ["measurement:" + type(error).__name__],
                                      "semantic_audit": "pending"}
        context.extensions["catalogue_measurements"] = measurements
        context.artifacts.write(context.task_directory + "/catalogue_measurements.json", measurements)
