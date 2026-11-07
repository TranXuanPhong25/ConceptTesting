"""Opt-in float-neighbor construction from saved seeds; not the default BVA flow."""
from __future__ import annotations

import ast
import copy
import math
import textwrap

from ..call_builder import CallBuilder


def numeric_string_parameters(program_source, contract, parameter_names):
    """A direct float(parameter) call is a construction cue, not intended semantics."""
    supported = set()
    for source in (program_source, contract):
        try:
            tree = ast.parse(textwrap.dedent(source))
        except (ValueError, SyntaxError, RecursionError):
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float"
                    and len(node.args) == 1 and isinstance(node.args[0], ast.Name)
                    and node.args[0].id in parameter_names):
                supported.add(node.args[0].id)
    return supported


def call_identity(record):
    return record["args"], record["kwargs"]


def named_values(builder, record):
    bound = builder.signature.bind(*ast.literal_eval(record["args"]), **ast.literal_eval(record["kwargs"]))
    bound.apply_defaults()
    return dict(bound.arguments)


def construction_receipt(seed_values, candidate_values, parameter, anchor, neighbor, direction, representation):
    """Validate arithmetic and preservation without executing a PUT or a contract."""
    if direction not in ("below", "above") or representation not in ("float", "numeric_string"):
        raise ValueError("unsupported_construction")
    if float(seed_values[parameter]).hex() != anchor.hex():
        raise ValueError("anchor_does_not_match_seed")
    expected = math.nextafter(anchor, -math.inf if direction == "below" else math.inf)
    if not math.isfinite(neighbor) or neighbor.hex() != expected.hex():
        raise ValueError("not_a_finite_adjacent_neighbor")
    value = candidate_values[parameter]
    if representation == "numeric_string":
        if type(value) is not str or float(value).hex() != neighbor.hex():
            raise ValueError("numeric_string_did_not_round_trip")
    elif type(value) is not float or value.hex() != neighbor.hex():
        raise ValueError("float_neighbor_did_not_round_trip")
    for name in seed_values:
        if name != parameter and repr(seed_values[name]) != repr(candidate_values[name]):
            raise ValueError("non_target_argument_changed")
    return {"parameter": parameter, "representation": representation, "direction": direction,
            "anchor": repr(anchor), "anchor_hex": anchor.hex(), "neighbor": repr(neighbor),
            "neighbor_hex": neighbor.hex(), "adjacent_verified": True,
            "non_target_arguments_unchanged": True, "domain_validation": "pending_reference_stage"}


def expand_seeds(*, specification, entry_point, program_source, contract, inputs):
    builder = CallBuilder.for_source(specification, entry_point)
    string_parameters = numeric_string_parameters(program_source, contract, set(builder.signature.parameters))
    seeds, values, seen = [], [], set()
    for record in inputs:
        arguments = named_values(builder, record)
        encoded = builder.build_values(arguments)
        if call_identity(encoded) in seen:
            continue
        seen.add(call_identity(encoded))
        seeds.append(encoded)
        values.append(arguments)
    anchors, unsupported = [], []
    for seed_index, arguments in enumerate(values):
        for parameter in builder.signature.parameters:
            value = arguments[parameter]
            representation = None
            if type(value) is float:
                representation = "float"
            elif type(value) is str and parameter in string_parameters:
                representation = "numeric_string"
            if representation is None:
                continue
            try:
                anchor = float(value)
            except (ValueError, OverflowError):
                unsupported.append({"seed_index": seed_index, "parameter": parameter, "reason": "not_a_finite_float"})
                continue
            if not math.isfinite(anchor):
                unsupported.append({"seed_index": seed_index, "parameter": parameter, "reason": "not_a_finite_float"})
                continue
            anchors.append((seed_index, parameter, representation, anchor))
    expansions, rejected = [], []
    for direction, destination in (("below", -math.inf), ("above", math.inf)):
        for seed_index, parameter, representation, anchor in anchors:
            neighbor = math.nextafter(anchor, destination)
            provenance = {"seed_index": seed_index, "parameter": parameter, "direction": direction}
            if not math.isfinite(neighbor):
                rejected.append({**provenance, "reason": "nonfinite_neighbor"})
                continue
            candidate = copy.deepcopy(values[seed_index])
            candidate[parameter] = repr(neighbor) if representation == "numeric_string" else neighbor
            receipt = construction_receipt(values[seed_index], candidate, parameter, anchor,
                                           neighbor, direction, representation)
            encoded = builder.build_values(candidate)
            if call_identity(encoded) in seen:
                rejected.append({**provenance, "reason": "duplicate_seed_or_expansion"})
                continue
            seen.add(call_identity(encoded))
            expansions.append({"input": encoded, "receipt": {"seed_index": seed_index, **receipt}})
    return {"seeds": seeds, "expansions": expansions, "unsupported": unsupported, "rejected": rejected,
            "numeric_string_parameters": sorted(string_parameters)}


