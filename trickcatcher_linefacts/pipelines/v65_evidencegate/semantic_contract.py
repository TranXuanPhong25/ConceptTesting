"""Public evidence contracts with stable AST IDs; semantic truth stays qualified."""
import ast
import hashlib
import json
from .binding_graph import build
from .predicates import validate, evaluate


def constant_predicate(node):
    """Conservative constant folding; unknown is not unsatisfiable."""
    if node['op'] in ('input', 'local'):
        return None
    children = [v for v in node.values() if isinstance(v, dict)]
    children += [v for values in node.values() if isinstance(values, list) for v in values]
    if node['op'] in ('and', 'or'):
        values = [constant_predicate(child) for child in children]
        if node['op'] == 'and' and False in values:
            return False
        if node['op'] == 'or' and True in values:
            return True
        if all(value is not None for value in values):
            return all(values) if node['op'] == 'and' else any(values)
    if node['op'] == 'not':
        value = constant_predicate(node['value'])
        if value is not None:
            return not value
    def dynamic(value):
        if isinstance(value, dict):
            return value.get('op') in ('input', 'local') or any(dynamic(v) for v in value.values())
        if isinstance(value, list):
            return any(dynamic(v) for v in value)
        return False
    if dynamic(node):
        return None
    try:
        value = evaluate(node, ())
    except (ValueError, TypeError, IndexError, ZeroDivisionError) as exc:
        raise ValueError('invalid_constant_predicate') from exc
    if type(value) is not bool:
        raise ValueError('nonboolean_constant_predicate')
    return value


def specification(request):
    tree=ast.parse(request['source'])
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==request['entry'])
    return request.get('spec',ast.get_docstring(fn)or '')


def spec_clauses(request):
    spec=specification(request)
    binding=hashlib.sha256((request['source']+'\0'+spec).encode()).hexdigest()[:12]
    # Exact contiguous excerpts; IDs bind both source and specification.
    rows=[]
    for line in spec.splitlines():
        for start in range(0,len(line),1200):
            text=line[start:start+1200].strip()
            if text:rows.append({'id':f'{binding}:{len(rows)}','text':text})
    return rows


def writer_packet(request):
    graph=build(request['source'])
    tree=ast.parse(request['source']);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==request['entry'])
    expressions={tuple([n.lineno,n.col_offset,n.end_lineno,n.end_col_offset])for n in ast.walk(tree)if isinstance(n,ast.expr)}
    eligible=[n for n in graph['nodes']if tuple(n['span'])in expressions and n['kind']in ('Compare','BinOp','BoolOp','Call','Subscript','IfExp')]
    unsupported_sites=sum(not n['scope'] for n in eligible)
    eligible=[n for n in eligible if n['scope']]
    sites=[{k:n[k]for k in ('id','kind','code','scope')}for n in eligible[:32]]
    grammar={
        'literal':{'op':'literal','value':'boolean, integer, or string'},
        'input':{'op':'input','arg':'zero-based positional argument INTEGER'},
        'local':{'op':'local','name':'local variable name; event_predicate ONLY'},
        'unary':{'op':'len | not | has_duplicate | all_distinct','value':'predicate node'},
        'binary':{'op':'add | sub | mod | eq | lt | le','left':'predicate node','right':'predicate node'},
        'boolean':{'op':'and | or','items':['predicate node','predicate node']},
    }
    return {'instruction':'Identify up to three plausible SPEC-versus-CODE mismatches, not merely code descriptions. Return a JSON object with a hypotheses array. Copy site_id and spec_clause_id from the supplied tables. The clause is evidence location, not proof of your interpretation. required_relation describes what spec requires; observed_relation describes how this exact code site may violate it; these must state different relations. alternative_rationale must explain why the replacement follows the selected spec clause and what change it predicts at this site under the trigger. An output difference alone is NOT evidence of a correct replacement. Do not invent a replacement just to change the output. It must preserve all supplied public examples. priority MUST be an integer 0..3, with 3 highest; NEVER high/medium/low. trigger and event_predicate MUST be JSON objects following predicate_grammar, NEVER strings or Python expressions. Trigger must evaluate to Boolean on positional inputs. Never use literal false for an unknown event; abstain instead. Use {"op":"literal","value":true} for an unconditional event. alternative is a PURE Python replacement EXPRESSION for this exact site, or JSON null; the string "None" is NOT abstention and is unsupported. Do not write a whole function. Choose concise hypotheses; return {"hypotheses":[]} if no mismatch is justified.',
            'output_fields':{'site_id':'exact supplied ID','spec_clause_id':'exact supplied clause ID','family':'short fault-type description',
                             'required_relation':'spec requirement','observed_relation':'potential code mismatch','priority':'INTEGER 0..3',
                             'trigger':'predicate object','event_predicate':'predicate object','alternative':'pure expression string or null',
                             'alternative_rationale':'20..1600 characters explaining spec-to-replacement and predicted local change; empty only for JSON null'},
            'predicate_grammar':grammar,
            'predicate_examples':[
                {'op':'eq','left':{'op':'len','value':{'op':'input','arg':0}},'right':{'op':'literal','value':3}},
                {'op':'and','items':[{'op':'lt','left':{'op':'literal','value':0},'right':{'op':'input','arg':0}},
                                     {'op':'eq','left':{'op':'mod','left':{'op':'input','arg':0},'right':{'op':'literal','value':2}},'right':{'op':'literal','value':1}}]}],
            'arguments':[{'arg':i,'name':a.arg}for i,a in enumerate(fn.args.posonlyargs+fn.args.args)],
            'spec_clauses':spec_clauses(request),'source':request['source'],'entry':request['entry'],
            'public_examples':request['public_examples'],'sites':sites,'site_cap':32,'omitted_sites':max(0,len(eligible)-32),
            'unsupported_module_sites':unsupported_sites,
            'uncertainty':'unverified hypotheses; observed PUT behavior cannot override spec requirements'}


