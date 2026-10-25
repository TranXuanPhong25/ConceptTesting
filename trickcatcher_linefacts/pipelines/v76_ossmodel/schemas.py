"""Mechanical stage validation and reference integrity; semantic vocabulary remains open."""
import json
import re
from .chain_inputs import parse_literal
STAGES=('S1','S2','S3','S4','S5')
CAPS={'S1':4,'S2':6,'S3':3,'S4':6,'S5':6}
KINDS={'statement_reach','operation_value','function_output'}


class ArtifactError(ValueError):pass


def need(condition,reason):
    if not condition:raise ArtifactError(reason)


def text(value,name,empty=False):
    need(type(value) is str and len(value)<=4096 and (empty or bool(value.strip())),name)


def refs(value,allowed,name,minimum=1):
    need(type(value) is list and minimum<=len(value)<=12 and len(value)==len(set(x for x in value if type(x) is str)) and all(type(x) is str and x in allowed for x in value),name)


def utf8_strings(value):
    pending=[(value,0)];count=0
    while pending:
        item,depth=pending.pop();count+=1
        need(count<=4096 and depth<=64,'response_structure_limit')
        if type(item) is str:
            try:item.encode('utf-8')
            except UnicodeError as exc:raise ArtifactError('invalid_unicode') from exc
        elif type(item) is dict:
            pending.extend((x,depth+1) for pair in item.items() for x in pair)
        elif type(item) is list:pending.extend((x,depth+1) for x in item)


def extract(raw,finish_reason='stop'):
    need(finish_reason not in ('length','truncated'),'truncated')
    need(type(raw) is str,'response_type');utf8_strings(raw)
    need(len(raw.encode('utf-8'))<=65536,'response_size')
    def object_pairs(pairs):
        out={}
        for key,value in pairs:
            need(key not in out,'duplicate_json_key');out[key]=value
        return out
    def load(value):
        return json.loads(value,object_pairs_hook=object_pairs,parse_constant=lambda x:(_ for _ in ()).throw(ArtifactError('nonfinite_json')))
    stripped=raw.strip();offset=raw.find(stripped)
    try:obj=load(stripped);utf8_strings(obj);need(type(obj) is dict,'object_required');return obj,[offset,offset+len(stripped)]
    except (json.JSONDecodeError,RecursionError):pass
    matches=list(re.finditer(r'```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```',raw))
    need(len(matches)==1,'unique_json_object_required')
    match=matches[0]
    # Outside text may contain prose, but no additional JSON objects/arrays or code fences.
    outside=raw[:match.start()]+raw[match.end():]
    need(not any(c in outside for c in '{}[]') and '```' not in outside,'ambiguous_json')
    try:obj=load(match.group(1))
    except (json.JSONDecodeError,RecursionError) as exc:raise ArtifactError('malformed_json') from exc
    utf8_strings(obj);need(type(obj) is dict,'object_required');return obj,[match.start(1),match.end(1)]


def prediction(row):
    need(type(row) is dict,'prediction_shape');kind=row.get('kind')
    fields={'exact_value':{'kind','value_repr'},'exception_type':{'kind','exception_type'},'relation_text':{'kind','text'},'unknown':{'kind'}}
    need(type(kind) is str and kind in fields and set(row)==fields[kind],'prediction_fields')
    if kind=='exact_value':text(row['value_repr'],'prediction_value')
    if kind=='exception_type':need(type(row['exception_type']) is str and re.fullmatch('[A-Za-z][A-Za-z0-9_]*',row['exception_type']) is not None,'exception_type')
    if kind=='relation_text':text(row['text'],'relation_text')


