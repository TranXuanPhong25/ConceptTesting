"""Reusable candidate families. No observed value becomes a semantic bound."""


class BoundaryTemplates:
    name = "templates"

    def run(self, context):
        candidates = []
        for parameter in context.input_types["parameters"]:
            characteristics = []
            for evidence in parameter["evidence"]:
                for description in evidence["types"]:
                    kind = description["kind"]
                    if kind in ("int", "float"):
                        characteristics.append(("value", "ordered_scalar"))
                    if kind in ("str", "list", "tuple", "set", "dict"):
                        characteristics.append(("length", "cardinality"))
                    item_types = description.get("items", [])
                    numeric_items = any(item["kind"] in ("int", "float") for item in item_types)
                    if kind in ("list", "tuple") and numeric_items:
                        characteristics.append(("elements", "element_values"))
                        characteristics.append(("sum", "aggregate"))
            seen = set()
            for operation, family in characteristics:
                if operation in seen:
                    continue
                seen.add(operation)
                candidates.append({
                    "id": f"{parameter['name']}:{operation}", "family": family,
                    "characteristic": {"parameter": parameter["name"], "operation": operation},
                    "neighborhood_modes": ["step", "float_adjacent"] if operation != "length" else ["step"],
                    "template": "Below, at, and above a spec-supported threshold; retain only defined input behavior.",
                    "threshold_sources": ["spec_constant", "input_value", "input_length", "input_sum"],
                    "requires": ["spec_evidence", "domain_constraints", "feasible_input"],
                })
        return {"status": "candidates" if candidates else "no_templates", "candidates": candidates,
                "unsupported_families": ["unordered_categories", "boolean_only", "custom_objects",
                                         "nested_element_paths", "date_objects", "custom_arithmetic"]}
