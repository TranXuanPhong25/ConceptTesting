"""Finite native candidate construction and repeatability certification.

It constructs tuples from a typed recipe, then delegates concrete execution to
the isolated v60 replay worker. It does not use references or hidden contracts.
"""
from __future__ import annotations

import copy
import ast
import hashlib
import time
import z3
from typing import Any

from .construction import replay
from .recipe_ir import validate


def _set_argument(args: tuple[Any, ...], index: int, value: Any) -> tuple[Any, ...]:
    result = list(copy.deepcopy(args))
    result[index] = value
    return tuple(result)


def candidates(recipe: dict[str, Any], base_args: tuple[Any, ...], deadline=None) -> list[tuple[Any, ...]]:
    recipe = validate(recipe)
    if any(a['index']>=len(base_args) for a in recipe['input_topology']['args']):
        raise ValueError('recipe_argument_out_of_range')
    limit = recipe["budget"]["max_candidates"]
    kind = recipe["kind"]
    values: list[tuple[Any, ...]] = []
    if kind == "joint_length_guard":
        data = recipe["input_predicate"]
        seq_index, int_index = [x["index"] for x in recipe["input_topology"]["args"]]
        for length in range(0,17):
            if len(values)>=limit or (deadline is not None and time.monotonic()>=deadline):break
            integer=z3.Int('joint_integer'); solver=z3.Solver(); solver.set(timeout=100)
            solver.add(integer>=-16,integer<=16,length==integer+data['delta'])
            if data['positive_int']: solver.add(integer>0)
            if solver.check()==z3.sat:
                value=solver.model().eval(integer).as_long()
                values.append(_set_argument(_set_argument(base_args,int_index,value),seq_index,[0]*length))
    elif kind == "multiplicity":
        seq_index = recipe["input_topology"]["args"][0]["index"]
        lengths = [recipe["input_predicate"]["required_length"]] if recipe["input_predicate"]["required_length"] else range(2,17)
        for length in lengths:
            if len(values)>=limit or (deadline is not None and time.monotonic()>=deadline):break
            if length and length >= 2:
                xs=[z3.Int(f'x{i}') for i in range(length)]
                solver=z3.Solver();solver.set(timeout=100)
                solver.add(*[z3.And(x>=-16,x<=16) for x in xs],z3.Not(z3.Distinct(*xs)))
                if solver.check()==z3.sat:
                    model=solver.model();values.append(_set_argument(base_args,seq_index,[model.eval(x,model_completion=True).as_long() for x in xs]))
    elif kind == "odd_cardinality_unique":
        seq_index = recipe["input_topology"]["args"][0]["index"]
        for length in range(3,17,2):
            if len(values)>=limit or (deadline is not None and time.monotonic()>=deadline):break
            xs=[z3.Int(f'x{i}') for i in range(length)]
            solver=z3.Solver();solver.set(timeout=100)
            solver.add(*[z3.And(x>=1,x<=16) for x in xs],z3.Distinct(*xs))
            if solver.check()==z3.sat:
                model=solver.model();values.append(_set_argument(base_args,seq_index,[model.eval(x,model_completion=True).as_long() for x in xs]))
    return list({repr(v): v for v in values}.values())[:limit]


def _obligation_holds(recipe: dict[str, Any], args: tuple[Any, ...]) -> bool:
    recipe = validate(recipe)
    if recipe["kind"] == "joint_length_guard":
        seq_index, int_index = [x["index"] for x in recipe["input_topology"]["args"]]
        sequence, integer = args[seq_index], args[int_index]
        data = recipe["input_predicate"]
        return type(sequence) is list and type(integer) is int and len(sequence) == integer + data["delta"] and (not data["positive_int"] or integer > 0)
    if recipe["kind"] == "multiplicity":
        sequence = args[recipe["input_topology"]["args"][0]["index"]]
        required = recipe["input_predicate"]["required_length"]
        return type(sequence) is list and len(sequence) >= 2 and len(set(sequence)) < len(sequence) and (required is None or len(sequence) == required)
    if recipe["kind"] == "odd_cardinality_unique":
        sequence = args[recipe["input_topology"]["args"][0]["index"]]
        return type(sequence) is list and len(sequence) >= 3 and len(sequence) % 2 == 1 and len(set(sequence)) == len(sequence)
    return False