def validate(stage,obj,task,registry,selected=(),feedback_ids=()):
    utf8_strings(obj);need(stage in STAGES and type(obj) is dict,'stage_shape')
    top={'status','items','reason'}
    if stage=='S3':top|={'selected_ids','comparisons'}
    if stage=='S5':top|={'decisions'}
    need(set(obj)==top,'envelope_fields')
    need(obj['status'] in ('ok','abstain','unknown'),'status');text(obj['reason'],'reason',True)
    need(type(obj['items']) is list and len(obj['items'])<=CAPS[stage],'items_cap')
    if obj['status']!='ok':need(not obj['items'] and bool(obj['reason'].strip()),'terminal_items')
    if obj['status']=='ok' and stage in ('S1','S2','S3'):need(bool(obj['items']),'empty_ok')
    nodes={r['id'] for r in task['nodes']};local=set()
    prefix={'S1':'O','S2':'B','S3':'H','S4':'P','S5':'P'}[stage]
    for row in obj['items']:
        need(type(row) is dict,'item_shape');ident=row.get('id')
        need(type(ident) is str and re.fullmatch(prefix+r'[1-9][0-9]*',ident) is not None and ident not in local,'local_id');local.add(ident)
        if stage=='S1':
            need(set(row)=={'id','statement','quote','span','domain','eligibility','relation','ambiguity','applicability'},'obligation_fields')
            for k in ('statement','quote','domain','relation','applicability'):text(row[k],k)
            text(row['ambiguity'],'ambiguity',True)
            need(row['eligibility'] is None or type(row['eligibility']) is str,'eligibility')
            span=row['span'];need(type(span) is list and len(span)==2 and all(type(x) is int for x in span),'quote_span')
            need(0<=span[0]<span[1]<=len(task['spec']) and task['spec'][span[0]:span[1]]==row['quote'],'quote_mismatch')
        elif stage=='S2':
            need(set(row)=={'id','statement','source_ids','guard','effect','uncertainty'},'behavior_fields')
            refs(row['source_ids'],nodes,'source_refs')
            for k in ('statement','guard','effect','uncertainty'):text(row[k],k,k!='statement')
        elif stage=='S3':
            need(set(row)=={'id','statement','obligation_ids','behavior_ids','source_ids','condition','effect','alternative','uncertainty'},'hypothesis_fields')
            refs(row['obligation_ids'],{k for k,r in registry.items() if r['stage']=='S1'},'obligation_refs')
            refs(row['behavior_ids'],{k for k,r in registry.items() if r['stage']=='S2'},'behavior_refs')
            refs(row['source_ids'],nodes,'source_refs')
            for k in ('statement','condition','effect','alternative','uncertainty'):text(row[k],k,k in ('alternative','uncertainty'))
        else:
            need(set(row)=={'id','input_repr','hypothesis_ids','domain_justification','prediction','observe'},'probe_fields')
            text(row['input_repr'],'input_repr');text(row['domain_justification'],'domain_justification')
            refs(row['hypothesis_ids'],set(selected),'selected_hypothesis_refs');prediction(row['prediction'])
            need(type(row['observe']) is list and len(row['observe'])<=4,'observation_requests')
            for observation in row['observe']:
                need(type(observation) is dict and set(observation)=={'source_id','kind'} and type(observation['source_id']) is str and observation['source_id'] in nodes and type(observation['kind']) is str and observation['kind'] in KINDS,'observation_request')
    if stage in ('S4','S5'):
        requested={h:set() for h in selected}
        for row in obj['items']:
            for h in row['hypothesis_ids']:requested[h].update(x['source_id'] for x in row['observe'])
        need(all(len(x)<=2 for x in requested.values()),'observation_source_cap')
    if stage=='S3':
        refs(obj['selected_ids'],local,'selected_ids',0);need(len(obj['selected_ids'])<=2,'selected_cap')
        comparisons=obj['comparisons'];need(type(comparisons) is list and len(comparisons)<=CAPS['S1'],'comparison_cap')
        obligations={k for k,r in registry.items() if r['stage']=='S1'}
        behaviors={k for k,r in registry.items() if r['stage']=='S2'}
        covered=set();mismatches=set();unknown=not obligations or not behaviors
        for audit in comparisons:
            need(type(audit) is dict and set(audit)=={'obligation_ids','behavior_ids','source_ids','required_relation','actual_relation','divergence_condition','verdict','justification'},'comparison_fields')
            refs(audit['obligation_ids'],obligations,'comparison_obligation_refs');need(len(audit['obligation_ids'])==1,'comparison_single_obligation')
            oid=audit['obligation_ids'][0];need(oid not in covered,'comparison_duplicate');covered.add(oid)
            refs(audit['behavior_ids'],behaviors,'comparison_behavior_refs',1 if behaviors else 0);refs(audit['source_ids'],nodes,'comparison_source_refs')
            for field in ('required_relation','actual_relation','divergence_condition','justification'):text(audit[field],field)
            need(type(audit['verdict']) is str and audit['verdict'] in ('consistent','mismatch','unknown'),'comparison_verdict')
            if not behaviors:need(audit['verdict']=='unknown','missing_behavior_requires_unknown')
            if audit['verdict']=='mismatch':mismatches.add(oid)
            unknown|=audit['verdict']=='unknown'
        need(covered==obligations,'comparison_coverage')
        linked={oid for h in obj['items'] for oid in h['obligation_ids']}
        need(mismatches<=linked,'unrepresented_mismatch')
        need(all(set(h['obligation_ids'])&mismatches for h in obj['items']),'hypothesis_without_mismatch')
        if mismatches:need(obj['status']=='ok' and bool(obj['selected_ids']),'mismatch_requires_selection')
        else:
            need(not obj['items'] and not obj['selected_ids'],'no_mismatch_hypotheses')
            need(obj['status']==('unknown' if unknown else 'abstain'),'comparison_terminal_status')
    if stage=='S5':
        need(type(obj['decisions']) is list and len(obj['decisions'])<=2,'decision_cap')
        seen=set();targets=set()
        for row in obj['decisions']:
            need(type(row) is dict and set(row)=={'id','supersedes','decision','statement','evidence_ids','condition','uncertainty'},'decision_fields')
            need(type(row['id']) is str and re.fullmatch(r'H[1-9][0-9]*',row['id']) is not None and row['id'] not in seen,'revision_id');seen.add(row['id'])
            need(type(row['supersedes']) is str and row['supersedes'] in selected and row['supersedes'] not in targets and row['decision'] in ('keep','revise','withdraw','unknown'),'revision_target')
            targets.add(row['supersedes'])
            refs(row['evidence_ids'],set(feedback_ids),'feedback_refs',0 if row['decision']=='unknown' else 1)
            for k in ('statement','condition','uncertainty'):text(row[k],k,k=='uncertainty' or (k=='condition' and row['decision'] in ('withdraw','unknown')))
        need(targets==set(selected),'per_hypothesis_decisions_required')
    return obj


def namespace(task_hash,stage,version,local):return f'{task_hash}:{stage}:v{version}:{local}'


def register(stage,obj,task_hash,registry,version=1):
    rows=[]
    for row in obj['items']:
        uid=namespace(task_hash,stage,version,row['id']);need(uid not in registry,'immutable_id')
        record=dict(row,id=uid,local_id=row['id'],stage=stage,version=version);registry[uid]=record;rows.append(record)
    selected=[namespace(task_hash,stage,version,x) for x in obj.get('selected_ids',[])]
    decisions=[]
    for row in obj.get('decisions',[]):
        uid=namespace(task_hash,stage,version,row['id']);need(uid not in registry,'immutable_id')
        prior=registry[row['supersedes']]
        record=dict(row,id=uid,local_id=row['id'],stage=stage,version=version,obligation_ids=prior['obligation_ids'],behavior_ids=prior['behavior_ids'],source_ids=prior['source_ids'])
        registry[uid]=record;decisions.append(record)
    result=dict(status=obj['status'],reason=obj['reason'],items=rows,selected_ids=selected,decisions=decisions)
    if stage=='S3':result['comparisons']=obj['comparisons']
    return result
