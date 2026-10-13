"""Optional round-two measurements. Called only inside the existing sandbox."""
import ast
from . import preconditions, tracer


def outcome(result):
    status, value = result
    return dict(status=status, value=repr(value))


def violated_condition(task, args):
    """Identify the failed conjunct in valid(), preserving the mined predicate."""
    source = task['mined_valid_src']
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'valid')
    returned = next((n.value for n in fn.body if isinstance(n, ast.Return)), None)
    terms = returned.values if isinstance(returned, ast.BoolOp) and isinstance(returned.op, ast.And) else [returned]
    params = fn.args
    for term in terms:
        if term is None:
            continue
        probe = ast.FunctionDef(name='_feedback_condition', args=params,
                                body=[ast.Return(value=term)], decorator_list=[])
        code = source + '\n' + ast.unparse(ast.fix_missing_locations(probe))
        try:
            checker = preconditions.load_predicate(code, '_feedback_condition')
            with tracer.alarm(1):
                if checker(*tracer.dcopy(args)) is True:
                    continue
            reason = ast.unparse(term)
        except BaseException as exc:
            reason = ast.unparse(term) + f' raised {type(exc).__name__}'
        # Expand the named mined conjunct, so feedback describes the condition.
        names = {n.id for n in ast.walk(term) if isinstance(n, ast.Name)}
        definitions = [ast.unparse(n) for n in tree.body if isinstance(n, ast.FunctionDef)
                       and (n.name in names or n.name in {name+'_m' for name in names})]
        return reason + ('\n' + '\n'.join(definitions) if definitions else '')
    return 'valid() did not return True'


def changed_expression(left, right, parents=()):
    """Find the expression computing the changed operation, not just its token."""
    if ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False):
        return None
    if type(left) is type(right):
        for field in left._fields:
            a, b = getattr(left, field), getattr(right, field)
            if isinstance(a, ast.AST) and isinstance(b, ast.AST):
                found = changed_expression(a, b, parents+((left, right),))
                if found:
                    return found
            elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
                for x, y in zip(a, b):
                    if isinstance(x, ast.AST) and isinstance(y, ast.AST):
                        found = changed_expression(x, y, parents+((left, right),))
                        if found:
                            return found
    options = parents + ((left, right),)
    for a, b in reversed(options):
        if isinstance(a, ast.expr) and isinstance(b, ast.expr):
            if isinstance(a, (ast.Constant, ast.Name, ast.Attribute)):
                parent = next(((x,y) for x,y in reversed(parents)
                               if isinstance(x, ast.expr) and isinstance(y, ast.expr)), None)
                if parent:
                    return parent
            if not isinstance(getattr(a, 'ctx', None), ast.Store):
                return a, b
    return None


def observe_expression(tree, target, entry, args, operands=False):
    observations = []
    def capture(label, value):
        if len(observations) < 64:
            observations.append([label, repr(value)[:300]])
        return value
    class Observe(ast.NodeTransformer):
        def visit(self, node):
            if node is target:
                if operands and isinstance(node, ast.Compare):
                    node.left = wrap(node.left, 'left')
                    node.comparators = [wrap(n, f'right_{i}') for i,n in enumerate(node.comparators)]
                return wrap(node, 'value')
            return super().visit(node)
    def wrap(node, label):
        return ast.copy_location(ast.Call(func=ast.Name(id='_callfb_observe', ctx=ast.Load()),
                                         args=[ast.Constant(label), node], keywords=[]), node)
    code = compile(ast.fix_missing_locations(Observe().visit(tree)), '<put>', 'exec')
    fn = tracer.load_module(code, {'_callfb_observe': capture})[entry]
    tracer.call(fn, (args, {}), T=1)
    return observations


def observe_state(source, entry, args, line):
    """Observe locals around a changed statement when no expression maps."""
    snapshots = []
    def capture(phase, local):
        if len(snapshots) < 64:
            snapshots.append([phase, {k:repr(v)[:300] for k,v in local.items() if not k.startswith('_callfb')}])
    class Observe(ast.NodeTransformer):
        def visit(self, node):
            if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.lineno == line:
                def hook(phase):
                    return ast.copy_location(ast.Expr(ast.Call(
                        func=ast.Name(id='_callfb_state', ctx=ast.Load()),
                        args=[ast.Constant(phase), ast.Call(func=ast.Name(id='locals', ctx=ast.Load()),
                                                          args=[], keywords=[])], keywords=[])),node)
                return [hook('before'), node, hook('after')]
            return super().visit(node)
    tree = ast.fix_missing_locations(Observe().visit(ast.parse(source)))
    fn = tracer.load_module(compile(tree,'<put>','exec'), {'_callfb_state':capture})[entry]
    tracer.call(fn, (args, {}), T=1)
    return snapshots


def hint_feedback(task, fact, args, trace, sites, hit, pout, mout):
    cells, lines, _, _ = trace
    targets = set(fact.get('lines', [fact.get('line')])) - {None}
    result = dict(reached_site=bool(targets & lines) if targets else None,
                  local_behavior_differs=None, output_differs=None,
                  local_observations=[])
    if 'input_class' in fact:
        result.update(reached_site=None, local_behavior_differs=hit,
                      local_measurement='specification input class; no source site')
    elif fact['kind'] == 'MUTANT':
        result['output_differs'] = not (pout[0] == mout[0] and
                                       (pout[0] != 'ok' or tracer.same(pout[1], mout[1])))
        left, right = ast.parse(task['put']), ast.parse(fact['mutant_src'])
        pair = changed_expression(left, right)
        if pair:
            a = observe_expression(left, pair[0], task['entry'], args)
            b = observe_expression(right, pair[1], task['entry'], args)
            result.update(local_behavior_differs=(a != b) if a or b else None,
                          local_observations=dict(put=a, mutant=b),
                          local_measurement='changed expression values (up to 64 observations)')
        else:
            a = observe_state(task['put'], task['entry'], args, fact['line'])
            b = observe_state(fact['mutant_src'], task['entry'], args, fact['line'])
            result.update(local_behavior_differs=(a != b) if a or b else None,
                          local_observations=dict(put=a, mutant=b),
                          local_measurement='locals before/after changed statement (up to 64 observations)')
    elif fact['kind'] != 'STMT':
        result['local_behavior_differs'] = hit
        result['local_measurement'] = 'target branch/value class taken'
        # Existing cells retain branch outcomes and boundary comparisons.
        sid = fact.get('cell', [None])[0]
        result['local_observations'] = sorted([[s,c] for s,c in cells if s == sid], key=repr)[:64]
        tree = ast.parse(task['put'])
        compared = next((n for n in ast.walk(tree) if isinstance(n, ast.Compare)
                         and n.lineno == fact.get('line')), None)
        if compared:
            result['compared_values'] = observe_expression(tree, compared, task['entry'], args, operands=True)
    return result
