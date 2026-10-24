"""v53 Stage 1: constraint concept vs line-by-line vs open (F1b-style) mining vs numeric tool as input-validity checks
(see PREREG.md, amendment 1). Repo root:
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v53_validity_smallscope/validity.py prompts
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v53_validity_smallscope/validity.py score
Answers (one per distinct problem and arm) are written by Sonnet subagents to out/.../answers/<problem>_<arm>.txt.
"""
import ast
import collections
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v48_e2e_oracle import menu_fixed as M
from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O
from trickcatcher_linefacts.analysis.v49_defn_oracle import plan_rules as R
from trickcatcher_linefacts.analysis.v52_sonnet_defn import pilot as P

E = O.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v53_validity_smallscope'
ARMS = ('concept', 'lines', 'open')
SYSTEM = 'You are an expert Python programmer. Reply with exactly one ```python code block and nothing else.'
SHARED = ('Only conditions the caller must guarantee about the inputs; never conditions on the answer. Write each check '
          'as a separate module-level function check_1, check_2, ... (unique names) with exactly the parameters of the '
          'signature, returning a bool that is True exactly when its condition holds. Use only builtins; no imports, '
          'global state, I/O or parameter mutation; guard types and operations so a check never raises.')
INSTR = {
    'concept': ('Go through the Constraints section line by line. For each line write one check, preceded by a comment '
                '`# [RANGE|RELATION|STRUCTURE] <the constraint line>`: RANGE = bounds on one value, length or element; '
                'RELATION = a condition linking two or more arguments; STRUCTURE = a property of one argument (sorted, '
                'distinct, permutation, character set, ...). ' + SHARED),
    'lines': ('Go through the Constraints section line by line. For each line write one check, preceded by a comment '
              '`# <the constraint line>`. ' + SHARED),
    'open': ('List every condition the specification places on the inputs: types, ranges, lengths, allowed characters '
             'or elements, and relations between parameters. Use one atomic condition per check. Include only what the '
             'statement states or necessarily implies (for example, a length cannot be negative; an index must lie '
             'within its sequence); reject guesses and merely plausible restrictions. Precede each check with a comment '
             '`# <condition>`. ' + SHARED),
}


def problems():
    run = E.ft_run.FTRun('vibepass_half')
    by = collections.defaultdict(list)
    for case in run.cases:
        by[O.problem_id(case)].append(case)
    return run, {pid[:12]: sorted(cs, key=lambda c: int(c['case_id'])) for pid, cs in by.items()}


def message(task, arm):
    return (f"Problem statement:\n{task['spec']}\n\nPublic tests (valid inputs):\n{task['base']}\n\n"
            f"Function signature:\ndef {task['signature']}:\n\n{INSTR[arm]}")


def prompts():
    _, probs = problems()
    for pid, cases in probs.items():
        for arm in ARMS:
            path = OUT / 'prompts' / f'{pid}_{arm}.txt'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"SYSTEM:\n{SYSTEM}\n\nUSER:\n{message(E.task_view(cases[0]), arm)}\n")
    (OUT / 'problems.json').write_text(json.dumps({p: [c['case_id'] for c in cs] for p, cs in probs.items()}, indent=1))
    print('problems', len(probs), 'prompts', len(ARMS) * len(probs))


def checks(text):
    """(code, checks, status): status 'ok', 'empty' (no check functions) or 'parse_error' (no block, syntax, duplicates)."""
    code = O.code_block(text)
    if not code:
        return '', [], 'parse_error'
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, [], 'parse_error'
    lines = code.splitlines()
    out, names = [], []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and re.fullmatch(r'check_\d+', node.name):
            above = lines[node.lineno - 2].strip() if node.lineno >= 2 else ''
            kind = re.match(r'#\s*\[(RANGE|RELATION|STRUCTURE)\]', above)
            out.append(dict(name=node.name, comment=above, kind=kind.group(1) if kind else None))
            names.append(node.name)
    if len(names) != len(set(names)):
        return code, [], 'parse_error'
    return code, out, 'ok' if out else 'empty'


def wrap(code, entry, name):
    return (code + f"\n\ndef {entry}(*a, **k):\n    r = {name}(*a, **k)\n    if type(r) is not bool:\n"
            f"        raise TypeError('non-bool check result')\n    return r\n")


