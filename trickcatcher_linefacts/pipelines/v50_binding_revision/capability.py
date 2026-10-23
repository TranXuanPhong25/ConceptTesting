"""Synthetic CPU capability API; never imported by the paired model diagnostic.

Hypothesis searches fallible operator predictions, not spec truth. Runtime snapshots
show observed local values, not a causal slice. No evaluator or episode-specific logic.
"""
import ast
import hashlib
from pathlib import Path
import random

from hypothesis import find, settings, Phase, strategies as st
from hypothesis.errors import NoSuchExample, Unsatisfiable
from jsonschema import Draft202012Validator

from . import identify_tools as relations
from .flow_common import digest
from .isolated import run_once
from .chain_inputs import parse_literal

HERE = Path(__file__).resolve().parent
DOMAIN = {'type': 'array', 'minItems': 1, 'maxItems': 2, 'items': {
    'type': 'object', 'additionalProperties': False,
    'required': ['name', 'kind', 'min_value', 'max_value', 'max_size'],
    'properties': {'name': {'type': 'string', 'pattern': '^[A-Za-z_][A-Za-z_0-9]*$'},
                   'kind': {'enum': ['int', 'int_list']},
                   'min_value': {'type': 'integer', 'minimum': -1000, 'maximum': 1000},
                   'max_value': {'type': 'integer', 'minimum': -1000, 'maximum': 1000},
                   'max_size': {'type': 'integer', 'minimum': 0, 'maximum': 16}}}}


def validate_domain(domain):
    Draft202012Validator(DOMAIN).validate(domain)
    if len({d['name'] for d in domain}) != len(domain) or any(d['min_value'] > d['max_value'] for d in domain):
        raise ValueError('invalid_domain')


def strategy(domain):
    validate_domain(domain)
    parts = []
    for d in domain:
        integers = st.integers(d['min_value'], d['max_value'])
        parts.append(st.lists(integers, max_size=d['max_size']) if d['kind'] == 'int_list' else integers)
    return st.tuples(*parts)


def in_domain(args, domain):
    validate_domain(domain)
    if type(args) is not tuple or len(args) != len(domain):
        return False
    for value, d in zip(args, domain):
        if d['kind'] == 'int_list':
            if type(value) is not list or len(value) > d['max_size']:
                return False
            values = value
        else:
            values = [value]
        if any(type(v) is not int or not d['min_value'] <= v <= d['max_value'] for v in values):
            return False
    return True


def prediction(binding, args, parameters):
    # The observed placeholder is never used as a target or normative expected value.
    result = relations.compare(binding, {'input': repr(args), 'execution_status': 'ok',
        'output': 'None', 'output_capture': 'literal', 'exception_type': None}, parameters)
    if result['status'] != 'computed' or 'candidate_value' not in result:
        return None  # Predicates such as ascending don't determine an exact output.
    return (result['candidate_value'], result['candidate_exception'])


class SearchBudget(Exception):
    pass


