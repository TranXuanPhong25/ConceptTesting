"""Measure frozen catalogues after domain/reference checks, before PUT execution."""
from .base import PipelineStage
from ..catalogue import measure_catalogue


class CatalogueMeasurementStage(PipelineStage):
    name = "catalogue_measurement"
    requires = ("reference_oracle",)

    def __init__(self, methods):
        self.names = tuple(method.name for method in methods if getattr(method, "measures_catalogue", False))

    def configuration(self):
        return {"arms": list(self.names), "protocol": "testing-catalogue-v1"}

    def run(self, context):
        # Validate the global freeze barrier before measuring any generated catalogue.
        if not context.inputs_frozen:
            raise RuntimeError("Catalogue measurement requires frozen inputs")
        if context.inputs.get("skip"):
            return
        measurements = {}
        for name in self.names:
            batch = context.inputs["arms"][name]
            indices = context.oracle.get("catalogue_valid_input_indices", {}).get(name, [])
            try:
                measurements[name] = measure_catalogue(batch, context.task, indices,
                                                       arm_name=name, input_budget=context.settings.input_budget)
            except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
                # Catalogue metadata may fail validation; valid calls still reach PUT evaluation.
                measurements[name] = {"status": "catalogue_invalid", "errors": ["measurement:" + type(error).__name__],
                                      "semantic_audit": "pending"}
        context.extensions["catalogue_measurements"] = measurements
        context.artifacts.write(context.task_directory + "/catalogue_measurements.json", measurements)
