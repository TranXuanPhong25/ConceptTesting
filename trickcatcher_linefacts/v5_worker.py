"""Isolated v3mm/v5 facts and targeted draws; no method-side plus data."""
import ast
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import facts
from trickcatcher_linefacts import preconditions, v4_runtime, v4_worker
from trickcatcher_linefacts.llm_client import atomic_json
from tracer import HOOKS, alarm, call, dcopy, fact_hit, instrument, load_module, run_base, trace


def build(job, directory):
    task = job['task']; n = task['task']
    points = None
    if job['mutant_source'] == 'mutmut':
        from trickcatcher_linefacts.v4_tools import enumerate_mutants
        points = enumerate_mutants(task['put'], directory)
    captured = {}

    def evidence(ctx):
        captured['base_inputs'] = [repr(a) for a in ctx['base_args']]
        captured['fuzz_inputs'] = [repr(a) for a in ctx['fz']]
        frozen = ctx['facts']
        gaps = [i for i,f in enumerate(frozen) if f['witness'] is None][:10]
        valid = preconditions.load_predicate(task['mined_valid_src'], 'valid')
        for row in job.get('gaps', []):
            i = row['fact_index']; f = frozen[i]
            if i not in gaps or row['fact'] != f:
                raise ValueError('fallback fact/order mismatch')
            literal = row.get('witness')
            if literal is None: continue
            args = (ast.literal_eval(literal), {})
            with alarm(1): accepted = valid(*dcopy(args[0])) is True
            if not accepted: raise ValueError('fallback witness violates mined validator')
            tr = trace(ctx['iput'], args)
            mout = call(ctx['mfns'][f['k']], args) if f['kind'] == 'MUTANT' else None
            if not fact_hit(f, tr, call(ctx['put'], args), mout):
                raise ValueError('fallback witness does not reach its fact')
            f['witness'] = len(ctx['fz'])
            ctx['fz'].append(args); ctx['fz_traces'].append(tr)
            ctx['fz_cells'].append(tr[0]); ctx['fz_lines'].append(tr[1]); ctx['fz_out'].append(tr[2:])

    output = directory/'facts.json'
    facts.main(n, task['put'], job['he'], output, validity='mined', precond_dir=job['precond_dir'],
               mutant_points=points, evidence=evidence)
    result = json.loads(output.read_text())
    result.update(captured, experiment=job['experiment'], mutant_source=job['mutant_source'])
    if job['experiment'] == 'v5':
        result['hypothesis_fallback'] = dict(gaps=len(job['gaps']),
            reached=sum(r['witness'] is not None for r in job['gaps']),
            witnesses=[dict(fact_index=r['fact_index'], input_repr=r['witness']) for r in job['gaps'] if r['witness'] is not None])
    return result


def targeted(job):
    task, fact = job['task'], job['fact']
    result = v4_worker.draw(dict(task=task, code=job['code'], seed=job['seed'], n=200, cap=200))
    result['validator'] = 'mined'
    result.update(witness=None, trace_errors=[])
    # Verification is the same as v4: malformed draws invalidate a strategy, even if another draw hits.
    if result['errors'] or result['wrong_arity'] or result['nonliteral']:
        return result
    pg = load_module(task['put']); put = pg[task['entry']]
    code, _ = instrument(task['put']); iput = load_module(code, HOOKS)[task['entry']]
    mutant = None
    if fact['kind'] == 'MUTANT':
        source = fact.get('mutant_src') or facts.make_mutant(task['put'], fact['k'])[0]
        mutant = load_module(source)[task['entry']]
    for row in result['candidates']:
        args = (ast.literal_eval(row['input_repr']), {})
        try:
            with alarm(10):
                tr = trace(iput, args)
                hit = fact_hit(fact, tr, call(put, args), call(mutant, args) if mutant else None)
            if hit:
                result['witness'] = row['input_repr']; break
        except BaseException as exc:
            result['trace_errors'].append(dict(input_repr=row['input_repr'], error=type(exc).__name__))
    return result


def main(job_path, output_path):
    v4_runtime.require_versions()
    directory = Path(output_path).parent
    os.environ['HYPOTHESIS_STORAGE_DIRECTORY'] = str(directory/'.hypothesis')
    job = json.loads(Path(job_path).read_text())
    if job['mode'] == 'facts': result = build(job, directory)
    elif job['mode'] == 'targeted': result = targeted(job)
    elif job['mode'] == 'offline':
        from trickcatcher_linefacts import offline
        os.environ['OFFLINE_SKIP_PILOT'] = '1'
        offline.worker(job['task'], job['facts_path'], output_path)
        return
    else: raise ValueError(job['mode'])
    atomic_json(output_path, result)


if __name__ == '__main__':
    try: main(*sys.argv[1:])
    except Exception as exc:
        atomic_json(sys.argv[2], dict(worker_error=f'{type(exc).__name__}: {str(exc)[:1000]}'))
