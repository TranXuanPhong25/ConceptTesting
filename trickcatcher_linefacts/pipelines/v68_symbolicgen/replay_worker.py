"""Network-isolated concrete replay; only this worker executes PUT/alternative code."""
import ast
import contextlib
import copy
import io
import json
import resource
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


def run(source, entry, arguments, hyp, variant):
    tree = ast.parse(source)
    events, branches = [], []
    prefix = '_v57_'  # Single underscore avoids Python class name-mangling in Solution methods.
    if any(isinstance(n, ast.Name) and n.id.startswith(prefix) for n in ast.walk(tree)):
        return {'status': 'unsupported', 'reason': 'reserved_identifier_collision'}
    def observe(value):
        events.append({'value': encode(value), 'branches': copy.deepcopy(branches)})
        if len(events) > 128: raise ValueError('event_cap')
        return value
    def branch(site, value):
        branches.append({'line': site, 'value': bool(value)})
        if len(branches) > 512: raise ValueError('branch_cap')
        return value
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
        tree = Instrument().visit(tree)
        if hyp is not None and target_count != 1: raise ValueError('target_count')
        namespace = {prefix + 'observe': observe, prefix + 'branch': branch, '__name__': '__v57_put__'}
        signal.alarm(2)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exec(compile(ast.fix_missing_locations(tree), '<v57-replay>', 'exec'), namespace)
            result = namespace[entry](*copy.deepcopy(arguments))
        return {'status': 'ok', 'output': encode(result), 'site_events': events, 'branches': branches}
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
    args = ast.literal_eval(request['arguments'])
    variants = (('put', False),) if request.get('hypothesis') is None else (('put', False), ('alternative', True))
    rows = {name: run(request['source'], request['entry'], args, request['hypothesis'], variant) for name, variant in variants}
    Path(sys.argv[2]).write_text(json.dumps(rows, ensure_ascii=True) + '\n')


if __name__ == '__main__':
    main()
