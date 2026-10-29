"""One frozen binder-only development regression; code-only inference worker."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
V11=HERE.parent
ROOT=V11.parent.parent
sys.path.insert(0,str(ROOT))
OLD=ROOT/'python_bug_concepts/research/vr10_retrieval_diagnostic_20261029'
EVAL=ROOT/'python_bug_concepts/retrieval_v2/evaluation'
ARMS=('A','B','C','D')


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def write(p,x):
    with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')


def fingerprints():
    runtime=read(V11/'IMPLEMENTATION_FREEZE.json')['files']
    for n,v in runtime.items():
        if sha(ROOT/n)!=v:raise ValueError('Runtime freeze mismatch: '+n)
    paths=[HERE/'evaluate.py',HERE/'PREREG.md',V11/'IMPLEMENTATION_FREEZE.json',
           OLD/'MANIFEST.json',OLD/'run01/RETRIEVAL.json',OLD/'run01/RETRIEVAL_SEAL.json',
           OLD/'run01/SEMANTIC_REVIEW.json',OLD/'run01/REVIEW_KEY.json',
           OLD/'run01/GRADES_1.json',OLD/'run01/GRADES_2.json',
           EVAL/'gold.json',EVAL/'mechanism_sites.json']
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}


def prepare():
    if read(OLD/'run01/RETRIEVAL_SEAL.json')['sha256']!=sha(OLD/'run01/RETRIEVAL.json'):
        raise ValueError('Old prediction seal invalid')
    write(HERE/'FREEZE.json',{'files':fingerprints(),'arms':ARMS,
                            'variant':'G_operation_legacyquery_no_family_dedup','queries':28,
                            'kind':'development_regression_on_exposed_sources'})
    print('prepared',sha(HERE/'FREEZE.json'))


def verify(approval=True):
    if fingerprints()!=read(HERE/'FREEZE.json')['files']:raise ValueError('Evaluation inputs/source changed')
    if approval:
        a=read(HERE/'REVIEW_APPROVAL.json')
        if a.get('status')!='approved' or not a.get('reviewer') or a.get('must_fixes_remaining')!=[] or a.get('freeze_sha256')!=sha(HERE/'FREEZE.json'):
            raise ValueError('Missing/stale independent approval')


def worker():
    from python_bug_concepts.retrieval_v13.hybrid_engine import Retriever
    from python_bug_concepts.retrieval_v13.dense import Encoder
    codes=json.load(sys.stdin)
    if not isinstance(codes,list) or not all(isinstance(x,str) for x in codes):raise ValueError('Code strings only')
    encoder=Encoder();r=Retriever(encoder=encoder,binder_policy='operation',query_strategy='legacy',family_diversity=False)
    records=[]
    try:
        for code in codes:
            records.append({'query_sha256':hashlib.sha256(code.encode()).hexdigest(),
                            'arms':{a:r.search(code=code,arm=a,top_k=3) for a in ARMS}})
    finally:r.close()
    json.dump({'records':records,'encoder':{'identity':encoder.identity,'new_texts':encoder.calls,
              'cached_texts':encoder.hits,'truncated_texts':encoder.truncated}},sys.stdout)


def retrieve(out):
    verify();out.mkdir(exist_ok=False)
    write(out/'FREEZE.json',{'evaluation_freeze_sha256':sha(HERE/'FREEZE.json'),
                           'approval_sha256':sha(HERE/'REVIEW_APPROVAL.json')})
    queries=read(OLD/'MANIFEST.json')['queries']
    if len(queries)!=28:raise ValueError('Unexpected manifest size')
    response=subprocess.run([sys.executable,str(HERE/'evaluate.py'),'worker'],cwd=ROOT,
                            input=json.dumps([q['code'] for q in queries]),text=True,capture_output=True,check=True)
    packets=json.loads(response.stdout)
    if [r['query_sha256'] for r in packets['records']]!=[q['query_sha256'] for q in queries]:raise ValueError('Query mismatch')
    old={r['query_sha256']:r for r in read(OLD/'run01/RETRIEVAL.json')['records']}
    for row in packets['records']:
        for a in ARMS:
            if row['arms'][a]['candidates']!=old[row['query_sha256']]['arms'][a]['candidates']:
                raise ValueError('Binder-only candidate control differs')
    verify();write(out/'RETRIEVAL.json',packets)
    write(out/'RETRIEVAL_SEAL.json',{'sha256':sha(out/'RETRIEVAL.json'),'candidate_identity':'PASS'})
    print('sealed',out)


def binding(source_sha,cid,evidence):
    return digest([source_sha,cid,{k:evidence.get(k) for k in ('line','end_line','expression')}])


def hits(packet,code_sha):
    return {binding(code_sha,h['concept']['id'],h['evidence'][0]):h for h in packet['results'][:3] if h.get('evidence')}


def old_grades():
    queue={q['review_id']:q for q in read(OLD/'run01/SEMANTIC_REVIEW.json')}
    keys=read(OLD/'run01/REVIEW_KEY.json');known={}
    for n in (1,2):
        values=read(OLD/f'run01/GRADES_{n}.json')
        if isinstance(values,dict):values=values['grades']
        for g in values:
            rid=g['review_id'];q=queue[rid];refs=keys[rid]
            if len({r['query_sha256'] for r in refs})!=1:raise ValueError('Cross-query old grade')
            source_sha=hashlib.sha256(q['code'].encode()).hexdigest()
            if source_sha!=refs[0]['query_sha256']:raise ValueError('Old grade source mismatch')
            k=binding(source_sha,q['concept']['id'],q['source_sites'][0])
            if k in known and known[k]!=g:raise ValueError('Conflicting old grades')
            known[k]=g
    return known


def label_hit(packet,accepted,sites):
    if not accepted:return None
    return any(h['concept']['id'] in accepted and h.get('evidence') and h['evidence'][0]['line'] in
               {s['line'] for s in sites.get(h['concept']['id'],[])} for h in packet['results'][:3])


def score(out):
    verify()
    receipt=read(out/'FREEZE.json')
    if receipt!={'evaluation_freeze_sha256':sha(HERE/'FREEZE.json'),'approval_sha256':sha(HERE/'REVIEW_APPROVAL.json')}:
        raise ValueError('Run freeze mismatch')
    if read(out/'RETRIEVAL_SEAL.json')['sha256']!=sha(out/'RETRIEVAL.json'):raise ValueError('New seal mismatch')
    from python_bug_concepts.retrieval_v2.evaluate import check_gold_freeze
    check_gold_freeze()
    grades=old_grades();gold=read(EVAL/'gold.json')['tasks'];sites=read(EVAL/'mechanism_sites.json')['tasks']
    queries={q['query_sha256']:q for q in read(OLD/'MANIFEST.json')['queries']}
    old={r['query_sha256']:r for r in read(OLD/'run01/RETRIEVAL.json')['records']}
    records=[];review={};key={}
    for row in read(out/'RETRIEVAL.json')['records']:
        source_sha=row['query_sha256'];q=queries[source_sha];tid=q['task_id'];systems={}
        accepted=gold.get(tid,{}).get('concept_ids',[]) if q['kind']=='buggy' else []
        accepted_sites=sites.get(tid,{}) if q['kind']=='buggy' else {}
        for a in ARMS:
            before,after=old[source_sha]['arms'][a],row['arms'][a]
            l,g=hits(before,source_sha),hits(after,source_sha)
            grade_counts=lambda ids:{status:sum(k in grades and grades[k]['status']==status for k in ids)
                                      for status in ('supported_fault','contradicted','unknown_or_conditional')}
            systems[a]={'old_returned':len(l),'new_returned':len(g),'old_abstained':not l,'new_abstained':not g,
                        'old_known_firstsite_hit':label_hit(before,accepted,accepted_sites),
                        'new_known_firstsite_hit':label_hit(after,accepted,accepted_sites),
                        'removed_old_reviewed':grade_counts(l.keys()-g.keys()),
                        'retained_old_reviewed':grade_counts(l.keys()&g.keys()),
                        'new_selected_old_reviewed':grade_counts(g),
                        'new_ungraded_bindings':sum(k not in grades for k in g),
                        'source_supported_count':len(after['source_supported_hypotheses']),
                        'test_opportunity_count':len(after['test_opportunities'])}
            for k,h in g.items():
                if k in grades:continue
                anon=digest(['vr11-newreview',k])[:20]
                review[anon]={'review_id':anon,'code':q['code'],'concept':h['concept'],
                              'source_sites':[{n:h['evidence'][0].get(n) for n in ('line','end_line','expression')}],
                              'status':None,'source_quotes':[],'reason':None}
                key.setdefault(anon,[]).append({'task_id':tid,'kind':q['kind'],'arm':a,'binding_key':k})
        records.append({'task_id':tid,'kind':q['kind'],'arms':systems})
    summary={}
    for kind in sorted({r['kind'] for r in records}):
        summary[kind]={}
        for a in ARMS:
            vals=[r['arms'][a] for r in records if r['kind']==kind]
            summary[kind][a]={n:sum(v[n] or 0 for v in vals) for n in
                 ('old_returned','new_returned','old_abstained','new_abstained','old_known_firstsite_hit',
                  'new_known_firstsite_hit','new_ungraded_bindings','source_supported_count','test_opportunity_count')}
            summary[kind][a]['removed_old_reviewed']={s:sum(v['removed_old_reviewed'][s] for v in vals)
                 for s in ('supported_fault','contradicted','unknown_or_conditional')}
    verify()
    write(out/'RESULTS.json',{'summary':summary,'records':records,'candidate_identity':'PASS',
          'old_grade_usage':'development_informed_exact_source_and_binding_only','ungraded_queue':len(review),
          'limits':['No independent efficacy claim: old sources/grades informed this binder.',
                    'Incomplete labels; missing grade remains unknown.',
                    'No target execution, generated tests or downstream bug-detection measurement.']})
    write(out/'NEW_SEMANTIC_REVIEW.json',sorted(review.values(),key=lambda r:r['review_id']))
    write(out/'NEW_REVIEW_KEY.json',key)
    print(json.dumps(summary,indent=2))


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','verify','worker','retrieve','score']);p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='verify':verify();print('verified')
    elif a.action=='worker':worker()
    elif a.out is None:p.error('--out required')
    elif a.action=='retrieve':retrieve(a.out.resolve())
    else:score(a.out.resolve())


if __name__=='__main__':main()
