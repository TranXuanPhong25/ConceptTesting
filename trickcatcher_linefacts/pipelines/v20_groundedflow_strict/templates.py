"""Typed reusable candidate spec models, semantic alternatives and discrimination.

No benchmark task IDs, function names or reference code. Parameters require public-spec support.
A compiled model is a candidate obligation, not a trusted oracle.
"""
import copy
from collections import Counter
import re

PREDICATES=('all','positive','nonnegative','negative','nonpositive','zero','even','odd',
            'member','not_member','upper','lower','alpha','length_even','length_odd')
COMMON={'argument':0,'predicate':'all','values':'','index':'all','component':None}
DEFAULTS={
 'MAP':{'argument':0,'other_argument':None,'transform':'identity','component':None},
 'FILTER':dict(COMMON,order='preserve',distinct=False),
 'REDUCE':dict(COMMON,aggregate='count',empty=None,empty_policy='value'),
 'ORDER_CHECK':{'argument':0,'direction':'nondecreasing','max_count':None,'component':None},
 'BALANCE':{'argument':0,'opening':'(','closing':')','check_prefix':True,'empty':True,'component':None},
 'SEGMENT_COUNT':{'argument':0,'delimiters':'.!?','token':'','match':'first_word','component':None},
 'CAPACITY':{'argument':0,'other_argument':1,'left_predicate':'odd','right_predicate':'even',
             'comparison':'le','true_value':True,'false_value':False,'component':None},
 'NEIGHBOR_SELECT':{'argument':0,'predicate':'member','values':'','neighbor_predicate':'not_member',
                    'direction':'rightmost','empty':'','component':None},
 'CONTAINMENT':{'argument':0,'other_argument':1,'mode':'subset','component':None},
}
CATALOG={
 'MAP':'transform each element: identity|abs|negate|square|swapcase|lower|upper; with other_argument: sub|abs_sub. Preserve length/order. str input returns str, lists return list.',
 'FILTER':'keep elements satisfying predicate and index=all|even|odd. values for member/not_member. order=preserve|ascending|descending|length_lex, distinct=false preserves duplicates.',
 'REDUCE':'filter by predicate, values and index, then aggregate=count|sum|min|max. count/sum empty=0; min/max empty returns empty parameter (default null). component optionally targets one output tuple component.',
 'ORDER_CHECK':'direction=nondecreasing|nonincreasing|either|strict_increasing|strict_decreasing. max_count optionally limits occurrences of any value. Output Boolean.',
 'BALANCE':'string token balance with single-char opening/closing; total balance zero and prefix never negative. empty Boolean. Output Boolean.',
 'SEGMENT_COUNT':'split string at ANY delimiter character; count segments with token as first_word or prefix (match). Exact case. Empty segments ignored.',
 'CAPACITY':'count left_predicate in argument vs right_predicate in other_argument; comparison=le|lt|eq|ge|gt. Return true_value or false_value.',
 'NEIGHBOR_SELECT':'choose leftmost/rightmost interior element satisfying predicate while BOTH immediate neighbors satisfy neighbor_predicate. values for member tests; empty is fallback.',
 'CONTAINMENT':'required elements (other_argument) vs container (argument). mode=subset|proper_subset|equal uses set semantics; multiset uses counts. Output Boolean.',
}


