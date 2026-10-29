"""Source-binding grade join after frozen new judgments; development analysis only."""
from collections import Counter
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('vr11_eval',HERE/'evaluate.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)


def main():
    out=HERE/'run01';e.verify()
    oldgrades=e.old_grades();newqueue={x['review_id']:x for x in e.read(out/'NEW_SEMANTIC_REVIEW.json')}
    raw=e.read(out/'GRADES_NEW.json');newgrades=raw['grades'] if isinstance(raw,dict) else raw
    keys=e.read(out/'NEW_REVIEW_KEY.json')
    if len(newgrades)!=len(newqueue) or {x['review_id'] for x in newgrades}!=set(newqueue):raise ValueError('Incomplete review')
    allgrades=dict(oldgrades)
    for g in newgrades:
        if not all(q in newqueue[g['review_id']]['code'] for q in g['source_quotes']):raise ValueError('Review quote mismatch')
        bindings={x['binding_key'] for x in keys[g['review_id']]}
        if len(bindings)!=1:raise ValueError('Mixed binding key')
        key=next(iter(bindings))
        if key in allgrades:raise ValueError('Do not overwrite old judgments')
        allgrades[key]=g
    queries={q['query_sha256']:q for q in e.read(e.OLD/'MANIFEST.json')['queries']}
    old={q['query_sha256']:q for q in e.read(e.OLD/'run01/RETRIEVAL.json')['records']}
    summary={}
    for kind in ('buggy','canonical','preinspected_engineering_fixture'):
        summary[kind]={}
        for arm in e.ARMS:
            counts={name:Counter() for name in ('old','new')};coverage={name:0 for name in counts}
            added=Counter();removed=Counter()
            for r in e.read(out/'RETRIEVAL.json')['records']:
                code=r['query_sha256']
                if queries[code]['kind']!=kind:continue
                before=e.hits(old[code]['arms'][arm],code);after=e.hits(r['arms'][arm],code)
                for name,bs in [('old',before),('new',after)]:
                    for key in bs:counts[name][allgrades[key]['status'] if key in allgrades else 'ungraded']+=1
                    coverage[name]+=bool(bs)
                for key in after.keys()-before.keys():added[allgrades[key]['status'] if key in allgrades else 'ungraded']+=1
                for key in before.keys()-after.keys():removed[allgrades[key]['status'] if key in allgrades else 'ungraded']+=1
            summary[kind][arm]={'old':dict(counts['old']),'new':dict(counts['new']),
                                'queries_returned':coverage,'added':dict(added),'removed':dict(removed)}
    result={'summary':summary,'old_judgments':len(oldgrades),'new_judgments':len(newgrades),
            'status':'development_regression_no_independent_efficacy_claim',
            'new_grade_sha256':e.sha(out/'GRADES_NEW.json'),
            'limitation':'Old grades informed development; lower returns and annotated-site losses must be reported.'}
    e.write(out/'REVIEW_SUMMARY.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
