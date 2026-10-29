"""Bound OBS measurements; neither contract truth nor a bug verdict."""
import ast
import operator
from decimal import Decimal, InvalidOperation

FAMILIES = {'py.text-normalization-contract':'normalization',
            'py.literal-classification-domain':'membership',
            'py.lexicographic-numeric-order':'ordering'}
PREFIX = '__vr8_probe_'
OPS = {'Lt':operator.lt, 'LtE':operator.le, 'Gt':operator.gt, 'GtE':operator.ge}


def signature(node):
    return ast.dump(node,include_attributes=False)


def location(node):
    return [node.lineno,node.col_offset,node.end_lineno,node.end_col_offset]


def bind(task,fact):
    family = FAMILIES.get(fact.get('card_id'))
    result = dict(family=family,status='unsupported',requirement_status='unknown')
    if family is None:
        return dict(result,reason='outside_registered_families')
    tree = ast.parse(task['put'])
    if any(isinstance(n,ast.Name) and n.id.startswith(PREFIX) or isinstance(n,ast.arg) and n.arg.startswith(PREFIX) for n in ast.walk(tree)):
        return dict(result,reason='probe_name_collision')
    evidence = fact.get('retrieval_evidence',{})
    try:
        wanted = signature(ast.parse(evidence['expression'],mode='eval').body)
    except (KeyError,SyntaxError):
        return dict(result,reason='non_expression_evidence')
    matches = [n for n in ast.walk(tree) if isinstance(n,ast.expr)
               and evidence['line'] <= n.lineno <= evidence.get('end_line',evidence['line'])
               and signature(n)==wanted]
    if len(matches)!=1:
        return dict(result,reason='ambiguous_or_missing_expression')
    node = matches[0]
    fn = next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==task['entry']),None)
    spec = ast.get_docstring(fn) or '' if fn else ''
    result.update(site=location(node),expression=ast.unparse(node),source_signature=wanted)
    if family=='normalization':
        if not (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
                and node.func.attr in ('lower','upper','casefold','strip','lstrip','rstrip','replace')
                and not node.keywords and not any(isinstance(a,ast.Starred) for a in node.args)):
            return dict(result,reason='unsupported_normalization_form')
        result.update(operation=node.func.attr,predicate='exact string receiver differs from the result of this normalization call')
    elif family=='membership':
        if not (isinstance(node,ast.Compare) and len(node.ops)==1 and isinstance(node.ops[0],(ast.In,ast.NotIn))):
            return dict(result,reason='unsupported_membership_form')
        if 'vowel' not in spec.lower():
            return dict(result,reason='no_registered_public_class_cue')
        # This is an explicit class hypothesis, not a verified natural-language parser.
        upper = 'uppercase vowel' in spec.lower() or 'upper case vowel' in spec.lower()
        lower = 'lowercase vowel' in spec.lower() or 'lower case vowel' in spec.lower()
        domain = 'AEIOU' if upper and not lower else 'aeiou' if lower and not upper else 'aeiouAEIOU'
        result.update(expected_members=domain,negated=isinstance(node.ops[0],ast.NotIn),
                      requirement_evidence=next(line.strip() for line in spec.splitlines() if 'vowel' in line.lower()),
                      requirement_status='public_lexical_cue_unverified',
                      predicate='membership result differs from the registered ASCII-vowel class hypothesis at this exact lookup')
    else:
        if not (isinstance(node,ast.Compare) and len(node.ops)==1 and type(node.ops[0]).__name__ in OPS):
            return dict(result,reason='unsupported_ordering_form')
        result['operator'] = type(node.ops[0]).__name__
        if any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='str' for n in ast.walk(node)):
            result.update(alternative='numeric',predicate='the string comparison disagrees with finite decimal-number comparison of its operands')
        elif isinstance(node.left,ast.Name) and isinstance(node.comparators[0],ast.Name) and fn:
            tables=[]
            for assign in ast.walk(fn):
                if not (isinstance(assign,ast.Assign) and len(assign.targets)==1 and isinstance(assign.targets[0],ast.Name)):
                    continue
                try: value=ast.literal_eval(assign.value)
                except (ValueError,TypeError,SyntaxError): continue
                if not (type(value) in (list,tuple) and len(value)>1 and all(type(x) is str for x in value) and len(value)==len(set(value))): continue
                name=assign.targets[0].id
                positions={n.args[0].id for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                           and n.func.attr=='index' and isinstance(n.func.value,ast.Name) and n.func.value.id==name
                           and len(n.args)==1 and isinstance(n.args[0],ast.Name)}
                if {node.left.id,node.comparators[0].id} <= positions: tables.append((name,value,assign.lineno))
            if len(tables)!=1:
                return dict(result,reason='no_unique_rank_table')
            name,value,line=tables[0]
            result.update(alternative='literal_rank',rank_values=value,rank_name=name,rank_line=line,
                          predicate='the string comparison disagrees with the unique literal rank-table ordering of its operands')
        else:
            return dict(result,reason='no_registered_alternative_order')
    return dict(result,status='supported')


