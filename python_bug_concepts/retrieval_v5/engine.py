"""V2 copied baseline + scoped facts, applicability and concept/site ranking."""
from __future__ import annotations
import ast
from pathlib import Path
from . import baseline_engine as baseline
from . import corpus
from .facts import Analysis,literal
from .applicability import condition

DEFAULT_DB=Path(__file__).resolve().parent/'index.sqlite3'
VERSION='scoped-v5.1'
build=baseline.build


def _match_node(a,record):
    candidates=[n for n in a.nodes if hasattr(n,'lineno') and n.lineno==record['line'] and hasattr(n,'end_lineno')]
    exact=[n for n in candidates if a.text(n)[:500]==record['expression']]
    return exact[0] if exact else None


def _candidates(code):
    original,spec,symbols,warning=baseline.structural_evidence(code)
    if warning:return original,spec,symbols,warning,None,[]
    try:a=Analysis(code)
    except Exception as exc:
        # Parser/backend availability is not evidence of safety. Retain baseline.
        return original,spec,symbols,'Scoped facts unavailable: '+type(exc).__name__+'; v2 evidence retained',None,[]
    observable=set()
    for chain in a.output_origins().values():
        observable.update(x['fact_id'] for x in chain if x.get('fact_id'))
    observable.update(a.id(n.value) for n in a.nodes if isinstance(n,ast.Return) and n.value is not None)
    output={};excluded=[]
    for cid,records in original.items():
        revised=[]
        for record in records:
            node=_match_node(a,record)
            if node is None:
                revised.append({**record,'applicability':{'status':'unknown','requires':['scope/source mapping available'],'support':[],'contradictions':[]}})
                continue
            verdict=condition(a,cid,node)
            fact=a.fact(node)
            flows=fact['id'] in observable
            row={**record,'fact_id':fact['id'],'scope_id':fact['scope_id'],'span':fact['span'],'applicability':verdict,
                 'priority':record['priority']+(6 if flows else 0),'output_dependency_status':'observed_local_dependency' if flows else 'unknown_not_excluded'}
            if verdict['contradictions']:
                excluded.append({'concept_id':cid,**row})
                continue
            revised.append(row)
            # A fixed initializer is the root definition, not its update compare.
            if cid=='py.extremum-initial-sentinel' and isinstance(node,ast.Compare):
                names=[x for x in [node.left,*node.comparators] if isinstance(x,ast.Name)]
                for name in names:
                    definition=a.stable_definition(node,name.id)
                    if definition is None or literal(definition.value) is None:continue
                    value=literal(definition.value)
                    if type(value) not in (int,float):continue
                    root=a.fact(definition)
                    revised.append({**row,'line':root['span']['line'],'end_line':root['span']['end_line'],'expression':root['expression'][:500],'fact_id':root['id'],'scope_id':root['scope_id'],'span':root['span'],'priority':row['priority']+12,'reason':'Same-scope fixed accumulator definition precedes the comparison update; admissible sentinel domain still requires contract review.','related_fact_ids':[row['fact_id']]})
        if revised:output[cid]=revised
    return output,spec,symbols,None,a,excluded


def structural_evidence(source):
    evidence,spec,symbols,warning,_,_=_candidates(source)
    return evidence,spec,symbols,warning


def _binding(card,row,a):
    fid=row.get('fact_id')
    origins=[]
    if a is not None and fid:
        node=next((n for n in a.nodes if hasattr(n,'lineno') and hasattr(n,'end_lineno') and a.id(n)==fid),None)
        if node is not None:origins=a.origins(node.value if isinstance(node,(ast.Assign,ast.AnnAssign,ast.Return)) else node)
    return {'where':{'fact_id':fid,'source_span':row.get('span'),'scope_id':row.get('scope_id'),'expression':row['expression']},
            'how':{'mechanism':card['how']['mechanism'],'observed_dependencies':origins,'status':'conditional_mechanism_not_bug_proof'},
            'what':{'failure_relation':card['what']['observable_failure'],'input_class_template':card['how']['trigger_template'],'expected_output':None,'status':'requires_public_contract_and_oracle_validation'},
            'public_contract':{'text':a.spec(node) if a is not None and fid and node is not None else '', 'status':'public_source_only_not_formalized'},
            'applicability':row.get('applicability',{'status':'unknown'})}


def search(query='',*,code=None,top_k=5,category=None,source=None,mode='hybrid',db=DEFAULT_DB,include_facts=True):
    if not 1<=top_k<=100 or mode not in {'hybrid','lexical'}:raise ValueError('Invalid top_k or retrieval mode')
    if code is None or mode=='lexical':
        result=baseline.search(query,code=code,top_k=top_k,category=category,source=source,mode=mode,db=db)
        return {**result,'engine_version':VERSION,'facts':None,'retrieval':'v5 lexical fallback; no scope/applicability claim'}
    evidence,spec,symbols,warning,a,excluded=_candidates(code)
    if a is None:
        result=baseline.search(query,code=code,top_k=top_k,category=category,source=source,mode=mode,db=db)
        return {**result,'engine_version':VERSION,'warning':warning,'facts':None,'retrieval':'v5 unavailable; baseline fallback, applicability unknown'}
    baseline.ensure(db)
    cards={c['id']:c for c in corpus.cards()}
    docs=baseline.lexical_scores(query+' '+spec,db)
    syms=baseline.lexical_scores(symbols,db)
    docmax=max(docs.values(),default=1) or 1;symmax=max(syms.values(),default=1) or 1
    pairs=[]
    for cid,records in evidence.items():
        card=cards[cid]
        if category and card['category']!=category or source and not any(s['source']==source for s in card['sources']):continue
        for row in records:
            value=row['priority']+10*docs.get(cid,0)/docmax+5*syms.get(cid,0)/symmax
            pairs.append((value,cid,row))
    pairs.sort(key=lambda x:(-x[0],x[1],x[2]['line']))
    selected=[];seen=set()
    for score,cid,row in pairs:
        if cid in seen:continue
        seen.add(cid)
        sites=sorted(evidence[cid],key=lambda r:(-r['priority'],r['line']))
        # The pair chosen above fixes the leading site; other sites stay inspectable.
        ordered=[row]+[r for r in sites if r!=row]
        selected.append({'score':score,'concept':cards[cid],'evidence':ordered[:3],'additional_sites_omitted':max(0,len(ordered)-3),
                         'instantiated':_binding(cards[cid],row,a),'status':'unverified_fault_hypothesis'})
        if len(selected)==top_k:break
    return {'query':query,'warning':warning,'code_hints':' '.join(evidence),'results':selected,'retrieval':'scoped facts + conditional applicability + concept/site pairs; scores are not bug probability',
            'engine_version':VERSION,'corpus_sha256':corpus.digest(),'facts':a.export() if include_facts else None,'excluded_bindings':excluded}
