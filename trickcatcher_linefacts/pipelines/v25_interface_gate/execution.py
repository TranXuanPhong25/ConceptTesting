"""Fixed-schedule native/traced replay through the parent's network-isolated sandbox."""
from pathlib import Path
import hashlib
import sys

from .chain_inputs import parse_arguments, literal_for_transport
from .common import digest, immutable, observation, native_observation, worker_identity
from .gen_inputs import sandbox
from .paths import CONFIG
from .isolated import run_once

HERE = Path(__file__).resolve().parent
KEYS = ('status', 'exception_type', 'exception_module', 'output_capture',
        'output_signature', 'input_before', 'input_after', 'output_aliases')


def execute(task, literal, root):
    args = parse_arguments(literal, task['arity'])
    literal = literal_for_transport(args)
    folder = Path(root) / digest({'task': task['task_hash'], 'input': literal,
                                'worker': (HERE / 'execution_worker.py').read_text(),
                                'interpreter': CONFIG['V4_PYTHON'], 'python': sys.version, 'worker_identity': worker_identity(),
                                'policy': {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
                                           for n in ('execution.py', 'isolated.py', 'chain_inputs.py', 'binding.py', 'config.json', 'source_view.py')}})
    results = {}
    for mode in ('ordinary', 'traced'):
        job = {'source': task['source_original'], 'entry': task['entry'],
               'input_repr': literal, 'mode': mode, 'valid_code': task.get('valid_code')}
        # Each mode owns a durable attempt/result namespace; no implicit retry on resume.
        result = run_once(HERE / 'execution_worker.py', job, folder / mode)
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

