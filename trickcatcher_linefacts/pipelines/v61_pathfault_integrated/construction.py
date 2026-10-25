"""Joint path/local-infection/output-propagation search and concrete certification."""
import ast
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import z3

from .symbolic import Evaluator, Unsupported, equal, input_shapes, materialize, symbolic_inputs

HERE = Path(__file__).resolve().parent


def encoded(value):
    if type(value) is range:
        return {'type': 'range', 'start': value.start, 'stop': value.stop, 'step': value.step}
    if value is None or type(value) in (int, bool, str):
        return {'type': type(value).__name__, 'repr': repr(value)}
    if type(value) in (list, tuple):
        return {'type': type(value).__name__, 'items': [encoded(x) for x in value]}
    raise Unsupported('predicted_output_type')


def replay(source, entry, args, hypothesis, deadline=None, seed=None, observe_only=False, observation_names=()):
    if deadline is not None and time.monotonic() >= deadline:
        return {'status': 'replay_deadline'}
    with tempfile.TemporaryDirectory(prefix='v57-replay-') as directory:
        folder = Path(directory); job, output = folder / 'job.json', folder / 'result.json'
        job.write_text(json.dumps(dict(source=source, entry=entry, arguments=repr(args), hypothesis=hypothesis, seed=seed, observe_only=observe_only, observation_names=list(observation_names))))
        env = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}
        if seed is not None:
            env['PYTHONHASHSEED'] = str(seed)
        # Sanitized environment contains no PYTHONPATH; -s excludes user site.
        # Do not use -I, which would ignore the registered PYTHONHASHSEED.
        p = subprocess.Popen(['unshare', '-rn', sys.executable, '-s', '-B', str(HERE / 'replay_worker.py'), str(job), str(output)],
                             cwd=folder, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try: status = p.wait(timeout=8 if deadline is None else max(.001, min(8, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL); p.wait()
            return {'status': 'worker_timeout'}
        if status or not output.exists() or output.stat().st_size > 1_000_000:
            return {'status': 'worker_error', 'exit_code': status}
        return {'status': 'ok', **json.loads(output.read_text())}


def branch_projection(branches):
    return [{'line': x['line'], 'value': x['value']} for x in branches]


def certify(candidate, observed):
    if observed.get('status') != 'ok': return False, observed.get('status', 'worker_error')
    put, alt = observed['put'], observed['alternative']
    if put['status'] != 'ok' or alt['status'] != 'ok': return False, 'replay_not_normal'
    if not put['site_events'] or not alt['site_events']: return False, 'exact_ast_site_not_reached'
    if put['output'] != candidate['predicted_put'] or alt['output'] != candidate['predicted_alternative']:
        return False, 'symbolic_concrete_output_mismatch'
    if put['output'] == alt['output']: return False, 'no_concrete_propagation'
    if put['branches'] != branch_projection(candidate['put_path']) or alt['branches'] != branch_projection(candidate['alternative_path']):
        return False, 'symbolic_concrete_branch_mismatch'
    if [e['value'] for e in put['site_events']] != candidate['predicted_site_values']:
        return False, 'symbolic_concrete_site_mismatch'
    return True, 'exact_site_path_and_output_verified'


def construct(source, entry, seeds, hypothesis, config):
    start = time.monotonic()
    deadline = start + config['case_timeout_seconds']
    report = dict(hypothesis=hypothesis, status='not_started', inputs=[], issues=[], queries=0,
                  solver_unknown=0, unsat_queries=0, rejected_models=[], shape_count=0,
                  normative_validity='unknown_spec_validation_required')
    try:
        shapes, truncated = input_shapes(seeds, config['max_seq_len'], config['max_shapes'])
    except Unsupported as exc:
        report.update(status='unsupported', issues=[str(exc)]); return report
    issues = {'shape_cap'} if truncated else set()
    for shape in shapes:
        if report['queries'] >= config.get('max_queries', 128):
            issues.add('query_cap'); break
        if len(report['inputs']) >= config['models_per_hypothesis']: break
        if time.monotonic() - start > config['case_timeout_seconds']:
            issues.add('construction_deadline'); break
        report['shape_count'] += 1
        args, domain = symbolic_inputs(shape, config['int_bound'], config['max_seq_len'])
        try:
            original = Evaluator(source, entry, hypothesis, max_steps=config['max_seq_len'], max_paths=config['max_paths'], deadline=deadline)
            alternative = Evaluator(source, entry, hypothesis, variant=True, max_steps=config['max_seq_len'], max_paths=config['max_paths'], deadline=deadline)
            put_states, alt_states = original.run(args), alternative.run(args)
            issues.update(original.issues | alternative.issues)
        except (Unsupported, StopIteration, z3.Z3Exception, ValueError, TypeError) as exc:
            issues.add(str(exc)); continue
        for put in put_states:
            if report['queries'] >= config.get('max_queries', 128):
                issues.add('query_cap'); break
            if len(report['inputs']) >= config['models_per_hypothesis']: break
            if not put.events: continue
            # A state accumulation obligation exercises repeated updates, not a single trivial visit.
            if hypothesis['family'] == 'STATE_ACCUMULATION' and len(put.events) < 2: continue
            for alt in alt_states:
                if report['queries'] >= config.get('max_queries', 128):
                    issues.add('query_cap'); break
                if time.monotonic() - start > config['case_timeout_seconds']:
                    issues.add('construction_deadline'); break
                solver = z3.Solver(); solver.set(timeout=max(1, min(config['solver_timeout_ms'], int((deadline - time.monotonic()) * 1000))), random_seed=57)
                try:
                    solver.add(*domain, *put.guards, *alt.guards,
                               z3.Or(*[e['condition'] for e in put.events]), z3.Not(equal(put.value, alt.value, typed=True)))
                except (Unsupported, z3.Z3Exception) as exc:
                    issues.add(str(exc)); continue
                for _ in range(config['models_per_hypothesis']):
                    if report['queries'] >= config.get('max_queries', 128):
                        issues.add('query_cap'); break
                    if time.monotonic() - start > config['case_timeout_seconds']:
                        issues.add('construction_deadline'); break
                    solver.set(timeout=max(1, min(config['solver_timeout_ms'], int((deadline - time.monotonic()) * 1000))))
                    report['queries'] += 1; result = solver.check()
                    if result == z3.unsat:
                        report['unsat_queries'] += 1; break
                    if result == z3.unknown:
                        report['solver_unknown'] += 1; issues.add('solver_unknown:' + solver.reason_unknown()); break
                    model = solver.model()
                    try:
                        values = tuple(materialize(a, model) for a in args)
                        candidate = dict(arguments=repr(values), predicted_put=encoded(materialize(put.value, model)),
                                         predicted_alternative=encoded(materialize(alt.value, model)),
                                         put_path=put.branches, alternative_path=alt.branches,
                                         predicted_site_values=[encoded(materialize(e['before'], model)) for e in put.events
                                                                if z3.is_true(model.eval(z3.And(*put.guards), model_completion=True))],
                                         path_predicates=[str(z3.simplify(g)) for g in put.guards],
                                         local_infection_predicates=[str(z3.simplify(e['condition'])) for e in put.events],
                                         domain=dict(shape=shape, int_bound=config['int_bound'], max_seq_len=config['max_seq_len']))
                        # A target inside short-circuit syntax has guarded events; retain only reached ones.
                        candidate['predicted_site_values'] = [encoded(materialize(e['before'], model)) for e in put.events
                                                               if z3.is_true(model.eval(e.get('reach', z3.And(*put.guards)), model_completion=True))]
                        seen = {x['arguments'] for x in report['inputs']}
                        if repr(values) not in seen:
                            observed = replay(source, entry, values, hypothesis, deadline=deadline)
                            ok, reason = certify(candidate, observed)
                            if ok:
                                candidate.update(verification=reason, observations=observed)
                                report['inputs'].append(candidate)
                            else: report['rejected_models'].append(dict(arguments=repr(values), reason=reason, observations=observed))
                        solver.add(z3.Not(z3.And(*[equal(a, b, typed=True) for a, b in zip(args, values)])))
                    except (Unsupported, z3.Z3Exception, ValueError, TypeError) as exc:
                        issues.add('model_materialization:' + str(exc)); break
                    if len(report['inputs']) >= config['models_per_hypothesis']: break
                if len(report['inputs']) >= config['models_per_hypothesis']: break
    report['issues'] = sorted(issues)
    if report['inputs']: report['status'] = 'verified_behavioral_difference'
    elif report['rejected_models']: report['status'] = 'replay_rejected'
    elif issues: report['status'] = 'unsupported_or_incomplete'
    else: report['status'] = 'bounded_no_difference'
    report['elapsed_seconds'] = round(time.monotonic() - start, 4)
    return report
