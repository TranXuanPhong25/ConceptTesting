"""Three real dev tasks, scripted fake completions, real namespace sandboxes."""
import argparse
import ast
import contextlib
import io
import json
import re
import socket
import tempfile
from pathlib import Path
from unittest.mock import patch
from . import paths, run_v4, v4_callfb, v4_runtime
from .offline_client import request

HERE = Path(__file__).resolve().parent
BUNDLE = paths.REPO / 'trickcatcher_linefacts/out/tasks_v7hyb_v4.json'


def dev_tasks():
    tasks = [t for t in json.loads(BUNDLE.read_text())['tasks'] if t['task'] in (2, 3, 4)]
    if len(tasks) != 3 or any(t['split'] != 'dev' for t in tasks):
        raise ValueError('expected dev tasks 2, 3, 4 in the historical v7 bundle')
    return tasks


class ScriptedClient:
    """No transport, credentials, environment access, or PUT execution."""
    model = paths.CONFIG['model']
    plans = {
        'truncate_number': ('-1.0', '2.5', '1.0', '123.0', '4.0'),
        'below_zero': ("'invalid'", '[]', '[1]', '[-1]', '[1, -1]'),
        'mean_absolute_deviation': ('[]', '[1.0, 2.0]', '[1.0]', '[2.0]', '[3.0]'),
    }
    first = {'truncate_number': 'assert truncate_number(2.5) == 0.5',
             'below_zero': 'assert below_zero([]) == False',
             'mean_absolute_deviation': 'assert mean_absolute_deviation([1.0, 2.0]) == 0.5'}

    def __init__(self, empty_target=False, empty_plain=False):
        self.requests = []
        self.empty_target, self.empty_plain = empty_target, empty_plain

    def chat(self, messages, seed, **kwargs):
        key, params = request(messages, seed, self.model, **kwargs)
        body = messages[1]['content']
        entry = next(n for n in self.plans if re.search(r'\b'+n+r'\s*\(', body))
        plan = self.plans[entry]
        if messages[0]['content'] == v4_callfb.SYSTEM:
            targeted = '\n\nHINT:\n' in body
            retry = (seed - v4_callfb.SEED_BASE) % 4
            empty = self.empty_target if targeted else self.empty_plain
            values = [plan[0]] * 5 if empty or retry == 0 else (
                [plan[1]] * 5 if retry == 1 else list(plan[2:]) + [plan[2], plan[3]])
            text = '\n'.join(f'{entry}({value})' for value in values)
        elif 'sample_one' in body:
            text = f'def sample_one():\n    return ({plan[1]},)'
        elif body.startswith('SPECIFICATION:') and 'For each call below write' in body:
            calls = re.findall(r'^'+entry+r'\(.*\)$', body, re.M)
            # Zero is an intentionally scripted fake expected value. The dry run
            # checks execution/protocol, never model quality or bug detection.
            text = '\n'.join(f'assert {call} == 0' for call in calls)
            text += f'\nassert {entry}({plan[0]}) == 999'  # must be filtered
        else:
            text = self.first[entry]
        result = dict(key=key, params=params, text='```python\n'+text+'\n```',
                      n_in=0, n_out=0, seconds=0, cache_hit=False)
        self.requests.append(dict(seed=seed, key=key, system=messages[0]['content']))
        return result


def execute(python=None, *, client=None):
    client = client or ScriptedClient()
    python = v4_runtime.interpreter(python)
    tasks = dev_tasks()
    with tempfile.TemporaryDirectory(prefix='offline-dry-', dir=HERE) as tmp:
        root = Path(tmp)
        def safe(path):
            path = Path(path).resolve()
            if root != path and root not in path.parents:
                raise ValueError('offline dry-run output escaped its new-folder temporary directory')
            return path
        with patch.object(run_v4, 'safe_path', safe), patch.object(socket, 'create_connection',
                side_effect=AssertionError('network forbidden in offline dry run')):
            with contextlib.redirect_stdout(io.StringIO()):
                output = run_v4.run(tasks, root/'generation', python, client=client, k=1, workers=1)
            rows = [json.loads(line) for line in output.read_text().splitlines()]
        for row in rows:
            if not row['arm'].endswith('-hybrid'):
                continue
            selected = {r['input_repr'] for r in row['selected_inputs']}
            task = next(t for t in tasks if t['task']==row['task'])
            final_calls = {v4_callfb.literal_call(ast.unparse(
                ast.parse(a).body[0].test.left), task)['input_repr']
                for a in row['assertions']}
            original_calls = {v4_callfb.literal_call(ast.unparse(ast.parse(a).body[0].test.left),task)['input_repr']
                              for a in row['round1_assertions']}
            assert selected <= final_calls
            assert final_calls == original_calls | selected
            assert row['round2_oracle_requests'] == int(bool(selected))
        for task in tasks:
            concept = next(r for r in rows if r['task']==task['task'] and r['arm']=='concept-hybrid')
            plain = next(r for r in rows if r['task']==task['task'] and r['arm']=='plain-hybrid')
            assert concept['round2_proposal_requests'] == plain['round2_proposal_requests']
        return dict(tasks=[t['task'] for t in tasks], rows=len(rows), physical_fake_requests=len(client.requests),
                    hybrid=[{k:r[k] for k in ('task','arm','round2_proposal_requests','round2_oracle_requests',
                                             'round2_proposal_schedule','round2_missing_expected_calls')}
                            | dict(kept=len(r['selected_inputs'])) for r in rows if r['arm'].endswith('-hybrid')])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--summary', type=Path, default=HERE/'validation/dry_run_summary.json')
    args = parser.parse_args()
    summary_path = args.summary.resolve()
    if HERE not in summary_path.parents:
        parser.error('summary must be inside pipelines/v9_callfb')
    result = execute(args.python)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
