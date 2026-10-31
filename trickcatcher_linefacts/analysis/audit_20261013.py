"""Read-only recomputation from saved observations. No PUT execution or LLM calls.

Writes only audit_20261013.json beside this script. Random-budget sensitivity
integrates uniformly over subsets exactly; it is not a new experiment.
"""
import ast
from collections import Counter, defaultdict
import hashlib
import json
from math import comb
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
RUNS = {
    'v7': ('out/gen2_qwen7b_v7hyb_v4_r2', 'out/oracle_v7hyb'),
    'v8-strict': ('out/gen2_qwen7b_v8strict_est', 'out/oracle_v8strict_est'),
    'v9': ('out/pipelines/v9_callfb/humaneval/generation', 'out/pipelines/v9_callfb/humaneval/oracle'),
    'mbpp12': ('out/heldout_mbpp_real12/gen2_qwen7b_v7hyb_v4', 'out/heldout_mbpp_real12/oracle_v7hyb'),
}


def call_of(src, entry):
    try:
        node = ast.parse(src).body[0].test
        calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == entry]
        return ast.unparse(calls[0]) if calls else None
    except (SyntaxError, AttributeError, IndexError):
        return None


def sign(w, l):
    n = w + l
    return min(1., 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2**n) if n else 1.


def subset_detection(bits, m):
    n, hits = len(bits), sum(bits)
    if not m or not hits:
        return 0.
    return 1. - (comb(n - hits, m) / comb(n, m) if n - hits >= m else 0.)


def audit(run, oracle):
    tasks = {t['task']: t for t in json.loads((run / 'tasks.json').read_text())['tasks']}
    rows = [json.loads(l) for l in (run / 'eval.jsonl').read_text().splitlines()]
    gen = [json.loads(l) for l in (run / 'gen.jsonl').read_text().splitlines()]
    ex = {n: json.loads((oracle / 'exec' / f'{n}.json').read_text()) for n in tasks}
    keys = [(r['task'], r['arm'], r['sample']) for r in rows]
    assert len(keys) == len(set(keys)), 'Duplicate observations'
    arms, samples = sorted({k[1] for k in keys}), sorted({k[2] for k in keys})
    expected = {(n, a, s) for n in tasks for a in arms for s in samples}
    assert set(keys) == expected, 'Missing observations'
    parsed, missing = {}, []
    for r in rows:
        seen, bits, fa, emit = set(), [], 0, 0
        for a in r['asserts']:
            c = call_of(a['src'], tasks[r['task']]['entry'])
            if not c or c in seen:
                continue
            seen.add(c)
            rec = ex[r['task']]['calls'].get(c)
            if rec is None:
                missing.append([r['task'], c]); rec = {}
            ref = rec.get('ref', {})
            valid = rec.get('valid', True)
            bits.append(bool(ref.get('emit') and ref.get('canon_ok') and not ref.get('put_ok') and valid))
            emit += bool(ref.get('emit'))
            fa += bool(ref.get('emit') and (not ref.get('canon_ok') or not valid))
        parsed[r['task'], r['arm'], r['sample']] = dict(bits=bits, fa=fa, emit=emit)
    assert not missing, 'Missing execution records'
    result = dict(n_tasks=len(tasks), n_rows=len(rows), K=len(samples), complete=True,
                  source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (run/'tasks.json', run/'eval.jsonl', run/'gen.jsonl')}, splits={})
    for split in sorted({t['split'] for t in tasks.values()}):
        ids = sorted(n for n, t in tasks.items() if t['split'] == split)
        k = len(samples)
        summary = {}
        for arm in arms:
            obs = [parsed[t, arm, s] for t in ids for s in samples]
            generated = [r for r in gen if r['task'] in ids and r['arm'] == arm]
            summary[arm] = dict(detected_per_run=sum(any(o['bits']) for o in obs)/k,
                                unique_calls_per_sample=sum(len(o['bits']) for o in obs)/len(obs),
                                emitted_per_sample=sum(o['emit'] for o in obs)/len(obs),
                                false_alarm=sum(o['fa'] for o in obs)/max(1, sum(o['emit'] for o in obs)),
                                mean_recorded_llm_calls=sum(r['llm_calls'] for r in generated)/len(generated))
        comparisons = {}
        for a, b in [('concept', 'plain'), ('concept-hybrid', 'plain-hybrid'),
                     ('concept-hybrid', 'placebo-hybrid'), ('concept-hybrid', 'toolinput')]:
            for mode in ('raw', 'prefix_matched', 'uniform_subset_matched'):
                scores = defaultdict(lambda: [0., 0.])
                for t in ids:
                    for s in samples:
                        left, right = parsed[t, a, s]['bits'], parsed[t, b, s]['bits']
                        m = min(len(left), len(right))
                        for j, bits in enumerate((left, right)):
                            v = subset_detection(bits, m) if mode == 'uniform_subset_matched' else float(any(bits if mode == 'raw' else bits[:m]))
                            scores[t][j] += v
                w = sum(v[0] > v[1]+1e-12 for v in scores.values())
                l = sum(v[0] < v[1]-1e-12 for v in scores.values())
                values = [sum(v[j] for v in scores.values())/k for j in (0,1)]
                record = dict(detected_per_run=values, wins=w, losses=l,
                              sign_p=sign(w, l) if mode != 'uniform_subset_matched' else None)
                if mode == 'raw':
                    # Task-cluster paired bootstrap; descriptive on reused DEV.
                    deltas = [(v[0]-v[1])/k for v in scores.values()]
                    rng = random.Random(20261013)
                    boot = sorted(sum(rng.choices(deltas, k=len(deltas))) / len(deltas) for _ in range(10000))
                    record['mean_detection_probability_delta'] = sum(deltas)/len(deltas)
                    record['descriptive_bootstrap_95ci'] = [boot[249], boot[9749]]
                comparisons[f'{a} vs {b} / {mode}'] = record
        budgets = [(r['task'], r['sample']) for r in gen if r['task'] in ids and r['arm']=='concept-hybrid']
        indexed = {(r['task'], r['arm'], r['sample']): r for r in gen}
        mismatches = sum(indexed[t,'concept-hybrid',s]['round2_strategy_requests'] !=
                         indexed[t,'plain-hybrid',s]['round2_strategy_requests'] for t,s in budgets)
        result['splits'][split] = dict(n_tasks=len(ids), arms=summary, comparisons=comparisons,
                                      concept_plain_strategy_budget_mismatches=mismatches)
    return result


def main():
    data = {name: audit(ROOT/run, ROOT/ora) for name,(run,ora) in RUNS.items()}
    data['notes'] = [
        'Recomputed from saved per-call execution observations; no fresh model or PUT execution.',
        'Uniform-subset sensitivity uses exact hypergeometric probabilities, not sampled trials; no sign p is claimed.',
        'Prefix matching depends on assertion order and post-treatment output counts.',
        'v8 recorded cost fields describe source v7 calls, not a freshly executed strict protocol.',
        'Bootstrap intervals are descriptive and unadjusted for development selection or multiple comparisons.',
    ]
    path = Path(__file__).with_suffix('.json')
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    for name, r in data.items():
        if name == 'notes': continue
        print(name, r['n_rows'], 'complete')
        for split, group in r['splits'].items():
            print(split, group['n_tasks'], {a: round(v['detected_per_run'],3) for a,v in group['arms'].items()})
            for pair, v in group['comparisons'].items():
                if pair.startswith('concept-hybrid'): print(pair, v)


if __name__ == '__main__':
    main()
