"""v64: plain-implementation and brute oracles vs v55h defn, Claude Haiku subagents as writer. Seed, prepare, split, score.

Run from repo root with PYTHONPATH=. and the registered interpreter.
No generation or scoring is performed by `prepare`.
"""
import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path

from trickcatcher_linefacts.analysis.v53_validity_smallscope import smallscope as S

O, V, E = S.O, S.V, S.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / HERE.name
ARMS = ('defn', 'brute', 'plainimpl')
NEW = ('brute', 'plainimpl')
INSTR = dict(defn='defn', brute='brute', plainimpl='plain')  # v49 gen.INSTR keys
V55H = OUT.parent / 'v55h_haiku_interpretation'


def digest(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def save(path, data):
    text = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != text:
        raise RuntimeError('immutable file differs: ' + str(path))
    path.write_text(text)


def prepare():
    _, probs = V.problems()
    manifest = []
    problem_list = list(sorted(probs))
    for kind in (*ARMS, 'open', 'plain'):
        for sample in range(3 if kind in ARMS else 1):
            for start in range(0, len(problem_list), 8):
                ids = problem_list[start:start+8]
                parts = []
                for pid in ids:
                    task = E.task_view(probs[pid][0])
                    if kind in ARMS:
                        msg = S.gen.messages(task, INSTR[kind])[1]['content']
                        msg += '\nUse at most 1024 output tokens for this answer.'
                    else:
                        msg = V.message(task, 'open') if kind == 'open' else S.message(task, 'plain')
                    parts.append(dict(id=pid, prompt=msg))
                prompt = ('Answer each problem independently using only the supplied prompt. Do not use tools, '
                          'search, files or external information. Return exactly a JSON object mapping each id '
                          'to a string containing one fenced Python code block, with no other text.\n\n'
                          + json.dumps(parts, ensure_ascii=False))
                name = f'{kind}_{sample}_{start//8}'
                path = OUT / 'prompts' / (name+'.txt')
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists() and path.read_text() != prompt:
                    raise RuntimeError('prompt changed')
                path.write_text(prompt)
                manifest.append(dict(call=name, kind=kind, sample=sample, problems=ids,
                                     entrypoints={pid: ('inputs' if kind == 'plain' else
                                         ast.parse('def '+E.task_view(probs[pid][0])['signature']+':\n pass').body[0].name)
                                         for pid in ids} if kind != 'open' else {},
                                     prompt_sha256=digest(prompt)))
    save(OUT/'manifest.json', manifest)
    save(OUT/'problems.json', {p: [c['case_id'] for c in cs] for p, cs in probs.items()})
    print(json.dumps(dict(problems=len(probs), calls=len(manifest), oracle_answers=len(probs)*9,
                          shared_answers=len(probs)*2)))


def answer_path(job, pid):
    kind = job['kind']
    return OUT/'answers'/kind/(f'{pid}_{job["sample"]}.txt' if kind in ARMS else pid+'.txt')


def answer_paths(jobs):
    return [answer_path(j, pid) for j in jobs for pid in j['problems']]


def seed():
    """Copy v55h defn answers and the shared plain-generator/open-filter answers byte-for-byte."""
    for kind in ('defn', 'open', 'plain'):
        for src in sorted((V55H/'answers'/kind).glob('*.txt')):
            dst = OUT/'answers'/kind/src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and dst.read_bytes() != src.read_bytes():
                raise RuntimeError('seeded answer differs: '+str(dst))
            dst.write_bytes(src.read_bytes())
    for kind in ('defn', 'open', 'plain'):
        for path in sorted((OUT/'prompts').glob(kind+'_*.txt')):
            if path.read_bytes() != (V55H/'prompts'/path.name).read_bytes():
                raise RuntimeError('prompt differs from v55h: '+path.name)
    print('seeded; defn/open/plain prompts identical to v55h')


def split():
    """One prompt file per problem of each new-arm batch, for Haiku subagents (same header as v55h)."""
    head = ('Answer using only this prompt. Reply with exactly one fenced ```python code block and nothing else.\n\n')
    for job in json.loads((OUT/'manifest.json').read_text()):
        if job['kind'] not in NEW:
            continue
        text = (OUT/'prompts'/(job['call']+'.txt')).read_text()
        parts = json.loads(text[text.index('\n\n')+2:])
        for part in parts:
            path = OUT/'split'/job['call']/(part['id']+'.txt')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(head+part['prompt']+'\n')
    print('split', sum(len(j['problems']) for j in json.loads((OUT/'manifest.json').read_text()) if j['kind'] in NEW))


def validate_answer(text, kind, entrypoint=None):
    code = O.code_block(text)
    if not code:
        raise ValueError('missing Python code block')
    tree = ast.parse(code)
    if kind == 'open':
        if V.checks(text)[2] != 'ok':
            raise ValueError('malformed open checker')
    elif not any(isinstance(node, ast.FunctionDef) and node.name == entrypoint for node in tree.body):
        raise ValueError('missing module-level entrypoint')


def accepted_inputs(case, rec, pid, inputs):
    code, checks, status = V.checks((OUT/'answers/open'/f'{pid}.txt').read_text())
    if status != 'ok':
        raise RuntimeError('malformed open checks')
    srcs = [V.wrap(code, case['entry'], c['name']) for c in checks]
    with E.execution_root(OUT):
        base = O.run_programs(case, 'codex_open', srcs, rec['base_inputs'], 'base', 2)
        ran = O.run_programs(case, 'codex_open', srcs, inputs, 'all')
    ok = lambda o: bool(o) and o[0] == 'ok' and o[1] == 'True'
    kept = [j for j in range(len(checks)) if all(ok(o) for o in base[f'p{j}'])]
    return {lit: all(ok(ran[f'p{j}'][n]) for j in kept) for n, lit in enumerate(inputs)}, dict(
        total=len(checks), kept=len(kept), dropped=len(checks)-len(kept))


def score():
    jobs = json.loads((OUT/'manifest.json').read_text())
    missing = [p for p in answer_paths(jobs) if not p.is_file()]
    if missing:
        raise RuntimeError(f'{len(missing)} writer answers missing; no outcomes')
    for j in jobs:
        for pid in j['problems']:
            validate_answer(answer_path(j, pid).read_text(), j['kind'], j['entrypoints'].get(pid))
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    cohort, _, records, _ = ready
    run, probs = V.problems()
    cases = {c['case_id']: c for c in run.cases}
    pid_of = {c['case_id']: p for p, cs in probs.items() for c in cs}
    official = E.Reference(run)
    official.root = OUT/'references/official'
    # All generator executions and new reference caches remain under v64.
    S.OUT = OUT
    tasks = {}
    for cid in cohort:
        case, rec, pid = cases[cid], records[cid], pid_of[cid]
        universe = E.ordered(rec['inputs'])
        generated, gen_info = S.generated(case, pid, 'plain')
        if gen_info['status'] != 'ok':
            raise RuntimeError('generator execution failed; run incomplete, no automatic repair')
        everything = list(dict.fromkeys(universe+generated))
        acc, filter_info = accepted_inputs(case, rec, pid, everything)
        pools = dict(universe=[l for l in universe if acc[l]], plain=[l for l in generated if acc[l]])
        used = list(dict.fromkeys(pools['universe']+pools['plain']))
        pools['union'] = used
        new = [l for l in used if l not in rec['inputs']]
        with E.execution_root(OUT):
            newput = O.run_programs(case, 'put', [case['source']], new, 'new')['p0'] if new else []
        puts = {l: rec['inputs'][l]['put'] for l in used if l in rec['inputs']} | dict(zip(new, newput))
        truth = S.truth_for(inv, case, {l: dict(put=puts[l]) for l in used}, official)
        arms = {}
        for arm in ARMS:
            srcs = [O.code_block((OUT/'answers'/arm/f'{pid}_{i}.txt').read_text()) for i in range(3)]
            with E.execution_root(OUT):
                base = O.run_programs(case, arm, srcs, rec['base_inputs'], 'base', 2)
                reasons = {j: O.rejection(rec['base_put'], base[f'p{j}']) for j in range(3)}
                strict = [j for j in range(3) if srcs[j] and not reasons[j]]
                tolerant = [j for j in range(3) if srcs[j] and (not reasons[j] or (
                    O.resource_only(reasons[j], base[f'p{j}']) and 'mismatch' not in reasons[j]
                    and any(o and o[0] == 'ok' for o in base[f'p{j}'])))]
                ran = O.run_programs(case, arm+'_valid', [srcs[j] for j in tolerant], used, 'used')
            rows = {}
            for name, ids in (('tolerant', tolerant), ('strict', strict)):
                rows[name] = {}
                for n, lit in enumerate(used):
                    outs = [ran[f'p{tolerant.index(j)}'][n] for j in ids]
                    rows[name][lit] = dict(put=puts[lit], programs=outs, **O.votes(puts[lit], outs))
            metrics = {name: S.arm_metrics(inputs, rows, truth, len(tolerant), len(strict))
                       for name, inputs in pools.items()}
            emitted = E.emitted(used, rows['tolerant'], 'primary', 20)
            labels = O.labels_for(rows['tolerant'], truth)
            split = collections.Counter()
            for lit in emitted:
                if labels[lit]['primary'] == 'confirmed':
                    continue
                t = truth[lit]
                value = E.iorel.value(rows['tolerant'][lit]['primary'])
                split['invalid' if not t['valid'] else 'unknown_reference' if t['ref'] is None else
                      'wrong_value' if not E.same(value, t['ref']) else 'unconfirmed'] += 1
            common = collections.Counter()
            abstentions = collections.Counter()
            for lit in used:
                row = rows['tolerant'][lit]
                abstentions['program_input_calls'] += len(row['programs'])
                abstentions['nonfinishing_program_inputs'] += sum(not o or o[0] != 'ok' for o in row['programs'])
                abstentions['no_primary_vote_inputs'] += row['primary'] is None
                t = truth[lit]
                if not t['valid'] or t['ref'] is None or not t['exposes']():
                    continue
                abstentions['exposing_inputs'] += 1
                abstentions['exposing_no_primary_vote'] += row['primary'] is None
                vals = [E.iorel.value(o) for o in rows['tolerant'][lit]['programs'] if o and o[0] == 'ok']
                if len(vals) >= 2 and all(v is not None and E.same(v, vals[0]) for v in vals) and not E.same(vals[0], t['ref']):
                    common['with_put' if E.same(vals[0], E.iorel.value(puts[lit])) else 'away_from_put'] += 1
            arms[arm] = dict(pools=metrics, fa_split=dict(split), common_mode=dict(common),
                             abstentions=dict(abstentions), strict=strict, tolerant=tolerant, rejection=reasons)
        tasks[cid] = dict(problem=pid, arms=arms, generator=gen_info, validity=filter_info)
        print('scored', cid, flush=True)
    totals = {}
    for arm in ARMS:
        sums = collections.Counter()
        for task in tasks.values():
            m = task['arms'][arm]
            sums.update({k: m['pools']['union'][k] for k in ('confirmed_tasks', 'confirmed_tests', 'tests', 'fa_tests')})
        totals[arm] = dict(sums, precision=sums['confirmed_tests']/sums['tests'] if sums['tests'] else None,
                          common_mode_problems=len({t['problem'] for t in tasks.values() if any(
                              t['arms'][arm]['common_mode'].values())}))
    def paired(arm, control):
        hit = lambda c, x: tasks[c]['arms'][x]['pools']['union']['confirmed_tasks']
        wins = [c for c in tasks if hit(c, arm) and not hit(c, control)]
        losses = [c for c in tasks if hit(c, control) and not hit(c, arm)]
        return dict(wins=wins, losses=losses, win_problems=len({tasks[c]['problem'] for c in wins}),
                    precision_gap=(totals[arm]['precision'] or 0) - (totals[control]['precision'] or 0))
    pairs = {f'{a}_vs_{b}': paired(a, b) for a, b in (('defn', 'plainimpl'), ('brute', 'plainimpl'), ('defn', 'brute'))}
    p = pairs['defn_vs_plainimpl']
    net = len(p['wins']) - len(p['losses'])
    decision = ('family effect holds' if net >= 2 and p['win_problems'] >= 2 and p['precision_gap'] >= -.02 else
                'weak-writer artefact' if net <= 0 and p['precision_gap'] <= .02 else 'inconclusive')
    save(OUT/'score.json', dict(tasks=tasks, totals=totals, paired=pairs, decision=decision))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'seed', 'split', 'score'))
    args = parser.parse_args()
    globals()[args.action]()
