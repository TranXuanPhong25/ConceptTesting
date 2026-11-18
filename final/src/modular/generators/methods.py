"""Adapt independent input-producing methods/stages to one generator interface."""
from __future__ import annotations
from collections import Counter

from .base import InputGenerator
from ..stages.input_preparation import InputPreparationStage


class MethodInputGenerator(InputGenerator):
    def __init__(self, methods, *, preparation_stages=None):
        self.methods = tuple(methods)
        names = []
        for method in self.methods:
            if not method.name or not method.name.replace("_", "").isalnum() or method.name in names:
                raise ValueError("Input method names must be unique nonempty identifiers")
            names.append(method.name)
        if not names:
            raise ValueError("At least one input-producing method is required")
        self.stages = (InputPreparationStage(self.methods),) if preparation_stages is None else tuple(preparation_stages)

    def configuration(self):
        return {"methods": [{"name": method.name, "class": type(method).__module__ + "." + type(method).__qualname__,
                             "configuration": method.configuration()} for method in self.methods]}

    def preparation_stages(self):
        return self.stages

    def post_reference_stages(self):
        if any(getattr(method, "measures_catalogue", False) for method in self.methods):
            from ..stages.catalogue_measurement import CatalogueMeasurementStage
            return (CatalogueMeasurementStage(self.methods),)
        return ()

    def generate(self, context):
        if context.packet and context.packet.get("skip"):
            return {"task_id": context.task["task_id"], "skip": context.packet["skip"]}
        batches = {}
        for method in self.methods:
            batches[method.name] = method.run(context)
        return {"task_id": context.task["task_id"], "arms": batches}

    def dependency_objects(self):
        return self.methods

    def runtime_dependencies(self):
        return tuple(dict.fromkeys(package for method in self.methods
                     for package in getattr(method, 'runtime_dependencies', lambda: ())()))

    def source_dependencies(self):
        paths = []
        for method in self.methods:
            dependencies = getattr(method, "source_dependencies", None)
            if dependencies is not None:
                paths.extend(dependencies())
        return paths

    def reporting_stage(self):
        selected_stage = None
        for method in self.methods:
            factory = getattr(method, "reporting_stage", None)
            stage = factory() if factory is not None else None
            if stage is not None:
                if selected_stage is not None and (type(stage) is not type(selected_stage)
                        or stage.configuration() != selected_stage.configuration()):
                    raise ValueError("Conflicting method reporting extensions")
                selected_stage = stage
        return selected_stage

    def extend_summary(self, contexts, summary, reporting):
        for method in self.methods:
            extension = getattr(method, "extend_summary", None)
            if extension is not None:
                extension(contexts, summary, reporting)
            batches=[c.inputs['arms'][method.name] for c in contexts if not c.inputs.get('skip')]
            if getattr(method,'requires_treatment',False) or any('treatment' in b for b in batches):
                states=Counter(b.get('treatment',{}).get('status','pending') for b in batches)
                summary.setdefault('method_treatments',{})[method.name]={
                    'tasks':len(batches),'states':dict(states),
                    'ready_for_efficacy':states['applied']>0 and not any(states[s] for s in ('failed','unknown','pending'))}
