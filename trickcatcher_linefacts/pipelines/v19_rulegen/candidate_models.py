"""Finite typed model candidates and a disclosed lexical prior; no task-ID dispatch."""
import itertools
import ast
import json
import random
import re
from . import templates,template_semantic


def kind(values):
    if all(type(x) is str for x in values):return 'text'
    if all(type(x) in (list,tuple) for x in values):
        elements=[v for xs in values for v in xs]
        if elements and all(type(x) is int for x in elements):return 'numbers'
        if elements and all(type(x) is str for x in elements):return 'words'
    return 'unsupported'


def vocabularies(spec):
    alphabets=['aeiouAEIOU','aeiou','AEIOU']
    alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    prime_digits=''.join(alphabet[n] for n in range(16) if n>=2 and all(n%d for d in range(2,n)))
    alphabets.append(prime_digits)
    quoted=re.findall(r'''['"]([^'"\n]{1,40})['"]''',spec)
    for word in quoted:
        if len(word)>1 and word.isalnum():alphabets.append(''.join(dict.fromkeys(word)))
    tokens=[x for x in quoted if x.isalpha() and len(x)<=12]
    tokens+=re.findall(r'\bword\s+[\'\"]?([A-Za-z]{1,12})\b',spec)
    return list(dict.fromkeys(alphabets))[:8],list(dict.fromkeys(tokens))[:4]


def lexical_prior(model,spec):
    """Hand-engineered evidence compatibility, not semantic entailment or bug reward."""
    text=spec.lower();p=model['params'];name=model['template'];score=0.
    has=lambda *words:any(w in text for w in words)
    if name=='MAP':
        score+=3*has('each','correspond','difference','case','flip')
        score+=4*(p['transform']=='abs_sub' and has('absolute','difference'))
        score+=4*(p['transform']=='swapcase' and has('flip','uppercase','lowercase'))
    if name=='FILTER':score+=3*has('remove','without','keep','exclude')
    if name=='REDUCE':
        score+=4*(p['aggregate']=='sum' and has('sum','add '))
        score+=4*(p['aggregate']=='count' and has('count','number of'))
        score+=3*(p['aggregate']=='min' and has('smallest','minimum'))
        score+=3*(p['aggregate']=='max' and has('largest','maximum'))
    if name in ('FILTER','REDUCE'):
        pred=p['predicate']
        score+=2*(pred=='positive' and has('positive'))+2*(pred=='negative' and has('negative'))
        score+=2*(pred in ('even','length_even') and has('even'))+2*(pred in ('odd','length_odd') and has('odd'))
        score+=2*(pred.startswith('length_') and has('length'))
        score+=3*(pred=='not_member' and has('without','remove','exclude') and has('vowel'))
        score+=2*(pred in ('member','not_member') and has('vowel') and 'aeiou' in str(p['values']).lower())
        score+=2*(pred=='member' and has('digit','hexadecimal') and str(p['values'])=='2357BD')
        score+=2*(p['index']=='odd' and has('odd indices','odd index','odd positions'))
        score+=2*(p['index']=='even' and has('even indices','even index','even positions'))
        if name=='FILTER':
            score+=2*(p['order']=='length_lex' and has('length') and has('sort','order'))
            score+=1*(p['order']=='ascending' and has('sort','ascending'))
            score+=2*(not p['distinct'] and has('repeated','duplicates','multiplicity'))
    if name=='ORDER_CHECK':
        score+=4*has('monoton','sorted','increasing','decreasing')
        score+=4*(p['direction']=='either' and has('increasing') and has('decreasing'))
        score+=2*(p['direction']=='nondecreasing' and has('sorted','nondecreasing'))
        score+=2*(p['max_count']==2 and has('twice','two',' 2'))
    if name=='BALANCE':score+=4*has('bracket','opening','closing')
    if name=='SEGMENT_COUNT':
        score+=4*has('sentence')+2*has('word','start')
        score+=2*(p['match']=='first_word' and has('word'))
        score+=sum(1 for c in p['delimiters'] if c in spec)
    if name=='CAPACITY':
        score+=4*has('exchange','swap')
        score+=2*(p['left_predicate']=='odd' and p['right_predicate']=='even' and has('even'))
        score+=1*(p['comparison']=='le')
    if name=='NEIGHBOR_SELECT':score+=4*has('consonant','between','closest')+2*(p['direction']=='rightmost' and has('right','end'))
    if name=='CONTAINMENT':score+=4*has('contain','subset','include')+1*(p['mode']=='subset')
    score-=.05*sum(v!=templates.DEFAULTS[name][k] for k,v in p.items())
    return score