def fixed_twenty(expanded):
    """Predeclared ten seeds + ten expansions, with remaining seeds filling unused slots."""
    seeds = expanded["seeds"]
    selected = [{"input": record, "kind": "seed", "seed_index": index}
                for index, record in enumerate(seeds[:10])]
    selected.extend({"input": item["input"], "kind": "expansion", "expansion_index": index,
                     "receipt": item["receipt"]} for index, item in enumerate(expanded["expansions"][:10]))
    seen = {call_identity(item["input"]) for item in selected}
    for index, record in enumerate(seeds[10:], start=10):
        if len(selected) == 20:
            break
        if call_identity(record) not in seen:
            selected.append({"input": record, "kind": "seed", "seed_index": index})
            seen.add(call_identity(record))
    return selected


def directed_expansions(expanded, requests):
    """Resolve optional seed-based requests against constructed candidates, not scores."""
    selected, receipts, seen = [], [], set()
    if not isinstance(requests, list) or len(requests) > 2:
        return [], [{"reason": "invalid_expansion_requests"}]
    for request_index, request in enumerate(requests):
        try:
            if not isinstance(request, dict) or set(request) != {"seed_index", "parameter", "quantity", "anchor", "neighbors"}:
                raise ValueError("invalid_expansion_request")
            index = request["seed_index"]
            if type(index) is not int or not 0 <= index < len(expanded["seeds"]):
                raise ValueError("unknown_seed_index")
            if request["neighbors"] != "adjacent" or request["quantity"] not in ("float", "parsed_float"):
                raise ValueError("unsupported_expansion")
            if type(request["anchor"]) not in (int, float) or not math.isfinite(float(request["anchor"])):
                raise ValueError("invalid_anchor")
            representation = "numeric_string" if request["quantity"] == "parsed_float" else "float"
            candidates = [item for item in expanded["expansions"] if item["receipt"]["seed_index"] == index
                          and item["receipt"]["parameter"] == request["parameter"]
                          and item["receipt"]["representation"] == representation
                          and item["receipt"]["anchor_hex"] == float(request["anchor"]).hex()]
            if not candidates:
                raise ValueError("no_supported_neighbor_for_request")
            added = 0
            for candidate in candidates:
                identity = call_identity(candidate["input"])
                if identity not in seen:
                    seen.add(identity)
                    selected.append(candidate)
                    added += 1
            receipts.append({"request_index": request_index, "status": "accepted", "new_candidates": added,
                             "request": request})
        except (ValueError, OverflowError, TypeError) as error:
            receipts.append({"request_index": request_index, "status": "rejected",
                             "reason": str(error) if type(error) is ValueError else type(error).__name__})
    return selected, receipts


def matched_twenty(expanded, requests):
    selected, receipts = directed_expansions(expanded, requests)

    def allocate(expansions):
        records = expanded["seeds"][:10] + [item["input"] for item in expansions]
        records += expanded["seeds"][10:20 - len(expansions)]
        return records

    return {"concept": allocate(selected), "generic": allocate(expanded["expansions"][:len(selected)]),
            "expansion_slots": len(selected), "request_receipts": receipts,
            "concept_expansions": selected, "generic_expansions": expanded["expansions"][:len(selected)]}
