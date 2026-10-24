"""Source-bound alternatives and executable construction facets; no oracle labels."""
import ast
import copy
import hashlib

FAMILIES = {
    'BOUNDARY': 'equality at a relational boundary can change the decision',
    'OPERATOR': 'a different arithmetic or Boolean operator can change behavior',
    'VALUE': 'a different value at this expression can change behavior',
    'CALL': 'a different pure function can change behavior',
    'MISSING_CASE': 'a low-cardinality input class remains untested (not a repair claim)',
    'LOOP_CARDINALITY': 'a range endpoint changes the number of executed iterations',
    'INDEX_SELECTION': 'a neighboring index selects a different valid element',
    'STATE_ACCUMULATION': 'overwriting and accumulating diverge after repeated updates',
    'ORDER_TIE': 'equal operands distinguish strict from inclusive ordering',
    'MULTIPLICITY': 'duplicate values distinguish counting occurrences from distinct values',
}

PURE_CALLS = {'len', 'set', 'sum', 'min', 'max', 'abs', 'range', 'enumerate', 'list', 'tuple', 'reversed', 'all', 'any'}
PURE_NODES = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.Store, ast.List, ast.Tuple,
              ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod,
              ast.UnaryOp, ast.Not, ast.USub, ast.UAdd, ast.BoolOp, ast.And, ast.Or,
              ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
              ast.IfExp, ast.Subscript, ast.Slice, ast.Call, ast.Assign, ast.AugAssign)


def validate_replacement(original, alternative):
    """Writer-proposed code must be a supported pure expression, not arbitrary executable text."""
    if isinstance(original, ast.AugAssign):
        if not isinstance(original.target, ast.Name): raise ValueError('proposal_target')
        targets = alternative.targets if isinstance(alternative, ast.Assign) else [alternative.target] if isinstance(alternative, ast.AugAssign) else []
        if len(targets) != 1 or not isinstance(targets[0], ast.Name) or targets[0].id != original.target.id:
            raise ValueError('proposal_must_preserve_assignment_target')
    elif not isinstance(alternative, ast.expr): raise ValueError('proposal_expression')
    for node in ast.walk(alternative):
        if not isinstance(node, PURE_NODES): raise ValueError('proposal_unsupported_syntax:' + type(node).__name__)
        if isinstance(node, ast.Constant) and node.value is not None and type(node.value) not in (bool, int, str):
            raise ValueError('proposal_constant_type')
        if isinstance(node, ast.Name) and (node.id.startswith('__') or node.id.startswith('_v57_')):
            raise ValueError('proposal_reserved_name')
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in PURE_CALLS or node.keywords):
            raise ValueError('proposal_external_or_keyword_call')


def span(node):
    return [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset]


def identifier(node, replacement):
    data = repr((span(node), ast.dump(node), ast.dump(replacement)))
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def describe(node, replacement, family, facets=(), origin='ast_catalog', **extra):
    replacement = ast.fix_missing_locations(ast.copy_location(replacement, node))
    return dict(id=identifier(node, replacement), span=span(node), node_kind=type(node).__name__,
                before=ast.unparse(node), after=ast.unparse(replacement), family=family,
                facets=list(dict.fromkeys((family, *facets))), meaning=FAMILIES[family],
                epistemic_status='behavioral_hypothesis_not_validated_repair', origin=origin,
                objective='reach exact AST site AND local value changes AND final output changes',
                spec_binding='unverified', **extra)


