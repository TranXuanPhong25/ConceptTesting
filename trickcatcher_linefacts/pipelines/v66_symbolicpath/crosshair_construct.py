"""CrossHair path exploration for the v57 objective: reach site AND local difference AND output difference.

Unchanged pinned CrossHair/Z3 explore the source-derived path conditions; every symbolic witness is
realized to concrete values and re-executed by an isolated CPython worker before it counts.
"""
import collections
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import crosshair
import crosshair.core_and_libs  # noqa: F401  registers library symbolic support
from crosshair.core import deep_realize, explore_paths
from crosshair.options import DEFAULT_OPTIONS
from crosshair.statespace import RootNode
from crosshair.tracers import NoTracing
from crosshair.util import IgnoreAttempt
import z3

from . import path_domain, path_instrument, value_graph

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


class Witness:
    __slots__ = ('put', 'alt', 'index')

    def __init__(self, put, alt, index):
        self.put, self.alt, self.index = put, alt, index


def same(a, b):
    return type(a) is type(b) and a == b


def sandbox_preflight():
    try:
        return subprocess.run(['unshare', '-rn', 'true'], timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def native_replay(source, entry, args_graph, hypothesis, deadline):
    """Two independent worker processes with different hash seeds; both must agree."""
    rows = [_worker(source, entry, args_graph, hypothesis, deadline, seed) for seed in ('0', '65')]
    bad = next((r for r in rows if r.get('status') != 'ok'), None)
    if bad is not None:
        return bad
    return {'status': 'ok', 'runs': [rows[0]['run'], rows[1]['run']]}


def _worker(source, entry, args_graph, hypothesis, deadline, hash_seed):
    if time.monotonic() >= deadline:
        return {'status': 'replay_deadline'}
    with tempfile.TemporaryDirectory(prefix='v66-replay-') as directory:
        folder = Path(directory); job, output = folder / 'job.json', folder / 'result.json'
        job.write_text(json.dumps(dict(source=source, entry=entry, arguments=args_graph, hypothesis=hypothesis, repo=str(REPO))))
        env = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': hash_seed}
        p = subprocess.Popen(['unshare', '-rn', sys.executable, '-I', '-B', str(HERE / 'native_replay.py'), str(job), str(output)],
                             cwd=folder, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            status = p.wait(timeout=max(.001, min(20, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL); p.wait()
            return {'status': 'worker_timeout'}
        if status or not output.exists() or output.stat().st_size > 4_000_000:
            return {'status': 'worker_error', 'exit_code': status}
        return {'status': 'ok', **json.loads(output.read_text())}


def certify(candidate, observed):
    """Concrete CPython must reproduce the realized symbolic witness exactly, twice."""
    if observed.get('status') != 'ok':
        return False, observed.get('status', 'worker_error')
    runs = observed['runs']
    if len(runs) != 2 or runs[0] != runs[1]:
        return False, 'native_nondeterministic'
    run = runs[0]
    put, alt = run['put'], run['alternative']
    if put['status'] != 'ok' or alt['status'] != 'ok':
        return False, 'native_not_normal_return'
    if run['plain_put'] != put['output'] or run['plain_alternative'] != alt['output']:
        return False, 'instrumentation_changed_output'
    if run['local_difference_index'] is None:
        return False, 'native_no_local_difference_with_equal_prestate'
    if put['output'] == alt['output']:
        return False, 'native_no_output_difference'
    if run['local_difference_index'] != candidate['local_difference_index']:
        return False, 'symbolic_native_local_index_mismatch'
    if put['output'] != candidate['symbolic_put_output'] or alt['output'] != candidate['symbolic_alternative_output']:
        return False, 'symbolic_native_output_mismatch'
    if put['branches'] != candidate['put_branches'] or alt['branches'] != candidate['alternative_branches']:
        return False, 'symbolic_native_branch_mismatch'
    if put['events'] != candidate['put_events'] or alt['events'] != candidate['alternative_events']:
        return False, 'symbolic_native_site_mismatch'
    return True, 'exact_site_prestate_path_and_output_replayed'


def encode_events(events):
    return [dict(frame=b[1], prestate=value_graph.encode(dict(b[2]), observation=True),
                 value=value_graph.encode(v, observation=True), branch_prefix=b[3]) for b, v in events]


def construct(source, entry, seeds, hypothesis, config):
    start = time.monotonic()
    budget = config['case_timeout_seconds']
    deadline = start + budget
    report = dict(hypothesis=hypothesis, backend='crosshair', status='not_started', inputs=[], issues=[],
                  rejected_models=[], path_outcomes={}, normative_validity='unknown_spec_validation_required',
                  library=dict(crosshair=crosshair.__version__, z3=z3.get_full_version()))
    bounds = dict(int_bound=config['int_bound'], max_seq_len=config['max_seq_len'], nested_max_len=config['nested_max_len'])
    try:
        profile = path_domain.profiles(seeds)
        sig = path_domain.signature(source, entry, profile)
        recorders = (path_instrument.Recorder(), path_instrument.Recorder())
        programs = tuple(path_instrument.load_program(source, entry, hypothesis, variant=v, recorder=r)
                         for v, r in zip((False, True), recorders))
    except Exception as exc:  # any load failure keeps the hypothesis in the denominator as unsupported
        report.update(status='unsupported', issues=[type(exc).__name__ + ':' + str(exc)[:160]], elapsed_seconds=round(time.monotonic() - start, 4))
        return report
    report['domain'] = dict(profile=profile, bounds=bounds, origin='public example types; finite search bounds, not validity rules')
    outcomes = collections.Counter()
    candidates = []

    def run(bound):
        args = bound.args
        if not all(path_domain.in_domain(a, p, bounds) for a, p in zip(args, profile)):
            raise IgnoreAttempt('outside_search_domain')
        outputs = []
        for program, recorder in zip(programs, recorders):
            recorder.events, recorder.branches = [], []
            outputs.append(program(*copy.deepcopy(args)))
        index = path_instrument.local_difference(recorders[0], recorders[1], hypothesis['family'], same)
        if index is None:
            return None
        if same(outputs[0], outputs[1]):
            return None
        return Witness(outputs[0], outputs[1], index)

    def done(space, pre, post, ret, exc, stack):
        if exc is not None:
            outcomes['exception:' + type(exc).__name__] += 1
            return False
        if not isinstance(ret, Witness):
            outcomes['no_local_or_output_difference'] += 1
            return False
        space.detach_path()
        outcomes['symbolic_witness'] += 1
        try:
            realized = deep_realize((tuple(pre.args), ret.put, ret.alt, ret.index, list(recorders[0].branches),
                                     list(recorders[1].branches), list(recorders[0].events), list(recorders[1].events)))
            assertions = space.solver.sexpr()[:200000]
            # Containers built while CrossHair traces are its shell types; encode realized values untraced (v66 Amendment 2).
            with NoTracing():
                args, put, alt, index, put_b, alt_b, put_e, alt_e = realized
                row = json.loads(json.dumps(dict(
                    arguments=repr(args), argument_graph=value_graph.encode(args),
                    symbolic_put_output=value_graph.encode(put, observation=True),
                    symbolic_alternative_output=value_graph.encode(alt, observation=True),
                    local_difference_index=index, put_branches=[list(x) for x in put_b],
                    alternative_branches=[list(x) for x in alt_b], put_events=encode_events(put_e),
                    alternative_events=encode_events(alt_e), solver_assertions=str(assertions))))
                opaque = 'opaque' in json.dumps([row['symbolic_put_output'], row['symbolic_alternative_output']])
        except Exception as exc:
            outcomes['realization:' + type(exc).__name__ + ':' + str(exc)[:80]] += 1
            return False
        if opaque:
            # Contents of unencoded objects cannot be compared exactly; never certify through them.
            outcomes['unsupported_opaque_output'] += 1
            return False
        if row['arguments'] not in {c['arguments'] for c in candidates}:
            candidates.append(row)
        return len(candidates) >= config['models_per_hypothesis']

    options = DEFAULT_OPTIONS.overlay(per_condition_timeout=budget, per_path_timeout=config['per_path_timeout_seconds'],
                                      max_iterations=config['max_paths'], stats=collections.Counter())
    try:
        explore_paths(run, sig, options, RootNode(), done, on_nondeterminism=lambda: outcomes.update(['nondeterministic_path']))
    except Exception as exc:  # library failure is unknown, never a witness or UNSAT
        report['issues'].append('explore_error:' + type(exc).__name__ + ':' + str(exc)[:160])
    report['path_outcomes'] = dict(outcomes)
    report['crosshair_stats'] = {k: v for k, v in options.stats.items()}
    replay_deadline = time.monotonic() + config['replay_timeout_seconds']
    for row in candidates:
        observed = native_replay(source, entry, row['argument_graph'], hypothesis, replay_deadline)
        ok, reason = certify(row, observed)
        if ok:
            row.update(verification=reason, observations=observed)
            report['inputs'].append(row)
        else:
            report['rejected_models'].append(dict(arguments=row['arguments'], reason=reason, observations=observed))
    elapsed = time.monotonic() - start
    if elapsed > budget + config['replay_timeout_seconds']:
        report['issues'].append('budget_overrun')
    if report['inputs']:
        report['status'] = 'verified_behavioral_difference'
    elif report['rejected_models']:
        report['status'] = 'replay_rejected'
    elif any(i.startswith('explore_error:') for i in report['issues']):
        report['status'] = 'unknown_library_error'
    elif any(k.startswith('realization:') or k == 'unsupported_opaque_output' for k in outcomes):
        report['status'] = 'unknown_realization'
    elif max(sum(outcomes.values()), options.stats.get('num_paths', 0)) >= config['max_paths'] or elapsed >= budget:
        # Search stopped by its cap, not by exhausting the bounded domain.
        report['status'] = 'unknown_timeout_or_cap'
    else:
        # Exhausted bounded search without a witness; still not program-level equivalence or UNSAT.
        report['status'] = 'bounded_no_witness'
    report['issues'] = sorted(set(report['issues']))
    report['elapsed_seconds'] = round(elapsed, 4)
    return report
