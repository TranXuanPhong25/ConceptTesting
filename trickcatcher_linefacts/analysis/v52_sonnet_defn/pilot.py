"""v52 pilot: v49 definitional concept with Claude Sonnet as the program writer (see PREREG.md). Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v52_sonnet_defn/pilot.py prompts   # v49 prompts -> prompt files
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v52_sonnet_defn/pilot.py score     # validate, run, judge
Programs are written by Sonnet subagents to out/.../programs/<arm>/<task>/<i>.txt (raw answer with one code block).
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v49_defn_oracle import gen
from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O

E = O.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v52_sonnet_defn'
TASKS = ('141', '46', '87', '65', '161', '103')
ARMS = ('defn', 'brute')
K = 3


def prompts():
    run = E.ft_run.FTRun('vibepass_half')
    cases = {c['case_id']: c for c in run.cases}
    for cid in TASKS:
        for arm in ARMS:
            system, user = gen.messages(E.task_view(cases[cid]), arm)
            path = OUT / 'prompts' / f'{cid}_{arm}.txt'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"SYSTEM:\n{system['content']}\n\nUSER:\n{user['content']}\n")
    print('prompts', len(TASKS) * len(ARMS), OUT / 'prompts')


def measure(inputs, rows, truth, valid):
    m = O.metrics(inputs, rows, truth, valid)['primary']['capped']
    return {k: m[k] for k in ('confirmed_tasks', 'correct_assertions', 'tests', 'fa_tests')} | dict(valid=valid)


def sonnet(case, rec, arm, inputs, excluded):
    cid = case['case_id']
    ids, srcs = [], []
    for i in range(K):
        path = OUT / 'programs' / arm / cid / f'{i}.txt'
        if path.is_file() and f'{cid}/{arm}/{i}' not in excluded:
            src = O.code_block(path.read_text())
            if src:
                ids.append(i)
                srcs.append(src)
    with E.execution_root(OUT):
        base = O.run_programs(case, 'sonnet_' + arm, srcs, rec['base_inputs'], 'base', 2)
        valid = [j for j in range(len(srcs)) if not O.rejection(rec['base_put'], base[f'p{j}'])]
        ran = O.run_programs(case, 'sonnet_' + arm + '_valid', [srcs[j] for j in valid], inputs, 'inputs')
    rows = {}
    for n, lit in enumerate(inputs):
        outs = [ran[f'p{j}'][n] for j in range(len(valid))]
        rows[lit] = dict(put=rec['inputs'][lit]['put'], programs=outs, **O.votes(rec['inputs'][lit]['put'], outs))
    audits = [O.audit(case, srcs[j]) for j in range(len(srcs))]
    return rows, len(valid), dict(written=len(srcs), valid_ids=[ids[j] for j in valid],
                                  concept_comments=sum(all(a['concept_comments'].values()) for a in audits),
                                  ast_similarity=[a.get('implementation_ast_similarity') for a in audits])


def score():
    excluded = set(json.loads((OUT / 'excluded.json').read_text())) if (OUT / 'excluded.json').is_file() else set()
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    if ready is None:
        raise SystemExit('v49 records incomplete')
    _, _, records, picks = ready
    run = E.ft_run.FTRun('vibepass_half')
    official = E.Reference(run)
    official.root = O.OUT / 'references' / 'official'
    cases = {c['case_id']: c for c in run.cases}
    prep = inv.read(E.select.OUT / 'prepared.json')
    v49 = {r['case_id']: r for r in json.loads((O.OUT / 'score.json').read_text())['rows']}
    result = {}
    for cid in TASKS:
        rec, case = records[cid], cases[cid]
        inputs = E.ordered(rec['inputs'])
        truth = O.task_truth(inv, case, rec, official, E.all_inputs(prep[cid]) | set(picks[cid]))
        task = {}
        for arm in ARMS:
            rows, valid, info = sonnet(case, rec, arm, inputs, excluded)
            qwen3 = [i for i in rec['families'][arm]['valid_programs'] if i < K]
            task[arm] = dict(sonnet=measure(set(inputs), rows, truth, valid) | info,
                             qwen_k3=measure(set(inputs), O.oracle_rows(rec, arm, subset=qwen3), truth, len(qwen3)),
                             qwen_k5={k: v49[cid]['input_sets']['decisive'][arm]['primary']['capped'][k]
                                      for k in ('confirmed_tasks', 'correct_assertions', 'tests', 'fa_tests')})
        result[cid] = task
    totals = {arm: {who: {k: sum(result[c][arm][who][k] for c in TASKS) for k in
                          ('confirmed_tasks', 'correct_assertions', 'tests', 'fa_tests')}
                    for who in ('sonnet', 'qwen_k3', 'qwen_k5')} for arm in ARMS}
    out = dict(tasks=result, totals=totals, excluded=sorted(excluded))
    O.immutable(OUT / 'score.json', out)
    print(json.dumps(dict(totals=totals, per_task={c: {a: result[c][a]['sonnet'] | dict(qwen_k3=result[c][a]['qwen_k3'])
                                                       for a in ARMS} for c in TASKS}), indent=1))


if __name__ == '__main__':
    dict(prompts=prompts, score=score)[sys.argv[1]]()
