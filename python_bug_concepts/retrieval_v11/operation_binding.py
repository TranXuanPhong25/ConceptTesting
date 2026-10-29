"""Conservative operation roles for nominated concept/site pairs; no code execution.

These rules establish an operation to inspect, never a target bug or output oracle.
Unimplemented roles remain unknown rather than inheriting AST-type compatibility.
"""
from __future__ import annotations

import ast
import re

VERSION = 'operation-roles-vr11.1'


def value_node(node):
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Return, ast.Expr)):
        return node.value if node.value is not None else node
    return node


def callee(node):
    if not isinstance(node, ast.Call):
        return ''
    return node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''


def builtin(a, node, names):
    if not isinstance(node, ast.Call):
        return False
    qualified=a.qname(node.func)
    if qualified is not None and qualified.startswith('builtins.'):
        return qualified.removeprefix('builtins.') in names
    if not isinstance(node.func,ast.Name):
        # An unresolved callable object may be an alias. Do not assert that its
        # operation is absent, and never promote it from AST shape alone.
        return None
    if qualified is not None:
        return None
    if node.func.id not in names:
        return None
    owner = a.owner(node)
    if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = owner.args
        if node.func.id in {p.arg for p in [*args.posonlyargs,*args.args,*args.kwonlyargs]}:
            return None
    if a.stable_definition(node,node.func.id) is not None:
        return None
    return True


def local_generator(function):
    if not isinstance(function,(ast.FunctionDef,ast.AsyncFunctionDef)):
        return False
    pending=list(function.body)
    while pending:
        node=pending.pop()
        if isinstance(node,(ast.Yield,ast.YieldFrom)):
            return True
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda,ast.ClassDef)):
            continue
        pending.extend(ast.iter_child_nodes(node))
    return False


def in_finally(a, node):
    child, parent = node, a.parent.get(node)
    while parent is not None and not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if isinstance(parent, (ast.Try, ast.TryStar)) and child in parent.finalbody:
            return True
        child, parent = parent, a.parent.get(parent)
    return False


def mutable_default(function):
    if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    defaults = [*function.args.defaults, *function.args.kw_defaults]
    return any(isinstance(x,(ast.List,ast.Dict,ast.Set)) or
               (isinstance(x,ast.Call) and callee(x) in {'list','dict','set'}) for x in defaults if x is not None)


def operation(a, cid, node):
    """Return True/False for an implemented role, None when not implemented."""
    n = value_node(node)
    name = callee(n)
    attr = isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
    membership = isinstance(n,ast.Compare) and any(isinstance(x,(ast.In,ast.NotIn)) for x in n.ops)
    if cid == 'py.mutable-default': return mutable_default(node)
    if cid == 'py.definition-time-call':
        return isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and any(isinstance(x,ast.Call) for x in [*node.args.defaults,*node.args.kw_defaults])
    if cid == 'py.finally-overrides-control-flow':
        return isinstance(node,(ast.Return,ast.Break,ast.Continue)) and in_finally(a,node)
    if cid == 'py.legacy-print-redirection':
        return isinstance(n,ast.BinOp) and isinstance(n.op,ast.RShift) and isinstance(n.left,ast.Name) and n.left.id=='print'
    if cid == 'py.invalid-special-method-return':
        return isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in {'__str__','__repr__','__len__','__bool__','__hash__','__bytes__','__iter__'}
    if cid == 'py.fstring-docstring':
        return isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Module)) and bool(node.body) and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.JoinedStr)
    if cid == 'py.scope-declaration-conflict':
        return isinstance(node,(ast.Global,ast.Nonlocal))
    if cid == 'py.property-missing-return':
        return isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and any(isinstance(x,ast.Name) and x.id=='property' for x in node.decorator_list)
    if cid == 'py.generator-return-is-not-yield':
        return local_generator(node)
    if cid in {'py.set-loses-multiplicity','py.set-order-loss'}:
        return isinstance(n,(ast.Set,ast.SetComp)) or builtin(a,n,{'set','frozenset'})
    if cid == 'py.empty-reduction-domain': return builtin(a,n,{'min','max'})
    if cid == 'py.text-normalization-contract': return attr and name in {'lower','upper','casefold','capitalize','title','swapcase','strip','lstrip','rstrip','replace','translate'}
    if cid == 'py.unicode-text-byte-domain': return attr and name in {'encode','decode'}
    if cid == 'py.ascii-unicode-classification': return attr and name in {'isdigit','isnumeric','isdecimal','isalpha','isalnum','isascii','isspace'}
    if cid == 'py.split-join-separator-loss': return attr and name in {'split','rsplit','splitlines','join'}
    if cid == 'py.numeric-cast-loss': return builtin(a,n,{'int','float','round'})
    if cid == 'py.presence-frequency-confusion': return membership or (attr and name=='count') or builtin(a,n,{'set'})
    if cid == 'py.first-match-vs-optimum':
        if builtin(a,n,{'next'}): return True
        p = a.parent.get(node)
        while p is not None and not isinstance(p,(ast.FunctionDef,ast.AsyncFunctionDef)):
            if isinstance(p,(ast.For,ast.AsyncFor,ast.While)): return isinstance(node,ast.Return)
            p=a.parent.get(p)
        return False
    if cid == 'py.extremum-initial-sentinel': return isinstance(node,(ast.Assign,ast.AnnAssign,ast.Compare))
    if cid in {'py.branch-boundary-contract','py.empty-singleton-shortcut','py.lexicographic-numeric-order','py.quantifier-scope','py.shortcircuit-boolean-result'}:
        return isinstance(n,ast.Compare) or (cid=='py.shortcircuit-boolean-result' and isinstance(n,ast.BoolOp))
    if cid in {'py.membership-wrong-domain','py.empty-membership'}: return membership
    if cid in {'py.index-out-of-bounds','py.negative-index-sentinel','py.invalid-sequence-index-type'}: return isinstance(n,ast.Subscript)
    if cid == 'py.range-exclusive-stop': return builtin(a,n,{'range'})
    if cid == 'py.strip-character-set': return attr and name in {'strip','lstrip','rstrip'}
    if cid == 'py.zip-truncates': return builtin(a,n,{'zip'})
    if cid == 'py.decimal-from-float': return name=='Decimal' and isinstance(n,ast.Call)
    if cid == 'py.mutator-return-none': return attr and name in {'append','extend','insert','remove','reverse','sort','clear','update','add','discard'}
    if cid == 'py.integer-division-precision': return isinstance(n,ast.BinOp) and isinstance(n.op,ast.Div)
    if cid == 'py.signed-modulo-domain': return isinstance(n,ast.BinOp) and isinstance(n.op,ast.Mod)
    if cid == 'py.digit-place-extraction': return isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Mod,ast.FloorDiv))
    if cid == 'py.absolute-difference': return builtin(a,n,{'abs'}) or (isinstance(n,ast.BinOp) and isinstance(n.op,ast.Sub))
    if cid == 'py.fresh-lock-per-operation': return name in {'Lock','RLock'}
    if cid == 'py.numeric-text-width': return builtin(a,n,{'str','int'}) or (attr and name in {'zfill','rjust','format'})
    if cid == 'py.first-occurrence-position': return attr and name in {'index','find','rindex','rfind'}
    if cid == 'py.tie-break-selection': return builtin(a,n,{'min','max','sorted'}) or (attr and name=='sort')
    if cid == 'py.rounding-policy': return builtin(a,n,{'round','int'}) or name in {'ceil','floor','quantize'}
    if cid == 'py.regex-fullmatch-boundary': return attr and name in {'match','search','fullmatch'}
    if cid == 'py.aggregation-scope': return builtin(a,n,{'sum','all','any','min','max'})
    if cid == 'py.fixed-chunk-run': return isinstance(n,ast.Subscript) and isinstance(n.slice,ast.Slice)
    return None