def certify(source: str, entry: str, recipe: dict[str, Any], base_args: tuple[Any, ...], case_budget=None) -> dict[str, Any]:
    recipe = validate(recipe)
    binding = recipe['site_and_frame']
    if hashlib.sha256(source.encode()).hexdigest() != binding['source_sha256']:
        raise ValueError('recipe_source_hash_mismatch')
    targets = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.expr)
               and [n.lineno,n.col_offset,n.end_lineno,n.end_col_offset] == binding['span']]
    if len(targets) != 1:
        raise ValueError('recipe_exact_expression_binding')
    target = targets[0]
    hypothesis = recipe.get('alternative') or dict(span=binding['span'], node_kind=type(target).__name__,
                                                 before=ast.unparse(target), after=ast.unparse(target))
    if hypothesis['span'] != binding['span'] or hypothesis['before'] != ast.unparse(target):
        raise ValueError('recipe_alternative_binding')
    if hypothesis.get('node_kind')!=type(target).__name__:
        raise ValueError('recipe_alternative_kind')
    if recipe.get('alternative'):
        if set(hypothesis)!={'span','before','after','node_kind'}:raise ValueError('native_alternative_schema')
        alternative=ast.parse(hypothesis['after'],mode='eval').body
        from .hypotheses import validate_replacement
        # The native rounding summary allows precisely math.ceil/floor(local / 2).
        rounding=(isinstance(alternative,ast.Call) and isinstance(alternative.func,ast.Attribute)
                  and isinstance(alternative.func.value,ast.Name) and alternative.func.value.id=='math'
                  and alternative.func.attr in ('ceil','floor') and len(alternative.args)==1 and not alternative.keywords
                  and isinstance(alternative.args[0],ast.BinOp) and isinstance(alternative.args[0].op,ast.Div)
                  and isinstance(alternative.args[0].left,ast.Name) and isinstance(alternative.args[0].right,ast.Constant)
                  and alternative.args[0].right.value==2)
        if not rounding:validate_replacement(target,alternative)
    runs: list[dict[str, Any]] = []
    execution_budget = recipe["budget"]["max_executions"]
    per_replay = 2 if recipe.get('alternative') else 1
    required_replays = len(recipe['budget']['seeds']) * recipe['budget']['repeats']
    if case_budget is None: case_budget={'remaining_executions':256,'remaining_candidates':64,'deadline':time.monotonic()+120}
    deadline = case_budget['deadline']
    count = 0
    generated=candidates(recipe,base_args,deadline=deadline)
    tested=0;stop_reason=None
    for args in generated:
        if count + required_replays * per_replay > execution_budget or case_budget['remaining_executions']<required_replays*per_replay or case_budget['remaining_candidates']<=0 or time.monotonic() >= deadline:
            stop_reason=('deadline' if time.monotonic()>=deadline else 'execution_or_candidate_budget')
            break
        case_budget['remaining_candidates']-=1
        tested+=1
        if not _obligation_holds(recipe, args):
            continue
        observations = []
        for seed in recipe["budget"]["seeds"]:
            for _ in range(recipe["budget"]["repeats"]):
                local_name=recipe['event_predicate'].get('local_odd_equals_input_length')
                observed = replay(source, entry, args, hypothesis, seed=seed, deadline=deadline,
                                  observe_only=not bool(recipe.get('alternative')),observation_names=[local_name] if local_name else [])
                observations.append({"seed": seed, "observation": observed})
                count += per_replay
                case_budget['remaining_executions']-=per_replay
                if count >= execution_budget:
                    break
            if count >= execution_budget:
                break
        # Repeatability is per seed. Cross-seed differences are conservatively unstable too.
        stable = len(observations) == required_replays and len({repr(x["observation"]) for x in observations}) == 1
        first = observations[0]["observation"] if observations else {"status": "budget_exhausted"}
        put = first.get('put', {})
        events = put.get('site_events', [])
        reached = bool(events) and all(e.get('function') == binding['function'] for e in events)
        event_realized=reached
        local_name=recipe['event_predicate'].get('local_odd_equals_input_length')
        if local_name:
            length=len(args[recipe['input_topology']['args'][0]['index']])
            event_realized=any(e.get('locals',{}).get(local_name)=={'type':'int','repr':str(length)} and length%2==1 for e in events)
        normal = first.get('status') == 'ok' and put.get('status') == 'ok'
        realized = stable and normal and reached and event_realized
        propagation = 'unknown'
        if recipe.get('alternative'):
            alt = first.get('alternative', {})
            local = [e['value'] for e in events] != [e['value'] for e in alt.get('site_events', [])]
            if realized and alt.get('status') == 'ok' and alt.get('site_events'):
                propagation = bool(local and put.get('output') != alt.get('output'))
        status = ('verified_behavioral_difference' if propagation is True else
                  'stable_input_and_site_realized' if realized else 'unstable_or_unresolved')
        runs.append({"arguments": repr(args), "input_predicate_realized": _obligation_holds(recipe,args),
                     "site_realized": reached, "obligation_realized": realized, 'output_sensitivity': propagation,
                     'realization_scope':'input_and_site_plus_explicit_local_predicate' if local_name else 'input_and_site_only',
                     'bug_truth': 'unknown', "status": status,
                     "observations": observations})
    if time.monotonic()>=deadline:stop_reason='deadline'
    return {"recipe_id": recipe["recipe_id"], "candidates_considered": len(generated),'candidates_tested':tested,
            "native_executions": count, "runs": runs,
            'stop_reason':stop_reason,"status": "budget_exhausted" if stop_reason else "complete"}


def certify_case(source,entry,recipes,base_args):
    if len(recipes)>3: raise ValueError('registered_recipe_count')
    budget={'remaining_executions':256,'remaining_candidates':64,'deadline':time.monotonic()+120}
    reports=[certify(source,entry,r,base_args,case_budget=budget) for r in recipes]
    return {'recipes':reports,'native_executions':256-budget['remaining_executions'],
            'candidates_tested':64-budget['remaining_candidates']}
