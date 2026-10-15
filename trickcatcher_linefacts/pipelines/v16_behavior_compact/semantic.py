"""Small JSON expression DSL: no generated Python predicates or arbitrary eval."""
import json
import operator
import re

FAMILIES={'ELEMENTWISE','MULTIPLICITY','ORDERING','BOUNDARY','EMPTY_AGGREGATION','INVARIANCE','CONTAINMENT'}
ARITIES={'arg':0,'result':0,'const':0,'len':1,'abs':1,'sum':1,'min':1,'max':1,'distinct':1,
         'sorted':1,'count_negative':1,'count_positive':1,'count_zero':1,'not':1,
         'eq':2,'ne':2,'lt':2,'le':2,'gt':2,'ge':2,'add':2,'sub':2,'mul':2,
         'subset':2,'contains':2,'and':2,'or':2,'at':2}

def validate(node,arity,allow_result=True,depth=0):
    if depth>12 or not isinstance(node,dict):raise ValueError('DSL depth/type')
    op=node.get('op');xs=node.get('args',[])
    if op not in ARITIES or type(xs) is not list or len(xs)!=ARITIES[op]:raise ValueError('DSL operator/arity')
    keys={'op','args'}|({'index'} if op=='arg' else {'value'} if op=='const' else set())
    if set(node)-keys:raise ValueError('DSL unknown field')
    if op=='arg' and (type(node.get('index')) is not int or not 0<=node['index']<arity):raise ValueError('DSL arg index')
    if op=='result' and not allow_result:raise ValueError('result in input predicate')
    if op=='const' and ('value' not in node or len(json.dumps(node['value']))>1000):raise ValueError('DSL constant')
    for x in xs:validate(x,arity,allow_result,depth+1)
    return node

def uses(node,op):return node['op']==op or any(uses(n,op) for n in node.get('args',[]))

def evaluate(node,args,result=None):
    op=node['op']
    if op=='arg':return args[node['index']]
    if op=='const':return node['value']
    if op=='result':return result
    # Preserve Boolean short-circuit semantics and reject non-Boolean predicates.
    if op in ('and','or'):
        a=evaluate(node['args'][0],args,result)
        if type(a) is not bool:raise TypeError('Boolean required')
        if op=='and' and not a:return False
        if op=='or' and a:return True
        b=evaluate(node['args'][1],args,result)
        if type(b) is not bool:raise TypeError('Boolean required')
        return b
    xs=[evaluate(n,args,result) for n in node.get('args',[])]
    binary={'eq':operator.eq,'ne':operator.ne,'lt':operator.lt,'le':operator.le,'gt':operator.gt,
            'ge':operator.ge,'add':operator.add,'sub':operator.sub,'mul':operator.mul,'at':operator.getitem,
            'subset':lambda a,b:set(a)<=set(b),'contains':lambda a,b:b in a}
    unary={'len':len,'abs':abs,'sum':sum,'min':min,'max':max,'distinct':lambda a:len(set(a)),
           'sorted':sorted,'count_negative':lambda a:sum(x<0 for x in a),
           'count_positive':lambda a:sum(x>0 for x in a),'count_zero':lambda a:sum(x==0 for x in a),
           'not':lambda a: not a if type(a) is bool else (_ for _ in ()).throw(TypeError('Boolean required'))}
    return binary[op](*xs) if op in binary else unary[op](*xs)

def truth(node,args,result=None):
    try:
        value=evaluate(node,args,result)
        return value if type(value) is bool else None
    except (TypeError,ValueError,IndexError,KeyError,OverflowError,ZeroDivisionError):return None

def parse(text):
    text=re.sub(r'^```(?:json)?\s*\n|\n```\s*$','',text.strip())
    if len(text)>80000:raise ValueError('response too large')
    return json.loads(text)

def obligations(raw,ir,cap=6):
    data=parse(raw);out=[];rejected=[];arity=len(ir['parameters']);doc=ir['docstring']
    for i,row in enumerate(data.get('obligations',[])[:cap]):
        try:
            quote=row['quote'];start=doc.find(quote)
            if not isinstance(quote,str) or len(quote.strip())<12 or start<0:raise ValueError('quote not verbatim docstring')
            d=validate(row['domain'],arity,False);o=validate(row['relation'],arity)
            if not uses(o,'result') or not uses(o,'arg'):raise ValueError('relation must connect input and result')
            out.append(dict(id=f'R{i}',quote=quote,span=[start,start+len(quote)],domain=d,relation=o,
                            entailment='unverified_candidate',description=row.get('description','')))
        except (ValueError,TypeError,KeyError) as exc:rejected.append(dict(index=i,reason=str(exc)))
    return out,rejected

