"""Post-hoc diagnostics: native claim audit and fixed generic ranking variants."""
import hashlib
import json
from pathlib import Path
from ..client import atomic
from ..run import tasks, OLD
from ..prompts import parse_retrieval
from ..grade_utility import equal
from ...retrieval_v2.grade_witnesses import isolated
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'out/run_20261026'

from ...retrieval_v4.engine import parse_recovered, interleave

def recover(record, code):
    rows, error, recovered = parse_recovered(record['response'], code)
    return rows, recovered

def fuse(qwen, baseline):
    return interleave(qwen, baseline)

def ranking():
    gold = json.loads((OLD/'gold.json').read_text())['tasks']
    sites = json.loads((OLD/'mechanism_sites.json').read_text())['tasks']
    records = []
    for task in tasks():
        tid = task['task_id']
        row = json.loads((OUT/'retrieved'/f"{tid.replace('/', '_')}.json").read_text())
        recovered, changed = recover(row,task['code'])
        variants = {'v2':row['baseline'], 'v3_original':row['selected'], 'v3_deduplicated':recovered, 'fusion':fuse(recovered,row['baseline'])}
        metrics = {}
        for name, selected in variants.items():
            positives = [r['concept_id'] in gold[tid]['concept_ids'] for r in selected]
            sitehits = [r['concept_id'] in gold[tid]['concept_ids'] and r['line'] in {s['line'] for s in sites.get(tid,{}).get(r['concept_id'],[])} for r in selected]
            metrics[name] = {'selected':selected,'family_hit':any(positives),'site_hit':any(sitehits),'positive_cards':sum(positives),'returned_cards':len(selected), 'top1':bool(positives and positives[0])}
        records.append({'task_id':tid,'split':task['split'],'duplicate_recovered':changed,'systems':metrics})
    summary = {}
    for name in variants:
        rows = [r['systems'][name] for r in records]
        n = sum(r['returned_cards'] for r in rows)
        summary[name] = {'family_hit_at_3':sum(r['family_hit'] for r in rows), 'site_hit_at_3':sum(r['site_hit'] for r in rows),'hit_at_1':sum(r['top1'] for r in rows),'returned_cards':n,'frozen_label_precision':sum(r['positive_cards'] for r in rows)/n if n else None,'splits':{split:{'tasks':sum(r['split']==split for r in records), 'site_hit_at_3':sum(r['systems'][name]['site_hit'] for r in records if r['split']==split)} for split in ['development','audit']}}
    atomic(HERE/'RANKING.json',{'post_hoc':True,'not_independent_holdout':True,'tasks':113,'duplicate_recovered':sum(r['duplicate_recovered'] for r in records),'summary':summary,'records':records})
    return summary

CASES = [
 (12,'py.tie-break-selection',[['a','b']], 'Qwen claims max retains the last tied maximum; Python retains the first. Lowercasing changes neither input in this case.'),
 (54,'py.set-loses-multiplicity',['aab','ab'], 'False contract: same character sets may have different multiplicities; public examples explicitly permit this.'),
 (66,'py.index-out-of-bounds',['a'], 'False control flow: every recursive invocation checks the empty-string guard before indexing.'),
 (68,'py.first-occurrence-position',[[4,2,2]], 'False mechanism: index(min_value) returns the first occurrence required by the specification. A separate first-even fallback bug exists.'),
 (68,'py.empty-reduction-domain',[[1,3,5]], 'False prediction: all-odd input reaches the final empty-list return.'),
 (71,'py.branch-boundary-contract',[1,2,3], 'False oracle: a degenerate triangle is invalid under the strict triangle-inequality contract.'),
 (5,'py.index-out-of-bounds',[[],9], 'False bounds claim: two inserted sentinels and range(len-1) keep every adjacent index in bounds.'),
 (48,'py.empty-singleton-shortcut',['a'], 'False requirement: a single-character string is a palindrome; no minimum length of two is specified.'),
 (16,'py.unicode-text-byte-domain',['é'], 'Positive control: encoding Unicode before taking a set counts bytes rather than characters.'),
 (35,'py.extremum-initial-sentinel',[[-5,-2]], 'Positive control: zero initialization hides a negative maximum.'),
 (140,'py.fixed-chunk-run',['a    b'], 'Positive control: fixed triple replacement leaves a residual underscore in a four-space run.'),
 (152,'py.absolute-difference',[[1],[3]], 'Positive control: signed subtraction violates the required absolute score difference.'),
]

def audit():
    refs = {r['task_id']:{k:r[k] for k in ['entry_point','prompt','canonical_solution','contract','atol']} for r in map(json.loads,(Path.home()/'.cache/evalplus/HumanEvalPlus-v0.1.10.jsonl').read_text().splitlines())}
    sources = {r['task_id']:r for r in tasks()}
    quality = {r['task_id']:r for r in json.loads((OUT/'QUALITY_TASKS.json').read_text())}
    results = []
    for number,cid,args,note in CASES:
        tid = f'HumanEval/{number}'
        ref = refs[tid]
        code = ref['prompt']+ref['canonical_solution']
        job = {'entry':ref['entry_point'],'args':args}
        validity = isolated({**job,'mode':'validity','source':code,'contract':ref['contract']})
        expected = isolated({**job,'mode':'value','source':code})
        actual = isolated({**job,'mode':'value','source':sources[tid]['code']})
        selected = quality[tid]['systems']['v3']['selected']
        match = next((r for r in selected if r['concept_id']==cid),None)
        results.append({'task_id':tid,'concept_id':cid,'args':args,'review':note,'selected_response':match,'validity':validity,'reference':expected,'put':actual,'values_equal':expected.get('status')==actual.get('status')=='ok' and equal(expected.get('value'),actual.get('value'),ref['atol'])})
    atomic(HERE/'NATIVE_CLAIM_AUDIT.json', {'sampling':'purposive error cases and positive controls; not a precision estimate','hidden_tests_used':False,'results':results})
    return [{'task':r['task_id'],'valid':r['validity'].get('value'),'equal':r['values_equal'],'grade':(r['selected_response'] or {}).get('judge_card')} for r in results]

if __name__=='__main__':
    print(json.dumps({'ranking':ranking(),'native_audit':audit()},indent=2))