def explicit_benign_contract(cid,spec):
    """Only direct, non-negated requirement clauses authorize exclusion.

    Broad co-occurrence is deliberately insufficient: 'occurrences of each
    distinct value' requires multiplicity, and negated case instructions do not
    authorize normalization. Ambiguous/conflicting clauses stay unknown.
    """
    clauses=[c.strip() for c in re.split(r'[\n.!?;]+',spec.lower()) if c.strip()]
    negation=re.compile(r"\b(?:not|never|without|cannot|mustn't|don't|doesn't|isn't|preserve|retain)\b")
    if cid in {'py.set-loses-multiplicity','py.presence-frequency-confusion'}:
        # Any explicit occurrence/frequency requirement defeats distinct-count
        # authorization, including occurrences *of each distinct value*.
        if re.search(r'\b(?:occurrences?|frequenc(?:y|ies)|repeated|duplicates?)\b',spec):
            return None
        cardinality=re.compile(r'\b(?:(?:number|count)\s+of\s+(?:the\s+)?(?:distinct|unique)\b|count\s+(?:the\s+)?(?:distinct|unique)\b|how\s+many\s+(?:distinct|unique)\b)')
        matches=[c for c in clauses if cardinality.search(c)]
        if matches and not any(negation.search(c) for c in matches):
            return 'excluded_explicit_distinct_contract'
    if cid=='py.text-normalization-contract':
        relevant=[c for c in clauses if re.search(r'\bcase\b|case[- ]sensitive|case[- ]insensitive',c)]
        # Negative/conflicting instructions anywhere in the relevant requirement
        # prevent an exclusion; no claim that we resolved their intended scope.
        if any(negation.search(c) or re.search(r'\bcase[- ]sensitive\b',c) for c in relevant):
            return None
        authorized=re.compile(r'case[- ]insensitive|\bignore\s+(?:letter\s+)?case\b|\bregardless\s+of\s+(?:letter\s+)?case\b')
        directive=re.compile(r'\b(?:compare|comparison|match|matching|search|sort|normalize|normalization|convert|return|ignore|regardless)\b')
        if any(authorized.search(c) and directive.search(c) for c in relevant):
            return 'excluded_explicit_case_contract'
    return None


def verdict(a, cid, node, *, existing=None):
    role = operation(a,cid,node)
    if role is False:
        return {'status':'unbound_operation_mismatch','operation_support':False,'reasons':['Required concept-specific operation is absent at the selected site.']}
    tier = (existing or {}).get('semantic_support',{}).get('tier',0)
    if role is None and (existing is None or tier<2):
        return {'status':'unbound_role_unknown','operation_support':None,'reasons':['No implemented operation role or independently recognized local relation; AST compatibility is insufficient.']}
    spec = a.spec(node).lower()
    n=value_node(node)
    benign=explicit_benign_contract(cid,spec)
    if benign=='excluded_explicit_distinct_contract' or (benign=='excluded_explicit_case_contract' and callee(n) in {'lower','upper','casefold'}):
        return {'status':benign,'operation_support':True,'reasons':['A direct non-negated public requirement authorizes this information loss; ambiguous or conflicting clauses are retained as unknown.']}
    return {'status':'source_supported_conditional_hypothesis' if tier>=2 else 'grounded_test_opportunity_contract_unknown',
            'operation_support':True if role else 'recognized_local_relation',
            'reasons':['Concept-specific source operation is present.' if role else 'Existing source relation retained; missing operation-role implementation remains explicit.',
                       'Public-contract alignment and behavioral failure require independent validation.']}
