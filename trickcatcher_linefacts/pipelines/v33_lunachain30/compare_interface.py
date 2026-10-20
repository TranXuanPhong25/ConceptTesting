"""Mechanical model-output compiler, not semantic matching or post-hoc repair."""
import copy,json
from . import chain_prompts,schemas,prompt_aliases

def need(value,message):
    if not value:raise ValueError(message)

def compile_output(stage,raw,artifacts):
    keys={'items','summary'} if stage in ('S1','S2','S4') else {'comparisons','hypotheses','selected','summary'} if stage=='S3' else {'items','decisions','retain','summary'}
    need(type(raw) is dict and set(raw)==keys,'interface_fields')
    need(type(raw['summary']) is str and len(raw['summary'])<=4096,'summary')
    rows=raw.get('hypotheses',raw.get('items'))
    need(type(rows) is list,'interface_items')
    prefix={'S1':'O','S2':'B','S3':'H','S4':'P','S5':'P'}[stage];items=[]
    for i,row in enumerate(rows,1):
        need(type(row) is dict and 'id' not in row,'model_row_ids_forbidden')
        items.append(dict(copy.deepcopy(row),id=prefix+str(i)))
    status='ok'
    if stage in ('S1','S2') and not items:status='unknown'
    if stage=='S3':
        need(type(raw['comparisons']) is list and all(type(c) is dict for c in raw['comparisons']),'comparisons')
        verdicts=[c.get('verdict') for c in raw['comparisons']]
        status='ok' if 'mismatch' in verdicts else 'unknown' if 'unknown' in verdicts or not artifacts.get('S1',{}).get('items') or not artifacts.get('S2',{}).get('items') else 'abstain'
    obj=dict(status=status,reason=raw['summary'],items=items)
    if stage=='S3':
        need(type(raw['selected']) is list and all(type(x) is int and x>0 for x in raw['selected']),'selected_indices')
        obj.update(comparisons=copy.deepcopy(raw['comparisons']),selected_ids=['H'+str(i) for i in raw['selected']])
    if stage=='S5':
        need(type(raw['decisions']) is list and type(raw['retain']) is list and len(raw['retain'])<=12 and all(type(x) is str for x in raw['retain']),'decisions_or_retention')
        decisions=[]
        for i,d in enumerate(raw['decisions'],1):
            need(type(d) is dict and 'hypothesis_id' in d and not {'id','supersedes'}&set(d),'decision_interface')
            d=copy.deepcopy(d);target=d.pop('hypothesis_id');decisions.append(dict(d,id='H'+str(i),supersedes=target))
        obj['decisions']=decisions
    return obj

def messages(stage,task,artifacts,feedback):
    # Original independent stage evidence/views, with a simpler serialization contract.
    data=chain_prompts.messages(stage,task,artifacts,feedback)[1]
    shape=copy.deepcopy(chain_prompts.SHAPES[stage]);items=shape['items']
    for row in items:row.pop('id',None)
    if stage=='S1':items[0].update(quote=task['spec'],span=[0,len(task['spec'])])
    if stage=='S3':shape=dict(comparisons=shape['comparisons'],hypotheses=items,selected=[1],summary='<brief conclusion or uncertainty>')
    elif stage=='S5':
        items=copy.deepcopy(chain_prompts.SHAPES['S4']['items'])
        for row in items:row.pop('id',None)
        decisions=shape['decisions']
        for d in decisions:d.pop('id');d['hypothesis_id']=d.pop('supersedes');d['decision']='<keep|revise|withdraw|unknown>'
        shape=dict(items=items,decisions=decisions,retain=[],summary='<brief evidence-based conclusion>')
    else:shape=dict(items=items,summary='<brief explanation; required if no items>')
    system=chain_prompts.ROLES[stage]+'''\nReturn one JSON object in exactly the shape below. No top-level status or row IDs: the tool assigns IDs in list order (O1/B1/H1/P1 etc). Fill descriptions, not literal placeholders. summary is your concise conclusion, not a correctness certificate. No tools, code execution or external information. Do not invent requirements.\n'''
    if stage=='S1':system+='At most4 obligations. Entire provided spec quote and [0,len(spec)] span for EACH obligation, never clause span with full quote. Domain/eligibility are distinct; undefined terms remain ambiguous. '
    if stage=='S2':system+='At most6 behavior summaries, not every AST node. N aliases belong only in source_ids. guard/effect/uncertainty may be empty; statement required. Source view masks documentation but executable behavior remains visible. '
    if stage=='S3':system+='Exactly one comparison per O obligation with actual O/B/N aliases. Compare required vs actual relations, including guards, exits and scope. verdict=consistent/mismatch/unknown. A sufficient divergence condition must make required and actual outcomes DIFFER, not merely reach a branch. Undefined eligibility remains unknown. No conclusion of equivalence from passing examples alone. For each mismatch produce a linked hypothesis (max3); selected contains up to2 one-based hypothesis positions. With no mismatch, hypotheses=[] and selected=[]. Unknown/missing upstream evidence stays unknown. Alternative/uncertainty may be empty; selected condition/effect must be nonempty. '
    if stage in ('S4','S5'):system+='At most6 new positional input tuples, <=12unique total. input_repr is a literal tuple string matching signature; hypothesis_ids are selected H aliases. Prediction describes what you expect the candidate runtime to do, not a trusted spec oracle. Prediction kinds: unknown; exact_value with value_repr; exception_type with exception_type; relation_text with text. observe=[] or at most2source IDs per hypothesis, kinds statement_reach/operation_value/function_output. Unsupported exact observations are unknown. '
    if stage=='S5':system+='Exactly one decision per selected H hypothesis. hypothesis_id points to original H alias. decision=keep/revise/withdraw/unknown, evidence_ids cite F feedback for keep/revise/withdraw. condition required for keep/revise, optional for others. Read counterevidence; do not treat predicted-output contradiction alone as refuting a spec mismatch. retain is a list of prior or same-response input_repr strings you choose as final tests (max12); do not list inputs never proposed. New items may be empty. '
    return [dict(role='system',content=system+'\n'+json.dumps(shape,ensure_ascii=False)),data]

def direct_messages(task,round_index,feedback,new_cap):
    system='''Generate tests directly for the supplied specification and implementation. Choose concrete input tuples that may expose wrong behavior; no concept/obligation/graph extraction stage is required. You may use your own earlier runtime feedback. Do not assume passing public examples means correctness. No tools or external information. Return only JSON {"inputs":["complete positional tuple literal"],"retain":[]}. No Python programs or expected-output oracle. '''
    system+=f'At most{new_cap} input proposals this round, <=12unique over5rounds. '
    if round_index==5:system+='retain may list any prior or same-response proposed tuples to keep as final tests(max12). No never-proposed inputs. '
    else:system+='retain must be empty before the last round. '
    data=dict(spec=task['spec'],implementation=task['source_original'],signature=task['signature'],public_examples=task['base'],round=round_index,own_previous_feedback=feedback)
    return [dict(role='system',content=system),dict(role='user',content=json.dumps(data,ensure_ascii=False))]
