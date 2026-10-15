"""Spec-only template proposals and source bindings; all predicates compiled by tool."""
import json
import re
from . import templates


def parse(raw,field):
    raw=re.sub(r'^```(?:json)?\s*\n|\n```\s*$','',raw.strip())
    data=json.loads(raw)
    if type(data) is not dict or type(data.get(field)) is not list or any(type(r) is not dict for r in data[field]):
        raise ValueError('expected_'+field+'_object_list')
    return data[field]


def units(ir):
    doc=ir['docstring'];end=doc.find('>>>')
    text=doc if end<0 else doc[:end]
    out=[]
    for m in re.finditer(r'\S[^\n]*(?:\n[ \t]*[^\s\n][^\n]*)*',text):
        quote=m.group(0)
        if len(quote.strip())<8 or quote.strip().lower().rstrip(':') in ('example','examples'):continue
        out.append(dict(id='S'+str(len(out)),span=[m.start(),m.end()],quote=quote,
                        text=' '.join(quote.split()),unit_kind='paragraph_not_atomic_obligation'))
    return out


def proposals(raw,ir,cap=6):
    source={u['id']:u for u in units(ir)};out=[];rejections=[]
    for i,row in enumerate(parse(raw,'proposals')[:cap]):
        try:
            evidence=row.get('evidence')
            if type(evidence) is not list or not evidence or any(type(s) is not str or s not in source for s in evidence):
                raise ValueError('unknown_spec_unit')
            model=templates.normalize(row,len(ir['parameters']))
            out.append(dict(id='P'+str(len(out)),model=model,evidence=[source[s] for s in evidence],
                            entailment='candidate_spec_interpretation_not_proof'))
        except (KeyError,TypeError,ValueError) as exc:rejections.append(dict(index=i,reason=str(exc)))
    return out,rejections


def bindings(raw,ir,proposals,cap=6):
    by_id={p['id']:p for p in proposals};blocks={b['id']:b for b in ir['blocks']};out=[];reject=[]
    for i,row in enumerate(parse(raw,'bindings')[:cap]):
        try:
            if type(row.get('proposal')) is not str or row['proposal'] not in by_id:raise ValueError('unknown_proposal')
            p=by_id[row['proposal']];faults={f['id']:f for f in p['faults']}
            if type(row.get('fault')) is not str or row['fault'] not in faults:raise ValueError('unknown_semantic_fault')
            anchors=row.get('blocks')
            if type(anchors) is not list or not anchors or any(type(b) is not str or b not in blocks for b in anchors):raise ValueError('unknown_source_block')
            rationale=row.get('reasoning')
            fields=('code_claim','path_guarantees','gap')
            if type(rationale) is not dict or any(type(rationale.get(k)) is not str or not 8<=len(rationale[k])<=1000 for k in fields):
                raise ValueError('missing_reasoning')
            out.append(dict(id='C'+str(len(out)),proposal_id=p['id'],model=p['model'],evidence=p['evidence'],
                            fault=faults[row['fault']],block_ids=anchors,
                            reasoning=dict(code_claim=rationale['code_claim'],path_guarantees=rationale['path_guarantees'],
                                unresolved_obligation=rationale['gap'],required_condition=templates.CATALOG[p['model']['template']],
                                predicted_effect='original candidate spec model differs from '+faults[row['fault']]['description']),
                            semantic_status='candidate_interpretation; source binding is not entailment proof'))
        except (KeyError,TypeError,ValueError) as exc:reject.append(dict(index=i,reason=str(exc)))
    return out,reject


def messages(stage,task,prepared,accepted=None):
    ir=prepared['ir']
    if stage=='spec':
        source=[dict(id=u['id'],text=u['text']) for u in units(ir)]
        text=('Choose reusable semantic requirement templates justified by the SPEC ONLY. Return ONLY JSON '
              '{"proposals":[{"template":"REDUCE","argument":0,"predicate":"negative",'
              '"aggregate":"count","evidence":["S0"]}]}. This is a TOY format for counting negative values, '
              'not a suggestion for this task. At most 6 proposals; omit unsupported algorithms. '
              'Use only listed fields/enums. No expression trees, Python, function names or invented operators. '
              'argument/other_argument are zero-based positional input indexes; component optionally selects an output tuple item. '
              'Parameters not supplied use the declared defaults. Evidence must be actual SPEC unit IDs. '
              'Do not propose a full task algorithm if a narrower reusable template suffices.\n'
              'TEMPLATE SEMANTICS:\n'+json.dumps(templates.CATALOG)+'\nFIELDS AND DEFAULTS:\n'+json.dumps(templates.DEFAULTS)+
              '\nFILTER PREDICATES:\n'+json.dumps(templates.PREDICATES)+
              '\nPARAMETER NAMES:\n'+json.dumps(ir['parameters'])+'\nSPEC UNITS:\n'+json.dumps(source))
    else:
        choices=[dict(id=p['id'],model=p['model'],evidence=p['evidence'],faults=[{k:f[k] for k in ('id','description','change')} for f in p['faults']]) for p in accepted]
        text=('Bind at most 6 candidate concepts to actual source blocks and choose a plausible semantic fault. '
              'Return ONLY JSON {"bindings":[{"proposal":"P0","fault":"F0","blocks":["actual block ID"],'
              '"reasoning":{"code_claim":"operation and state observed in source",'
              '"path_guarantees":"what the guards actually ensure",'
              '"gap":"missing condition or plausible semantic misunderstanding"}}]}. '
              'Use only actual IDs from choices/behavior. If no supported choice, return {"bindings":[]}. '
              'Do not write a discriminator or Python; the tool compares the candidate model and fault model. '
              'A semantic alternative is not assumed to be correct. Anchor the concern to the current flow.\n'
              'CHOICES:\n'+json.dumps(choices)+'\nSOURCE:\n'+task['put']+
              '\nBEHAVIOR:\n'+prepared['pseudocode'])
    return [dict(role='system',content='Return exactly one JSON object. Use the provided template/ID vocabulary.'),dict(role='user',content=text)]