def find_discriminator(left, right, domain, *, seed=20261023, max_examples=100, max_checks=512):
    """No native PUT executions; exact-output relations only, no invented alternative."""
    space = strategy(domain)
    if type(max_examples) is not int or not 1 <= max_examples <= 200:
        raise ValueError('search_example_budget')
    if type(max_checks) is not int or not 1 <= max_checks <= 1024:
        raise ValueError('search_check_budget')
    parameters = [d['name'] for d in domain]
    if any(b.get('relation') not in relations.RELATIONS or b.get('relation') in ('unknown', 'ascending', 'preserve_occurrences')
           or type(b.get('arguments')) is not list or len(b['arguments']) != relations.arity(b['relation'])
           or any(a not in parameters for a in b['arguments']) for b in (left, right)):
        return {'status': 'not_available', 'reason': 'two_executable_exact_predictions_required', 'checks': 0}
    state = {'checks': 0, 'comparable': 0, 'witness': None}

    def separates(args):
        if state['checks'] >= max_checks:
            raise SearchBudget()
        state['checks'] += 1
        a, b = prediction(left, args, parameters), prediction(right, args, parameters)
        if a is None or b is None:
            return False
        state['comparable'] += 1
        if a != b:
            state['witness'] = args
            return True
        return False

    exhausted = None
    try:
        witness = find(space, separates, settings=settings(database=None, max_examples=max_examples,
            deadline=None, phases=(Phase.generate, Phase.shrink)), random=random.Random(seed))
    except (NoSuchExample, Unsatisfiable, SearchBudget) as exc:
        witness = state['witness']
        exhausted = type(exc).__name__
    if witness is None:
        return {'status': 'not_found_within_budget' if state['comparable'] else 'not_available',
                'reason': exhausted or 'no_comparable_predictions', 'checks': state['checks'],
                'comparable': state['comparable'], 'scope': 'finite domain and search budget, not infeasibility proof'}
    return {'status': 'found', 'input': repr(witness), 'checks': state['checks'], 'comparable': state['comparable'],
            'left_prediction': prediction(left, witness, parameters), 'right_prediction': prediction(right, witness, parameters),
            'budget_stop': exhausted, 'scope': 'fallible candidate disagreement; neither prediction is a spec oracle; no minimality proof'}


def observed_parity(ordinary, traced):
    keys = ('status', 'exception_type', 'exception_module', 'output_capture', 'output_signature',
            'input_before', 'input_after', 'output_aliases')
    return (ordinary.get('status') in ('ok', 'exception')
            and ordinary.get('input_before') is not None and ordinary.get('input_after') is not None
            and (ordinary.get('status') == 'exception' or ordinary.get('output_signature') is not None)
            and all(ordinary.get(k) == traced.get(k) for k in keys))


def execute_probe(source, entry, literal, domain, directory, *, names=(), lines=(), max_events=128):
    """One durable ordinary+traced pair. Caller explicitly supplies domain, names, lines."""
    args = parse_literal(literal)
    if not in_domain(args, domain):
        raise ValueError('outside_declared_domain')
    if not isinstance(source, str) or len(source.encode()) > 65536:
        raise ValueError('source_size')
    tree = ast.parse(source)
    functions = [f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == entry]
    if len(functions) != 1 or [a.arg for a in functions[0].args.args] != [d['name'] for d in domain]:
        raise ValueError('signature_domain_mismatch')
    if len(names) > 8 or any(type(n) is not str or not n.isidentifier() for n in names):
        raise ValueError('snapshot_names')
    if len(lines) > 32 or any(type(n) is not int or n < 1 or n > len(source.splitlines()) for n in lines):
        raise ValueError('snapshot_lines')
    if type(max_events) is not int or not 1 <= max_events <= 256:
        raise ValueError('event_budget')
    limits = {'max_events': max_events, 'max_names': 8, 'snapshot_bytes': 256,
              'max_output_bytes': 4096, 'worker_timeout': 2, 'address_space_bytes': 512 * 1024 * 1024}
    worker_hashes = {n: hashlib.sha256((HERE/n).read_bytes()).hexdigest()
                     for n in ('flow_worker.py', 'chain_inputs.py', 'paths.py', 'config.json')}
    results = {}
    for mode in ('ordinary', 'traced'):
        job = {'source': source, 'entry': entry, 'input_repr': literal, 'mode': mode,
               'valid_code': None, 'limits': limits}
        if mode == 'traced':
            job.update(snapshot_names=list(names), snapshot_lines=sorted(set(lines)))
        folder = Path(directory) / digest({'job': job, 'worker_hashes': worker_hashes})
        results[mode] = run_once(HERE/'flow_worker.py', job, folder, timeout=8)
    return dict(results, native_checked=observed_parity(results['ordinary'], results['traced']),
                scope='observed runtime values only; no causal attribution or normative proof')
