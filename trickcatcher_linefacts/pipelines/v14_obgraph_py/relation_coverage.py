"""Offline coverage of the frozen 133-task v7 hint selection (no LLM)."""
import argparse
import hashlib
import json
from pathlib import Path
from . import relations
from .paths import HERE, REPO

DEFAULT_TASKS = REPO / 'trickcatcher_linefacts/out/tasks_v7hyb_v4.json'


def report(source=DEFAULT_TASKS, output=HERE/'RELATIONS.md'):
    source, output = Path(source), Path(output).resolve()
    if HERE.resolve() not in output.parents:
        raise ValueError('coverage output must be inside v12_rel')
    raw = source.read_bytes()
    tasks = json.loads(raw)['tasks']
    if len(tasks) != 133 or len({t['task'] for t in tasks}) != 133:
        raise ValueError('expected the frozen 133-task cohort')
    totals = dict(tasks=133, hints=0, data=0, control=0, spec=0, all_three=0,
                  any_edge=0, parameter_anchors=0, base_failures=0, base_trace_timeouts=0,
                  witness_trace_timeouts=0)
    counts = {k:0 for k in ('data','control','spec')}
    per_task, examples = [], []
    for t in tasks:
        r = relations.extract(t)
        totals['base_failures'] += r['base_ok'] is not True
        totals['base_trace_timeouts'] += r['base_trace_statuses'].get('timeout',0)
        totals['witness_trace_timeouts'] += r['witness_trace_statuses'].get('timeout',0)
        hints = r['hints']
        totals['hints'] += len(hints)
        for h in hints:
            for key in counts:
                totals[key] += bool(h[key])
                counts[key] += len(h[key]) if key != 'spec' else bool(h[key])
            totals['all_three'] += all(h[k] for k in counts)
            totals['any_edge'] += any(h[k] for k in counts)
            totals['parameter_anchors'] += h['site']=='parameter definition'
        per_task.append(dict(task=t['task'], split=t['split'], **r))
        for h in hints:
            if h['control'] and h['data'] and len(examples)<4:
                examples.append((t['task'],h['hint_index'],relations.render(h)))
    artifact = dict(summary=totals, edge_counts=counts, source=str(source.relative_to(REPO)),
                    source_sha256=hashlib.sha256(raw).hexdigest(), version=relations.VERSION,
                    extractor_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('relations.py','tracer.py')}, tasks=per_task)
    output.with_suffix('.json').write_text(json.dumps(artifact,indent=2)+'\n')
    lines = ['# v12_rel offline relation coverage', '',
             f"Source: `{artifact['source']}`; SHA256 `{artifact['source_sha256']}`.",
             'Frozen v7 selections, in their original order; includes 113 dev and 20 pilot tasks. No ranking, fuzz mining, or LLM calls.', '',
             '| Item | Count |', '| --- | ---: |']
    lines += [f'| {key} | {value} |' for key,value in totals.items()]
    lines += ['', 'Counts above are hints with at least one edge of that type. Individual edge counts: '+json.dumps(counts,sort_keys=True)+'.', '',
              '## Method and limits', '',
              'AST enclosing if/while/for guards; branch outcomes come only from base tracer cells. '
              '`always` / `never` describe evaluations of that guard, not every base test. '
              'A guard absent from all base executions is labelled `not evaluated`; a truncated base trace makes the outcome unknown.', '',
              'Def-use edges are observed by the unchanged tracer while replaying base inputs and the selected fuzz witnesses. '
              'There is no speculative static reaching-definition fallback. Loop-carried and same-line def-use edges are retained. '
              'Comprehensions/lambdas have limited def-use instrumentation; mutation of an object is not a new variable definition. '
              'Only syntactically enclosing guards are included, not a full postdominator control-dependence graph; loop else exhaustion without break has no tracer probe and is omitted.', '',
              'SPEC hints without a line are anchored at the relevant parameter definition, with no invented data/control edge. '
              'Docstring prose before the first doctest is split into sentences; maximum identifier/operator word overlap wins, '
              'ties choose the first sentence, zero overlap gives no spec edge. This is lexical evidence, not proof of a specification obligation.', '',
              'Witness values are replayed internally and are absent from chains and this report. '
              'The JSON companion contains per-task, per-hint relations and provenance.', '', '## Examples', '']
    for task,index,chain in examples:
        lines += [f'HumanEval/{task}, selected hint {index+1}:', '', chain, '']
    output.write_text('\n'.join(lines)+'\n')
    return artifact


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tasks',type=Path,default=DEFAULT_TASKS)
    ap.add_argument('--output',type=Path,default=HERE/'RELATIONS.md')
    a = ap.parse_args()
    print(json.dumps(report(a.tasks,a.output)['summary'],sort_keys=True))