def normalize(row,arity):
    if type(row) is not dict or type(row.get('template')) is not str or row['template'] not in DEFAULTS:
        raise ValueError('unknown_template')
    template=row['template'];allowed=set(DEFAULTS[template])|{'template','evidence','description'}
    if set(row)-allowed:raise ValueError('unknown_parameter')
    p=copy.deepcopy(DEFAULTS[template]);p.update({k:v for k,v in row.items() if k in p})
    for key in ('argument','other_argument'):
        if key in p and p[key] is not None:
            if type(p[key]) is not int or not 0<=p[key]<arity:raise ValueError('argument_index')
    if 'other_argument' in p and p['other_argument'] is not None and p['other_argument']==p['argument']:
        raise ValueError('distinct_arguments_required')
    if p.get('component') is not None and (type(p['component']) is not int or not 0<=p['component']<4):
        raise ValueError('component_index')
    for key in ('predicate','left_predicate','right_predicate','neighbor_predicate'):
        if key in p and (type(p[key]) is not str or p[key] not in PREDICATES):raise ValueError('predicate_enum')
    enums={'index':('all','even','odd'),'order':('preserve','ascending','descending','length_lex'),
           'aggregate':('count','sum','min','max'),'empty_policy':('value','raise'),
           'comparison':('le','lt','eq','ge','gt'),'mode':('subset','proper_subset','equal','multiset'),
           'match':('first_word','prefix')}
    for key,choices in enums.items():
        if key in p and (type(p[key]) is not str or p[key] not in choices):raise ValueError(key+'_enum')
    if 'direction' in p:
        choices=('leftmost','rightmost') if template=='NEIGHBOR_SELECT' else ('nondecreasing','nonincreasing','either','strict_increasing','strict_decreasing')
        if type(p['direction']) is not str or p['direction'] not in choices:raise ValueError('direction_enum')
    if template=='MAP':
        choices=('identity','abs','negate','square','swapcase','lower','upper','sub','abs_sub')
        if type(p['transform']) is not str or p['transform'] not in choices:raise ValueError('transform_enum')
        if p['transform'] in ('sub','abs_sub') and p['other_argument'] is None:raise ValueError('pair_transform_needs_other_argument')
        if p['transform'] not in ('sub','abs_sub') and p['other_argument'] is not None:raise ValueError('unary_transform_has_other_argument')
    if template in ('CAPACITY','CONTAINMENT') and p['other_argument'] is None:raise ValueError('missing_other_argument')
    if 'max_count' in p and p['max_count'] is not None and (type(p['max_count']) is not int or not 1<=p['max_count']<=100):raise ValueError('max_count')
    for key in ('distinct','check_prefix'):
        if key in p and type(p[key]) is not bool:raise ValueError(key+'_type')
    if template=='BALANCE':
        if any(type(p[k]) is not str or len(p[k])!=1 for k in ('opening','closing')) or p['opening']==p['closing'] or type(p['empty']) is not bool:
            raise ValueError('balance_parameters')
    if template=='SEGMENT_COUNT':
        if type(p['delimiters']) is not str or not 1<=len(p['delimiters'])<=12 or type(p['token']) is not str or not 1<=len(p['token'])<=40:
            raise ValueError('segmentation_parameters')
    if 'values' in p and (type(p['values']) not in (str,list) or len(p['values'])>100):raise ValueError('values_type')
    for key in ('empty','true_value','false_value'):
        if key in p and type(p[key]) not in (type(None),bool,int,str):raise ValueError('scalar_output_parameter')
    return dict(template=template,params=p)


def predicate(name,x,values):
    if name=='all':return True
    if name in ('member','not_member'):return (x in values) if name=='member' else (x not in values)
    if name in ('upper','lower','alpha'):
        if type(x) is not str:raise TypeError('string element required')
        return {'upper':str.isupper,'lower':str.islower,'alpha':str.isalpha}[name](x)
    if name.startswith('length_'):
        if type(x) not in (str,list,tuple):raise TypeError('sized element required')
        return len(x)%2==(0 if name=='length_even' else 1)
    if type(x) is not int:raise TypeError('integer element required')
    return {'positive':lambda:x>0,'nonnegative':lambda:x>=0,'negative':lambda:x<0,
            'nonpositive':lambda:x<=0,'zero':lambda:x==0,'even':lambda:x%2==0,'odd':lambda:x%2!=0}[name]()


def sequence(x):
    if type(x) not in (str,list,tuple):raise TypeError('sequence required')
    return x


def selected(xs,p):
    return [x for i,x in enumerate(xs) if (p['index']=='all' or i%2==(0 if p['index']=='even' else 1))
            and predicate(p['predicate'],x,p['values'])]