def cards(raw,ir,obs,mutants,cap=6):
    data=parse(raw);by_r={o['id']:o for o in obs};blocks={b['id'] for b in ir['blocks']};ms={m['id']:m for m in mutants}
    out=[];rejected=[]
    fields=('code_claim','required_condition','path_guarantees','unresolved_obligation','predicted_effect')
    for i,row in enumerate(data.get('concepts',[])[:cap]):
        try:
            if row['family'] not in FAMILIES:raise ValueError('concept family')
            obligation=by_r[row['obligation_id']];anchors=row['block_ids'];mut=ms[row['mutant_id']]
            if not anchors or not set(anchors)<=blocks:raise ValueError('invalid block binding')
            if mut['target'] not in anchors and not any(mut['target'].startswith(b.split('_')[0]+'_') for b in anchors):
                raise ValueError('mutation must be on bound block or its expression line')
            disc=validate(row['discriminator'],len(ir['parameters']),False)
            if not uses(disc,'arg'):raise ValueError('constant discriminator')
            reason=row['reasoning']
            if any(type(reason.get(f)) is not str or len(reason[f].strip())<8 for f in fields):raise ValueError('incomplete reasoning record')
            out.append(dict(id=f'C{i}',family=row['family'],obligation=obligation,block_ids=anchors,
                            mutant_id=mut['id'],alternative=dict(operator=mut['operator'],target=mut['target'],origin='implementation'),
                            discriminator=disc,reasoning={f:reason[f] for f in fields},semantic_status='candidate_not_proof'))
        except (ValueError,TypeError,KeyError) as exc:rejected.append(dict(index=i,reason=str(exc)))
    return out,rejected

def messages(stage,task,prepared,obs=None):
    ir=prepared['ir'];grammar='JSON expression node {"op":name,"args":[nodes]}; leaves {"op":"arg","index":0}, {"op":"result"}, {"op":"const","value":0}. Operators/arity: '+json.dumps(ARITIES)
    if stage=='spec':
        content=('Extract at most 6 atomic candidate obligations from this DOCSTRING ONLY. Return JSON '
                 '{"obligations":[{"quote":"verbatim contiguous docstring text","description":"meaning",'
                 '"domain":DSL_boolean_input_precondition,"relation":DSL_boolean_input_output_relation}]}. '
                 'Relation must reference arg and result. Do not invent requirements. Unsupported obligations can be omitted. '
                 'A true domain is {"op":"const","value":true}. For output equal to input length use '
                 '{"op":"eq","args":[{"op":"result"},{"op":"len","args":[{"op":"arg","index":0}]}]}.\n'+
                 grammar+'\nParameters: '+json.dumps(ir['parameters'])+'\nDOCSTRING:\n'+ir['docstring'])
    else:
        from .behavior import pseudocode
        mutants=[{k:m[k] for k in ('id','target','operator','origin')} for m in prepared['mutants']]
        content=('Bind at most 6 concepts to the provided obligations and implementation. Return JSON '
                 '{"concepts":[{"family":"one of '+','.join(sorted(FAMILIES))+'","obligation_id":"R0",'
                 '"block_ids":["actual block ID"],"mutant_id":"actual mutant ID",'
                 '"discriminator":DSL_boolean_input_predicate,"reasoning":{'
                 '"code_claim":"current operation and state","required_condition":"what must hold",'
                 '"path_guarantees":"what current guards guarantee","unresolved_obligation":"specific missing implication",'
                 '"predicted_effect":"specific output or exception"}}]}. '
                 'Mutation is an alternative implementation, not the spec. The discriminator should isolate its semantic difference. '
                 'No concrete tests or unverifiable correctness claims.\n'+grammar+'\nOBLIGATIONS:\n'+json.dumps(obs)+
                 '\nPUT:\n'+task['put']+'\nBEHAVIOR:\n'+pseudocode(ir)+'\nMUTATIONS:\n'+json.dumps(mutants))
    return [dict(role='system',content='Return one JSON object only. Do not write Python functions.'),dict(role='user',content=content)]
