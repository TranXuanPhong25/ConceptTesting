"""Source-bound paired instrumentation shared by symbolic and native execution."""
import ast
import copy
import types
from .hypotheses import PURE_CALLS, span, replacement, validate_replacement


def callees(tree):
    return {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)} | \
           {ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}

PREFIX = '_v66_'


OPAQUE = (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type)
UNSAFE = (ast.NamedExpr, ast.Yield, ast.YieldFrom, ast.Await)


class Uncopyable:
    def __init__(self, kind):
        self.kind = kind

    def __eq__(self, other):
        return isinstance(other, Uncopyable) and other.kind == self.kind

    def __hash__(self):
        return hash(self.kind)


def snap(value, memo):
    try:
        return copy.deepcopy(value, memo)
    except TypeError:
        return Uncopyable(type(value).__qualname__)


class CaptureLimit(Exception):
    pass


class Recorder:
    def __init__(self, limit=20000):
        self.limit = limit
        self.events = []
        self.branches = []
        self.pending = []

    def branch(self, location, value):
        condition = bool(value)
        if len(self.branches) >= self.limit:
            raise CaptureLimit('branch_capture_limit')
        self.branches.append((location, condition))
        return condition

    def before(self, location, frame, values):
        if len(self.events) >= self.limit:
            raise CaptureLimit('event_capture_limit')
        # Snapshot before evaluation, preserving aliases within pre-site state (shared memo).
        memo = {}
        snapshot = tuple((name, value if isinstance(value, OPAQUE) else snap(value, memo)) for name, value in values)
        return (location, frame, snapshot, len(self.branches))

    def after(self, before, value):
        self.events.append((before, copy.deepcopy(value)))
        return value

    def expression(self, before, thunk):
        return self.after(before, thunk())


