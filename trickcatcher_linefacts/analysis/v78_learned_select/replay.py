"""Original cached-data diagnostic; does not execute PUTs, references, or LLMs."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys
import warnings

import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v34_ftplacebo.chain_inputs import parse_literal, typed_value
from trickcatcher_linefacts.pipelines.v34_ftplacebo.source_view import prepare

BASE = REPO / 'trickcatcher_linefacts/out/analysis'
SEED = 20261026
ARMS = ('spec+code', 'spec-only')
GENERATED = ('class', 'boundary', 'spec_range', 'value_biased')
PINNED = {
    'v44_concept_matrix/matrix.json': '3fe4296b8e7a8405be9892db1564d5a8b1e5897054e4cb0cc9cc2a6b272a3faa',
    'v44_concept_matrix/instances.json': 'e8a890a7682bcdab4047c06186c56974f53bd736e923e78d68b0825cc22581ce',
    'v47_concept_select/prepared.json': '5c829119ce1cb04e968f885339132e7a94b68dacb68d09e1999f6d077f82a696',
    'v47_concept_select/score.json': 'e22d87677fb5d1efbf32ffadd944120696f920f495bd50e2d0af87ddec1f5826',
}
SPEC_WORDS = {
    'order': r'sort|order|increas|decreas|ascending|descending',
    'duplicate': r'duplicat|distinct|unique|repeat|equal',
    'boundary': r'bound|at least|at most|empty|minimum|maximum|less than|greater than',
    'numeric': r'integer|number|float|digit|sum|product|divis|precision',
    'string': r'string|character|letter|substring|palindrome',
    'graph': r'graph|edge|vertex|vertices|node|path|tree',
    'state': r'state|operation|update|insert|delete|remove|query',
    'optimization': r'minim|maxim|optimal|largest|smallest|shortest|longest',
    'membership': r'contain|belong|present|member|subset',
    'counting': r'count|frequency|number of|how many',
    'parity': r'even|odd|parity|modulo|remainder',
    'sequence': r'sequence|array|list|consecutive|adjacent|subarray|subsequence',
}
AST_TYPES = ('For', 'While', 'If', 'Compare', 'BoolOp', 'BinOp', 'Subscript', 'ListComp', 'Dict', 'Set', 'Return', 'Call')
CALLS = ('sorted', 'sort', 'set', 'dict', 'sum', 'min', 'max', 'len', 'range')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class Cache:
    def __init__(self):
        self.hashes = {}

    def read(self, path):
        path = Path(path)
        raw = path.read_bytes()  # missing data is fatal; there is no execution fallback
        rel, fingerprint = str(path.relative_to(REPO)), hashlib.sha256(raw).hexdigest()
        if rel in self.hashes and self.hashes[rel] != fingerprint:
            raise ValueError('parent_changed_between_reads:' + rel)
        self.hashes[rel] = fingerprint
        return json.loads(raw)

    def verify(self):
        for rel, h in self.hashes.items():
            if sha(REPO / rel) != h:
                raise ValueError('parent_changed:' + rel)


def same_typed(x, y):
    """Historical v34 equality: exact type tags, floats isclose(1e-6, 1e-9)."""
    if type(x) is tuple and type(y) is tuple and len(x) == len(y) == 2 and type(x[0]) is str and type(y[0]) is str:
        if x[0] != y[0]:
            return False
        if x[0] == 'float':
            return math.isclose(x[1], y[1], rel_tol=1e-6, abs_tol=1e-9)
        if type(x[1]) is tuple and type(y[1]) is tuple:
            return len(x[1]) == len(y[1]) and all(same_typed(a, b) for a, b in zip(x[1], y[1]))
        return x[1] == y[1]
    if type(x) is tuple and type(y) is tuple:
        return len(x) == len(y) and all(same_typed(a, b) for a, b in zip(x, y))
    return x == y


def observation(outcome, *, official=False):
    if official:
        status = outcome.get('status')
        if status == 'exception':
            return ('exception', outcome['exception_type'])
        if status != 'ok' or outcome.get('output_repr') is None:
            return None
        outcome = ['ok', outcome['output_repr']]
    if not outcome:
        return None
    if outcome[0] == 'exception':
        return ('exception', outcome[1])
    if outcome[0] != 'ok':
        return None
    try:
        return ('ok', typed_value(parse_literal(outcome[1], output=True)))
    except (ValueError, TypeError, SyntaxError, RecursionError):
        return None


def same(a, b):
    return a[0] == b[0] and (a[1] == b[1] if a[0] == 'exception' else same_typed(a[1], b[1]))


def batch(cache, directory):
    job = cache.read(directory / 'job.json')
    result = cache.read(directory / 'result.json')
    assert set(job['sources']) == set(result), 'batch source/result keys'
    assert all(len(v) == len(job['inputs']) for v in result.values()), 'batch length'
    return job, result


def batch_exposures(pjob, pres, rjob, rres):
    assert pjob['inputs'] == rjob['inputs'] and pjob['entry'] == rjob['entry']
    out = set()
    for lit, p, c, r in zip(pjob['inputs'], pres['put'], rres['contract'], rres['ref']):
        a, b = observation(p), observation(r)
        if c[0] == 'ok' and a is not None and b is not None and not same(a, b):
            out.add(lit)
    return out


def official_read(cache, source, entry, lit):
    directory = BASE / 'v41_iorel/official' / digest(dict(source=source, entry=entry, input=lit))
    job = cache.read(directory / 'job.json')
    assert job['source'] == source and job['entry'] == entry and job['input_repr'] == lit
    assert job['mode'] == 'ordinary' and job['valid_code'] is None
    return cache.read(directory / 'result.json')


def normalize(item):
    kind = item['kind']
    m = re.match(r'arg(\d+):(.*)', item['instance'])
    subtype = m.group(2) if m else kind
    return kind + ':' + subtype, int(m.group(1)) if m else -1


def context_features(public, arm):
    context = {'spec:' + k: float(bool(re.search(p, public['spec'].lower()))) for k, p in SPEC_WORDS.items()}
    if arm == 'spec-only':
        return context
    tree = ast.parse(public['code'])
    nodes = list(ast.walk(tree))
    counts = Counter(type(n).__name__ for n in nodes)
    context.update({'ast:' + k: math.log1p(min(counts[k], 20)) / math.log(21) for k in AST_TYPES})
    calls = [n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else ''
             for n in nodes if isinstance(n, ast.Call)]
    context.update({'call:' + k: float(k in calls) for k in CALLS})
    context['recursion'] = float(public['entry'] in calls)
    context['nested_loop'] = float(any(isinstance(n, (ast.For, ast.While)) and
        any(isinstance(c, (ast.For, ast.While)) for child in n.body for c in ast.walk(child)) for n in nodes))
    return context


def candidate_features(item, bundle, context=None):
    subtype, arg = normalize(item)
    base = {'kind=' + item['kind']: 1., 'subtype=' + subtype: 1., 'arg=' + str(arg): 1.,
            'bundle_size': math.log1p(len(set(bundle))) / math.log(33)}
    base.update({'operator=' + op: float(op in item['text']) for op in ('==', '!=', '<', '>', '+', '-', '*', '/')})
    for name, value in (context or {}).items():
        if value:
            base['kind=' + item['kind'] + '*' + name] = value
            base['subtype=' + subtype + '*' + name] = value
    return {k: v for k, v in base.items() if v}


def load_material(cache):
    for rel, expected in PINNED.items():
        assert sha(BASE / rel) == expected, 'frozen artifact mismatch:' + rel
        cache.read(BASE / rel)
    prepared = cache.read(BASE / 'v47_concept_select/prepared.json')
    frozen = cache.read(BASE / 'v47_concept_select/score.json')
    assert len(prepared) == len(frozen['rows']) == 33
    historical = {r['case_id']: r for r in frozen['rows']}
    pool_metadata = {r['case_id']: r for r in cache.read(BASE / 'v41_iorel/ceiling.json')['rows']}
    public, batches = {}, {}
    for cid, p in prepared.items():
        assert cid == p['case_id'] and not p.get('error') and not p['errors']
        root = BASE / 'v41_iorel/cases' / cid
        pj, pr = batch(cache, root / 'put')
        rj, rr = batch(cache, root / 'ref')
        assert hashlib.sha256(json.dumps(pj['inputs']).encode()).hexdigest() == pool_metadata[cid]['inputs_sha256'], 'v41 pool fingerprint'
        assert set(pj['sources']) == {'put'} and set(rj['sources']) == {'contract', 'ref'}
        assert pj['entry'] == rj['entry'] and pj['inputs'] == rj['inputs']
        view = prepare(pj['sources']['put'], pj['entry'])
        public[cid] = dict(spec=view['spec'], code=view['source_masked'], entry=pj['entry'])
        batches[cid] = (pj, pr, rj, rr)
    spec_hashes = [digest(p['spec']) for p in public.values()]
    assert all(p['spec'].strip() for p in public.values()), 'empty spec cannot identify a problem'
    assert len(set(spec_hashes)) == 24, 'unexpected problem groups require prospective review'
    # Public-only features are built before evaluator-only exposure reconstruction.
    features = {arm: {cid: [candidate_features(it, p['kinds'][it['kind']][it['instance']], context_features(public[cid], arm))
                            for it in p['menus'][arm]['items']] for cid, p in prepared.items()} for arm in ARMS}
    bare = {arm: {cid: [candidate_features(it, p['kinds'][it['kind']][it['instance']])
                        for it in p['menus'][arm]['items']] for cid, p in prepared.items()} for arm in ARMS}
    tasks = {arm: [] for arm in ARMS}
    for cid, p in prepared.items():
        pj, pr, rj, rr = batches[cid]
        exposing = batch_exposures(pj, pr, rj, rr)
        pool = set(pj['inputs'])
        for kind in GENERATED:
            expected_new = sorted(set(p['universes'][kind]) - pool)
            if not expected_new:
                continue
            root = BASE / 'v47_concept_select/cases' / cid / 'generated' / kind
            gj, gr = batch(cache, root / 'put')
            hj, hr = batch(cache, root / 'ref')
            assert gj['inputs'] == expected_new and gj['sources'] == pj['sources'] and hj['sources'] == rj['sources']
            exposing |= batch_exposures(gj, gr, hj, hr)
        memo = {}

        def confirmed(lit):
            if lit not in memo:
                c = official_read(cache, rj['sources']['contract'], pj['entry'], lit)
                if c['status'] != 'ok':
                    memo[lit] = False
                else:
                    a = observation(official_read(cache, pj['sources']['put'], pj['entry'], lit), official=True)
                    b = observation(official_read(cache, rj['sources']['ref'], pj['entry'], lit), official=True)
                    memo[lit] = a is not None and b is not None and not same(a, b)
            return memo[lit]

        labels = {(k, n): int(any(confirmed(l) for l in shown if l in exposing)) for k, d in p['kinds'].items() for n, shown in d.items()}
        for arm in ARMS:
            items = p['menus'][arm]['items']
            assert len({it['id'] for it in items}) == len(items) >= 3
            ys = [labels[(it['kind'], it['instance'])] for it in items]
            bundles = [p['kinds'][it['kind']][it['instance']] for it in items]
            assert all(0 < len(b) <= 32 for b in bundles)
            expected = historical[cid][arm]
            assert len(items) == expected['menu'] and sum(ys) == expected['menu_covering']
            byid = {it['id']: y for it, y in zip(items, ys)}
            assert bool(any(byid[i] for i in expected['picks'])) == expected['covered3']
            assert bool(any(ys[:3])) == expected['first3'] and bool(any(ys)) == expected['perfect']
            metrics = triple_table(ys, bundles, items)
            assert abs(metrics['uniform']['reach'] - expected['random3']) <= 0.000051
            assert abs(metrics['per_kind']['reach'] - expected['per_kind_random3']) <= 0.000051
            tasks[arm].append(dict(cid=cid, group=digest(public[cid]['spec']), items=items, y=ys, bundles=bundles, x=features[arm][cid], bare=bare[arm][cid],
                                   historical=expected, triples=metrics))
    assert sum(len(t['items']) for t in tasks['spec+code']) == 841
    assert sum(len(t['items']) for t in tasks['spec-only']) == 500
    return tasks


def triple_table(y, bundles, items):
    universe = {v: j for j, v in enumerate(sorted(set().union(*map(set, bundles))))}
    masks = [sum(1 << universe[v] for v in set(b)) for b in bundles]
    triples, counts, hits = [], Counter(), Counter()
    kinds = sorted({it['kind'] for it in items})
    kind_counts = Counter(it['kind'] for it in items)
    perkind = defaultdict(float)
    denom = math.comb(len(kinds), min(3, len(kinds)))
    for ids in itertools.combinations(range(len(y)), 3):
        a, b, c = ids
        cost = (masks[a] | masks[b] | masks[c]).bit_count()
        hit = int(any(y[i] for i in ids))
        nominal = sum(len(bundles[i]) for i in ids)
        triples.append((ids, hit, cost, nominal))
        counts[cost] += 1
        hits[cost] += hit
        ks = [items[i]['kind'] for i in ids]
        if len(set(ks)) == 3:
            w = 1 / (denom * math.prod(kind_counts[k] for k in ks))
            perkind['reach'] += w * hit
            perkind['unique_inputs'] += w * cost
            perkind['requested_inputs'] += w * nominal
            perkind['mass'] += w
    if len(kinds) < 3:
        # Historical v47 uses one item from each available kind when fewer than three exist.
        for ids in itertools.combinations(range(len(y)), len(kinds)):
            ks = [items[i]['kind'] for i in ids]
            if len(set(ks)) != len(kinds):
                continue
            w = 1 / math.prod(kind_counts[k] for k in ks)
            mask = 0
            for i in ids:
                mask |= masks[i]
            perkind['reach'] += w * int(any(y[i] for i in ids))
            perkind['unique_inputs'] += w * mask.bit_count()
            perkind['requested_inputs'] += w * sum(len(bundles[i]) for i in ids)
            perkind['mass'] += w
    assert math.isclose(perkind['mass'], 1, abs_tol=1e-9)
    perkind['candidate_count'] = min(3, len(kinds))
    cumulative, nh, nt = {}, 0, 0
    for cost in sorted(counts):
        nh += hits[cost]
        nt += counts[cost]
        cumulative[cost] = nh / nt
    n = len(triples)
    uniform = dict(candidate_count=3, reach=sum(t[1] for t in triples)/n, unique_inputs=sum(t[2] for t in triples)/n,
                   requested_inputs=sum(t[3] for t in triples)/n)
    return dict(all=triples, cost_random=cumulative, uniform=uniform, per_kind=dict(perkind))


def tie_choices(scores):
    rounded = [round(float(s), 12) for s in scores]
    boundary = sorted(rounded, reverse=True)[2]
    fixed = [i for i, s in enumerate(rounded) if s > boundary]
    tied = [i for i, s in enumerate(rounded) if s == boundary]
    return [tuple(sorted(fixed + list(extra))) for extra in itertools.combinations(tied, 3 - len(fixed))]


def evaluate_policy(task, scores):
    choices = tie_choices(scores)
    records = {ids: (hit, cost, nominal) for ids, hit, cost, nominal in task['triples']['all']}
    outcomes = [records[c] for c in choices]
    n = len(outcomes)
    representative = min(choices, key=lambda ids: digest([SEED, task['cid'], [task['items'][i]['id'] for i in ids]]))
    return dict(candidate_count=3, reach=sum(o[0] for o in outcomes)/n, unique_inputs=sum(o[1] for o in outcomes)/n,
                requested_inputs=sum(o[2] for o in outcomes)/n,
                cost_random=sum(task['triples']['cost_random'][o[1]] for o in outcomes)/n,
                tie_subsets=n, representative_picks=[task['items'][i]['id'] for i in representative],
                representative_reach=records[representative][0], scores=[round(float(s), 12) for s in scores])


def fit_scores(train, test, key):
    vectorizer = DictVectorizer(sparse=True)
    xs = [x for t in train for x in t[key]]
    ys = [y for t in train for y in t['y']]
    groups = Counter(t['group'] for t in train)
    weights = [len(xs) / (len(groups)*groups[t['group']]*len(t['y'])) for t in train for _ in t['y']]
    if len(set(ys)) == 1:
        return [float(ys[0])] * len(test[key])
    xtrain = vectorizer.fit_transform(xs)
    xtest = vectorizer.transform(test[key])
    model = LogisticRegression(C=1., solver='liblinear', max_iter=5000, random_state=SEED)
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        model.fit(xtrain, ys, sample_weight=weights)
    return model.predict_proba(xtest)[:, 1].tolist()


def prior_scores(train, test, subtype=False):
    group_rates, rates = defaultdict(list), defaultdict(list)
    for task in train:
        grouped = defaultdict(list)
        for item, y in zip(task['items'], task['y']):
            grouped[item['kind']].append(y)
            grouped[normalize(item)[0]].append(y)
        for name, values in grouped.items():
            group_rates[(task['group'], name)].append(sum(values)/len(values))
    for (_, name), values in group_rates.items():
        rates[name].append(sum(values)/len(values))
    def predict(item):
        key = normalize(item)[0] if subtype else item['kind']
        values = rates.get(key, rates[item['kind']])
        return (sum(values)+1) / (len(values)+2)
    return [predict(it) for it in test['items']]


def bootstrap_difference(a, b, groups):
    aggregated = defaultdict(float)
    for x, y, group in zip(a, b, groups):
        aggregated[group] += x - y
    diff = np.array(list(aggregated.values()))
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(diff), size=(10000, len(diff)))
    return dict(task_total_difference=float(diff.sum()), ci95=np.quantile(diff[draws].sum(axis=1), [.025, .975]).tolist(),
                groups=len(diff), uncertainty='paired problem-group bootstrap of fixed CV predictions; no model refit')


def training_tasks(tasks, test):
    return [t for t in tasks if t['group'] != test['group']]


def run_arm(tasks):
    rows = []
    for task in tasks:
        train = training_tasks(tasks, task)
        assert all(t['group'] != task['group'] for t in train)
        assert len({t['group'] for t in train}) == 23
        scores = dict(context=fit_scores(train, task, 'x'), context_removed=fit_scores(train, task, 'bare'),
                      kind_prior=prior_scores(train, task), subtype_prior=prior_scores(train, task, True),
                      first3=[-i for i in range(len(task['y']))])
        policies = {k: evaluate_policy(task, v) for k, v in scores.items()}
        rows.append(dict(case_id=task['cid'], problem_group=task['group'], train_case_ids=[t['cid'] for t in train],
                         labels=dict(zip([it['id'] for it in task['items']], task['y'])), policies=policies,
                         random3=task['triples']['uniform'], per_kind_random3=task['triples']['per_kind'],
                         historical_qwen=task['historical']['covered3'], perfect=int(any(task['y']))))
    summary = {}
    for policy in rows[0]['policies']:
        ps = [r['policies'][policy] for r in rows]
        summary[policy] = {name: sum(p[name] for p in ps) for name in ('candidate_count', 'reach', 'unique_inputs', 'requested_inputs', 'cost_random')}
        summary[policy]['representative_reach'] = sum(p['representative_reach'] for p in ps)
    for policy in ('random3', 'per_kind_random3'):
        summary[policy] = {name: sum(r[policy][name] for r in rows) for name in ('candidate_count', 'reach', 'unique_inputs', 'requested_inputs')}
    summary['historical_qwen'] = sum(r['historical_qwen'] for r in rows)
    summary['perfect'] = sum(r['perfect'] for r in rows)
    best = max(summary[k]['reach'] for k in ('first3', 'kind_prior', 'subtype_prior', 'context_removed', 'per_kind_random3'))
    gates = dict(uniform_margin=summary['context']['reach'] - summary['random3']['reach'] >= 3,
                 cost_margin=summary['context']['reach'] - summary['context']['cost_random'] >= 3,
                 context_margin=summary['context']['reach'] - best >= 2)
    summary['gates'] = gates
    summary['verdict'] = 'promising' if all(gates.values()) else 'NO-GO'
    summary['paired'] = {k: bootstrap_difference([r['policies']['context']['reach'] for r in rows],
                            [r['policies'][k]['reach'] for r in rows], [r['problem_group'] for r in rows])
                         for k in ('context_removed', 'kind_prior', 'subtype_prior')}
    return dict(summary=summary, rows=rows)


def source_manifest():
    paths = [HERE / x for x in ('replay.py', 'test_replay.py', 'PREREG.md', 'requirements.lock')]
    paths += [REPO / 'trickcatcher_linefacts/pipelines/v34_ftplacebo' / x for x in ('source_view.py', 'chain_inputs.py', 'paths.py', 'config.json')]
    return {str(p.relative_to(REPO)): sha(p) for p in paths}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    approval = json.loads((HERE / 'APPROVAL.json').read_text())
    assert approval['status'] == 'GO' and approval['source_manifest'] == source_manifest(), 'review/freeze required'
    assert sklearn.__version__ == '1.7.2'
    assert not args.output.exists(), 'fresh output path required'
    cache = Cache()
    tasks = load_material(cache)
    cache.verify()
    print('Replay integrity passed: 33 PUTs/24 problem groups; 841/500 candidates; historical metrics reproduced.', flush=True)
    results = {arm: run_arm(tasks[arm]) for arm in ARMS}
    cache.verify()
    assert approval['source_manifest'] == source_manifest(), 'source changed during run'
    args.output.mkdir(parents=True)
    result = dict(protocol='v78', api_calls=0, api_cost_usd=0, new_program_executions=0,
                  versions=dict(python=sys.version, sklearn=sklearn.__version__, numpy=np.__version__),
                  source_manifest=source_manifest(), inputs=cache.hashes, results=results)
    (args.output / 'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({a: r['summary'] for a, r in results.items()}, indent=2))


if __name__ == '__main__':
    main()
