import json, sys, re, ast
from pathlib import Path
H = Path('/home/phong/dev/ConceptTester/trickcatcher_linefacts'); sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob
W = Path('/home/phong/.claude/jobs/08a7596f/tmp/why')
hep = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, ob.HEP.open())}
runs = {'v3m2hyb': 'gen2_qwen7b_v3m2hyb_v4', 'advhyb': 'gen2_qwen7b_advhyb_v4_partial', 'em': 'gen2_qwen7b_evalmitigate'}
keep = {'concept-hybrid', 'plain-hybrid', 'concept', 'plain', 'toolinput', 'advdoc-hybrid', 'advdoc-plainhybrid', 'advdoc', 'onlydoc'}
calls, rows_all, tasks = {}, [], {}
for name, d in runs.items():
    tk, rows = ob.load_run(H/'out'/d)
    tasks.update(tk)
    gen = {(g['task'], g['arm'], g['sample']): g for g in map(json.loads, open(H/'out'/d/'gen.jsonl'))}
    for r in rows:
        if r['arm'] not in keep or r['split'] != 'dev': continue
        entry = tk[r['task']]['entry']; g = gen[r['task'], r['arm'], r['sample']]
        c_all = [ob.call_of(a['src'], entry) for a in r['asserts']]
        c_r1 = [ob.call_of(a, entry) for a in g['round1_assertions']] if 'round1_assertions' in g else c_all
        r = dict(r, round2_strategy_requests=g.get('round2_strategy_requests', 0), round1_input_summary=g.get('round1_input_summary'))
        rows_all.append(dict(task=r['task'], arm=r['arm'], sample=r['sample'], all=[c for c in c_all if c], r1=[c for c in c_r1 if c],
                             r2req=r.get('round2_strategy_requests', 0), r1sum=r.get('round1_input_summary'), nshown=None))
        calls.setdefault(r['task'], set()).update(c for c in c_all if c)
(W/'jobs').mkdir(exist_ok=True)
for t, cs in calls.items():
    h = hep[t]
    json.dump(dict(entry=tasks[t]['entry'], put=tasks[t]['put'], canon=h['prompt'] + h['canonical_solution'],
                   contract=h['prompt'] + h['contract'] + '\n    pass\n', atol=h['atol'], calls=sorted(cs)), open(W/'jobs'/f'{t}.job.json', 'w'))
json.dump(rows_all, open(W/'rows.json', 'w'))
# base test inputs (normalised calls)
base = {}
for t in calls:
    entry = tasks[t]['entry']; src = tasks[t]['base']
    found = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'candidate':
            node.func.id = entry
            try: found.add(ast.unparse(node))
            except Exception: pass
    base[t] = sorted(found)
json.dump(base, open(W/'base.json', 'w'))
print(len(rows_all), 'rows', len(calls), 'tasks', sum(map(len, calls.values())), 'calls')
