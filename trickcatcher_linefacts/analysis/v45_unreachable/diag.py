"""v45 exploratory diagnosis (no decision rule, no LLM): what do the hidden bug-revealing inputs of the tasks that no v44
method reached look like, compared with the v41 pool? Hidden inputs (`plus_input`) are evaluator-only; used here only
to characterise the missing input structure. Usage: PYTHONPATH=. $V4_PYTHON .../v45_unreachable/diag.py
"""
import json
from pathlib import Path

from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.analysis.v42_mutoracle import mutoracle
from trickcatcher_linefacts.analysis.v44_concept_matrix.matrix import exposing_set
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.paths import CONFIG, REPO

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v45_unreachable'
V44 = HERE.parents[1] / 'out' / 'analysis' / 'v44_concept_matrix' / 'matrix.json'


def stats(args):
    """Size/value features of one argument tuple: max sequence length (any depth), nesting depth, max |int|, total elements."""
    s = dict(maxlen=0, depth=0, maxabs=0, total=0)

    def walk(v, d):
        s['depth'] = max(s['depth'], d)
        if type(v) in (list, tuple, str):
            s['maxlen'] = max(s['maxlen'], len(v))
            if type(v) is not str:
                s['total'] += len(v)
                for e in v:
                    walk(e, d + 1)
            else:
                s['total'] += len(v)
        elif type(v) is int and type(v) is not bool:
            s['maxabs'] = max(s['maxabs'], abs(v))
    for a in args:
        walk(a, 0)
    return s


def agg(rows):
    return {k: max((r[k] for r in rows), default=0) for k in ('maxlen', 'depth', 'maxabs', 'total')}


def main():
    run = ft_run.FTRun('vibepass_half')
    v44 = {r['case_id']: r for r in json.loads(V44.read_text())['rows']}
    v41 = {r['case_id']: r for r in json.loads((iorel.OUT / 'ceiling.json').read_text())['rows']}
    root = REPO / CONFIG['vibepass']['root']
    plus = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, (root / 'humaneval_mbpp_plus.jsonl').read_text().splitlines())}
    rows = []
    for case in run.cases:
        cid = case['case_id']
        hidden = [repr(tuple(a)) for a in plus[int(cid)]['plus_input']]
        put = iorel.run_batch(OUT / cid / 'put', {'put': case['source']}, case['entry'], hidden)['put']
        ref = case['reference']
        rr = iorel.run_batch(OUT / cid / 'ref', {'contract': ref['contract'], 'ref': ref['source']}, ref['entry'], hidden)
        exp, valid = exposing_set(hidden, put, rr['contract'], rr['ref'])
        pool, _ = mutoracle.load_pool(cid, v41[cid])
        import ast
        ps = agg([stats(ast.literal_eval(l)) for l in pool])
        hs = [stats(ast.literal_eval(l)) for l in sorted(exp)]
        reached = v44[cid].get('c1', False)
        smallest = min(hs, key=lambda s: (s['total'], s['maxabs'])) if hs else None
        beyond = None
        if smallest:
            beyond = [k for k in ('maxlen', 'maxabs', 'depth', 'total') if smallest[k] > ps[k]]
        rows.append(dict(case_id=cid, reached_by_v44=reached, hidden=len(hidden), hidden_valid=len(valid), hidden_exposing=len(exp),
                         pool_max=ps, smallest_exposing=smallest, smallest_exceeds_pool_on=beyond,
                         smallest_exposing_input=(min(sorted(exp), key=len)[:300] if exp else None)))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'diag.json').write_text(json.dumps(rows, indent=1) + '\n')
    for r in rows:
        if not r['reached_by_v44']:
            print(r['case_id'], 'hidden exp %d/%d' % (r['hidden_exposing'], r['hidden_valid']), 'pool', r['pool_max'],
                  'smallest', r['smallest_exposing'], 'exceeds', r['smallest_exposing_input'] and r['smallest_exceeds_pool_on'])
            print('    ', (r['smallest_exposing_input'] or '')[:160])


if __name__ == '__main__':
    main()
