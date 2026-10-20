"""v37 Mokav gate (see PREREG.md). CPU only: v31 tool stage on pilot20 + PUT/ref/survivors on EvalPlus inputs.
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v37_mokav_gate/gate.py
"""
import ast
import json
import math
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trickcatcher_linefacts.pipelines.v34_ftplacebo import flow_run, ft_run

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v37_mokav_gate'
SEED, MAX_PLUS = 20261020, 300


def value(text):
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return text


def close(a, b, atol):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b or (math.isfinite(a) and math.isfinite(b) and abs(a - b) <= max(atol, 1e-6))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(close(x, y, atol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], atol) for k in a)
    return a == b


def same(o1, o2, atol):
    """None when not comparable (timeout / skipped)."""
    if not o1 or not o2 or o1[0] not in ('ok', 'exception') or o2[0] not in ('ok', 'exception'):
        return None
    if o1[0] != o2[0]:
        return False
    return o1[1] == o2[1] if o1[0] == 'exception' else close(value(o1[1]), value(o2[1]), atol)


def pool(hep):
    plus = list(hep['plus_input'])
    rng = random.Random(f'{SEED}/{hep["task_id"]}')
    if len(plus) > MAX_PLUS:
        plus = [plus[i] for i in sorted(rng.sample(range(len(plus)), MAX_PLUS))]
    return [list(x) for x in hep['base_input']] + [list(x) for x in plus]


def analyse(case, heps):
    root = OUT / 'pilot20'
    tool = ft_run.tool_stage(case, 'pilot20', root)
    work = root / 'cases' / case['case_id'] / 'tool'
    p2job = json.loads((work / 'phase2' / 'job.json').read_text()) if (work / 'phase2' / 'job.json').exists() else None
    p2 = json.loads((work / 'phase2' / 'result.json').read_text()) if p2job else None
    hep = heps[int(case['case_id'])]
    atol = hep.get('atol') or 0
    ref_src = hep['prompt'] + hep['canonical_solution']
    names = p2job['order'][1:] if p2job else []
    srcs = {'put': case['source'], 'ref': ref_src, **({n: p2job['sources'][n] for n in names} if p2job else {})}
    U = pool(hep)
    res = ft_run.execute(work / 'phase3_U', srcs, ['put', 'ref'] + names, case['entry'], U)
    put, ref = res['put'], res['ref']
    exposed = [i for i in range(len(U)) if same(put[i], ref[i], atol) is False]
    correcting, clean, noneq, rarity = [], [], [], []
    for n in names:
        m = res[n]
        if any(same(m[i], put[i], atol) is False for i in range(len(U))):
            noneq.append(n)
        fix = [i for i in exposed if same(m[i], ref[i], atol)]
        if fix:
            correcting.append(n)
            rarity.append((len(fix), sum(same(m[i], put[i], atol) is False for i in range(len(U))) / len(U)))
        comp = [same(m[i], ref[i], atol) for i in range(len(U))]
        if exposed and all(c is not False for c in comp) and any(c for c in comp):
            clean.append(n)
    # v31 template pool exposure (same comparison, reference run on the template candidates)
    tmpl_exposed = None
    if p2job:
        cand = [value(x) for x in p2job['inputs']]
        rt = ft_run.execute(work / 'phase2_ref', {'ref': ref_src}, ['ref'], case['entry'], cand)['ref']
        tmpl_exposed = sum(same(p2['put'][i], rt[i], atol) is False for i in range(len(cand)))
    best = max(rarity) if rarity else None
    return dict(case_id=case['case_id'], mutants=tool['mutants'], survivors=len(names), pool=len(U), exposed=len(exposed),
                correcting=len(correcting), clean=len(clean), non_equivalent=len(noneq),
                useful_share=(len(correcting) / len(noneq)) if noneq else None,
                best_det_rarity=best[1] if best else None, best_correcting_inputs=best[0] if best else None,
                template_candidates=len(p2job['inputs']) if p2job else 0, template_exposed=tmpl_exposed,
                C=bool(correcting), F=bool(clean), H=bool(correcting) and not tmpl_exposed, correcting_names=correcting[:20])


def main():
    paths = flow_run.dataset_paths()
    heps = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, paths['oracle_hep'].read_text().splitlines())}
    cases = flow_run.cohort('pilot20')
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(lambda c: analyse(c, heps), cases))
    s = lambda k: sum(r[k] for r in rows)
    summary = dict(tasks=len(rows), exposed=sum(r['exposed'] > 0 for r in rows), C=s('C'), F=s('F'), H=s('H'),
                   template_pool_exposed=sum(bool(r['template_exposed']) for r in rows),
                   G1=s('C') >= 10, G2=s('H') >= 3)
    summary['verdict'] = 'go' if summary['G1'] and summary['G2'] else ('no-go: G1' if not summary['G1'] else 'no-go: G2')
    (OUT / 'gate.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1) + '\n')
    print(json.dumps(summary))
    for r in rows:
        print({k: r[k] for k in ('case_id', 'survivors', 'exposed', 'correcting', 'clean', 'non_equivalent', 'best_det_rarity', 'template_exposed')})


if __name__ == '__main__':
    sys.exit(main())