def enumerate_models(base,spec,arity,cap=2048):
    if not base:return []
    kinds=[kind([r['args'][i] for r in base]) for i in range(arity)]
    outputs=[r['result'] for r in base]
    scopes=list(range(len(outputs[0]))) if outputs and all(type(x) is tuple and len(x)==len(outputs[0]) for x in outputs) else [None]
    alphabets,tokens=vocabularies(spec);seen=set();rows=[]
    def emit(template,**params):
        if len(rows)>=cap:return
        try:m=templates.normalize(dict(template=template,**params),arity)
        except ValueError:return
        key=json.dumps(m,sort_keys=True)
        if key not in seen:seen.add(key);rows.append(m)
    for component in scopes:
        targets=[x if component is None else x[component] for x in outputs]
        types={type(x) for x in targets}
        numeric=types<={int,type(None)};boolean=types=={bool}
        labels=list({repr(x):x for x in targets if type(x) in (bool,str)}.values())
        labels=sorted(labels,key=repr)
        for argument,k in enumerate(kinds):
            if k=='unsupported':continue
            common=dict(argument=argument,component=component)
            same_output=types==({str} if k=='text' else {list})
            predicates=[('all','')]
            if k=='numbers':predicates += [(p,'') for p in ('positive','nonnegative','negative','nonpositive','zero','even','odd')]
            elif k=='words':predicates += [(p,'') for p in ('length_even','length_odd','upper','lower','alpha')]
            else:
                predicates += [(p,'') for p in ('upper','lower','alpha')]
                predicates += [(p,values) for values in alphabets for p in ('member','not_member')]
            if same_output:
                transforms=('identity','swapcase','lower','upper') if k in ('text','words') else ('identity','abs','negate','square')
                for transform in transforms:emit('MAP',transform=transform,**common)
                for other,other_kind in enumerate(kinds):
                    if other!=argument and k==other_kind=='numbers':
                        for transform in ('sub','abs_sub'):emit('MAP',other_argument=other,transform=transform,**common)
                orders=('preserve','ascending','descending','length_lex') if k=='words' else ('preserve','ascending','descending')
                for (predicate,values),order,distinct,index in itertools.product(predicates,orders,(False,True),('all','even','odd')):
                    emit('FILTER',predicate=predicate,values=values,order=order,distinct=distinct,index=index,**common)
            if numeric:
                for (predicate,values),aggregate,index in itertools.product(predicates,('count','sum','min','max'),('all','even','odd')):
                    emit('REDUCE',predicate=predicate,values=values,aggregate=aggregate,index=index,**common)
                if k=='text':
                    for token,delimiters,match in itertools.product(tokens,('.','?','!','.!?'),('first_word','prefix')):
                        emit('SEGMENT_COUNT',token=token,delimiters=delimiters,match=match,**common)
            if boolean:
                for direction,max_count in itertools.product(('nondecreasing','nonincreasing','either','strict_increasing','strict_decreasing'),(None,1,2)):
                    emit('ORDER_CHECK',direction=direction,max_count=max_count,**common)
                if k=='text':
                    for (opening,closing),prefix,empty in itertools.product((('(',')'),('<','>'),('[',']'),('{','}')),(True,False),(True,False)):
                        emit('BALANCE',opening=opening,closing=closing,check_prefix=prefix,empty=empty,**common)
                for other in range(arity):
                    if other!=argument and kinds[other]!='unsupported':
                        for mode in ('subset','proper_subset','equal','multiset'):emit('CONTAINMENT',other_argument=other,mode=mode,**common)
            if k=='text' and types<={str,type(None)}:
                for values,direction in itertools.product(alphabets,('leftmost','rightmost')):
                    emit('NEIGHBOR_SELECT',values=values,direction=direction,**common)
            if len(labels)==2 and types<={str,bool} and k=='numbers':
                for other,other_kind in enumerate(kinds):
                    if other==argument or other_kind!='numbers':continue
                    for left,right,comparison,reverse in itertools.product(('all','positive','negative','even','odd'),('all','positive','negative','even','odd'),('le','lt','eq','ge','gt'),(False,True)):
                        true_value,false_value=(labels[::-1] if reverse else labels)
                        emit('CAPACITY',other_argument=other,left_predicate=left,right_predicate=right,comparison=comparison,
                             true_value=true_value,false_value=false_value,**common)
    return rows


