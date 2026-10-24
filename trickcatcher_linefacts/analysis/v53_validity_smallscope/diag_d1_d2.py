"""$0 diagnostics before v53: D1 are FA inputs detectable from the spec's Constraints? D2 how small are exposing inputs?"""
import ast, collections, json, re, sys
sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v52_sonnet_defn import pilot as P
from trickcatcher_linefacts.analysis.v49_defn_oracle import plan_rules as R
from trickcatcher_linefacts.analysis.v48_e2e_oracle import menu_fixed as M
O, E = P.O, P.E

def size(v):
    if isinstance(v, str): return len(v)
    if isinstance(v, (list, tuple)): return sum(max(1, size(e)) if isinstance(e, (list, tuple, str)) else 1 for e in v)
    return 1

def maxint(v):
    if isinstance(v, bool): return 0
    if isinstance(v, int): return abs(v)
    if isinstance(v, (list, tuple)): return max([maxint(e) for e in v] or [0])
    return 0

def violates(x, cons):
    for (i, kind), (lo, hi) in cons.items():
        if i >= len(x): continue
        v = x[i]
        if kind == 'length' and isinstance(v, (list, str)) and not lo <= len(v) <= hi: return f'len(arg{i})={len(v)}∉[{lo},{hi}]'
        if kind == 'value' and isinstance(v, int) and not isinstance(v, bool) and not lo <= v <= hi: return f'arg{i}={v}∉[{lo},{hi}]'
        if kind == 'elem' and isinstance(v, list):
            bad = [e for e in v if isinstance(e, int) and not lo <= e <= hi]
            if bad: return f'arg{i} elem {bad[0]}∉[{lo},{hi}]'
        if kind == 'elem2' and isinstance(v, list):
            bad = [e for r in v if isinstance(r, list) for e in r if isinstance(e, int) and not lo <= e <= hi]
            if bad: return f'arg{i} elem2 {bad[0]}∉[{lo},{hi}]'
    return None

inv = O.Inventory(); _, ready = O.score_inputs(inv); cohort, _, records, picks = ready
run = E.ft_run.FTRun('vibepass_half'); official = E.Reference(run); official.root = O.OUT / 'references' / 'official'
cases = {c['case_id']: c for c in run.cases}; prep = inv.read(E.select.OUT / 'prepared.json')
d1 = {}; d2 = {}
for cid in cohort:
    rec, case = records[cid], cases[cid]
    task = E.task_view(case)
    names = re.findall(r'(\w+)\s*:', task['signature'].split('->')[0])
    cons, unsupported = M.constraints_report(task['spec'], names)
    inputs = E.ordered(rec['inputs'])
    truth = O.task_truth(inv, case, rec, official, E.all_inputs(prep[cid]) | set(picks[cid]))
    fams = {'qwen_defn': O.oracle_rows(rec, 'defn')}
    if cid in P.TASKS:
        fams['sonnet_defn'] = P.sonnet(case, rec, 'defn', inputs, set())[0]
    # D1: FA tests whose input is invalid by the hidden contract: caught by spec bounds?
    for fam, rows in fams.items():
        labels = O.labels_for(rows, truth)
        for lit in E.emitted(set(inputs), rows, 'primary', 20):
            if labels[lit]['primary'] != 'confirmed' and not truth[lit]['valid']:
                x = ast.literal_eval(lit)
                d1.setdefault(fam, []).append(dict(task=cid, caught=violates(x, cons), size=size(x)))
    # D2: exposing inputs (official where computed, else valid ∧ ref ≠ PUT): size and finishing
    exp = [lit for lit in inputs if R.exposing(truth[lit], E.iorel.value(rec['inputs'][lit]['put']))]
    if exp:
        sizes = sorted(size(ast.literal_eval(l)) for l in exp)
        fin = {}
        for fam, rows in fams.items():
            V = len(rows[exp[0]]['programs'])
            q = max(2, V // 2 + 1)
            fin[fam] = dict(V=V, quorum_finishes=sum(sum(bool(o and o[0] == 'ok') for o in rows[l]['programs']) >= q for l in exp))
        d2[cid] = dict(exposing=len(exp), min_size=sizes[0], median_size=sizes[len(sizes)//2], small_le6=sum(s <= 6 for s in sizes),
                       small_le10=sum(s <= 10 for s in sizes), finishes=fin, n_cons=len(cons), unsupported=len(unsupported))
    else:
        d2[cid] = dict(exposing=0, n_cons=len(cons), unsupported=len(unsupported))
out = dict(d1={f: dict(total=len(v), caught_by_spec_bounds=sum(bool(r['caught']) for r in v),
                       by_task={t: [sum(1 for r in v if r['task'] == t), sum(1 for r in v if r['task'] == t and r['caught'])] for t in sorted({r['task'] for r in v}, key=int)},
                       examples=[r for r in v if r['caught']][:3]) for f, v in d1.items()}, d2=d2)
print(json.dumps(out, indent=1, ensure_ascii=False))
