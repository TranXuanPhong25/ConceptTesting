"""Reusable candidate families. No observed value becomes a semantic bound."""
from .grounding import checked, declared_scalar_types


class BoundaryTemplates:
    name = "templates"

    def run(self, context):
        candidates = []
        declared = declared_scalar_types(context) if checked(context) else {}
        for parameter in context.input_types["parameters"]:
            characteristics = []
            numeric_kinds = set()
            for evidence in parameter["evidence"]:
                for description in evidence["types"]:
                    kind = description["kind"]
                    if kind in ("int", "float"):
                        numeric_kinds.add(kind)
                        characteristics.append(("value", "ordered_scalar"))
                    if kind in ("str", "list", "tuple", "set", "dict"):
                        characteristics.append(("length", "cardinality"))
                    item_types = description.get("items", [])
                    numeric_items = any(item["kind"] in ("int", "float") for item in item_types)
                    if kind in ("list", "tuple") and numeric_items:
                        numeric_kinds.update(item["kind"] for item in item_types if item["kind"] in ("int", "float"))
                        characteristics.append(("elements", "element_values"))
                        characteristics.append(("sum", "aggregate"))
                        characteristics.append(("range", "extrema_difference"))
                        characteristics.append(("minimum", "extremum"))
                        characteristics.append(("maximum", "extremum"))
                    if kind == "str":
                        characteristics.append(("run_length", "consecutive_run"))
                        characteristics.append(("parsed_float", "parsed_numeric_string"))
                        if checked(context):
                            characteristics.append(("code_point", "raw_character_code"))
            if parameter["name"] in declared and "float" in declared[parameter["name"]]["types"]:
                numeric_kinds.add("float")
            seen = set()
            for operation, family in characteristics:
                if operation in seen:
                    continue
                seen.add(operation)
                integer = operation in ("length", "run_length", "code_point") or (
                    operation != "parsed_float" and numeric_kinds == {"int"})
                candidates.append({
                    "id": f"{parameter['name']}:{operation}", "family": family,
                    "characteristic": {"parameter": parameter["name"], "operation": operation},
                    "numeric_kind": "int" if integer else "float",
                    "neighborhood_modes": ["step"] if integer else ["step", "float_adjacent"],
                    "template": "Below, at, and above a spec, code, or natural-edge threshold; retain only defined input behavior.",
                    "threshold_sources": ["spec_constant", "code_transition", "natural_edge",
                                          "input_value", "input_length", "input_sum", "input_extrema"],
                    "required_slots": {"token": "one-character string"} if operation == "run_length" else {},
                    "requires": ["public_domain_or_quantity_evidence", "threshold_rationale",
                                 "domain_constraints", "feasible_input"],
                })
        return {"status": "candidates" if candidates else "no_templates", "candidates": candidates,
                "unsupported_families": ["unordered_categories", "boolean_only", "custom_objects",
                                         "nested_element_paths", "date_objects", "custom_arithmetic"]}
