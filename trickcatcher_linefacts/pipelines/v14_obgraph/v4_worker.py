"""All PUT, mutant, validator and strategy execution is isolated by v4_runtime."""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import ast
import builtins
import contextlib
import io
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

from . import preconditions, v4_runtime
from .llm_client import atomic_json


def draw(job):
    import typing
    from hypothesis import given, settings, Phase, HealthCheck, seed, assume, strategies as st
    from hypothesis.errors import Unsatisfiable
    from .tracer import alarm, dcopy
    from .v4_strategies import checked, TYPES
    task = job['task']
    # Recheck untrusted syntax inside the sandbox, including trusted from_type fallback.
    code = checked(job['code'])
    ns = {'__builtins__': {n:getattr(builtins,n) for n in preconditions.SAFE_BUILTINS}, 'st':st,
          **{n:getattr(typing,n) for n in TYPES}, 'object':object, 'bytes':bytes, 'frozenset':frozenset}
    valid = preconditions.load_predicate(task['mined_valid_src'], 'valid')
    with alarm(5):
        exec(compile(code,'<strategy>','exec'),ns)
        strategy = ns['strategy']()
    trigger_errors = []
    if job.get('trigger_src'):
        trigger = preconditions.load_predicate(job['trigger_src'], 'trigger')
        from .gen_inputs import arity
        size = arity(task)
        def satisfies(args):
            if size == 1 and not (type(args) is tuple and len(args) == 1): args = (args,)
            elif type(args) is list and len(args) == size: args = tuple(args)
            if type(args) is not tuple or len(args) != size: return False
            from .tracer import call
            status, value = call(trigger, (args, {}), T=1)
            if status != 'ok' and len(trigger_errors) < 20: trigger_errors.append(status)
            return status == 'ok' and value is True
        strategy = strategy.filter(satisfies)
    from .hypothesis_replay import freeze_local_constants
    freeze_local_constants()
    n, cap = job['n'], job['cap']
    result = dict(attempts=0, checked=0, invalid=0, valid=0, accepted=0, duplicate=0, oversize=0,
                  nonliteral=0, wrong_arity=0, errors=[], candidates=[], cap=cap, requested=n)
    seen = set(job.get('exclude',()))
    from .gen_inputs import arity, MAX_INPUT_CHARS
    size = arity(task)

    class Finished(BaseException): pass

    @seed(job['seed'])
    @settings(max_examples=cap, database=None, deadline=None, phases=(Phase.generate,),
              suppress_health_check=(HealthCheck.too_slow,HealthCheck.filter_too_much))
    @given(strategy)
    def collect(args):
        if result['attempts'] >= cap or len(result['candidates']) >= n:
            raise Finished()
        result['attempts'] += 1
        # A strategy for a one-parameter function may draw the argument itself; a list of the right length is a tuple.
        if size == 1 and not (type(args) is tuple and len(args) == 1):
            args = (args,)
        elif type(args) is list and len(args) == size:
            args = tuple(args)
        if type(args) is not tuple or len(args) != size:
            result['wrong_arity'] += 1; assume(False)
        literal = repr(args)
        if len(literal)>MAX_INPUT_CHARS:
            result['oversize'] += 1; assume(False)
        try:
            restored = ast.literal_eval(literal)
            if type(restored) is not tuple or restored != args:
                raise ValueError('literal roundtrip')
        except (ValueError,SyntaxError,TypeError,RecursionError):
            result['nonliteral'] += 1; assume(False)
        result['checked'] += 1
        try:
            with alarm(1): accepted = valid(*dcopy(args)) is True
        except BaseException:
            accepted = False
        if not accepted: result['invalid'] += 1
        assume(accepted)
        result['accepted'] += 1
        if literal in seen:
            result['duplicate'] += 1; assume(False)
        seen.add(literal)
        result['candidates'].append(dict(input_repr=literal))
        result['valid'] += 1

    try:
        collect()
    except Finished:
        pass
    except Unsatisfiable:
        if not result['candidates']: result['errors'].append('no valid draws (Unsatisfiable)')
    except BaseException as exc:
        result['errors'].append(f'{type(exc).__name__}: {str(exc)[:500]}')
    result.update(valid_rate=result['valid']/max(1,result['attempts']),
                  contract_valid_rate=result['accepted']/max(1,result['checked']), validator='B5')
    if job.get('trigger_src'):
        result.update(trigger_errors=trigger_errors, filter_usable=not trigger_errors)
    return result


def capture(task, assertions):
    from .tracer import alarm, dcopy, load_module
    pg = load_module(task['put']); fn = pg[task['entry']]
    calls, errors = [], []
    def wrapped(*args, **kwargs):
        calls.append((dcopy(args),dcopy(kwargs)))
        return fn(*args,**kwargs)
    for src in assertions:
        ns = dict(pg); ns[task['entry']] = wrapped
        try:
            with contextlib.redirect_stdout(io.StringIO()), alarm(5):
                exec('import math\n'+src,ns)
        except BaseException as exc:
            errors.append(type(exc).__name__)
    # Normalize keyword calls using the actual signature; no loss of kwargs/defaults.
    import inspect
    signature = inspect.signature(fn)
    candidates = []
    for args,kwargs in calls:
        try:
            bound = signature.bind(*args,**kwargs); bound.apply_defaults()
            args = tuple(bound.arguments[name] for name in signature.parameters)
            literal = repr(args)
            if len(literal)<=1000 and ast.literal_eval(literal)==args:
                candidates.append(dict(input_repr=literal))
        except (TypeError,ValueError,SyntaxError):
            pass
    return candidates, errors