def expected(model,args):
    template=model['template'];p=model['params'];raw=args[p['argument']]
    xs=raw if template=='CONTAINMENT' and type(raw) in (set,frozenset,dict) else sequence(raw)
    if template=='MAP':
        op=p['transform']
        if p['other_argument'] is not None:
            ys=sequence(args[p['other_argument']])
            if len(xs)!=len(ys):raise TypeError('paired sequences require equal length')
            if any(type(x) is not int for x in list(xs)+list(ys)):raise TypeError('integer pair required')
            result=[abs(x-y) if op=='abs_sub' else x-y for x,y in zip(xs,ys)]
        else:
            if op in ('abs','negate','square') and any(type(x) is not int for x in xs):raise TypeError('integer element required')
            if op in ('swapcase','lower','upper') and any(type(x) is not str for x in xs):raise TypeError('string element required')
            fn={'identity':lambda x:x,'abs':abs,'negate':lambda x:-x,'square':lambda x:x*x,
                'swapcase':str.swapcase,'lower':str.lower,'upper':str.upper}[op]
            result=[fn(x) for x in xs]
        return ''.join(result) if type(xs) is str else result
    if template in ('FILTER','REDUCE'):
        ys=selected(xs,p)
        if template=='REDUCE':
            if not ys:
                if p['empty_policy']=='raise':raise ValueError('empty aggregation')
                return 0 if p['aggregate'] in ('count','sum') else p['empty']
            return {'count':len,'sum':sum,'min':min,'max':max}[p['aggregate']](ys)
        if p['distinct']:
            ys=list(dict.fromkeys(ys))
        if p['order']=='ascending':ys=sorted(ys)
        if p['order']=='descending':ys=sorted(ys,reverse=True)
        if p['order']=='length_lex':ys=sorted(ys,key=lambda x:(len(x),x))
        return ''.join(ys) if type(xs) is str else ys
    if template=='ORDER_CHECK':
        up=all(x<=y for x,y in zip(xs,xs[1:]));down=all(x>=y for x,y in zip(xs,xs[1:]))
        order={'nondecreasing':up,'nonincreasing':down,'either':up or down,
               'strict_increasing':all(x<y for x,y in zip(xs,xs[1:])),
               'strict_decreasing':all(x>y for x,y in zip(xs,xs[1:]))}[p['direction']]
        return order and (p['max_count'] is None or all(c<=p['max_count'] for c in Counter(xs).values()))
    if template=='BALANCE':
        if type(xs) is not str:raise TypeError('string required')
        if not xs:return p['empty']
        balance=0
        for char in xs:
            if char not in (p['opening'],p['closing']):return False
            balance+=1 if char==p['opening'] else -1
            if p['check_prefix'] and balance<0:return False
        return balance==0
    if template=='SEGMENT_COUNT':
        if type(xs) is not str:raise TypeError('string required')
        parts=re.split('['+re.escape(p['delimiters'])+']',xs)
        if p['match']=='prefix':return sum(part.strip().startswith(p['token']) for part in parts)
        return sum(bool(words) and words[0]==p['token'] for part in parts for words in [part.split()])
    if template=='CAPACITY':
        ys=sequence(args[p['other_argument']])
        left=sum(predicate(p['left_predicate'],x,'') for x in xs)
        right=sum(predicate(p['right_predicate'],y,'') for y in ys)
        condition={'le':left<=right,'lt':left<right,'eq':left==right,'ge':left>=right,'gt':left>right}[p['comparison']]
        return p['true_value'] if condition else p['false_value']
    if template=='NEIGHBOR_SELECT':
        indices=range(1,len(xs)-1)
        if p['direction']=='rightmost':indices=reversed(list(indices))
        for i in indices:
            if predicate(p['predicate'],xs[i],p['values']) and all(predicate(p['neighbor_predicate'],xs[j],p['values']) for j in (i-1,i+1)):
                return xs[i]
        return p['empty']
    if template=='CONTAINMENT':
        ys=args[p['other_argument']]
        if type(ys) not in (set,frozenset,dict):ys=sequence(ys)
        mode=p['mode']
        if mode=='multiset':return all(Counter(xs)[v]>=n for v,n in Counter(ys).items())
        return {'subset':lambda:set(ys)<=set(xs),'proper_subset':lambda:set(ys)<set(xs),'equal':lambda:set(ys)==set(xs)}[mode]()
    raise ValueError('unsupported template')


