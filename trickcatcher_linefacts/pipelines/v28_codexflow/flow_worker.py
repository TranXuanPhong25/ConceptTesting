"""One ordinary OR traced PUT execution in a clean isolated process, with invocation-scoped events.

Traced mode records call/line/return/exception events of module code with invocation IDs and code identity, plus
bounded pre-statement snapshots of requested names. Hitting the event cap stops recording (trace_complete=False) but
never changes execution. No semantic matcher.
"""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import resource
import signal
import sys
if not __package__:
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parents[2]))
    __package__ = 'trickcatcher_linefacts.pipelines.' + here.name
from .chain_inputs import check_topology, typed_value, parse_literal


class Deadline(BaseException):
    pass


def signature(value):
    try:
        check_topology(value, max_nodes=2048, max_items=512)
        text = repr(typed_value(value))
        return text if len(text.encode('utf-8')) <= 4096 else None
    except (ValueError, RecursionError, TypeError):
        return None


def bounded_repr(value, limit):
    try:
        if signature(value) is None:
            return dict(type=type(value).__name__, capture='type_only')
        text = repr(value)
    except Exception:
        return dict(type=type(value).__name__, capture='type_only')
    raw = text.encode('utf-8')
    if len(raw) <= limit:
        return dict(type=type(value).__name__, capture='literal', repr=text)
    return dict(type=type(value).__name__, capture='truncated', repr=raw[:limit].decode('utf-8', 'ignore'), omitted_bytes=len(raw) - limit)


def run(job):
    limits = job['limits']
    args = ast.literal_eval(job['input_repr'])
    check_topology(args)
    args = copy.deepcopy(args)
    if job.get('valid_code'):
        try:
            valid_namespace = {'__name__': '__mined_filter__'}
            exec(compile(job['valid_code'], '<mined>', 'exec'), valid_namespace)
            accepted = valid_namespace['valid'](*copy.deepcopy(args)) is True
        except BaseException as exc:
            return dict(status='unresolved', reason='validity:' + type(exc).__name__, events=[], validity_checks=1)
        if not accepted:
            return dict(status='filtered', reason='mined_filter_not_spec_proof', events=[], validity_checks=1)
    before = signature(args)
    traced = job['mode'] == 'traced'
    filename = '<flow-put>'
    events, snapshots = [], []
    state = dict(inv=0, frames={}, truncated=False, omitted=0)
    snap_lines = set(job.get('snapshot_lines', []))
    names = job.get('snapshot_names', [])[:limits['max_names']]

    def record(row):
        if len(events) >= limits['max_events']:
            state['truncated'] = True
            state['omitted'] += 1
            return
        row['seq'] = len(events)
        events.append(row)

    def trace(frame, event, arg):
        code = frame.f_code
        if code.co_filename != filename:
            return None
        key = id(frame)
        if event == 'call':
            state['inv'] += 1
            state['frames'][key] = state['inv']
        inv = state['frames'].get(key)
        if event in ('call', 'line', 'return', 'exception'):
            row = dict(inv=inv, code=[code.co_name, code.co_firstlineno], event=event, line=frame.f_lineno)
            if event == 'exception':
                row['exception_type'] = arg[0].__name__
            record(row)
            if event == 'line' and frame.f_lineno in snap_lines and len(snapshots) < limits['max_events']:
                local = frame.f_locals
                snapshots.append(dict(inv=inv, line=frame.f_lineno, event_seq=events[-1]['seq'] if not state['truncated'] else None,
                                      kind='pre_statement_locals',
                                      values={n: (bounded_repr(local[n], limits['snapshot_bytes']) if n in local else dict(capture='unbound')) for n in names}))
        if event == 'return':
            state['frames'].pop(key, None)
        return trace

    namespace = {'__name__': '__flow_put__'}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(job['source'], filename, 'exec'), namespace)
    except BaseException as exc:
        return dict(status='unresolved', reason='module_load:' + type(exc).__name__, events=[])
    value = None
    try:
        if traced:
            sys.settrace(trace)
        with contextlib.redirect_stdout(io.StringIO()):
            value = namespace[job['entry']](*args)
        status, exception, exception_module = 'ok', None, None
    except Deadline:
        status, exception, exception_module = 'unresolved', None, None
    except BaseException as exc:
        status, exception, exception_module = 'exception', type(exc).__name__, type(exc).__module__
    finally:
        sys.settrace(None)
    output, capture = None, 'unavailable'
    if status == 'ok':
        try:
            if signature(value) is None:
                raise ValueError('unsupported_output')
            output = repr(value)
            if len(output.encode('utf-8')) > limits['max_output_bytes']:
                raise ValueError('oversize')
            parse_literal(output, output=True)
            capture = 'literal'
        except (ValueError, TypeError, RecursionError):
            output, capture = None, 'unsupported_or_oversize'
    return dict(status=status, exception_type=exception, exception_module=exception_module, output_capture=capture, output_repr=output,
                output_signature=signature(value) if status == 'ok' and capture == 'literal' else None,
                input_before=before, input_after=signature(args),
                output_aliases=[i for i, a in enumerate(args) if type(a) in (list, tuple, dict, set) and value is a] if status == 'ok' else [],
                events=events, snapshots=snapshots, trace_complete=traced and status != 'unresolved' and not state['truncated'],
                trace_truncated=state['truncated'], omitted_events=state['omitted'],
                validity_checks=1 if job.get('valid_code') else 0,
                validity_provenance='mined_filter_not_spec_proof' if job.get('valid_code') else 'no_filter',
                trace_scope='module_code_calls_after_initialization')


def main():
    job = json.loads(Path(sys.argv[1]).read_text())
    memory = job['limits']['address_space_bytes']
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (job['limits']['worker_timeout'] + 2,) * 2)

    def expire(*_):
        raise Deadline()
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(job['limits']['worker_timeout'])
    try:
        result = run(job)
    except BaseException as exc:
        result = dict(status='unresolved', reason=type(exc).__name__, events=[])
    finally:
        signal.alarm(0)
    Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
