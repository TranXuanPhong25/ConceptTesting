"""v72 score (registered v4 interpreter): v64 plainimpl scoring path with an added `crosshair` pool. After search freeze."""
import collections
import json
from pathlib import Path

from trickcatcher_linefacts.analysis.v64_haiku_plainoracle import experiment as X

S, O, V, E = X.S, X.O, X.V, X.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / HERE.name
UNREACHABLE = ('6', '39', '48', '58', '69', '70', '73', '74', '168', '171')


def accepted_inputs(case, rec, pid, inputs):
    """X.accepted_inputs with executions under the v72 root (v64 caches untouched)."""
    code, checks, status = V.checks((X.OUT / 'answers/open' / f'{pid}.txt').read_text())
    if status != 'ok':
        raise RuntimeError('malformed open checks')
    srcs = [V.wrap(code, case['entry'], c['name']) for c in checks]
    with E.execution_root(OUT):
        base = O.run_programs(case, 'codex_open', srcs, rec['base_inputs'], 'base', 2)
        ran = O.run_programs(case, 'codex_open', srcs, inputs, 'all')
    ok = lambda o: bool(o) and o[0] == 'ok' and o[1] == 'True'
    kept = [j for j in range(len(checks)) if all(ok(o) for o in base[f'p{j}'])]
    return {lit: all(ok(ran[f'p{j}'][n]) for j in kept) for n, lit in enumerate(inputs)}


def main():
    found = {p.stem: json.loads(p.read_text()) for p in (OUT / 'search').glob('*.json')}
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    cohort, _, records, _ = ready
    if set(found) != set(cohort):
        raise RuntimeError('search incomplete: no outcomes')
    run, probs = V.problems()
    cases = {c['case_id']: c for c in run.cases}
    pid_of = {c['case_id']: p for p, cs in probs.items() for c in cs}
    official = E.Reference(run)
    official.root = OUT / 'references/official'
    S.OUT = OUT
    v64 = json.loads((X.OUT / 'score.json').read_text())
    tasks = {}
    for cid in cohort:
        case, rec, pid = cases[cid], records[cid], pid_of[cid]
        universe = E.ordered(rec['inputs'])
        generated, gen_info = S.generated(case, pid, 'plain')
        cross = list(dict.fromkeys(found[cid]['witnesses']))
        everything = list(dict.fromkeys(universe + generated + cross))
        acc = accepted_inputs(case, rec, pid, everything)
        pools = dict(universe=[l for l in universe if acc[l]], plain=[l for l in generated if acc[l]],
                     crosshair=[l for l in cross if acc[l]])
        pools['union'] = list(dict.fromkeys(pools['universe'] + pools['plain']))
        pools['union_x'] = list(dict.fromkeys(pools['union'] + pools['crosshair']))
        used = pools['union_x']
        new = [l for l in used if l not in rec['inputs']]
        with E.execution_root(OUT):
            newput = O.run_programs(case, 'put', [case['source']], new, 'new')['p0'] if new else []
        puts = {l: rec['inputs'][l]['put'] for l in used if l in rec['inputs']} | dict(zip(new, newput))
        truth = S.truth_for(inv, case, {l: dict(put=puts[l]) for l in used}, official)
        tolerant = v64['tasks'][cid]['arms']['plainimpl']['tolerant']
        strict = v64['tasks'][cid]['arms']['plainimpl']['strict']
        srcs = [O.code_block((X.OUT / 'answers/plainimpl' / f'{pid}_{i}.txt').read_text()) for i in range(3)]
        with E.execution_root(OUT):
            ran = O.run_programs(case, 'plainimpl_valid', [srcs[j] for j in tolerant], used, 'used')
        rows = {}
        for name, ids in (('tolerant', tolerant), ('strict', strict)):
            rows[name] = {}
            for n, lit in enumerate(used):
                outs = [ran[f'p{tolerant.index(j)}'][n] for j in ids]
                rows[name][lit] = dict(put=puts[lit], programs=outs, **O.votes(puts[lit], outs))
        metrics = {name: S.arm_metrics(inputs, rows, truth, len(tolerant), len(strict)) for name, inputs in pools.items()}
        tasks[cid] = dict(problem=pid, pools=metrics, crosshair_raw=len(cross), crosshair_accepted=len(pools['crosshair']),
                          search_status=found[cid].get('status'))
        print('scored', cid, flush=True)
    hit = lambda c, pool: tasks[c]['pools'][pool]['confirmed_tasks']
    sums = lambda pool, key: sum(t['pools'][pool][key] for t in tasks.values())
    primary = [c for c in UNREACHABLE if hit(c, 'crosshair')]
    tests, conf = sum(tasks[c]['pools']['crosshair']['tests'] for c in tasks), sum(tasks[c]['pools']['crosshair']['confirmed_tests'] for c in tasks)
    precision = conf / tests if tests else None
    summary = dict(primary_new_confirmed_unreachable=primary, crosshair_precision=precision,
                   crosshair_tests=tests, crosshair_fa=sums('crosshair', 'fa_tests'),
                   union_confirmed=sorted(c for c in tasks if hit(c, 'union')),
                   union_x_confirmed=sorted(c for c in tasks if hit(c, 'union_x')),
                   crosshair_confirmed_all=sorted(c for c in tasks if hit(c, 'crosshair')),
                   decision='GO' if len(primary) >= 2 and (precision or 0) >= .9 else 'STOP')
    (OUT / 'score.json').write_text(json.dumps(dict(tasks=tasks, summary=summary), indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
