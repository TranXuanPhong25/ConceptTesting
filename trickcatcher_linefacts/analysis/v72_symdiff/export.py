"""v72 export (registered v4 interpreter): public-side inputs for the CrossHair differential search.

Writes PUT source/entry, public base inputs, v64 Haiku plain-implementation programs (tolerant set, as v64 scored them)
and the kept v55h/v64 open validity checkers. No reference, contract or label leaves this script.
"""
import json
from pathlib import Path

from trickcatcher_linefacts.analysis.v64_haiku_plainoracle import experiment as X

S, O, V, E = X.S, X.O, X.V, X.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / HERE.name


def main():
    score = json.loads((X.OUT / 'score.json').read_text())
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    cohort, _, records, _ = ready
    run, probs = V.problems()
    cases = {c['case_id']: c for c in run.cases}
    pid_of = {c['case_id']: p for p, cs in probs.items() for c in cs}
    rows = []
    for cid in cohort:
        case, rec, pid = cases[cid], records[cid], pid_of[cid]
        tolerant = score['tasks'][cid]['arms']['plainimpl']['tolerant']
        programs = [O.code_block((X.OUT / 'answers/plainimpl' / f'{pid}_{i}.txt').read_text()) for i in tolerant]
        code, checks, status = V.checks((X.OUT / 'answers/open' / f'{pid}.txt').read_text())
        srcs = [V.wrap(code, case['entry'], c['name']) for c in checks] if status == 'ok' else []
        with E.execution_root(OUT):
            base = O.run_programs(case, 'codex_open', srcs, rec['base_inputs'], 'base', 2) if srcs else {}
        ok = lambda o: bool(o) and o[0] == 'ok' and o[1] == 'True'
        kept = [srcs[j] for j in range(len(srcs)) if all(ok(o) for o in base[f'p{j}'])]
        rows.append(dict(case_id=cid, problem=pid, entry=case['entry'], put_source=case['source'],
                         base_inputs=list(rec['base_inputs']), programs=programs, program_indices=tolerant,
                         checkers=kept, checker_status=status))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'public_export.json').write_text(json.dumps(rows, indent=1) + '\n')
    print(json.dumps(dict(cases=len(rows), programs=sum(len(r['programs']) for r in rows),
                          checkers=sum(len(r['checkers']) for r in rows))))


if __name__ == '__main__':
    main()
