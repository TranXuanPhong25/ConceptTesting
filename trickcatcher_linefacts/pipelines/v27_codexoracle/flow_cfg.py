"""Intraprocedural normal-flow CFG, control dependence and syntactic data facts for a supported subset.

Unsupported constructs fail closed (no graph); expression-internal control and call effects are labeled, never guessed.
Postdominators come from networkx on the reversed graph; scope = terminating paths to normal or explicit-raise exits.
"""
import ast
import networkx as nx

ENTRY, EXIT, RAISE_EXIT = 'ENTRY', 'EXIT', 'RAISE_EXIT'
SYNTHETIC = (ENTRY, EXIT, RAISE_EXIT)
UNSUPPORTED_STMT = (ast.Try, ast.With, ast.AsyncWith, ast.AsyncFor, ast.Match, ast.FunctionDef, ast.AsyncFunctionDef,
                    ast.ClassDef, ast.Global, ast.Nonlocal) + ((ast.TryStar,) if hasattr(ast, 'TryStar') else ())
GENERATOR_EXPR = (ast.Yield, ast.YieldFrom, ast.Await)
COMPOUND = (ast.If, ast.While, ast.For)
SCOPES = (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
CD_SCOPE = 'terminating_paths_to_normal_or_explicit_raise_exit; implicit exceptions and infinite paths not modeled'


def uid(task, node):
    return f"{task['source_hash']}:{type(node).__name__}:{node.lineno}:{node.col_offset}:{node.end_lineno}:{node.end_col_offset}"


def entry_function(task):
    tree = ast.parse(task['source_original'])
    return next(x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == task['entry'])


def body_without_docstring(fn):
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and type(body[0].value.value) is str:
        return body[1:]
    return body


def header_exprs(stmt):
    """Expressions evaluated at the statement node itself (compound headers exclude their bodies)."""
    if isinstance(stmt, (ast.If, ast.While)):
        return [stmt.test]
    if isinstance(stmt, ast.For):
        return [stmt.target, stmt.iter]
    return [stmt]


def header_lines(stmt):
    if isinstance(stmt, COMPOUND):
        first_body = stmt.body[0].lineno
        return stmt.lineno, max(stmt.lineno, first_body - 1)
    return stmt.lineno, stmt.end_lineno


def walk_header(stmt):
    for root in header_exprs(stmt):
        yield from ast.walk(root)


def unsupported_reasons(fn):
    reasons = []
    if isinstance(fn, ast.AsyncFunctionDef):
        reasons.append('async_function')
    for node in ast.walk(fn):
        if node is fn:
            continue
        if isinstance(node, UNSUPPORTED_STMT):
            reasons.append(f'{type(node).__name__}@{node.lineno}')
        elif isinstance(node, GENERATOR_EXPR):
            reasons.append(f'generator_or_await@{node.lineno}')
    return sorted(set(reasons))


def expression_limits(stmt):
    limits = set()
    for node in walk_header(stmt):
        if isinstance(node, ast.Call):
            limits.add('call_semantics_and_effects_unknown')
        elif isinstance(node, (ast.BoolOp, ast.IfExp)):
            limits.add('expression_internal_control_not_modeled')
        elif isinstance(node, SCOPES):
            limits.add('nested_expression_scope_not_modeled')
        elif isinstance(node, ast.NamedExpr):
            limits.add('assignment_expression_write')
    return sorted(limits)


def data_facts(stmt):
    """Syntactic reads/writes of the statement header; no reaching definitions, aliases or heap propagation."""
    reads, writes, heap = set(), set(), set()
    scoped = set()
    for node in walk_header(stmt):
        if isinstance(node, SCOPES):
            for inner in ast.walk(node):
                if isinstance(inner, ast.comprehension):
                    scoped.update(n.id for n in ast.walk(inner.target) if isinstance(n, ast.Name))
                elif isinstance(inner, ast.Lambda):
                    scoped.update(a.arg for a in inner.args.posonlyargs + inner.args.args + inner.args.kwonlyargs)
    for node in walk_header(stmt):
        if isinstance(node, ast.Name):
            if node.id in scoped:
                continue
            (reads if isinstance(node.ctx, ast.Load) else writes).add(node.id)
        elif isinstance(node, (ast.Subscript, ast.Attribute)) and isinstance(node.ctx, (ast.Store, ast.Del)):
            base = node.value
            while isinstance(base, (ast.Subscript, ast.Attribute)):
                base = base.value
            if isinstance(base, ast.Name):
                heap.add(base.id)
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
        reads.add(stmt.target.id)
    return dict(reads=sorted(reads), writes=sorted(writes), heap_writes_through=sorted(heap),
                scope='syntactic_header_names_only', reaching_definitions='unknown', alias_heap_propagation='unknown')


class _Builder:
    def __init__(self, task):
        self.task, self.nodes, self.edges, self.stmts = task, {}, [], {}

    def node(self, stmt):
        sid = uid(self.task, stmt)
        lo, hi = header_lines(stmt)
        self.stmts[sid] = stmt
        self.nodes[sid] = dict(id=sid, kind=type(stmt).__name__, span=[stmt.lineno, stmt.col_offset, stmt.end_lineno, stmt.end_col_offset],
                               header_lines=[lo, hi], limits=expression_limits(stmt), data=data_facts(stmt))
        return sid

    def connect(self, preds, target):
        for source, label in preds:
            self.edges.append((source, target, label))

    def seq(self, stmts, preds, loop):
        for stmt in stmts:
            preds = self.stmt(stmt, preds, loop)
        return preds

    def stmt(self, s, preds, loop):
        sid = self.node(s)
        self.connect(preds, sid)
        if isinstance(s, ast.If):
            true = self.seq(s.body, [(sid, 'true')], loop)
            false = self.seq(s.orelse, [(sid, 'false')], loop) if s.orelse else [(sid, 'false')]
            return true + false
        if isinstance(s, (ast.While, ast.For)):
            enter, leave = ('true', 'false') if isinstance(s, ast.While) else ('iterate', 'exhausted')
            ctx = dict(head=sid, breaks=[])
            self.connect(self.seq(s.body, [(sid, enter)], ctx), sid)
            # Only the literal `while True` idiom drops its syntactic false edge; no other constant folding.
            infinite = isinstance(s, ast.While) and isinstance(s.test, ast.Constant) and s.test.value is True
            exits = [] if infinite else [(sid, leave)]
            if s.orelse and exits:
                exits = self.seq(s.orelse, exits, loop)
            elif s.orelse:
                self.seq(s.orelse, [], loop)
            return exits + ctx['breaks']
        if isinstance(s, ast.Return):
            self.edges.append((sid, EXIT, 'return'))
            return []
        if isinstance(s, ast.Raise):
            self.edges.append((sid, RAISE_EXIT, 'raise'))
            return []
        if isinstance(s, ast.Assert):
            self.edges.append((sid, RAISE_EXIT, 'assert_fail'))
            return [(sid, 'assert_pass')]
        if isinstance(s, ast.Break):
            loop['breaks'].append((sid, 'break'))
            return []
        if isinstance(s, ast.Continue):
            self.edges.append((sid, loop['head'], 'continue'))
            return []
        return [(sid, 'next')]


def control_dependence(graph, reachable):
    """Ferrante-style CD over the supported graph; None when some reachable node cannot reach an exit."""
    sub = graph.subgraph(reachable).copy()
    exits = [x for x in (EXIT, RAISE_EXIT) if x in sub]
    sink = '__SINK__'
    sub.add_node(sink)
    for x in exits:
        sub.add_edge(x, sink, label='virtual')
    can_exit = nx.ancestors(sub, sink) | {sink}
    if set(reachable) - can_exit:
        return None, sorted(set(reachable) - can_exit)
    ipdom = nx.immediate_dominators(sub.reverse(copy=True), sink)
    deps = {}
    for a, b, data in sub.edges(data=True):
        if b == sink:
            continue
        runner = b
        while runner != ipdom[a] and runner != sink:
            if runner not in SYNTHETIC:
                deps.setdefault(runner, []).append(dict(source=a, label=data['label']))
            runner = ipdom[runner]
    return {k: sorted(v, key=lambda d: (d['source'], d['label'])) for k, v in deps.items()}, []


def build(task):
    fn = entry_function(task)
    reasons = unsupported_reasons(fn)
    params = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
    params += [a.arg for a in (fn.args.vararg, fn.args.kwarg) if a is not None]
    base = dict(task_hash=task['task_hash'], entry=task['entry'], code_identity=[fn.name, fn.lineno], parameters=params,
                scope='entry_function_only; helpers and imported code not modeled')
    if reasons:
        return dict(base, supported=False, unsupported=reasons, nodes={}, edges=[], control_dependence=None)
    b = _Builder(task)
    tail = b.seq(body_without_docstring(fn), [(ENTRY, 'entry')], None)
    for source, label in tail:
        b.edges.append((source, EXIT, 'fall_off_end' if source != ENTRY else 'empty_body'))
    graph = nx.DiGraph()
    graph.add_nodes_from([ENTRY, EXIT, RAISE_EXIT, *b.nodes])
    edges, duplicates = [], []
    for i, (source, target, label) in enumerate(b.edges):
        if graph.has_edge(source, target):
            duplicates.append([source, target, label])
            continue
        graph.add_edge(source, target, label=label, id=f'E{len(edges) + 1}')
        edges.append(dict(id=f'E{len(edges) + 1}', source=source, target=target, label=label))
    if duplicates:
        return dict(base, supported=False, unsupported=['parallel_edges'], nodes={}, edges=[], control_dependence=None)
    reachable = nx.descendants(graph, ENTRY) | {ENTRY}
    for sid, rec in b.nodes.items():
        rec['reachable'] = sid in reachable
    cd, stuck = control_dependence(graph, reachable)
    lines = {}
    for sid, rec in b.nodes.items():
        lo, hi = rec['header_lines']
        for line in range(lo, hi + 1):
            lines.setdefault(line, []).append(sid)
    return dict(base, supported=True, unsupported=[], nodes=b.nodes, edges=edges, line_candidates=lines,
                control_dependence=cd, control_dependence_scope=CD_SCOPE if cd is not None else 'unknown',
                control_dependence_unknown_reason=None if cd is not None else dict(nodes_without_exit_path=stuck),
                parameter_definitions_at=ENTRY, graph=graph)


def edge_lookup(cfg):
    return {(e['source'], e['target']): e for e in cfg['edges']}


def neighborhood(cfg, ids, radius, max_nodes):
    """Bounded undirected BFS over CFG edges; deterministic order, omission count kept."""
    graph = cfg['graph'].to_undirected(as_view=True)
    seen, frontier = list(dict.fromkeys(ids)), list(dict.fromkeys(ids))
    for _ in range(radius):
        nxt = []
        for n in frontier:
            for m in sorted(graph.neighbors(n)):
                if m not in seen and m not in nxt:
                    nxt.append(m)
        seen += nxt
        frontier = nxt
    return seen[:max_nodes], max(0, len(seen) - max_nodes)
