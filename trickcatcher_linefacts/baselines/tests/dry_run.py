"""Reproducible CPU-only end-to-end verification on three HumanEval development tasks.

Run with the interpreter in CoverUp_concept/.venv, using -B. All written artifacts stay
below baselines/tests/dry_runs by default. No online client or endpoint configuration is used.
"""
import argparse
import ast
import json
import platform
import sys
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from trickcatcher_linefacts.baselines.common import HERE, atomic_json, cli
from trickcatcher_linefacts.baselines.coverup.run import generate as coverup, provenance as coverup_provenance
from trickcatcher_linefacts.baselines.mutap.run import generate as mutap, provenance as mutap_provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=HERE/'tests/dry_runs')
    args = parser.parse_args(argv)
    destination = args.out.resolve()
    # This verification entry point intentionally permits only the task's writable paths.
    destination.relative_to((HERE/'tests').resolve())
    report = dict(python=platform.python_version(),
                  dependencies={name: version(name) for name in ('pytest', 'coverage', 'mutmut', 'httpx')},
                  dataset='HumanEval development tasks 2, 3, 4', k=3,
                  llm='ScriptedClient; no network requests; token counts zero', baselines={})
    for arm, generate, provenance in [('coverup', coverup, coverup_provenance), ('mutap', mutap, mutap_provenance)]:
        out = destination/arm
        cli(arm, generate, provenance, ['--tasks', str(HERE/'tests/dev_tasks.json'),
                                      '--out', str(out), '--responses', str(HERE/'tests/dev_responses.json')])
        rows = [json.loads(line) for line in (out/'gen.jsonl').read_text().splitlines()]
        assert len(rows) == 9
        assert {(r['task'], r['sample']) for r in rows} == {(t, s) for t in (2, 3, 4) for s in range(3)}
        assert all(r['llm_calls'] <= 8 and r['n_assertions'] <= 20 and r['offline'] for r in rows)
        assert all(r['stop_reason'] not in ('base_failed', 'base_screen_failed', 'mutation_failed', 'suite_failed') for r in rows)
        for row in rows:
            ast.parse('\n'.join(row['assertions']))
            if arm == 'mutap':
                assert row['mutation_backend'] == 'mutmut' and row['n_live_selected'] <= 7
        report['baselines'][arm] = dict(rows=len(rows), llm_calls=sum(r['llm_calls'] for r in rows),
                                       assertions=sum(r['n_assertions'] for r in rows),
                                       dropped=sum(r['n_assertions_dropped'] for r in rows),
                                       stop_reasons=dict(Counter(r['stop_reason'] for r in rows)),
                                       per_sample=[{k: r[k] for k in ('task', 'sample', 'llm_calls', 'n_assertions', 'stop_reason')}
                                                   for r in rows],
                                       output=str(out.relative_to(HERE)/'gen.jsonl'))
    atomic_json(destination/'summary.json', report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