def instrument(source, hypothesis, variant=False):
    tree = ast.parse(source)
    if any(isinstance(n, ast.Name) and n.id.startswith(PREFIX) for n in ast.walk(tree)):
        raise ValueError('reserved_instrument_identifier')
    count = 0
    frames = []

    class Transform(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            frames.append((f'{node.name}@{node.lineno}', True))
            node = self.generic_visit(node)
            frames.pop()
            return node

        def visit_ClassDef(self, node):
            frames.append((f'{node.name}@{node.lineno}', False))
            node = self.generic_visit(node)
            frames.pop()
            return node

        def visit(self, node):
            nonlocal count
            if hasattr(node, 'end_lineno') and span(node) == hypothesis['span'] and type(node).__name__ == hypothesis['node_kind']:
                if ast.unparse(node) != hypothesis['before']:
                    raise ValueError('source_binding_mismatch')
                if not frames or not frames[-1][1]:
                    raise ValueError('unsupported_site_outside_function')
                alt = replacement(hypothesis)
                store = isinstance(node, ast.Subscript) and not isinstance(node.ctx, ast.Load)
                if store:
                    # Store/Del target: the observed site value is the selected index, evaluated once.
                    if not isinstance(alt, ast.Subscript) or ast.dump(alt.value) != ast.dump(node.value):
                        raise ValueError('store_alternative_must_change_index_only')
                    site, alt_site = node.slice, alt.slice
                else:
                    site, alt_site = node, alt
                if hypothesis.get('origin') == 'external_proposal':
                    validate_replacement(node, alt)
                elif not callees(alt) - callees(node) <= PURE_CALLS:
                    # Source-derived edits may only recombine operations the PUT already performs at this site.
                    raise ValueError('catalog_alternative_new_callee')
                if any(isinstance(n, UNSAFE) for x in (node, alt) for n in ast.walk(x)):
                    raise ValueError('unsupported_site_syntax_in_thunk')
                count += 1
                call_names = {n.func.id for x in (site, alt_site) for n in ast.walk(x)
                              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
                # Comprehension targets are local to the site expression, not pre-site state.
                bound = {t.id for x in (site, alt_site) for c in ast.walk(x) if isinstance(c, ast.comprehension)
                         for t in ast.walk(c.target) if isinstance(t, ast.Name)}
                bound |= {a.arg for x in (site, alt_site) for l in ast.walk(x) if isinstance(l, ast.Lambda)
                          for a in l.args.posonlyargs + l.args.args + l.args.kwonlyargs}
                names = sorted({n.id for x in (site, alt_site) for n in ast.walk(x)
                                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - call_names - bound)
                if isinstance(node, ast.AugAssign):
                    names = sorted(set(names) | {node.target.id})
                values = ast.Tuple(elts=[ast.Tuple(elts=[ast.Constant(name), ast.Name(name, ast.Load())],ctx=ast.Load()) for name in names],ctx=ast.Load())
                before = ast.Call(func=ast.Name(PREFIX+'before', ast.Load()),
                                  args=[ast.Constant(hypothesis['id']), ast.Constant('/'.join(f for f, _ in frames)), values],keywords=[])
                actual = copy.deepcopy(alt if variant else node)
                if isinstance(node, ast.AugAssign):
                    save = ast.Assign(targets=[ast.Name(PREFIX+'pre', ast.Store())], value=before)
                    after = ast.Expr(value=ast.Call(func=ast.Name(PREFIX+'after', ast.Load()),
                        args=[ast.Name(PREFIX+'pre', ast.Load()), ast.Name(node.target.id,ast.Load())], keywords=[]))
                    return [ast.copy_location(x,node) for x in (save,actual,after)]
                empty = ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[])
                if store:
                    actual.ctx = type(node.ctx)()
                    actual.slice = ast.copy_location(ast.Call(func=ast.Name(PREFIX+'expression',ast.Load()),
                        args=[before, ast.Lambda(args=empty, body=actual.slice)], keywords=[]), node.slice)
                    return ast.copy_location(actual, node)
                thunk = ast.Lambda(args=empty,body=actual)
                return ast.copy_location(ast.Call(func=ast.Name(PREFIX+'expression',ast.Load()),args=[before,thunk],keywords=[]),node)
            return super().visit(node)

        def branch_node(self, node):
            node = self.generic_visit(node)
            location = f'{type(node).__name__}@{node.lineno}:{node.col_offset}'
            node.test = ast.copy_location(ast.Call(func=ast.Name(PREFIX+'branch',ast.Load()),
                args=[ast.Constant(location),node.test],keywords=[]),node.test)
            return node
        visit_If = branch_node
        visit_While = branch_node
        visit_IfExp = branch_node

    tree = Transform().visit(tree)
    if count != 1:
        raise ValueError('expected_one_target:' + str(count))
    return ast.fix_missing_locations(tree)


def load_program(source, entry, hypothesis=None, variant=False, recorder=None):
    tree = instrument(source,hypothesis,variant) if recorder is not None else (
        __import__(__package__+'.hypotheses',fromlist=['patch_tree']).patch_tree(source,hypothesis)
        if variant else ast.parse(source))
    namespace = {'__name__': '__v66_put__'}
    if recorder is not None:
        namespace.update({PREFIX+name:getattr(recorder,name) for name in ('before','after','expression','branch')})
    exec(compile(tree, '<v66-alternative>' if variant else '<v66-put>', 'exec'), namespace)
    return namespace[entry]


def local_difference(put, alt, family, equal):
    """First differing site occurrence must have equal pre-state and path prefix."""
    if family == 'STATE_ACCUMULATION' and (len(put.events)<2 or len(alt.events)<2):
        return None
    for index, (left, right) in enumerate(zip(put.events,alt.events)):
        if equal(left[1], right[1]):
            continue
        a, b = left[0], right[0]
        if a[:2] != b[:2] or not equal(a[2],b[2]):
            return None
        if put.branches[:a[3]] != alt.branches[:b[3]]:
            return None
        return index
    return None
