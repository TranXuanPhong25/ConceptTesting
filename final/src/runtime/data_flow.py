"""Conservative local-binding DU candidates and bounded, sandbox-only event tracing.

Static pairs deliberately overapproximate: their feasibility is unknown. Runtime
pairs require an observed def-clear reaching binding in the same invocation.
Heap/alias flow, interprocedural flow and all-DU-path adequacy are not measured.
"""
from __future__ import annotations

import ast
import sys

MAX_NODES = 10000
MAX_PAIRS = 20000
MAX_EVENTS = 100000
MAX_FRAMES = 2000
HOOK = '__data_flow_trace__'


class Index(ast.NodeVisitor):
    def __init__(self, source, entry):
        self.tree = ast.parse(source)
        self.definitions, self.uses, self.conditions = [], [], []
        self.def_nodes, self.use_nodes, self.condition_nodes = {}, {}, {}
        self.scope, self.locals, self.predicate = '', set(), None
        self.unsupported = set()
        self.pairs = []
        nodes = list(ast.walk(self.tree))
        if len(nodes) > MAX_NODES:
            self.unsupported.add('source_node_limit')
            return
        forbidden = (ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda, ast.ListComp,
                     ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.Global,
                     ast.Nonlocal, ast.NamedExpr, ast.Yield, ast.YieldFrom,
                     ast.Await, ast.Delete, ast.With, ast.AsyncWith, ast.Match)
        for node in nodes:
            if isinstance(node, ast.Compare) and len(node.ops) > 1:
                self.unsupported.add('chained_comparison_truthiness')
            if isinstance(node, forbidden):
                self.unsupported.add(type(node).__name__)
            if isinstance(node, ast.Name) and node.id.startswith(HOOK):
                self.unsupported.add('reserved_trace_name')
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {
                    'exec', 'eval', 'locals', 'globals', 'vars', 'compile'}:
                self.unsupported.add('dynamic_namespace')
            if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
                    alias.name in {'sys', 'inspect'} for alias in node.names):
                self.unsupported.add('frame_introspection')
            if isinstance(node, ast.ExceptHandler) and node.name:
                self.unsupported.add('exception_binding')
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.For)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(not isinstance(target, ast.Name) for target in targets):
                    self.unsupported.add('heap_or_destructuring_store')
        functions = [n for n in self.tree.body if isinstance(n, ast.FunctionDef)]
        if not any(fn.name == entry for fn in functions):
            self.unsupported.add('missing_entry')
        for fn in functions:
            if any(isinstance(n, ast.FunctionDef) and n is not fn for n in ast.walk(fn)):
                self.unsupported.add('nested_function_or_closure')
            if any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(fn)):
                self.unsupported.add('local_import_binding')
            if fn.decorator_list:
                self.unsupported.add('decorated_function')
            self.scope = fn.name + ':' + str(fn.lineno)
            arguments = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
            arguments += [a for a in (fn.args.vararg, fn.args.kwarg) if a]
            self.locals = {a.arg for a in arguments} | {
                n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            for arg in arguments:
                self.define(arg, arg.arg)
            for statement in fn.body:
                self.visit(statement)
        self.pairs = []
        for definition in self.definitions:
            for use in self.uses:
                if (definition['variable'], definition['scope']) != (use['variable'], use['scope']):
                    continue
                for outcome in ('T', 'F') if use['kind'] == 'p-use' else (None,):
                    pair = dict(id='du:' + definition['id'] + ':' + use['id'] + (':' + outcome if outcome else ''),
                                definition_id=definition['id'], use_id=use['id'], variable=use['variable'],
                                scope=use['scope'], definition=definition['line'], use=use['line'], kind=use['kind'])
                    if outcome:
                        pair['outcome'] = outcome
                    self.pairs.append(pair)
                    if len(self.pairs) >= MAX_PAIRS:
                        self.unsupported.add('static_pair_limit')
                        return

    def define(self, node, variable):
        row = dict(id='d' + str(len(self.definitions)), variable=variable, scope=self.scope,
                   line=node.lineno, column=node.col_offset)
        self.definitions.append(row)
        self.def_nodes[id(node)] = row

    def use(self, node, variable):
        row = dict(id='u' + str(len(self.uses)), variable=variable, scope=self.scope,
                   line=node.lineno, column=node.col_offset, kind='p-use' if self.predicate else 'c-use')
        if self.predicate:
            row['condition_id'] = self.predicate
        self.uses.append(row)
        self.use_nodes[id(node)] = row

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.define(node, node.id)
        elif isinstance(node.ctx, ast.Load) and node.id in self.locals:
            self.use(node, node.id)

    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.use(node.target, node.target.id)
        self.generic_visit(node)

    def condition(self, node):
        row = dict(id='condition' + str(len(self.conditions)), scope=self.scope,
                   line=node.lineno, column=node.col_offset, source=ast.unparse(node),
                   role='decision' if isinstance(node, ast.BoolOp) else 'atom')
        self.conditions.append(row)
        self.condition_nodes[id(node)] = row
        previous = self.predicate
        self.predicate = row['id']
        if isinstance(node, ast.BoolOp):
            for child in node.values:
                self.condition(child)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            self.condition(node.operand)
        else:
            self.visit(node)
        self.predicate = previous

    def visit_If(self, node):
        self.condition(node.test)
        for statement in node.body + node.orelse:
            self.visit(statement)

    visit_While = visit_If

    def visit_IfExp(self, node):
        self.condition(node.test)
        self.visit(node.body)
        self.visit(node.orelse)

    def visit_Assert(self, node):
        self.condition(node.test)
        if node.msg:
            self.visit(node.msg)

    def result(self):
        return dict(definitions=self.definitions, uses=self.uses,
                    pairs=[] if self.unsupported else self.pairs, conditions=self.conditions,
                    unsupported=sorted(self.unsupported), status='unsupported' if self.unsupported else 'supported',
                    pair_feasibility='unknown',
                    limitations=['local_name_bindings_only', 'heap_alias_flow_not_measured',
                                 'interprocedural_flow_not_measured', 'all_du_paths_not_measured',
                                 'chained_comparisons_unsupported'])


def analyze(source: str, entry: str) -> dict:
    try:
        return Index(source, entry).result()
    except (SyntaxError, RecursionError, ValueError) as error:
        return dict(definitions=[], uses=[], pairs=[], conditions=[],
                    unsupported=[type(error).__name__], status='unsupported', pair_feasibility='unknown')


class Instrument(ast.NodeTransformer):
    def __init__(self, index):
        self.index = index

    def call(self, method, args, location):
        node = ast.Call(func=ast.Attribute(value=ast.Name(id=HOOK, ctx=ast.Load()),
                                         attr=method, ctx=ast.Load()), args=args, keywords=[])
        return ast.copy_location(node, location)

    def event(self, method, value, location):
        event = ast.Expr(value=self.call(method, [ast.Constant(value=value)], location))
        for node in ast.walk(event):
            node.lineno = node.end_lineno = location.lineno
            node.col_offset = node.end_col_offset = location.col_offset
        return event

    def visit_FunctionDef(self, node):
        node.body = self.transform_body(node.body)
        parameters = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        parameters += [a for a in (node.args.vararg, node.args.kwarg) if a]
        ids = [self.index.def_nodes[id(arg)]['id'] for arg in parameters]
        has_docstring = (isinstance(node.body[0], ast.Expr) and
                         isinstance(node.body[0].value, ast.Constant) and
                         isinstance(node.body[0].value.value, str))
        position = 1 if has_docstring else 0
        location = node.body[position] if position < len(node.body) else node.body[0]
        node.body.insert(position, self.event('enter', tuple(ids), location))
        return node

    def transform_body(self, body):
        transformed = []
        for statement in body:
            value = self.visit(statement)
            transformed.extend(value if isinstance(value, list) else [value])
        return transformed

    def visit_Name(self, node):
        row = self.index.use_nodes.get(id(node))
        if row and isinstance(node.ctx, ast.Load):
            return self.call('use', [ast.Constant(row['id']), node], node)
        return node

    def visit_Assign(self, node):
        definitions = [self.index.def_nodes[id(target)]['id'] for target in node.targets]
        self.generic_visit(node)
        return [node] + [self.event('define', value, node) for value in definitions]

    def visit_AnnAssign(self, node):
        definition = self.index.def_nodes[id(node.target)]['id']
        self.generic_visit(node)
        return [node, self.event('define', definition, node)] if node.value else node

    def visit_AugAssign(self, node):
        use = self.index.use_nodes[id(node.target)]['id']
        definition = self.index.def_nodes[id(node.target)]['id']
        node.value = self.visit(node.value)
        read = ast.Name(id=node.target.id, ctx=ast.Load())
        ast.copy_location(read, node.target)
        before = ast.copy_location(ast.Expr(value=self.call('use', [ast.Constant(use), read], node)), node)
        return [before, node, self.event('define', definition, node)]

    def visit_For(self, node):
        definition = self.index.def_nodes[id(node.target)]['id']
        self.generic_visit(node)
        node.body.insert(0, self.event('define', definition, node.body[0]))
        return node

    def condition(self, node):
        row = self.index.condition_nodes[id(node)]
        if isinstance(node, ast.BoolOp):
            node.values = [self.condition(child) for child in node.values]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            node.operand = self.condition(node.operand)
        else:
            node = self.visit(node)
        finish = self.call('condition', [ast.Constant(row['id']), node], node)
        start = self.call('begin', [ast.Constant(row['id'])], node)
        return ast.copy_location(ast.Subscript(value=ast.Tuple(elts=[start, finish], ctx=ast.Load()),
                                               slice=ast.Constant(1), ctx=ast.Load()), node)

    def visit_If(self, node):
        node.test = self.condition(node.test)
        node.body = self.transform_body(node.body)
        node.orelse = self.transform_body(node.orelse)
        return node

    visit_While = visit_If

    def visit_IfExp(self, node):
        node.test = self.condition(node.test)
        node.body, node.orelse = self.visit(node.body), self.visit(node.orelse)
        return node

    def visit_Assert(self, node):
        node.test = self.condition(node.test)
        if node.msg:
            node.msg = self.visit(node.msg)
        return node


class Trace:
    """No candidate values are retained or included in feedback."""
    def __init__(self, source, entry):
        self.index = Index(source, entry)
        self.analysis = self.index.result()
        self.frames, self.pairs, self.outcomes = {}, set(), set()
        self.events = 0
        self.truncated = False
        self.definitions = {row['id']: row for row in self.index.definitions}
        self.uses = {row['id']: row for row in self.index.uses}
        self.pair_ids = {(row['definition_id'], row['use_id'], row.get('outcome')): row['id']
                         for row in self.analysis['pairs']}

    def state(self, frame):
        self.events += 1
        if self.events > MAX_EVENTS:
            self.truncated = True
            return None
        return self.frames.get(frame)

    def enter(self, ids):
        frame = sys._getframe(1)
        if len(self.frames) >= MAX_FRAMES:
            self.truncated = True
            return
        self.frames[frame] = ({self.definitions[value]['variable']: value for value in ids}, {})

    def define(self, definition):
        state = self.state(sys._getframe(1))
        if state:
            state[0][self.definitions[definition]['variable']] = definition

    def use(self, use, value):
        state = self.state(sys._getframe(1))
        if state:
            row = self.uses[use]
            definition = state[0].get(row['variable'])
            if definition:
                if row['kind'] == 'p-use':
                    state[1].setdefault(row['condition_id'], {})[use] = definition
                else:
                    self.pairs.add(self.pair_ids[(definition, use, None)])
        return value

    def begin(self, condition):
        state = self.state(sys._getframe(1))
        if state:
            state[1][condition] = {}

    def condition(self, condition, value):
        # Convert the original object exactly once; outer BoolOps see booleans.
        outcome = 'T' if value else 'F'
        state = self.state(sys._getframe(1))
        if state:
            self.outcomes.add((condition, outcome))
            for use, definition in state[1].pop(condition, {}).items():
                self.pairs.add(self.pair_ids[(definition, use, outcome)])
        return outcome == 'T'

    def code(self, source):
        if self.analysis['status'] != 'supported':
            return compile(source, '/work/program.py', 'exec')
        tree = self.index.tree
        instrument = Instrument(self.index)
        tree.body = [instrument.visit(node) if isinstance(node, ast.FunctionDef) else node for node in tree.body]
        return compile(ast.fix_missing_locations(tree), '/work/program.py', 'exec')

    def result(self):
        unsupported = self.analysis['unsupported'][:]
        if self.truncated:
            unsupported.append('runtime_event_or_frame_limit')
        return dict(status='partial' if self.truncated else self.analysis['status'],
                    pairs=sorted(self.pairs), condition_outcomes=[list(item) for item in sorted(self.outcomes)],
                    unsupported=unsupported, events=min(self.events, MAX_EVENTS),
                    limitations=self.analysis['limitations'])
