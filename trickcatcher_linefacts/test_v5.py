"""Offline integration checks with canned strategies; writes only to a fresh scratch directory."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
from trickcatcher_linefacts import run_v5, v5_offline, v4_runtime


class Canned:
    model = 'qwen2.5-coder-7b-instruct'
    def __init__(self, replies):
        self.replies = iter(replies); self.calls = []

    def chat(self, messages, seed, **kwargs):
        self.calls.append(dict(messages=messages, seed=seed, **kwargs))
        return dict(text=next(self.replies), n_in=0, n_out=0, seconds=0)


def run(root, python, original_facts=None):
    bundle, tasks, he = run_v5.inputs(run_v5.INPUT, run_v5.PRECOND, [2,3,4])
    config = run_v5.provenance(tasks, he, run_v5.PRECOND, 'mutmut', 'v3mm')
    fd = run_v5.manifest(root/'facts_v3mm', config)
    records = [run_v5.build_one(t, he, run_v5.PRECOND, 'mutmut', fd, python, 'v3mm') for t in tasks]
    for t, fr in zip(tasks, records):
        old = json.loads((HERE/'out/facts_v3m2'/f"{t['task']}.json").read_text())
        for key in ('fuzz_validity','n_fuzz','valid_sha256','doc_fail','base_ok'):
            assert fr[key] == old[key], (t['task'], key)
        assert [f for f in fr['facts'] if f['kind'] != 'MUTANT'] == [f for f in old['facts'] if f['kind'] != 'MUTANT']
        assert all('mutant_src' in f for f in fr['facts']+fr['placebo_all'] if f['kind'] == 'MUTANT')
    run_v5.bundle_facts(bundle, tasks, records, root/'tasks_v3mm_all.json', config)
    v5_offline.evaluate('v3mm', root/'tasks_v3mm_all.json', fd, root/'offline_v3mm', python, workers=3)
    # Real DEV tasks: validators exclude some tempting witnesses; no live client is constructed.
    client = Canned(['def strategy():\n    return st.just(2.5)\n']*60)
    mined = run_v5.mine_tasks(tasks, he, run_v5.PRECOND, 'mutmut', root/'strategies', python, 1, client)
    assert not mined[2]['gaps']  # task 4 has no gaps and consumes no calls
    assert all(len(r['attempts']) <= 2 for t in mined for r in t['gaps'])
    assert all(c['temperature'] == 0 and c['top_p'] == 1 and c['max_tokens'] == 4096 for c in client.calls)
    # Exercise the public final-facts CLI and immutable resume.
    command = [str(python), '-B', str(HERE/'run_v5.py'), 'facts', '--mutant-source', 'mutmut',
        '--task-ids', '2','3','4', '--workers','3', '--strategy-dir', str(root/'strategies'),
        '--facts-dir',str(root/'facts_v5'), '--tasks-path',str(root/'tasks_v5_all.json')]
    subprocess.run(command, check=True)
    subprocess.run(command, check=True)
    v5_offline.evaluate('v5', root/'tasks_v5_all.json', root/'facts_v5', root/'offline_v5', python, workers=3)

    # A gap v3 fuzz cannot reach, with a validator forbidding the negative solution.
    src = 'def target(x: int):\n    """x is a positive integer."""\n    if x*x == 1369:\n        return 1\n    return 0\n'
    base = 'def check(candidate):\n    assert candidate(2) == 0\n'
    task = dict(task=2, entry='target', put=src, base=base, split='dev',
                mined_valid_src='def valid(x):\n    return isinstance(x, int) and x > 0\n')
    pred = root/'fixture_valid/2'; pred.mkdir(parents=True)
    (pred/'valid.py').write_text(task['mined_valid_src'])
    row = dict(task_id='HumanEval/2', entry_point='target', prompt=src, test=base)
    job = dict(task=task, he=row, precond_dir=str(pred.parent), mutant_source='handwritten', experiment='v5-base')
    fr = run_v5.isolated('facts', job, root/'fixture_base', python)
    i, fact = next((i,f) for i,f in enumerate(fr['facts']) if f['kind']=='OUTCOME' and not f['reached'])
    fact = {k:v for k,v in fact.items() if k not in ('reached','witness_call','block','g_demote','tier')}
    hit = 'def strategy():\n    return st.just(37)\n'
    cases = {
        'hit': [hit],
        'syntax': ['def strategy(:', hit],
        'draw_error': ['def strategy():\n    return st.integers(min_value="bad")\n', hit],
        'no_hit': ['def strategy():\n    return st.integers(min_value=100, max_value=10000)\n', hit],
        'invalid': ['def strategy():\n    return st.just(-37)\n', hit],
        'exhausted': ['def strategy():\n    return st.just(2)\n']*2,
    }
    for name,replies in cases.items():
        canned = Canned(replies)
        result = run_v5.mine_gap(task, fact, i, 0, fr['base_inputs'], canned, root/name, python)
        assert len(canned.calls) == len(replies)
        assert result['witness'] == (None if name == 'exhausted' else '(37,)')
        assert all(r['cap'] == 200 for r in result['attempts'])
        if name == 'no_hit':
            assert result['attempts'][0]['draw_stats']['attempts'] == 200
            assert '200 valid draws, none reached the fact' in canned.calls[1]['messages'][-1]['content']
        if name == 'invalid': assert result['attempts'][0]['draw_stats']['valid'] == 0
        if name == 'syntax': assert result['attempts'][0]['error'].startswith('SyntaxError')
        if name == 'hit':
            final = run_v5.isolated('facts', dict(job, experiment='v5', gaps=[result]), root/'fixture_final', python)
            assert final['facts'][i]['reached'] and final['facts'][i]['witness_call'] == 'target(37)'
            assert final['n_fuzz'] == fr['n_fuzz'] and final['fuzz_inputs'] == fr['fuzz_inputs']
            assert final['hypothesis_fallback']['reached'] == 1
    # Confirm the default path against the pre-edit implementation, ignoring wall time only.
    if original_facts:
        script = root/'regression.py'
        script.write_text('''import importlib.util, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import facts
spec = importlib.util.spec_from_file_location('original', sys.argv[2])
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
tasks = json.loads(Path(sys.argv[1], 'out/tasks_v3m2_all.json').read_text())['tasks']
he = {int(r['task_id'].split('/')[1]):r for r in map(json.loads, Path(sys.argv[1]).parent.joinpath('PBT_EdgeCases/run/data/humaneval.jsonl').open())}
for task in tasks:
    n = task['task']
    if n not in (2,3,4): continue
    results = []
    for module, label in ((old,'old'),(facts,'new')):
        output = Path(sys.argv[3], f'{label}_{n}.json')
        module.main(n, task['put'], he[n], output, validity='mined', precond_dir=Path(sys.argv[1], 'out/precond_qwen7b_v2'))
        value = json.loads(output.read_text()); value.pop('secs'); results.append(value)
    assert results[0] == results[1], n
print('default facts unchanged on DEV 2/3/4')
''')
        subprocess.run(['unshare','-rn',str(python),'-I','-B',str(script),str(HERE),str(original_facts),str(root)], check=True)
    print(f'v5 smoke checks passed: {root}', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--python', type=Path)
    p.add_argument('--out-dir', type=Path)
    p.add_argument('--original-facts', type=Path)
    a = p.parse_args()
    root = a.out_dir or Path(tempfile.mkdtemp(prefix='v5-smoke-'))
    root.mkdir(parents=True, exist_ok=True)
    run(root, v4_runtime.interpreter(a.python), a.original_facts)