def retain(models,base,spec,cap=64):
    survivors=[]
    for i,model in enumerate(models):
        if all(templates.holds(model,r['args'],r['result']) is True for r in base):
            survivors.append(dict(model=model,prior=lexical_prior(model,spec),enumeration_index=i))
    survivors.sort(key=lambda r:(-r['prior'],r['enumeration_index']))
    return [dict(row,id='M'+str(i)) for i,row in enumerate(survivors[:cap])],len(survivors)


def fingerprint(model,inputs):
    return json.dumps([model['params']['component'],[templates.observe(model,args) for args in inputs]],sort_keys=True)


def display(pool,inputs,seed,cap=4):
    chosen=[];signatures=set()
    for row in pool:
        key=fingerprint(row['model'],inputs)
        if key not in signatures:chosen.append(row);signatures.add(key)
        if len(chosen)>=cap:break
    for row in pool:
        if len(chosen)>=cap:break
        if row not in chosen:chosen.append(row)
    random.Random(seed).shuffle(chosen)
    return [dict(id='C'+str(i),model_id=row['id'],model=row['model']) for i,row in enumerate(chosen)]


def structured_inputs(base,arity,seed,cap=80):
    kinds=[kind([r['args'][i] for r in base]) for i in range(arity)]
    choices={
      'numbers':[[],[0],[1],[-1],[0,0],[1,1],[0,1],[-1,1],[2,1],[1,2],[1,1,2],[2,2,1],[1,1,1],[2,4,6],[2,4,6,8]],
      'words':[[],['a'],['aa'],['aa','aa'],['aa','b'],['zz','aa','aaaa'],['aa','b','aa'],['','aa']],
      'text':['','a','A','I','i',' ','aa','a b','é','É','ß','İ','<>','><','()','(()','I wait? I go!','Iceland. I run!','1357BD','0123456789ABCDEF','AaEeIiOoUu'],
    }
    if any(k not in choices for k in kinds):return []
    if arity==1:return [(v,) for v in choices[kinds[0]]][:cap]
    domains=[choices[k] for k in kinds]
    prefix=list(itertools.product(*(xs[:6] for xs in domains)))
    rest=list(itertools.product(*domains));random.Random(seed).shuffle(rest)
    out=[];seen=set()
    for args in prefix+rest:
        key=repr(args)
        if key not in seen:seen.add(key);out.append(ast.literal_eval(repr(args)))
        if len(out)>=cap:break
    return out


def choice_messages(spec,menu):
    names={row['model']['template'] for row in menu}
    definitions={k:templates.CATALOG[k] for k in sorted(names)}
    text=('Select the candidate model best justified by the REQUIREMENT. Base agreement alone is not proof. '
          'Return {"choice":"actual candidate ID"}; use NONE if none is supported or menu is empty. '
          'Do not construct parameters, quote IDs, source bindings, or explanations.\nREQUIREMENT:\n'+spec+
          '\nMODEL DEFINITIONS:\n'+json.dumps(definitions)+'\nCANDIDATES:\n'+json.dumps([dict(id=r['id'],model=r['model']) for r in menu]))
    return [dict(role='system',content='Return one JSON object with a choice ID only.'),dict(role='user',content=text)]


def parse_choice(raw,menu):
    raw=re.sub(r'^```(?:json)?\s*\n|\n```\s*$','',raw.strip());data=json.loads(raw)
    if type(data) is not dict or type(data.get('choice')) is not str:raise ValueError('invalid_choice_shape')
    choice=data['choice']
    if choice!='NONE' and choice not in {r['id'] for r in menu}:raise ValueError('unknown_choice_id')
    return choice
