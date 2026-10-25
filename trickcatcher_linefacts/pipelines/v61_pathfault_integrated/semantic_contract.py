"""Public evidence contracts with stable AST IDs; semantic truth stays qualified."""
import ast
import hashlib
import json
from .binding_graph import build
from .predicates import validate


def writer_packet(request):
    graph=build(request['source'])
    tree=ast.parse(request['source']);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==request['entry'])
    expressions={tuple([n.lineno,n.col_offset,n.end_lineno,n.end_col_offset])for n in ast.walk(tree)if isinstance(n,ast.expr)}
    eligible=[n for n in graph['nodes']if tuple(n['span'])in expressions and n['kind']in ('Compare','BinOp','BoolOp','Call','Subscript','IfExp')]
    sites=[dict(n,code=n['code'][:180])for n in eligible[:32]]
    return {'instruction':'Compare required spec behavior with observed code. Return {hypotheses:[{site_id,family,required_relation,observed_relation,spec_quote,trigger,event_predicate,priority,alternative}]}. trigger is a data predicate AST using input/len/literal/add/sub/mod/eq/lt/le/and/or/has_duplicate/all_distinct. event_predicate uses the same grammar and may also use local(name) values observed at the exact target frame; use literal true when no local condition is justified and retain uncertainty. alternative is a pure expression string or null. Quote is evidence, not proof. At most three hypotheses; abstain when uncertain.',
            'spec':request.get('spec',ast.get_docstring(fn)or ''),'source':request['source'],'entry':request['entry'],
            'public_examples':request['public_examples'],'sites':sites,'site_cap':32,'omitted_sites':max(0,len(eligible)-32),
            'uncertainty':'unverified hypotheses; observed PUT behavior cannot override spec requirements'}


def admit(request,proposals):
    graph=build(request['source']);nodes={n['id']:n for n in graph['nodes']}
    tree=ast.parse(request['source']);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==request['entry'])
    arity=len(fn.args.posonlyargs+fn.args.args)
    accepted=[];rejected=[]
    if not isinstance(proposals,list):return [],[{'reason':'proposal_list'}]
    for index,p in enumerate(proposals[:3]):
        try:
            required={'site_id','family','required_relation','observed_relation','spec_quote','trigger','priority','alternative'}
            if not isinstance(p,dict) or not required<=set(p) or set(p)-required-{'event_predicate'}:raise ValueError('hypothesis_fields')
            site=nodes.get(p['site_id'])
            if not site:raise ValueError('unknown_site_id')
            if site['kind']not in ('Compare','BinOp','BoolOp','Call','Subscript','IfExp'):raise ValueError('nonexpression_hypothesis_site')
            if not p['spec_quote'] or p['spec_quote'] not in request.get('spec',ast.get_docstring(fn) or ''):raise ValueError('spec_quote_binding')
            if any(not isinstance(p[k],str) or not 1<=len(p[k])<=1600 for k in ('family','required_relation','observed_relation','spec_quote')):raise ValueError('hypothesis_claim')
            if type(p['priority'])is not int or not 0<=p['priority']<=3:raise ValueError('hypothesis_priority')
            validate(p['trigger'],arity)
            event=p.get('event_predicate',{'op':'literal','value':True});validate(event,arity,allow_local=True)
            if p['alternative']is not None:
                from .hypotheses import validate_replacement
                target=next(n for n in ast.walk(tree) if isinstance(n,ast.expr) and [n.lineno,n.col_offset,n.end_lineno,n.end_col_offset]==site['span'])
                alt=ast.parse(p['alternative'],mode='eval').body
                rounding=(isinstance(target,ast.Call)and isinstance(alt,ast.Call)and isinstance(target.func,ast.Attribute)
                          and isinstance(alt.func,ast.Attribute)and isinstance(target.func.value,ast.Name)
                          and isinstance(alt.func.value,ast.Name)and target.func.value.id==alt.func.value.id=='math'
                          and target.func.attr in ('ceil','floor')and alt.func.attr in ('ceil','floor')
                          and not target.keywords and not alt.keywords and len(target.args)==len(alt.args)==1
                          and ast.dump(target.args[0])==ast.dump(alt.args[0])
                          and isinstance(alt.args[0],ast.BinOp)and isinstance(alt.args[0].op,ast.Div)
                          and isinstance(alt.args[0].left,ast.Name)and isinstance(alt.args[0].right,ast.Constant)
                          and alt.args[0].right.value==2)
                if not rounding:validate_replacement(target,alt)
            accepted.append(dict(p,event_predicate=event,site=site,source_sha256=graph['source_sha256'],
                                 semantic_status='unverified',source_binding='verified',spec_quote_status='present',
                                 id=hashlib.sha256(json.dumps({'proposal':dict(p,event_predicate=event),'source':graph['source_sha256']},sort_keys=True).encode()).hexdigest()[:16]))
        except (ValueError,KeyError,TypeError,SyntaxError,StopIteration) as exc:rejected.append({'index':index,'reason':type(exc).__name__+':'+str(exc)[:120]})
    if len(proposals)>3:rejected.append({'reason':'proposal_cap','omitted':len(proposals)-3})
    accepted.sort(key=lambda h:(-h['priority'],h['site']['span'],h['id']))
    return accepted,rejected