def run_checks(case, rec, arm, code, found, inputs):
    """Per check: drop it if any public input is not accepted; accept = every kept check returns True."""
    srcs = [wrap(code, case['entry'], c['name']) for c in found]
    with E.execution_root(OUT):
        base = O.run_programs(case, 'chk_' + arm, srcs, rec['base_inputs'], 'base', 2)
        ran = O.run_programs(case, 'chk_' + arm, srcs, inputs, 'inputs')
    ok = lambda o: bool(o) and o[0] == 'ok' and o[1] == 'True'
    kept = []
    for j, c in enumerate(found):
        c['dropped_on_public'] = not all(ok(o) for o in base[f'p{j}'])
        c['raised_on_public'] = sum(bool(o) and o[0] != 'ok' for o in base[f'p{j}'])
        if not c['dropped_on_public']:
            kept.append(j)
    for j, c in enumerate(found):
        c['rejections'] = sum(not ok(o) for o in ran[f'p{j}']) if j in kept else None
        c['raised_on_universe'] = sum(bool(o) and o[0] != 'ok' for o in ran[f'p{j}']) if j in kept else None
    return {lit: all(ok(ran[f'p{j}'][n]) for j in kept) for n, lit in enumerate(inputs)}, len(kept)


def violates(x, key, bound):
    (i, kind), (lo, hi) = key, bound
    if i >= len(x):
        return False
    v = x[i]
    if kind == 'length':
        return isinstance(v, (list, str)) and not lo <= len(v) <= hi
    if kind == 'value':
        return isinstance(v, int) and not isinstance(v, bool) and not lo <= v <= hi
    if kind == 'elem':
        return isinstance(v, list) and any(isinstance(e, int) and not lo <= e <= hi for e in v)
    if kind == 'elem2':
        return isinstance(v, list) and any(isinstance(e, int) and not lo <= e <= hi for r in v if isinstance(r, list) for e in r)
    return False


def tool_accept(case, rec, inputs):
    """Numeric spec bounds, each dropped if it rejects a public input (same rule as the LLM arms)."""
    task = E.task_view(case)
    names = re.findall(r'(\w+)\s*:', task['signature'].split('->')[0])
    cons, unsupported = M.constraints_report(task['spec'], names)
    public = [ast.literal_eval(x) for x in rec['base_inputs']]
    kept = {k: b for k, b in cons.items() if not any(violates(x, k, b) for x in public)}
    parsed = {lit: ast.literal_eval(lit) for lit in inputs}
    return {lit: not any(violates(parsed[lit], k, b) for k, b in kept.items()) for lit in inputs}, \
        dict(bounds=len(cons), kept=len(kept), unsupported=len(unsupported))


def effect(inputs, accept, rows, truth, valid):
    """Confirmed tests before/after filtering as sets (the cap-20 list refills, so a net count would hide losses)."""
    def confirmed(subset):
        labels = O.labels_for({l: rows[l] for l in subset}, truth)
        return {l for l in E.emitted(set(subset), rows, 'primary', 20) if labels[l]['primary'] == 'confirmed'}
    before, after = confirmed(inputs), confirmed([l for l in inputs if accept[l]])
    a = O.metrics(set(inputs), rows, truth, valid)['primary']['capped']
    b = O.metrics({l for l in inputs if accept[l]}, rows, truth, valid)['primary']['capped']
    return dict(confirmed_lost=len(before - after), confirmed_gained=len(after - before),
                task_lost=bool(before) and not after, task_gained=not before and bool(after),
                fa_before=a['fa_tests'], fa_after=b['fa_tests'], tests_before=a['tests'], tests_after=b['tests'])


