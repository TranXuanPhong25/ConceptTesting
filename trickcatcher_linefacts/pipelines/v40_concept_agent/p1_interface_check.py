"""P1 CPU interface check on real PUTs: CFG support and trace-proof rates on public docstring example inputs.

No model calls, no reference/oracle, no witness selection by outcome. Reports mechanism coverage only, never efficacy.
Usage: PYTHONPATH=<repo> $V4_PYTHON -m trickcatcher_linefacts.pipelines.v21_flowtools.p1_interface_check [--limit N]
"""
import argparse
import ast
import collections
import json
from concurrent.futures import ThreadPoolExecutor
from . import source_view, flow_tools
from .chain_inputs import literal_for_transport
from .llm_client import atomic_json
from .paths import CONFIG, DATA_OUT, dataset_paths

OUT = DATA_OUT / 'p1_interface'


def docstring_inputs(task):
    """Public `>>> entry(...)` examples in the PUT docstring; literal positional calls only, first 6 unique."""
    out = []
    for line in task['spec'].splitlines():
        line = line.strip()
        if not line.startswith('>>> '):
            continue
        try:
            call = ast.parse(line[4:], mode='eval').body
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == task['entry']) or call.keywords:
                continue
            literal = literal_for_transport(tuple(ast.literal_eval(a) for a in call.args))
        except (SyntaxError, ValueError, TypeError):
            continue
        if literal not in out:
            out.append(literal)
    return out[:CONFIG['flowtools']['common_inputs']]


def one(row, entries, puts):
    tid = row['task']
    source = (puts / f'HumanEval_{tid}' / 'put0.py').read_text()
    rec = dict(task=tid, split=row['split'])
    try:
        task = source_view.prepare(source, entries[tid])
    except ValueError as exc:
        return dict(rec, status='prepare_failed', reason=str(exc))
    session = flow_tools.FlowSession(task, OUT / 'tasks' / str(tid) / 'discovery', arm='p1_interface_check')
    rec.update(cfg_supported=session.cfg['supported'], unsupported=session.cfg['unsupported'],
               statements=len(session.cfg['nodes']), control_dependence=session.cfg['control_dependence'] is not None)
    inputs = docstring_inputs(task)
    rec['inputs'] = len(inputs)
    results = session.discover(inputs) if inputs else []
    rec['native_checked'] = sum(1 for r in results if r.get('native_checked'))
    rec['proven'] = sum(1 for r in results if r.get('all_invocations_proven'))
    rec['complete'] = sum(1 for r in results if r.get('trace_complete'))
    breaks = collections.Counter()
    for r in results:
        internal = session.traces.get(r.get('trace'))
        for inv in (internal or {}).get('projection', {}).get('invocations', []):
            breaks.update(b['reason'] for b in inv['breaks'])
    rec['break_reasons'] = dict(breaks)
    rec['physical_processes'] = session.executor.physical
    return dict(rec, status='ok')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    paths = dataset_paths()
    entries = {}
    for line in paths['he'].read_text().splitlines():
        r = json.loads(line)
        entries[int(r['task_id'].split('/')[1])] = r['entry_point']
    rows = json.loads(paths['selection'].read_text())['tasks'][:args.limit]
    with ThreadPoolExecutor(CONFIG['workers']) as pool:
        recs = list(pool.map(lambda r: one(r, entries, paths['puts']), rows))
    ok = [r for r in recs if r['status'] == 'ok']
    unsupported = collections.Counter(u.split('@')[0] for r in ok for u in r['unsupported'])
    breaks = collections.Counter()
    for r in ok:
        breaks.update(r['break_reasons'])
    summary = dict(scope='P1 CPU interface only; docstring example inputs; no model, oracle or efficacy claim',
                   tasks=len(recs), prepared=len(ok), cfg_supported=sum(r['cfg_supported'] for r in ok),
                   control_dependence_available=sum(r['control_dependence'] for r in ok), unsupported_constructs=dict(unsupported),
                   tasks_with_inputs=sum(1 for r in ok if r['inputs']), inputs=sum(r['inputs'] for r in ok),
                   native_checked=sum(r['native_checked'] for r in ok), traces_complete=sum(r['complete'] for r in ok),
                   traces_proven_on_supported=sum(r['proven'] for r in ok if r['cfg_supported']),
                   inputs_on_supported=sum(r['inputs'] for r in ok if r['cfg_supported']), break_reasons=dict(breaks),
                   physical_processes=sum(r['physical_processes'] for r in ok), model_calls=0)
    atomic_json(OUT / 'summary.json', dict(summary=summary, tasks=recs))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