def classify(job, directory):
    from .tracer import HOOKS, alarm, call, dcopy, fact_hit, instrument, load_module
    from .v4_tools import Coverage
    from . import spec_facts
    task, shown = job['task'], job.get('shown',[])
    valid = preconditions.load_predicate(task['mined_valid_src'],'valid')
    pg = load_module(task['put']); put = pg[task['entry']]
    code,_ = instrument(task['put']); iput = load_module(code,HOOKS)[task['entry']]
    coverage = Coverage(task['put'],task['entry'],directory)
    facts = task['concept_meta']+shown
    mutants = {f['k']:load_module(f['mutant_src'])[task['entry']] for f in facts if f['kind']=='MUTANT'}
    candidates = job.get('candidates',[])
    capture_errors = []
    if 'assertions' in job:
        candidates,capture_errors = capture(task,job['assertions'])
    rows, seen = [], set()
    for candidate in candidates:
        literal = candidate['input_repr']
        if literal in seen: continue
        seen.add(literal)
        row = dict(candidate, valid=False, concept_hits=[False]*len(task['concept_meta']), shown_hits=[False]*len(shown))
        try:
            if len(literal)>1000: raise ValueError('oversize')
            args = ast.literal_eval(literal)
            with alarm(1): accepted = valid(*dcopy(args)) is True
            row.update(valid=accepted, contract_error=None if accepted else 'B5 precondition rejected input')
            row['call'] = task['entry']+'('+', '.join(repr(a) for a in args)+')'
            if accepted:
                with alarm(10):
                    tr = coverage.trace(iput,(args,{})); pout = call(put,(args,{})) if mutants else None
                    mouts = {k:call(fn,(args,{})) for k,fn in mutants.items()}
                    hits = [spec_facts.in_class(f['input_class']['cls'],args[f['input_class']['param']]) if 'input_class' in f else fact_hit(f,tr,pout,mouts.get(f.get('k'))) for f in facts]  # v7 spec facts: input-class hit
                row.update(concept_hits=hits[:len(task['concept_meta'])],shown_hits=hits[len(task['concept_meta']):])
        except BaseException as exc:
            row['contract_error' if not row['valid'] else 'trace_error'] = type(exc).__name__
        rows.append(row)
    good = [r for r in rows if r['valid']]
    counts=[sum(r['concept_hits'][i] for r in good) for i in range(len(task['concept_meta']))]
    return dict(records=rows,capture_errors=capture_errors,summary=dict(candidates=len(rows),valid=len(good),
                removed=len(rows)-len(good), raw_candidates=sum(r.get('occurrences',1) for r in rows),
                raw_valid=sum(r.get('occurrences',1) for r in good), requested_draws=job.get('requested_draws',len(rows)),
                oversize=sum(len(r['input_repr'])>1000 for r in rows),trace_errors=sum('trace_error' in r for r in rows),
                first_contract_message=next((r.get('contract_error') for r in rows if not r['valid']),None),
                concept_hit_rates=[c/max(1,len(good)) for c in counts],
                concept_hit_counts=[sum(r['concept_hits'][i] for r in good) for i in range(len(task['concept_meta']))],
                shown_hit_counts=[sum(r['shown_hits'][i] for r in good) for i in range(len(shown))]))


def main(job_path, output_path):
    v4_runtime.require_versions()
    os.environ['HYPOTHESIS_STORAGE_DIRECTORY'] = str(Path(output_path).parent/'.hypothesis')
    job = json.loads(Path(job_path).read_text())
    mode = job['mode']
    if mode.startswith('hyp_'):
        from . import hyp_worker
        if mode == 'hyp_candidates': result = hyp_worker.candidates(job['task'], Path(output_path).parent)
        elif mode == 'hyp_check': result = hyp_worker.check(job)
        elif mode == 'hyp_classify': result = hyp_worker.classify(job, Path(output_path).parent)
        elif mode == 'hyp_draw': result = hyp_worker.filtered_draw(job)
        elif mode == 'hyp_attribution': result = hyp_worker.attribution(job)
        else: raise ValueError(mode)
    elif mode == 'relations':
        from .relations import extract
        result = extract(job['task'])
    elif mode == 'draw': result = draw(job)
    elif mode == 'classify': result = classify(job,Path(output_path).parent)
    elif mode == 'facts':
        from .v4_facts import build
        result = build(job,Path(output_path).parent)
    elif mode == 'evaluate':
        from .v4_evaluation import worker
        result = worker(job,Path(output_path).parent)
    elif mode == 'offline':
        from .v4_offline import worker
        result = worker(job,Path(output_path).parent)
    else: raise ValueError(mode)
    atomic_json(output_path,result)


if __name__=='__main__':
    try:
        main(*sys.argv[1:])
    except Exception as exc:
        atomic_json(sys.argv[2],dict(worker_error=f'{type(exc).__name__}: {str(exc)[:1000]}'))
