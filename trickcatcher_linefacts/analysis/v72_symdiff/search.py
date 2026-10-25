"""v72 CrossHair differential search on the public export (pinned CrossHair venv). No reference/contract access."""
import argparse
import collections
import copy
import json
from pathlib import Path
import time

import crosshair
import crosshair.core_and_libs  # noqa: F401
from crosshair.core import deep_realize, explore_paths
from crosshair.options import DEFAULT_OPTIONS
from crosshair.statespace import RootNode
from crosshair.tracers import NoTracing
from crosshair.util import IgnoreAttempt
import ast
import inspect
import z3

from trickcatcher_linefacts.pipelines.v66_symbolicpath import path_domain

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / HERE.name
BOUNDS = dict(int_bound=1000, max_seq_len=6, nested_max_len=4)
BUDGET = dict(per_condition_timeout=300, per_path_timeout=2.0, max_iterations=5000, witnesses=5)


class Witness:
    def __init__(self, put, value):
        self.put, self.value = put, value


def load(source, entry):
    namespace = {'__name__': '__v72__'}
    exec(compile(source, '<v72>', 'exec'), namespace)
    return namespace[entry]


def same(a, b):
    return type(a) is type(b) and a == b


def signature(entry, profile):
    return inspect.Signature([inspect.Parameter(f'a{i}', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                                annotation=path_domain.annotation(p)) for i, p in enumerate(profile)])


def search(row):
    start = time.monotonic()
    seeds = [ast.literal_eval(x) for x in row['base_inputs']]
    report = dict(case_id=row['case_id'], witnesses=[], outcomes={}, issues=[])
    try:
        profile = path_domain.profiles(seeds)
        sig = signature(row['entry'], profile)
        put = load(row['put_source'], row['entry'])
        programs = [load(src, row['entry']) for src in row['programs']]
        checkers = [load(src, row['entry']) for src in row['checkers']]
    except Exception as exc:
        report.update(status='unsupported', issues=[type(exc).__name__ + ':' + str(exc)[:160]])
        return report
    outcomes = collections.Counter()

    def run(bound):
        args = tuple(bound.args)
        if not all(path_domain.in_domain(a, p, BOUNDS) for a, p in zip(args, profile)):
            raise IgnoreAttempt('outside_search_domain')
        for check in checkers:
            try:
                accepted = check(*copy.deepcopy(args))
            except Exception:
                raise IgnoreAttempt('checker_error')
            if not accepted:
                raise IgnoreAttempt('checker_rejects')
        observed = put(*copy.deepcopy(args))
        outs = []
        for program in programs:
            try:
                outs.append((True, program(*copy.deepcopy(args))))
            except Exception:
                outs.append((False, None))
        values = [v for ok, v in outs if ok]
        for i, v in enumerate(values):
            if sum(1 for w in values if same(w, v)) >= 2 and not same(v, observed):
                return Witness(observed, v)
        return None

    def done(space, pre, post, ret, exc, stack):
        if exc is not None:
            outcomes['exception:' + type(exc).__name__] += 1
            return False
        if not isinstance(ret, Witness):
            outcomes['no_disagreement'] += 1
            return False
        space.detach_path()
        try:
            args = deep_realize(tuple(pre.args))
            with NoTracing():
                text = repr(args)
        except Exception as exc:
            outcomes['realization:' + type(exc).__name__] += 1
            return False
        outcomes['symbolic_witness'] += 1
        if text not in report['witnesses']:
            report['witnesses'].append(text)
        return len(report['witnesses']) >= BUDGET['witnesses']

    options = DEFAULT_OPTIONS.overlay(per_condition_timeout=BUDGET['per_condition_timeout'], per_path_timeout=BUDGET['per_path_timeout'],
                                      max_iterations=BUDGET['max_iterations'], stats=collections.Counter())
    try:
        explore_paths(run, sig, options, RootNode(), done, on_nondeterminism=lambda: outcomes.update(['nondeterministic_path']))
    except Exception as exc:
        report['issues'].append('explore_error:' + type(exc).__name__ + ':' + str(exc)[:160])
    report.update(outcomes=dict(outcomes), crosshair_stats=dict(options.stats), elapsed=round(time.monotonic() - start, 2),
                  status='witness' if report['witnesses'] else 'no_witness_within_budget')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    row = next(r for r in json.loads((OUT / 'public_export.json').read_text()) if r['case_id'] == args.case)
    target = OUT / 'search' / f'{args.case}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SystemExit('exists')
    report = search(row)
    report['library'] = dict(crosshair=crosshair.__version__, z3=z3.get_full_version(), budget=BUDGET, bounds=BOUNDS)
    with target.open('x') as stream:
        json.dump(report, stream, indent=1)
    print(json.dumps({k: report[k] for k in ('case_id', 'status', 'witnesses', 'outcomes')})[:600])


if __name__ == '__main__':
    main()