def admit(request,proposals):
    graph=build(request['source']);nodes={n['id']:n for n in graph['nodes']}
    tree=ast.parse(request['source']);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==request['entry'])
    arity=len(fn.args.posonlyargs+fn.args.args)
    accepted=[];rejected=[]
    if not isinstance(proposals,list):return [],[{'reason':'proposal_list'}]
    for index,p in enumerate(proposals[:3]):
        try:
            if isinstance(p,dict)and 'spec_clause_id'in p:
                clauses={row['id']:row['text']for row in spec_clauses(request)}
                if 'spec_quote'in p or p['spec_clause_id']not in clauses:raise ValueError('spec_clause_binding')
                p=dict(p);p['spec_quote']=clauses[p.pop('spec_clause_id')]
            required={'site_id','family','required_relation','observed_relation','spec_quote','trigger','priority','alternative'}
            if not isinstance(p,dict) or not required<=set(p) or set(p)-required-{'event_predicate','alternative_rationale'}:raise ValueError('hypothesis_fields')
            site=nodes.get(p['site_id'])
            if not site:raise ValueError('unknown_site_id')
            if site['kind']not in ('Compare','BinOp','BoolOp','Call','Subscript','IfExp'):raise ValueError('nonexpression_hypothesis_site')
            if not site['scope']:raise ValueError('unsupported_module_scope')
            if not p['spec_quote'] or p['spec_quote'] not in request.get('spec',ast.get_docstring(fn) or ''):raise ValueError('spec_quote_binding')
            if any(not isinstance(p[k],str) or not 1<=len(p[k])<=1600 for k in ('family','required_relation','observed_relation','spec_quote')):raise ValueError('hypothesis_claim')
            normalize=lambda text:' '.join(text.casefold().split())
            if normalize(p['required_relation'])==normalize(p['observed_relation']):raise ValueError('no_claimed_mismatch')
            if type(p['priority'])is not int or not 0<=p['priority']<=3:raise ValueError('hypothesis_priority')
            validate(p['trigger'],arity)
            event=p.get('event_predicate',{'op':'literal','value':True});validate(event,arity,allow_local=True)
            for label,predicate in (('trigger',p['trigger']),('event',event)):
                if constant_predicate(predicate) is False:raise ValueError('constant_false_'+label)
            if p['alternative']is not None:
                reason=p.get('alternative_rationale')
                if not isinstance(reason,str) or not 20<=len(reason.strip())<=1600:raise ValueError('alternative_rationale_required')
                from .hypotheses import validate_replacement
                target=next(n for n in ast.walk(tree) if isinstance(n,ast.expr) and [n.lineno,n.col_offset,n.end_lineno,n.end_col_offset]==site['span'])
                alt=ast.parse(p['alternative'],mode='eval').body
                if isinstance(alt,ast.Constant) and alt.value is None:raise ValueError('none_expression_not_abstention')
                if ast.dump(target)==ast.dump(alt):raise ValueError('no_op_alternative')
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
