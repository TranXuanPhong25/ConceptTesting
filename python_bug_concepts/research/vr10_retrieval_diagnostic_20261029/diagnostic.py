"""Prepare, retrieve once after review, then score; never execute target programs."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO))
EVAL = ROOT / 'retrieval_v2/evaluation'
PRIOR = ROOT / 'retrieval_v6/evaluation_v6/iter06/RESULTS.json'
CANONICAL = Path.home() / '.cache/evalplus/HumanEvalPlus-v0.1.10.jsonl'
SEED = 'vr10-fixed-20261029/'
ARMS = ('V6', 'A', 'B', 'C', 'D')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashed(text):
    return hashlib.sha256(text.encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def implementation():
    paths = [ROOT / x for x in ('base.py', 'ingest.py')]
    paths += list((ROOT / 'data').glob('*'))
    for version in ('retrieval_v2', 'retrieval_v6', 'retrieval_v7'):
        folder = ROOT / version
        paths += list(folder.glob('*.py')) + list((folder / 'data').glob('*'))
    paths += [ROOT / 'retrieval_v7/MODEL_MANIFEST.json', HERE / 'PREREG.md', HERE / 'diagnostic.py']
    # Data and implementation only: no output-directory hashes or review circularity.
    return {str(p.relative_to(REPO)): sha(p) for p in sorted(set(paths)) if p.is_file()}


def old_signature(record, newer):
    if newer:
        return [(x['concept_id'], x.get('line')) for x in record['systems']['balanced']['selected']]
    old = record['baseline']
    evidence = {x['id']: x['sites'] for x in old.get('evidence', [])}
    return [(cid, evidence.get(cid, [{}])[0].get('line') if evidence.get(cid) else None)
            for cid in old['predictions']]


def prepare():
    from python_bug_concepts.retrieval_v2.evaluate import check_gold_freeze
    check_gold_freeze()
    smoke = ast.parse((ROOT/'retrieval_v7/engineering_smoke.py').read_text())
    fixture_sources = next(ast.literal_eval(n.value) for n in smoke.body if isinstance(n,ast.Assign)
                           and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in n.targets))
    overlay = read(ROOT / 'retrieval_v7/data/mechanism_evidence.json')['records']
    overlay_ids = {x['concept_id'] for x in overlay}
    tasks = {x['task_id']: x for x in read(EVAL / 'inputs.json')}
    prior = {x['task_id']: x for x in read(PRIOR)['records']}
    if tasks.keys() != prior.keys() or len(tasks) != 113:
        raise ValueError('Historical cohort mismatch')
    strata = {f'{change}_{overlay}': [] for change in ('changed', 'unchanged') for overlay in ('overlay', 'other')}
    for tid, row in prior.items():
        a, b = old_signature(row, False), old_signature(row, True)
        key = ('changed' if a != b else 'unchanged') + ('_overlay' if overlay_ids & {x[0] for x in a+b} else '_other')
        strata[key].append(tid)
    key = lambda tid: hashed(SEED + tid)
    selected = []
    for ids in strata.values():
        ids.sort(key=key)
        selected.extend(ids[:3])
    selected.extend(sorted(tasks.keys()-set(selected), key=key)[:12-len(selected)])
    selected.sort(key=key)
    refs = {x['task_id']: x for x in map(json.loads, CANONICAL.read_text().splitlines())}
    queries = []
    for tid in selected:
        for kind, code in [('buggy', tasks[tid]['code']),
                           ('canonical', refs[tid]['prompt'] + refs[tid]['canonical_solution'])]:
            queries.append({'task_id': tid, 'kind': kind, 'code': code, 'query_sha256': hashed(code),
                            'historical_split': tasks[tid]['split']})
    for name, code in fixture_sources.items():
        queries.append({'task_id': name, 'kind': 'preinspected_engineering_fixture',
                        'code': code, 'query_sha256': hashed(code)})
    if len({x['query_sha256'] for x in queries}) != len(queries):
        raise ValueError('Duplicate query sources')
    manifest = {'seed': SEED, 'tasks': selected,
                'strata': {k: {'available': len(v), 'selected': [t for t in v if t in selected]} for k,v in strata.items()},
                'queries': queries, 'arms': ARMS, 'candidate_budget': 12, 'top_k': 3,
                'label_usage': 'No label values used for sampling or query construction'}
    write_new(HERE / 'MANIFEST.json', manifest)
    frozen = {'implementation': implementation(), 'manifest_sha256': sha(HERE / 'MANIFEST.json'),
              'inputs': {str(p.relative_to(REPO)): sha(p) for p in [PRIOR, EVAL/'inputs.json', EVAL/'gold.json', EVAL/'mechanism_sites.json']},
              'canonical_cache_sha256': sha(CANONICAL)}
    write_new(HERE / 'FREEZE.json', frozen)
    print(json.dumps({'queries': len(queries), 'tasks': selected, 'strata': manifest['strata'],
                      'freeze_sha256': sha(HERE / 'FREEZE.json')}, indent=2))


def verify(approval=True):
    frozen = read(HERE / 'FREEZE.json')
    if implementation() != frozen['implementation'] or sha(HERE / 'MANIFEST.json') != frozen['manifest_sha256']:
        raise ValueError('Implementation/manifest changed after freeze')
    for name, digest in frozen['inputs'].items():
        if sha(REPO / name) != digest:
            raise ValueError('Frozen input changed: ' + name)
    if sha(CANONICAL) != frozen['canonical_cache_sha256']:
        raise ValueError('Canonical cache changed')
    if approval:
        receipt = read(HERE / 'REVIEW_APPROVAL.json')
        if (receipt.get('status') != 'approved' or receipt.get('must_fixes_remaining') != []
                or not receipt.get('reviewer') or receipt.get('freeze_sha256') != sha(HERE/'FREEZE.json')
                or receipt.get('prereg_sha256') != sha(HERE/'PREREG.md')):
            raise ValueError('Independent review approval missing or stale')
    return frozen


def worker():
    # No ID/label/reference arguments or manifest reads in this entrypoint.
    from python_bug_concepts.retrieval_v6.engine import search
    from python_bug_concepts.retrieval_v7.dense import Encoder
    from python_bug_concepts.retrieval_v7.hybrid_engine import Retriever
    codes = json.load(sys.stdin)
    if not isinstance(codes, list) or not all(isinstance(x, str) for x in codes):
        raise ValueError('Worker accepts code strings only')
    encoder = Encoder()
    retriever = Retriever(encoder=encoder)
    records = []
    try:
        for code in codes:
            packets = {'V6': search(code=code, top_k=12, policy='balanced', include_facts=False)}
            packets.update({arm: retriever.search(code=code, arm=arm, top_k=3) for arm in ARMS[1:]})
            records.append({'query_sha256': hashed(code), 'arms': packets})
    finally:
        retriever.close()
    json.dump({'records': records, 'encoder': {'identity': encoder.identity,
              'new_texts': encoder.calls, 'cached_texts': encoder.hits, 'truncated_texts': encoder.truncated}}, sys.stdout)


def retrieve(out):
    verify()
    out.mkdir(parents=False, exist_ok=False)
    write_new(out/'FREEZE.json', {'freeze_sha256': sha(HERE/'FREEZE.json'), 'approval_sha256': sha(HERE/'REVIEW_APPROVAL.json')})
    queries = read(HERE/'MANIFEST.json')['queries']
    result = subprocess.run([sys.executable, str(HERE/'diagnostic.py'), 'worker'],
                            input=json.dumps([q['code'] for q in queries]), text=True,
                            capture_output=True, cwd=REPO, check=True)
    packets = json.loads(result.stdout)
    if [x['query_sha256'] for x in packets['records']] != [x['query_sha256'] for x in queries]:
        raise ValueError('Worker query mapping differs')
    verify()
    write_new(out/'RETRIEVAL.json', packets)
    write_new(out/'RETRIEVAL_SEAL.json', {'sha256': sha(out/'RETRIEVAL.json'),
                                       'kind': 'all retrieval frozen before gold scoring'})
    print('Retrieval sealed; run score separately:', out)


def metrics(packet, arm, accepted, sites, families):
    hits = packet['results'][:3]
    shortlist = ([x['concept']['id'] for x in packet['results'][:12]] if arm == 'V6'
                 else [x['concept_id'] for x in packet['candidates'][:12]])
    support = [x.get('mechanism_support', x.get('ranking', {}).get('semantic_support', {})) or {} for x in hits]
    return {'shortlist': shortlist, 'top3': [x['concept']['id'] for x in hits],
            'top3_bindings': [json.dumps([x['concept']['id'],
                {k:x.get('evidence',[{}])[0].get(k) for k in ('line','end_line','expression')}],sort_keys=True) for x in hits],
            'known_concept_hit_at12': bool(set(shortlist) & set(accepted)) if accepted else None,
            'known_family_hit_at12': bool({families.get(x,x) for x in shortlist} & {families.get(x,x) for x in accepted}) if accepted else None,
            'known_first_site_hit_at3': any(h['concept']['id'] in accepted and h.get('evidence') and h['evidence'][0]['line'] in
                {s['line'] for s in sites.get(h['concept']['id'], [])} for h in hits) if accepted else None,
            'returned': len(hits), 'recognized_tier_ge2': sum(x.get('tier',0)>=2 for x in support),
            'support_other_or_unknown': sum(x.get('tier',0)<2 for x in support),
            'shortlist_kind': 'post_policy_v6' if arm=='V6' else 'pre_binding_v7'}


def score(out):
    verify()
    receipt = read(out/'FREEZE.json')
    if receipt['freeze_sha256'] != sha(HERE/'FREEZE.json') or receipt['approval_sha256'] != sha(HERE/'REVIEW_APPROVAL.json'):
        raise ValueError('Run receipt differs')
    if read(out/'RETRIEVAL_SEAL.json')['sha256'] != sha(out/'RETRIEVAL.json'):
        raise ValueError('Unsealed retrieval')
    from python_bug_concepts.retrieval_v2.evaluate import check_gold_freeze
    check_gold_freeze()
    gold = read(EVAL/'gold.json')['tasks']
    site_gold = read(EVAL/'mechanism_sites.json')['tasks']
    families = {x['concept_id']: x['family'] for x in read(ROOT/'retrieval_v7/data/mechanism_evidence.json')['records']}
    queries = {x['query_sha256']: x for x in read(HERE/'MANIFEST.json')['queries']}
    records, review, keymap = [], {}, {}
    for record in read(out/'RETRIEVAL.json')['records']:
        q = queries[record['query_sha256']]
        tid = q['task_id']
        accepted = gold.get(tid, {}).get('concept_ids', []) if q['kind']=='buggy' else []
        sites = site_gold.get(tid, {}) if q['kind']=='buggy' else {}
        systems = {a: metrics(p,a,accepted,sites,families) for a,p in record['arms'].items()}
        shifts = {}
        for a,b in [('A','B'),('C','D')]:
            shifts[b+'-'+a] = {k: {'added': sorted(set(systems[b][k])-set(systems[a][k])),
                                  'removed': sorted(set(systems[a][k])-set(systems[b][k]))} for k in ['shortlist','top3','top3_bindings']}
        records.append({'task_id':tid, 'kind':q['kind'], 'labelled':bool(accepted), 'arms':systems, 'paired_shifts':shifts})
        for arm,packet in record['arms'].items():
            for rank,hit in enumerate(packet['results'][:3],1):
                # Deduplicated union: method-specific explanations, scores, tier and
                # recognition metadata must not leak into the semantic review queue.
                evidence = [{k:row.get(k) for k in ['line','end_line','expression','span']}
                            for row in hit.get('evidence',[])[:1]]
                token = hashed(SEED+q['query_sha256']+hit['concept']['id']+json.dumps(evidence,sort_keys=True))[:20]
                review[token] = {'review_id':token, 'code':q['code'], 'concept':hit['concept'],
                                 'source_sites':evidence, 'judgment':None, 'source_quotes':[],
                                 'useful_conditional_hypothesis':None, 'reason':None}
                keymap.setdefault(token,[]).append({'task_id':tid,'kind':q['kind'],'arm':arm,
                                                   'rank':rank,'query_sha256':q['query_sha256']})
    summary = {a: {m: sum(r['arms'][a][m] is True for r in records if r['kind']=='buggy')
                   for m in ['known_concept_hit_at12','known_family_hit_at12','known_first_site_hit_at3']} for a in ARMS}
    result = {'summary_buggy_only':summary,'query_counts':dict(Counter(q['kind'] for q in queries.values())),
              'records':records,'go_decision':'PENDING independent applicability review',
              'limits':['Incomplete gold: unmatched is unknown, no precision claim.',
                        'Post-policy V6 shortlist differs from pre-binding V7 shortlist.',
                        'Previously exposed development sources and preinspected fixtures.',
                        'No target execution or downstream detection measurement.']}
    verify()
    write_new(out/'RESULTS.json',result)
    write_new(out/'SEMANTIC_REVIEW.json',sorted(review.values(),key=lambda x:x['review_id']))
    write_new(out/'REVIEW_KEY.json',keymap)
    print(json.dumps(summary,indent=2))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['prepare','verify','worker','retrieve','score'])
    p.add_argument('--out',type=Path)
    args=p.parse_args()
    if args.action=='prepare': prepare()
    elif args.action=='verify': verify(); print('freeze and review verified')
    elif args.action=='worker': worker()
    elif args.out is None: p.error('--out required')
    elif args.action=='retrieve': retrieve(args.out.resolve())
    else: score(args.out.resolve())


if __name__=='__main__':
    main()