class Probe:
    def __init__(self,source,entry,bindings):
        self.bindings=bindings
        self.events={}
        by_site={tuple(b['site']):(str(i),b) for i,b in enumerate(bindings) if b['status']=='supported'}
        if len(by_site)!=sum(b['status']=='supported' for b in bindings):
            raise ValueError('duplicate_probe_site')
        owner=self
        seen=set()
        class Rewrite(ast.NodeTransformer):
            def visit(self,node):
                match=by_site.get(tuple(location(node))) if isinstance(node,ast.expr) else None
                if match:
                    key,b=match
                    seen.add(tuple(b['site']))
                    if signature(node)!=b['source_signature']:
                        raise ValueError('semantic_binding_source_changed')
                    # Visit nested operands but evaluate each original operand/method only once.
                    node=self.generic_visit(node)
                    if b['family']=='normalization':
                        args=[ast.Constant(key),node.func,*node.args]
                        name=PREFIX+'normalization'
                    else:
                        args=[ast.Constant(key),node.left,node.comparators[0]]
                        name=PREFIX+b['family']
                    return ast.copy_location(ast.Call(func=ast.Name(id=name,ctx=ast.Load()),args=args,keywords=[]),node)
                return super().visit(node)
        tree=Rewrite().visit(ast.parse(source));ast.fix_missing_locations(tree)
        if seen!=set(by_site):
            raise ValueError('semantic_binding_source_changed')
        self.code=compile(tree,'<vr8-semantic>','exec');self.entry=entry
        self.hooks={PREFIX+name:getattr(owner,name) for name in ('normalization','membership','ordering')}

    def record(self,key,hit,detail):
        event=self.events.setdefault(key,dict(observations=0,hits=0,unknown=0,examples=[]))
        event['observations']+=1;event['hits']+=hit is True;event['unknown']+=hit is None
        if len(event['examples'])<3:
            event['examples'].append(dict(hit=hit,detail=detail))

    def normalization(self,key,method,*args):
        result=method(*args)
        receiver=getattr(method,'__self__',None)
        known=type(receiver) is str and type(result) is str
        self.record(key,receiver!=result if known else None,
                    dict(receiver=repr(receiver)[:160] if known else '<unsupported>',result=repr(result)[:160] if known else '<unsupported>'))
        return result

    def membership(self,key,value,container):
        b=self.bindings[int(key)]
        result=value not in container if b['negated'] else value in container
        known=(type(value) is str and len(value)==1 and type(container) in (str,list,tuple,set,frozenset)
               and all(type(v) is str and len(v)==1 for v in container))
        alternative=(value not in b['expected_members'] if b['negated'] else value in b['expected_members']) if known else None
        self.record(key,result!=alternative if known else None,dict(value=repr(value)[:160] if known else '<unsupported>',observed=result,alternative=alternative))
        return result

    def ordering(self,key,left,right):
        b=self.bindings[int(key)];op=OPS[b['operator']];result=op(left,right)
        hit=None;alternative=None
        if type(left) is str and type(right) is str:
            try:
                if b['alternative']=='numeric':
                    a,z=Decimal(left.replace(',','.')),Decimal(right.replace(',','.'))
                    if not(a.is_finite() and z.is_finite()): raise ValueError('nonfinite')
                else:
                    a,z=b['rank_values'].index(left),b['rank_values'].index(right)
                alternative=op(a,z);hit=result!=alternative
            except (ValueError,InvalidOperation):
                pass
        self.record(key,hit,dict(left=repr(left)[:160] if type(left) is str else '<unsupported>',right=repr(right)[:160] if type(right) is str else '<unsupported>',observed=result if type(result) is bool else '<unsupported>',alternative=alternative))
        return result

    def run(self,args,kwargs=None):
        from .tracer import call,load_module
        self.events={}
        # Fresh namespace per input: this diagnostic supports isolated function calls only.
        fn=load_module(self.code,self.hooks)[self.entry]
        outcome=call(fn,(args,kwargs or {}),T=1,filename='<vr8-semantic>')
        states=[]
        for i,b in enumerate(self.bindings):
            event=self.events.get(str(i))
            state=True if event and event['hits'] else None if not event or event['unknown'] else False
            states.append(dict(state=state,status='unsupported' if b['status']!='supported' else 'unknown' if state is None else 'observed',
                               evidence=event,requirement_status=b['requirement_status']))
        return states,outcome
