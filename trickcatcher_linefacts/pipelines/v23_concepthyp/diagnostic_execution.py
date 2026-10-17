"""Fixed-schedule native/traced replay through the parent's network-isolated sandbox."""
from pathlib import Path

from .chain_inputs import parse_arguments, literal_for_transport
from .diagnostic_core import digest, immutable, observation, native_observation
from .gen_inputs import sandbox
from .paths import CONFIG

HERE = Path(__file__).resolve().parent
KEYS = ('status', 'exception_type', 'exception_module', 'output_capture',
        'output_signature', 'input_before', 'input_after', 'output_aliases')


def execute(task, literal, root):
    args = parse_arguments(literal, task['arity'])
    literal = literal_for_transport(args)
    folder = Path(root) / digest({'task': task['task_hash'], 'input': literal,
                                'worker': (HERE / 'execution_worker.py').read_text(),
                                'interpreter': CONFIG['V4_PYTHON']})
    results = {}
    for mode in ('ordinary', 'traced'):
        job = {'source': task['source_original'], 'entry': task['entry'],
               'input_repr': literal, 'mode': mode, 'valid_code': task.get('valid_code')}
        jp = folder / (mode + '_job.json')
        op = folder / (mode + '_result.json')
        immutable(jp, job)
        if op.exists():
            import json
            result = json.loads(op.read_text())
        else:
            # An unresolved/failed isolated worker is cached as unknown; no host execution fallback.
            try:
                result = sandbox(CONFIG['V4_PYTHON'], HERE / 'execution_worker.py', jp, op, 8)
            except (RuntimeError, OSError):
                result = {'status': 'unresolved', 'reason': 'isolated_worker_failed', 'events': []}
                # sandbox may have left an oversize/broken file; it is not a trusted cache entry.
                if op.exists():
                    op.rename(op.with_suffix('.rejected'))
                immutable(op, result)
        results[mode] = result
    ordinary, traced = results['ordinary'], results['traced']
    checked = (ordinary.get('status') in ('ok', 'exception')
               and traced.get('trace_complete') is True
               and all(ordinary.get(k) == traced.get(k) for k in KEYS)
               and ordinary.get('input_before') is not None
               and ordinary.get('input_after') is not None)
    if ordinary.get('status') == 'ok':
        checked = checked and ordinary.get('output_capture') == 'literal' and ordinary.get('output_signature') is not None
    events = traced.get('events', [])
    cap = CONFIG['diagnostic']['trace_prompt_events']
    return {'input': literal, 'status': ordinary.get('status'),
            'output_repr': ordinary.get('output_repr'),
            'exception_type': ordinary.get('exception_type'),
            'native_checked': checked,
            'verification_reason': 'native_and_traced_signatures_agree' if checked else 'unresolved_or_disagreeing_execution',
            'events': events[:cap], 'omitted_events': max(0, len(events) - cap),
            'trace_scope': 'line events; no local-effect or data-propagation proof',
            'validity_scope': 'authored fixture type/domain filter',
            'worker_status': {k: v.get('status') for k, v in results.items()}}


def replay_candidates(task, proposal, root):
    records = []
    for index, item in enumerate(proposal['inputs']):
        row = {'slot': index, 'proposal': item}
        try:
            args = parse_arguments(item['arguments'], task['arity'])
            literal = literal_for_transport(args)
            expected = observation(item['expected'])
            predicted = observation(item['predicted_actual'])
        except ValueError as exc:
            row.update(state='invalid_literal', reason=str(exc))
            records.append(row)
            continue
        result = execute(task, literal, root)
        actual = native_observation(result)
        row.update(state='observed' if actual is not None else 'unknown',
                   input=literal, execution=result,
                   prediction_matches_native=predicted == actual if actual is not None else None,
                   expected_differs_native=expected != actual if actual is not None else None)
        records.append(row)
    return records