def score():
    excluded = set(json.loads((OUT / 'excluded_problems.json').read_text())) if (OUT / 'excluded_problems.json').is_file() else set()
    probs = json.loads((OUT / 'problems.json').read_text())
    pid_of = {cid: p for p, cids in probs.items() for cid in cids}
    status = {}
    for p in probs:
        if p in excluded:
            continue
        for arm in ARMS:
            path = OUT / 'answers' / f'{p}_{arm}.txt'
            status[f'{p}_{arm}'] = checks(path.read_text())[2] if path.is_file() else 'missing'
    blocked = sorted(k for k, s in status.items() if s in ('missing', 'parse_error'))
    if blocked:  # registered: no verdict until every included answer is present and parseable
        print(json.dumps(dict(verdict='incomplete', blocked=blocked), indent=1))
        return 1
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    cohort, _, records, picks = ready
    run = E.ft_run.FTRun('vibepass_half')
    official = E.Reference(run)
    official.root = O.OUT / 'references' / 'official'
    cases = {c['case_id']: c for c in run.cases}
    prep = inv.read(E.select.OUT / 'prepared.json')
    tasks, answers = {}, {}
    for cid in cohort:
        if pid_of[cid] in excluded:
            continue
        rec, case = records[cid], cases[cid]
        inputs = E.ordered(rec['inputs'])
        truth = O.task_truth(inv, case, rec, official, E.all_inputs(prep[cid]) | set(picks[cid]))
        accepts, info = {}, {}
        for arm in ARMS:
            key = f'{pid_of[cid]}_{arm}'
            code, found, st = checks((OUT / 'answers' / f'{key}.txt').read_text())
            if found:
                accepts[arm], kept = run_checks(case, rec, arm, code, found, inputs)
            else:
                accepts[arm], kept = {l: True for l in inputs}, 0
            info[arm] = dict(status=st, checks=len(found), kept=kept)
            answers.setdefault(key, dict(status=st, checks=found))
        accepts['tool'], info['tool'] = tool_accept(case, rec, inputs)
        put = {l: E.iorel.value(rec['inputs'][l]['put']) for l in inputs}
        invalid = [l for l in inputs if not truth[l]['valid']]
        valid = [l for l in inputs if truth[l]['valid']]
        exposing = [l for l in inputs if R.exposing(truth[l], put[l])]
        oracles = {'qwen_defn': (O.oracle_rows(rec, 'defn'), len(rec['families']['defn']['valid_programs']))}
        if cid in P.TASKS:
            oracles['sonnet_defn'] = (P.sonnet(case, rec, 'defn', inputs, set())[0], 3)
        tasks[cid] = dict(problem=pid_of[cid], inputs=len(inputs), invalid=len(invalid), valid=len(valid),
                          exposing=len(exposing), arms={})
        for arm, acc in accepts.items():
            tasks[cid]['arms'][arm] = dict(info[arm], invalid_caught=sum(not acc[l] for l in invalid),
                                           valid_rejected=sum(not acc[l] for l in valid),
                                           exposing_rejected=sum(not acc[l] for l in exposing),
                                           oracles={o: effect(inputs, acc, rows, truth, v) for o, (rows, v) in oracles.items()})
    totals = {}
    for arm in (*ARMS, 'tool'):
        t = collections.Counter()
        for row in tasks.values():
            a = row['arms'][arm]
            t.update(invalid=row['invalid'], valid=row['valid'], exposing=row['exposing'],
                     invalid_caught=a['invalid_caught'], valid_rejected=a['valid_rejected'],
                     exposing_rejected=a['exposing_rejected'])
            for o, e in a['oracles'].items():
                t.update({f'{o}_{k}': int(v) for k, v in e.items()})
        t = dict(t)
        t['recall'] = t['invalid_caught'] / t['invalid'] if t['invalid'] else None
        t['valid_rejected_rate'] = t['valid_rejected'] / t['valid'] if t['valid'] else None
        totals[arm] = t

    def safe(arm, ref):
        a, r = totals[arm], totals[ref]
        return dict(valid_rejected_le_1pct=(a['valid_rejected_rate'] or 0) <= 0.01,
                    exposing_le_ref=a['exposing_rejected'] <= r['exposing_rejected'],
                    **{f'{o}_no_task_lost': a.get(f'{o}_task_lost', 0) == 0 for o in ('qwen_defn', 'sonnet_defn')},
                    **{f'{o}_lost_le_ref': a.get(f'{o}_confirmed_lost', 0) <= r.get(f'{o}_confirmed_lost', 0)
                       for o in ('qwen_defn', 'sonnet_defn')})
    c, o, l = totals['concept'], totals['open'], totals['lines']
    primary = dict(recall_margin=(c['recall'] or 0) - (o['recall'] or 0),
                   checks=dict(recall=(c['recall'] or 0) >= (o['recall'] or 0) + 0.10, **safe('concept', 'open')))
    primary['verdict'] = 'promising' if all(primary['checks'].values()) else 'not promising'
    taxonomy = dict(recall_margin=(c['recall'] or 0) - (l['recall'] or 0), report_only=True, safety=safe('concept', 'lines'))
    out = dict(decision=dict(primary=primary, taxonomy_vs_lines=taxonomy), totals=totals, tasks=tasks,
               answers=answers, answer_status=status, excluded_problems=sorted(excluded))
    O.immutable(OUT / 'score.json', out)
    print(json.dumps(dict(decision=out['decision'], totals=totals), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(dict(prompts=prompts, score=score)[sys.argv[1]]() or 0)
