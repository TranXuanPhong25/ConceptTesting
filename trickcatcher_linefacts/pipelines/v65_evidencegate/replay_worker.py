"""Network-isolated concrete replay; only this worker executes PUT/alternative code."""
import ast
import contextlib
import copy
import io
import json
import resource
import random
import signal
import sys
from pathlib import Path


class Deadline(BaseException):
    pass


def encode(value):
    if value is None or type(value) in (int, bool, str):
        text = repr(value)
        if len(text) > 8000: raise ValueError('value_size')
        return {'type': type(value).__name__, 'repr': text}
    if type(value) in (list, tuple):
        if len(value) > 64: raise ValueError('value_size')
        return {'type': type(value).__name__, 'items': [encode(x) for x in value]}
    if type(value) is range:
        return {'type': 'range', 'start': value.start, 'stop': value.stop, 'step': value.step}
    raise ValueError('unsupported_replay_output:' + type(value).__name__)


def run(source, entry, arguments, hyp, variant, seed=None, observation_names=()):
    if seed is not None:
        random.seed(seed)
    tree = ast.parse(source)
    events, branches = [], []
    capture={'events_truncated':False,'branches_truncated':False,'capture_error':False}
    prefix = '_v57_'  # Single underscore avoids Python class name-mangling in Solution methods.
    if hyp is not None and any(isinstance(n, ast.Name) and n.id.startswith(prefix) for n in ast.walk(tree)):
        return {'status': 'unsupported', 'reason': 'reserved_identifier_collision'}
    def observe(value):
        if len(events)>=128:
            capture['events_truncated']=True
            return value
        frame = sys._getframe(1)
        locals_snapshot={}
        for name in observation_names[:8]:
            if name in frame.f_locals:
                try: locals_snapshot[name]=encode(frame.f_locals[name])
                except Exception:
                    locals_snapshot[name]={'capture':'unsupported'};capture['capture_error']=True
        try:observed_value=encode(value)
        except Exception:
            observed_value={'capture':'unsupported'};capture['capture_error']=True
        events.append({'value': observed_value, 'branch_count':len(branches),
                       'function': frame.f_code.co_name, 'function_line': frame.f_code.co_firstlineno,
                       'locals':locals_snapshot})
        return value
    def branch(site, value):
        condition=bool(value)
        if len(branches)<512:branches.append({'line': site, 'value':condition})
        else:capture['branches_truncated']=True
        return condition
    target_count = 0
    class Instrument(ast.NodeTransformer):
        def visit(self, node):
            nonlocal target_count
            if hyp is not None and hasattr(node, 'end_lineno'):
                span = [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset]
                if span == hyp['span'] and type(node).__name__ == hyp['node_kind']:
                    if ast.unparse(node) != hyp['before']: raise ValueError('source_binding')
                    target_count += 1
                    if variant:
                        mode = 'exec' if isinstance(node, ast.AugAssign) else 'eval'
                        parsed = ast.parse(hyp['after'], mode=mode)
                        actual = parsed.body[0] if mode == 'exec' else parsed.body
                    else: actual = copy.deepcopy(node)
                    if isinstance(actual, ast.AugAssign):
                        if not isinstance(actual.target, ast.Name): raise ValueError('assignment_target')
                        # Preserve Python in-place semantics, including aliases. Observe after the real update.
                        observation = ast.Expr(value=ast.Call(func=ast.Name(prefix + 'observe', ast.Load()),
                                                             args=[ast.Name(actual.target.id, ast.Load())], keywords=[]))
                        return [ast.copy_location(actual, node), ast.copy_location(observation, node)]
                    if isinstance(actual, ast.Assign):
                        actual.value = ast.Call(func=ast.Name(prefix + 'observe', ast.Load()), args=[actual.value], keywords=[])
                    elif isinstance(actual, ast.expr):
                        actual = ast.Call(func=ast.Name(prefix + 'observe', ast.Load()), args=[actual], keywords=[])
                    else: raise ValueError('target_kind')
                    return ast.copy_location(actual, node)
            return super().visit(node)
        def visit_If(self, node):
            node = self.generic_visit(node)
            node.test = ast.copy_location(ast.Call(func=ast.Name(prefix + 'branch', ast.Load()), args=[ast.Constant(node.lineno), node.test], keywords=[]), node.test)
            return node
    try:
        if hyp is not None:tree = Instrument().visit(tree)
        if hyp is not None and target_count != 1: raise ValueError('target_count')
        namespace = {prefix + 'observe': observe, prefix + 'branch': branch, '__name__': '__v57_put__'}
        signal.alarm(2)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exec(compile(ast.fix_missing_locations(tree), '<v57-replay>', 'exec'), namespace)
            result = namespace[entry](*copy.deepcopy(arguments))
        try:output=encode(result)
        except Exception:
            return {'status':'output_unavailable','reason':'unsupported_or_oversize_output',
                    'execution_status':'returned','site_events':events,'branches':branches,'capture':capture}
        return {'status': 'ok', 'output':output, 'site_events': events, 'branches': branches,'capture':capture}
    except Deadline:
        return {'status': 'timeout'}
    except BaseException as exc:
        return {'status': 'error', 'reason': type(exc).__name__ + ':' + str(exc)[:160]}
    finally:
        signal.alarm(0)


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(Deadline()))
    request = json.loads(Path(sys.argv[1]).read_text())
    if request.get('seed') is not None:
        random.seed(request['seed'])
    args = ast.literal_eval(request['arguments'])
    variants = (('put', False),) if request.get('hypothesis') is None or request.get('observe_only') else (('put', False), ('alternative', True))
    rows = {name: run(request['source'], request['entry'], args, request['hypothesis'], variant, request.get('seed'),request.get('observation_names',())) for name, variant in variants}
    Path(sys.argv[2]).write_text(json.dumps(rows, ensure_ascii=True) + '\n')


if __name__ == '__main__':
    main()
