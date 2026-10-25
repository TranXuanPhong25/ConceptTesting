"""Typed, data-only recipe IR for native-first construction.

The IR deliberately describes a small set of joint input predicates. It never
contains executable Python from a model response.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any


KINDS = frozenset({"joint_length_guard", "multiplicity", "odd_cardinality_unique"})
PROPAGATION = frozenset({"alternative_output_difference", "unknown"})


def _id(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:16]


def validate(recipe: dict[str, Any]) -> dict[str, Any]:
    required = {"kind", "input_topology", "input_predicate", "site_and_frame", "event_predicate",
                "propagation_mode", "provenance", "backend", "budget"}
    if set(recipe) - (required | {"recipe_id", "alternative"}) or not required <= set(recipe):
        raise ValueError("recipe_schema")
    if recipe["kind"] not in KINDS or recipe["backend"] != "native":
        raise ValueError("recipe_kind_or_backend")
    if recipe["propagation_mode"] not in PROPAGATION:
        raise ValueError("recipe_propagation")
    if (recipe['propagation_mode']=='alternative_output_difference') != bool(recipe.get('alternative')):
        raise ValueError('recipe_alternative_required')
    topology = recipe["input_topology"]
    if not isinstance(topology, dict) or not isinstance(topology.get("args"), list):
        raise ValueError("recipe_topology")
    for arg in topology["args"]:
        if set(arg) != {"index", "kind"} or type(arg["index"]) is not int or arg['index']<0:
            raise ValueError("recipe_arg")
        if arg["kind"] not in {"int", "seq_int", "nested_seq_int"}:
            raise ValueError("recipe_arg_kind")
    if not isinstance(recipe["input_predicate"], dict) or not isinstance(recipe["event_predicate"], dict):
        raise ValueError("recipe_predicate")
    if not isinstance(recipe["site_and_frame"], dict) or not isinstance(recipe["provenance"], dict):
        raise ValueError("recipe_binding")
    binding=recipe['site_and_frame']
    if set(binding)!={'source_sha256','span','function'} or not re.fullmatch('[a-f0-9]{64}',binding.get('source_sha256','')):
        raise ValueError('recipe_source_binding')
    if not isinstance(binding['function'],str) or not binding['function'].isidentifier():
        raise ValueError('recipe_function_binding')
    if not isinstance(binding['span'],list) or len(binding['span'])!=4 or any(type(x)is not int or x<0 for x in binding['span']):
        raise ValueError('recipe_span')
    expected_predicates={
        'joint_length_guard':({'relation','delta','positive_int'},'len(seq)=int+delta',2),
        'multiplicity':({'relation','required_length'},'has_duplicate',1),
        'odd_cardinality_unique':({'relation','minimum_length'},'odd_length_all_distinct',1),
    }
    keys,relation,arity=expected_predicates[recipe['kind']]
    p=recipe['input_predicate']
    if set(p)!=keys or p.get('relation')!=relation or len(topology['args'])!=arity:
        raise ValueError('recipe_predicate_schema')
    if len({a['index'] for a in topology['args']})!=arity:
        raise ValueError('recipe_argument_overlap')
    if [a['kind'] for a in topology['args']]!=(['seq_int','int'] if recipe['kind']=='joint_length_guard' else ['seq_int']):
        raise ValueError('recipe_topology_constructor_mismatch')
    if recipe['kind']=='joint_length_guard' and (type(p['delta'])is not int or abs(p['delta'])>16 or type(p['positive_int'])is not bool):
        raise ValueError('recipe_length_parameters')
    if recipe['kind']=='multiplicity' and p['required_length']is not None and (type(p['required_length'])is not int or not 2<=p['required_length']<=16):
        raise ValueError('recipe_multiplicity_length')
    if recipe['kind']=='odd_cardinality_unique' and p['minimum_length']!=3:
        raise ValueError('recipe_minimum_length')
    allowed_events={
        'joint_length_guard':'target_reached_after_joint_guard',
        'multiplicity':'target_reached_with_duplicate',
        'odd_cardinality_unique':'target_reached_with_odd_cardinality',
    }
    event=recipe['event_predicate']
    if set(event)-{'kind','local_odd_equals_input_length'} or event.get('kind')!=allowed_events[recipe['kind']]:
        raise ValueError('recipe_event_predicate')
    if 'local_odd_equals_input_length' in event and (recipe['kind']!='odd_cardinality_unique' or not isinstance(event['local_odd_equals_input_length'],str) or not event['local_odd_equals_input_length'].isidentifier()):
        raise ValueError('recipe_local_predicate')
    if set(recipe["budget"]) != {"max_candidates", "max_executions", "seeds", "repeats"}:
        raise ValueError("recipe_budget")
    if any(type(recipe["budget"][key]) is not int or recipe["budget"][key] < 1
           for key in ("max_candidates", "max_executions", "repeats")):
        raise ValueError("recipe_budget_values")
    if not isinstance(recipe["budget"]["seeds"], list) or not all(type(x) is int for x in recipe["budget"]["seeds"]):
        raise ValueError("recipe_seeds")
    if not recipe['budget']['seeds'] or len(set(recipe['budget']['seeds']))!=len(recipe['budget']['seeds']):
        raise ValueError('recipe_seed_uniqueness')
    if recipe['budget']['max_candidates']>64 or recipe['budget']['max_executions']>256:
        raise ValueError('recipe_registered_budget_cap')
    result = dict(recipe)
    identity=_id({k: v for k, v in recipe.items() if k != "recipe_id"})
    if recipe.get('recipe_id',identity)!=identity: raise ValueError('recipe_identity_mismatch')
    result['recipe_id']=identity
    return result


def joint_length_guard(*, source_sha256: str, span: list[int], function: str,
                       seq_arg: int, int_arg: int, delta: int, positive: bool,
                       budget: dict[str, Any], provenance: dict[str, Any], alternative: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate({
        "kind": "joint_length_guard",
        "input_topology": {"args": [{"index": seq_arg, "kind": "seq_int"}, {"index": int_arg, "kind": "int"}]},
        "input_predicate": {"relation": "len(seq)=int+delta", "delta": delta, "positive_int": positive},
        "site_and_frame": {"source_sha256": source_sha256, "span": span, "function": function},
        "event_predicate": {"kind": "target_reached_after_joint_guard"},
        "propagation_mode": "alternative_output_difference" if alternative else "unknown",
        "provenance": provenance, "backend": "native", "budget": budget,
        **({"alternative": alternative} if alternative else {}),
    })


def multiplicity(*, source_sha256: str, span: list[int], function: str, seq_arg: int,
                 require_length: int | None, budget: dict[str, Any], provenance: dict[str, Any],
                 alternative: dict[str, Any] | None = None) -> dict[str, Any]:
    predicate = {"relation": "has_duplicate", "required_length": require_length}
    return validate({
        "kind": "multiplicity",
        "input_topology": {"args": [{"index": seq_arg, "kind": "seq_int"}]},
        "input_predicate": predicate,
        "site_and_frame": {"source_sha256": source_sha256, "span": span, "function": function},
        "event_predicate": {"kind": "target_reached_with_duplicate"},
        "propagation_mode": "alternative_output_difference" if alternative else "unknown",
        "provenance": provenance, "backend": "native", "budget": budget,
        **({"alternative": alternative} if alternative else {}),
    })


def odd_cardinality_unique(*, source_sha256: str, span: list[int], function: str, seq_arg: int,
                           budget: dict[str, Any], provenance: dict[str, Any],
                           alternative: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate({
        "kind": "odd_cardinality_unique",
        "input_topology": {"args": [{"index": seq_arg, "kind": "seq_int"}]},
        "input_predicate": {"relation": "odd_length_all_distinct", "minimum_length": 3},
        "site_and_frame": {"source_sha256": source_sha256, "span": span, "function": function},
        "event_predicate": {"kind": "target_reached_with_odd_cardinality"},
        "propagation_mode": "alternative_output_difference" if alternative else "unknown",
        "provenance": provenance, "backend": "native", "budget": budget,
        **({"alternative": alternative} if alternative else {}),
    })
