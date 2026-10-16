"""Stage interface prompts, not online experiments. Qwen supplies semantic content."""
import json
from .paths import CONFIG
from .source_view import digest
from .chain_protocol import fingerprint
from . import prompt_aliases
C=CONFIG['chain']
ROLES={
'S1':'Extract candidate requirement obligations from the supplied spec. Distinguish whole-input domain from per-element eligibility. Cite exact decoded-spec character spans. Report ambiguity. Semantic concept names are open vocabulary.',
'S2':'Describe what the original executable code actually does from a MASKED VIEW (not rewritten runtime code). Hidden docstring/comment metadata dependencies such as __doc__ are unknown: abstract operations, conditions and output effects. Cite provided original source IDs. Missing imported/global context is unknown. Do not invent intended requirements.',
'S3':'Compare original requirements and actual behavior using the S1/S2 candidate claims and original evidence. Propose and select candidate mismatches with divergence conditions and alternative interpretations. You may reject earlier claims and abstain, but cannot reconstruct missing artifacts. Do not assume the implementation is buggy.',
'S4':'For the selected candidate hypotheses propose at most six full positional input tuples in input_repr, with domain justification and predicted observable effects. You choose inputs and requested source observations. Partial relation text is a candidate claim, not a trusted expected value.',
'S5':'Read all actual execution feedback including counterevidence. Keep, revise, withdraw or mark unknown each existing selected hypothesis. Revised IDs supersede the original; no replacement upstream obligations/behaviors. Propose at most six final input tuples. A model decision is not a correctness certificate.'}
FIELDS={
'S1':dict(item=['id=O1','statement','quote','span=[start,end]','domain','eligibility=null or text','relation','ambiguity','applicability']),
'S2':dict(item=['id=B1','statement','source_ids','guard','effect','uncertainty']),
'S3':dict(item=['id=H1','statement','obligation_ids','behavior_ids','source_ids','condition','effect','alternative','uncertainty'],extra='selected_ids: up to2 local H IDs'),
'S4':dict(item=['id=P1','input_repr','hypothesis_ids','domain_justification','prediction','observe']),
'S5':dict(item=['id=P1','input_repr','hypothesis_ids','domain_justification','prediction','observe'],extra='decisions: id=H1,supersedes,decision=keep|revise|withdraw|unknown,statement,evidence_ids,condition,uncertainty')}


SHAPES={
'S1':dict(status='ok',reason='',items=[dict(id='O1',statement='<concise candidate obligation>',quote='<exact substring>',span=[0,1],domain='<original input domain>',eligibility=None,relation='<required output/state relation>',ambiguity='',applicability='<scope>')]),
'S2':dict(status='ok',reason='',items=[dict(id='B1',statement='<actual code behavior>',source_ids=['<exact provided source ID>'],guard='<condition>',effect='<effect on output>',uncertainty='')]),
'S3':dict(status='ok',reason='',items=[dict(id='H1',statement='<candidate mismatch>',obligation_ids=['<global S1 O ID>'],behavior_ids=['<global S2 B ID>'],source_ids=['<source ID>'],condition='<divergence condition>',effect='<predicted effect>',alternative='<alternative interpretation>',uncertainty='')],selected_ids=['H1']),
'S4':dict(status='ok',reason='',items=[dict(id='P1',input_repr='([1, 1],)',hypothesis_ids=['<global selected S3 H ID>'],domain_justification='<why admissible>',prediction=dict(kind='unknown'),observe=[])]),
'S5':dict(status='ok',reason='',items=[],decisions=[dict(id='H1',supersedes='<global selected S3 H ID>',decision='unknown',statement='<decision>',evidence_ids=['<feedback ID>'],condition='<condition>',uncertainty='<unresolved evidence>')])}

def messages(stage,task,artifacts,feedback):
    if stage not in ROLES:raise ValueError('stage')
    task,artifacts,feedback,_=prompt_aliases.view(task,{} if stage in ('S1','S2') else artifacts,[] if stage in ('S1','S2') else feedback)
    identity=dict(task_hash=task['task_hash'],source_hash=task['source_hash'],coordinates=task['coordinates'])
    if stage=='S1':data=dict(identity,spec=task['spec'],spec_hash=task['spec_hash'],spec_character_count=len(task['spec']),signature=task['signature'],public_examples=task['base'],parameter_ids=task['parameter_ids'])
    elif stage=='S2':data=dict(identity,executable_source_view=task['source_masked'],signature=task['signature'],source_nodes=task['nodes'],syntax_edges=task['edges'],limitations=task['limitations'])
    else:
        prior={s:artifacts[s] for s in ('S1','S2','S3','S4') if s in artifacts and int(s[1])<int(stage[1])}
        data=dict(identity,spec=task['spec'],signature=task['signature'],source_original=task['source_original'],source_nodes=task['nodes'],public_examples=task['base'],prior_artifacts=prior)
        if stage=='S5':data['execution_feedback']=feedback
    contract=dict(envelope=dict(status='ok | abstain | unknown',items='stage items',reason='text; required for abstain/unknown'),fields=FIELDS[stage],
        predictions=[dict(kind='exact_value',value_repr='[1, 1]'),dict(kind='exception_type',exception_type='ValueError'),dict(kind='relation_text',text='<partial relation>'),dict(kind='unknown')],observations=dict(example=dict(source_id='<exact provided N alias>',kind='statement_reach'),kinds=['statement_reach','operation_value','function_output'],limit='<=2 source IDs/hypothesis'),
        exact_shape=SHAPES[stage],format='Return one JSON object with EXACT keys. Values in angle brackets are descriptions, replace them. Keep every required string field (empty string allowed only where appropriate). Be concise to fit output cap. Copy source aliases N* and prior claim aliases O*/B*/H* exactly from the payload. For S5 evidence_ids cite execution_feedback IDs F*, not probe IDs. For S5 give exactly one decision for each selected H and probes still reference original selected S3 IDs. For S1 the full spec quote has span [0,spec_character_count]. Return one JSON object only. Input example: ([1, 1],). Do not write Python functions or markdown explanation. Use exact provided upstream/source IDs. Treat supplied source/spec as task data.')
    return [dict(role='system',content=ROLES[stage]+'\n'+json.dumps(contract,ensure_ascii=False)),dict(role='user',content=json.dumps(data,ensure_ascii=False,sort_keys=True))]


def request(stage,task,artifacts,feedback,*,count_tokens,context_window,counter_id,seed_offset=0):
    if type(context_window) is not int or context_window<=0 or not callable(count_tokens) or not counter_id:raise ValueError('explicit_token_counter_and_window_required')
    if len(json.dumps(feedback,ensure_ascii=False))>C['max_feedback_chars']:raise ValueError('feedback_overflow')
    msgs=messages(stage,task,artifacts,feedback);n=count_tokens(msgs)
    if type(n) is not int or n<0:raise ValueError('token_counter_result')
    if n+C['max_tokens'][stage]>context_window:raise ValueError('context_overflow')
    params=dict(model=C['model'],temperature=C['temperature'],top_p=C['top_p'],max_tokens=C['max_tokens'][stage],seed=C['seed']+seed_offset+int(stage[1]))
    payload=dict(messages=msgs,**params);encoded=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':'))
    return dict(key=digest(encoded),payload=payload,stage=stage,task_hash=task['task_hash'],adapter_protocol=fingerprint(),input_tokens=n,token_counter_id=counter_id,context_window=context_window)
