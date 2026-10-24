import ast, sys
sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v52_sonnet_defn import pilot as P
O, E = P.O, P.E
REL = {'87': lambda a: len(a[0]) == len(a[1]), '103': lambda a: a[1] < len(a[0]), '161': lambda a: len(str(a[0])) == len(str(a[1]))}
inv = O.Inventory(); _, ready = O.score_inputs(inv); _, _, records, picks = ready
run = E.ft_run.FTRun('vibepass_half'); official = E.Reference(run); official.root = O.OUT / 'references' / 'official'
cases = {c['case_id']: c for c in run.cases}; prep = inv.read(E.select.OUT / 'prepared.json')
for cid, ok in REL.items():
    rec, case = records[cid], cases[cid]; inputs = E.ordered(rec['inputs'])
    truth = O.task_truth(inv, case, rec, official, E.all_inputs(prep[cid]) | set(picks[cid]))
    rows = P.sonnet(case, rec, 'defn', inputs, set())[0]; labels = O.labels_for(rows, truth)
    fa = [l for l in E.emitted(set(inputs), rows, 'primary', 20) if labels[l]['primary'] != 'confirmed']
    inval = [l for l in fa if not truth[l]['valid']]
    caught = [l for l in inval if not ok(ast.literal_eval(l))]
    # how many confirmed tests would the relation filter remove (must be 0)
    conf = [l for l in E.emitted(set(inputs), rows, 'primary', 20) if labels[l]['primary'] == 'confirmed']
    print(cid, 'FA', len(fa), 'invalid', len(inval), 'caught by relation', len(caught), '| confirmed tests removed by relation', sum(not ok(ast.literal_eval(l)) for l in conf), '| universe inputs violating relation', sum(not ok(ast.literal_eval(l)) for l in inputs), '/', len(inputs))
