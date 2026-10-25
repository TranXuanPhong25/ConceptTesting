"""Freeze six outcome-blind dev requests using public fields and original PUTs only."""
import ast
import hashlib
import json
from pathlib import Path

from .deep_run import validate_request
from .public_adapter import adapt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LABEL = 'v57-ngrok-mechanism-20261024'


def prepare_pilot():
    ids = json.loads((HERE.parent / 'v31_faulttemplate' / 'vibepass_half.json').read_text())['tasks']
    selected = sorted(ids, key=lambda n: hashlib.sha256(f'{LABEL}:{n}'.encode()).hexdigest())[:6]
    root = REPO / 'trickcatcher_linefacts/out/heldout_vibepass_real/he'
    # The normalized public file also carries a canonical field. Project it away immediately, never pass it on.
    public = {}
    for line in (root / 'humaneval_mbpp.jsonl').read_text().splitlines():
        row = json.loads(line)
        public[int(row['task_id'].split('/')[-1])] = {key: row[key] for key in ('prompt', 'entry_point', 'test')}
    requests, limitations = [], []
    for n in selected:
        row = public[n]
        source = (root / 'PUTs' / f'HumanEval_{n}' / 'put0.py').read_text()
        try:
            prompt_tree = ast.parse(row['prompt'])
            fn = next(x for x in prompt_tree.body if isinstance(x, ast.FunctionDef) and x.name == row['entry_point'])
            spec = ast.get_docstring(fn, clean=False) or row['prompt']
        except (SyntaxError, StopIteration): spec = row['prompt']
        request, unsupported = adapt(source, row['entry_point'], row['test'], n, spec=spec)
        validate_request(request)
        requests.append(request)
        limitations.append(dict(case_id=str(n), skipped_asserts=unsupported))
    return dict(label=LABEL, selected_ids=selected, requests=requests, adapter_limitations=limitations,
                selection='first6 sha256(label:case_id) over frozen v31 dev33; no outcome filtering')


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    data = prepare_pilot()
    a.out.mkdir(parents=True, exist_ok=True)
    for name, value in [('requests.json', data['requests']), ('selection.json', {k: v for k, v in data.items() if k != 'requests'})]:
        with (a.out / name).open('x') as stream: json.dump(value, stream, indent=2)
    print(json.dumps(dict(selected_ids=data['selected_ids'], requests=len(data['requests']))))


if __name__ == '__main__': main()