def observe(model,args):
    try:return dict(status='ok',value=expected(model,args))
    except ValueError as exc:
        if str(exc)=='empty aggregation':return dict(status='ValueError',value=None)
        return dict(status='unknown',value=None)
    except (TypeError,IndexError,KeyError,OverflowError):return dict(status='unknown',value=None)


def holds(model,args,result):
    value=observe(model,args)
    if value['status']!='ok':return None
    try:
        component=model['params'].get('component')
        actual=result if component is None else result[component]
        return type(actual) is type(value['value']) and actual==value['value']
    except (TypeError,IndexError,KeyError):return False


def alternatives(model,cap=6):
    p=model['params'];changes=[];t=model['template']
    if t=='MAP':
        alts={'identity':'abs','abs':'identity','negate':'identity','square':'identity',
              'swapcase':'lower','lower':'identity','upper':'identity','sub':'abs_sub','abs_sub':'sub'}
        changes.append(('transform',alts[p['transform']]))
    if t in ('FILTER','REDUCE'):
        pred={'positive':'nonnegative','nonnegative':'positive','negative':'nonpositive',
              'nonpositive':'negative','even':'odd','odd':'even','member':'not_member',
              'not_member':'member','length_even':'length_odd','length_odd':'length_even',
              'upper':'all','lower':'all','alpha':'all','zero':'all','all':'positive'}
        changes.append(('predicate',pred[p['predicate']]))
        if p['predicate']!='all':changes.append(('predicate','all'))
        changes.append(('index',{'all':'even','even':'odd','odd':'even'}[p['index']]))
        if p['predicate'] in ('member','not_member') and p['values']:
            for i in range(len(p['values'])):changes.append(('values',p['values'][:i]+p['values'][i+1:]))
        if t=='FILTER':
            changes.append(('distinct',not p['distinct']))
            changes.append(('order','preserve' if p['order']!='preserve' else 'ascending'))
        else:
            changes.insert(0,('aggregate',{'count':'sum','sum':'count','min':'max','max':'min'}[p['aggregate']]))
            changes.append(('empty_policy','raise'))
    if t=='ORDER_CHECK':
        changes.append(('direction',{'nondecreasing':'strict_increasing','nonincreasing':'strict_decreasing',
                                    'either':'nondecreasing','strict_increasing':'nondecreasing','strict_decreasing':'nonincreasing'}[p['direction']]))
        changes.append(('max_count',None if p['max_count'] is not None else 1))
    if t=='BALANCE':changes=[('check_prefix',False),('empty',not p['empty'])]
    if t=='SEGMENT_COUNT':
        if len(p['delimiters'])>1:changes.append(('delimiters',p['delimiters'][0]))
        changes.append(('match','prefix' if p['match']=='first_word' else 'first_word'))
    if t=='CAPACITY':changes=[('comparison','lt' if p['comparison']=='le' else 'le'),('comparison','eq')]
    if t=='NEIGHBOR_SELECT':changes=[('direction','leftmost' if p['direction']=='rightmost' else 'rightmost'),('neighbor_predicate',p['predicate'])]
    if t=='CONTAINMENT':changes=[('mode','proper_subset' if p['mode']=='subset' else 'subset'),('mode','equal')]
    out=[]
    for field,value in changes:
        if value==p[field] or any(a['change']['field']==field and a['change']['alternative']==value for a in out):continue
        alternative=copy.deepcopy(model);alternative['params'][field]=value
        out.append(dict(id='F'+str(len(out)),model=alternative,origin='candidate_spec_model',
                        change=dict(field=field,original=p[field],alternative=value),
                        description=f'{field}: {p[field]!r} -> {value!r}'))
    return out[:cap]


def activates(card,args):
    a=observe(card['model'],args);b=observe(card['fault']['model'],args)
    return a['status']=='ok' and b['status']!='unknown' and a!=b


def visible(card):
    return {k:card[k] for k in ('id','model','evidence','fault','block_ids','reasoning')}
