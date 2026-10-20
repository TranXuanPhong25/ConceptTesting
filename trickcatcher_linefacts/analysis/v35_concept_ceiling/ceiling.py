"""v35 concept ceiling (CPU only). See PREREG.md. Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v35_concept_ceiling/ceiling.py
"""
import difflib
import json
import statistics
from pathlib import Path

from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, put_observation, same

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v35_concept_ceiling'


def obs(o):
    if not o or o[0] not in ('ok', 'exception'):
        return None
    return put_observation(dict(status='ok', native_checked=True, execution_status=o[0], output=o[1] if o[0] == 'ok' else None,
                                exception_type=o[1] if o[0] == 'exception' else 'None'))


def edited_line(put, mutant):
    a, b = put.split('\n'), mutant.split('\n')
    for tag, i1, _, _, _ in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != 'equal':
            return i1 + 1
    return None


def main():
    run = ft_run.FTRun('vibepass_half')
    ref = Reference(run)
    ref.root = OUT / 'reference'
    rows = []
    for case in run.cases:
        cid = case['case_id']
        base = run.root / 'cases' / cid
        tool = json.loads((base / 'tool.json').read_text())
        job = json.loads((base / 'tool' / 'phase2' / 'job.json').read_text())
        res = json.loads((base / 'tool' / 'phase2' / 'result.json').read_text())
        put_rows = res['put']
        exposing = {}
        for i, lit in enumerate(job['inputs']):
            put = obs(put_rows[i])
            if put is None or not ref.contract_valid(case, lit):
                continue
            truth = ref(case, lit)
            if truth is not None and not same(put, truth):
                exposing[i] = truth
        locating_lines, strict = set(), False
        for name in job['order'][1:]:
            outs = res.get(name) or []
            hits = [i for i, t in exposing.items() if i < len(outs) and obs(outs[i]) is not None and same(obs(outs[i]), t)]
            ran = [i for i in exposing if i < len(outs) and obs(outs[i]) is not None]
            if hits:
                locating_lines.add(edited_line(job['sources']['put'], job['sources'][name]))
            if ran and len(hits) == len(ran) == len(exposing):
                strict = True
        sites = [c for c in tool['concepts'] if c['type'] != 'MISSING_CASE' and c['line']]
        ranked_lines = [r['line'] for r in tool['ranked'] if r.get('line')]
        first = next((k + 1 for k, l in enumerate(ranked_lines) if l in locating_lines), None)
        rows.append(dict(case_id=cid, exposing_inputs=len(exposing), locating_mutant_lines=sorted(l for l in locating_lines if l),
                         ceiling=bool(locating_lines), strict_ceiling=strict,
                         top1_hit=bool(sites) and sites[0]['line'] in locating_lines,
                         any_concept_hit=any(c['line'] in locating_lines for c in sites),
                         first_locating_rank=first, ranked_sites=len(ranked_lines)))
    n = len(rows)
    ceiling = sum(r['ceiling'] for r in rows)
    top1 = sum(r['top1_hit'] for r in rows)
    verdict = ('stop' if ceiling < 17 else 'ranking_bottleneck' if top1 < ceiling / 2 else 'llm_side')
    ranks = [r['first_locating_rank'] for r in rows if r['first_locating_rank']]
    summary = dict(n=n, pool_coverage=sum(r['exposing_inputs'] > 0 for r in rows), ceiling=ceiling,
                   strict_ceiling=sum(r['strict_ceiling'] for r in rows), top1_hit=top1,
                   any_concept_hit=sum(r['any_concept_hit'] for r in rows),
                   first_locating_rank_median=statistics.median(ranks) if ranks else None, verdict=verdict)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'ceiling.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
