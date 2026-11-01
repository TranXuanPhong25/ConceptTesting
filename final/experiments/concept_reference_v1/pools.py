"""Deterministic Hypothesis inputs from observed base values; no reference access."""
from __future__ import annotations

import ast
import copy
import math
import random

from hypothesis import given, seed, settings, HealthCheck
from hypothesis import strategies as st


def variations(value):
    values=[value]
    if type(value)==int:
        values += [0,1,-1,value-1,value+1,-value,2*value]
    elif type(value)==float and math.isfinite(value):
        values += [0.,1.,-1.,value-1.,value+1.,-value,math.nextafter(value,-math.inf),math.nextafter(value,math.inf)]
    elif isinstance(value,(str,list,tuple)):
        values += [value[:0],value[:1],value[-1:],value[::-1],(value+value)[:80]]
        if isinstance(value,str):
            values += [value.lower(),value.upper(),' '+value,value+' ']
        elif value:
            values += [type(value)([value[0]]*min(8,len(value)+1))]
    elif isinstance(value,dict):
        values += [{}]
    return values


def candidate_pool(programs, task_number, limit=64):
    observations={}
    names=None
    for program in programs:
        for call in program['base'].get('calls',[])[:100]:
            bound=call.get('bound',{})
            if names is None:
                names=list(bound)
            if list(bound)!=names:
                continue
            for name,literal in bound.items():
                try:
                    observations.setdefault(name,[]).append(ast.literal_eval(literal))
                except (ValueError,SyntaxError):
                    continue
    if not names or any(not observations.get(n) for n in names):
        return []
    domains=[]
    for name in names:
        unique={}
        for original in observations[name][:25]:
            for value in variations(original):
                unique.setdefault(repr(value),value)
        domains.append(st.sampled_from(list(unique.values())))
    records,seen=[],set()

    @seed(20261030+task_number)
    @settings(max_examples=limit*2,database=None,deadline=None,suppress_health_check=[HealthCheck.too_slow])
    @given(st.tuples(*domains))
    def collect(args):
        literal=repr(args)
        if literal not in seen and len(records)<limit:
            seen.add(literal)
            records.append(dict(args=literal,kwargs='{}'))

    collect()
    return records


def select_witnesses(pool, checks, base_keys, task_number, limit=8):
    eligible={check['input_key']:record for record,check in zip(pool,checks)
              if check['status']=='valid' and check['input_key'] not in base_keys}
    items=list(eligible.items())
    random.Random(982451653+task_number).shuffle(items)
    return [dict(record,input_key=key) for key,record in items[:limit]]