def catalog(source, entry, cap=48):
    tree = ast.parse(source)
    from .bindings import resolve
    try: fn, _ = resolve(tree, entry)
    except ValueError as exc: return [], [str(exc)]
    rows = []
    comparisons = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
                   ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
    arithmetic = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add}
    for n in ast.walk(fn):
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and type(n.ops[0]) in comparisons:
            alt = copy.deepcopy(n); alt.ops = [comparisons[type(n.ops[0])]()]
            strict = isinstance(n.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE))
            rows.append(describe(n, alt, 'BOUNDARY' if strict else 'OPERATOR', ('ORDER_TIE',) if strict else ()))
        elif isinstance(n, ast.BinOp) and type(n.op) in arithmetic:
            alt = copy.deepcopy(n); alt.op = arithmetic[type(n.op)]()
            rows.append(describe(n, alt, 'OPERATOR'))
        elif isinstance(n, ast.BoolOp):
            alt = copy.deepcopy(n); alt.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
            rows.append(describe(n, alt, 'OPERATOR'))
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            alt = ast.Assign(targets=[copy.deepcopy(n.target)], value=copy.deepcopy(n.value))
            rows.append(describe(n, alt, 'STATE_ACCUMULATION'))
        elif isinstance(n, ast.Subscript) and not isinstance(n.slice, ast.Slice):
            for delta in (-1, 1):
                alt = copy.deepcopy(n)
                alt.slice = ast.BinOp(left=copy.deepcopy(n.slice), op=ast.Add(), right=ast.Constant(delta))
                rows.append(describe(n, alt, 'INDEX_SELECTION'))
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            name = n.func.id
            if name == 'range' and 1 <= len(n.args) <= 3:
                stop = 0 if len(n.args) == 1 else 1
                for delta in (-1, 1):
                    alt = copy.deepcopy(n)
                    alt.args[stop] = ast.BinOp(left=alt.args[stop], op=ast.Add(), right=ast.Constant(delta))
                    rows.append(describe(n, alt, 'LOOP_CARDINALITY'))
            elif name in ('sum', 'len') and len(n.args) == 1 and not n.keywords:
                alt = copy.deepcopy(n)
                arg = alt.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'set' and len(arg.args) == 1 and not arg.keywords:
                    alt.args[0] = arg.args[0]
                else:
                    alt.args[0] = ast.Call(func=ast.Name(id='set', ctx=ast.Load()), args=[arg], keywords=[])
                rows.append(describe(n, alt, 'MULTIPLICITY'))
            elif name in ('min', 'max'):
                alt = copy.deepcopy(n); alt.func.id = 'max' if name == 'min' else 'min'
                rows.append(describe(n, alt, 'CALL'))
            elif name == 'abs' and len(n.args) == 1:
                rows.append(describe(n, copy.deepcopy(n.args[0]), 'VALUE'))
    # Round-robin across mechanisms before capping; do not let early operators starve later facets.
    grouped = {name: [r for r in rows if r['family'] == name] for name in FAMILIES}
    out = []
    while any(grouped.values()) and len(out) < cap:
        for group in grouped.values():
            if group and len(out) < cap:
                out.append(group.pop(0))
    return out, ([f'catalog_cap:{len(rows)}->{cap}'] if len(rows) > cap else [])


def replacement(hypothesis):
    mode = 'exec' if hypothesis['node_kind'] == 'AugAssign' else 'eval'
    parsed = ast.parse(hypothesis['after'], mode=mode)
    return parsed.body[0] if mode == 'exec' else parsed.body


def patch_tree(source, hypothesis):
    tree = ast.parse(source)
    count = 0
    class Patch(ast.NodeTransformer):
        def visit(self, node):
            nonlocal count
            if hasattr(node, 'end_lineno') and span(node) == hypothesis['span'] and type(node).__name__ == hypothesis['node_kind']:
                if ast.unparse(node) != hypothesis['before']:
                    raise ValueError('source_binding_mismatch')
                count += 1
                return ast.copy_location(replacement(hypothesis), node)
            return super().visit(node)
    tree = Patch().visit(tree)
    if count != 1:
        raise ValueError(f'expected_exactly_one_target:{count}')
    return ast.fix_missing_locations(tree)


def import_proposals(source, entry, proposals, cap=48, spec=None):
    """Validate binding, not the truth of a writer's semantic interpretation."""
    tree = ast.parse(source)
    from .bindings import resolve
    fn, _ = resolve(tree, entry)
    wrapper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == entry)
    spec = spec if spec is not None else ast.get_docstring(wrapper, clean=False) or ''
    nodes = {tuple(span(n)): n for n in ast.walk(fn) if hasattr(n, 'end_lineno') and isinstance(n, (ast.expr, ast.AugAssign))}
    out = []
    if len(proposals) > cap:
        raise ValueError('proposal_cap')
    for p in proposals:
        if set(p) != {'span', 'before', 'after', 'family', 'rationale', 'spec_quote', 'required_relation', 'observed_relation', 'trigger_reason'}:
            raise ValueError('proposal_fields')
        if p['family'] not in FAMILIES or p['family'] == 'MISSING_CASE':
            raise ValueError('proposal_family')
        n = nodes.get(tuple(p['span']))
        if n is None or p['before'] != ast.unparse(n):
            raise ValueError('proposal_source_binding')
        if not p['spec_quote'] or p['spec_quote'] not in spec:
            raise ValueError('proposal_quote_not_in_docstring')
        if not isinstance(p['rationale'], str) or not 1 <= len(p['rationale']) <= 1600:
            raise ValueError('proposal_rationale')
        for field in ('required_relation', 'observed_relation', 'trigger_reason'):
            if not isinstance(p[field], str) or not 1 <= len(p[field]) <= 1600:
                raise ValueError('proposal_claim:' + field)
        alt = ast.parse(p['after'], mode='exec').body if isinstance(n, ast.AugAssign) else ast.parse(p['after'], mode='eval').body
        if isinstance(alt, list):
            if len(alt) != 1 or not isinstance(alt[0], (ast.Assign, ast.AugAssign)):
                raise ValueError('proposal_statement')
            alt = alt[0]
        if ast.dump(n) == ast.dump(alt):
            raise ValueError('proposal_no_change')
        validate_replacement(n, alt)
        h = describe(n, alt, p['family'], origin='external_proposal', rationale=p['rationale'], spec_quote=p['spec_quote'],
                     required_relation=p['required_relation'], observed_relation=p['observed_relation'], trigger_reason=p['trigger_reason'])
        patch_tree(source, h)
        out.append(h)
    return out
