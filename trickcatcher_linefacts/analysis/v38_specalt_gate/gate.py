"""v38 spec-alternative gate (see PREREG.md). CPU only: existing Qwen DPP programs vs PUT on the v37 EvalPlus pool.
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v38_specalt_gate/gate.py
"""
import ast
import collections
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trickcatcher_linefacts.pipelines.v34_ftplacebo import flow_run, ft_run

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v37_mokav_gate'))
from gate import pool, same, value  # noqa: E402  (v37 pool and comparison, unchanged)

HERE = Path(__file__).resolve().parent
LF = HERE.parents[1]
OUT = LF / 'out' / 'analysis' / 'v38_specalt_gate'
V37 = LF / 'out' / 'analysis' / 'v37_mokav_gate'
REFS = LF / 'out' / 'oracle_v7hyb_witness' / 'ref_responses.json'


def code_block(text):  # B2 parser (pipelines/v7/oracle_b01.py)
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def analyse(case, heps, programs, v37rows):
    hep = heps[int(case['case_id'])]
    atol = hep.get('atol') or 0
    seeds = ft_run.base_inputs(case, 'pilot20')
    U = pool(hep)
    progs = {f'p{i}': src for i, src in enumerate(programs.get(case['case_id'], []))}
    work = OUT / 'pilot20' / case['case_id']
    srcs = {'put': case['source'], **progs}
    base = ft_run.execute(work / 'base', srcs, list(srcs), case['entry'], seeds) if seeds else {k: [] for k in srcs}
    valid = [n for n in progs if base[n] and all(same(a, b, atol) for a, b in zip(base['put'], base[n]))]
    srcs = {'put': case['source'], 'ref': hep['prompt'] + hep['canonical_solution'], **{n: progs[n] for n in valid}}
    res = ft_run.execute(work / 'U', srcs, list(srcs), case['entry'], U)
    put, ref = res['put'], res['ref']
    exposed = [i for i in range(len(U)) if same(put[i], ref[i], atol) is False]
    witness = [n for n in valid if any(same(res[n][i], ref[i], atol) for i in exposed)]
    consensus_det, consensus_right = 0, 0
    for i in range(len(U)):
        outs = [res[n][i] for n in valid]
        if len(valid) < 3 or any(same(outs[0], o, atol) is not True for o in outs[1:]):
            continue
        if same(outs[0], put[i], atol) is False:
            consensus_det += 1
            consensus_right += same(put[i], ref[i], atol) is False and bool(same(outs[0], ref[i], atol))
    tmpl = v37rows[case['case_id']]['template_exposed']
    return dict(case_id=case['case_id'], programs=len(progs), valid=len(valid), exposed=len(exposed), witnesses=len(witness),
                consensus_det_inputs=consensus_det, consensus_correct_det=consensus_right,
                C=bool(witness), consensus=consensus_right > 0, template_exposed=tmpl, H=bool(witness) and not tmpl)


def main():
    paths = flow_run.dataset_paths()
    heps = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, paths['oracle_hep'].read_text().splitlines())}
    programs = collections.defaultdict(list)
    for r in sorted(json.loads(REFS.read_text()), key=lambda r: (str(r['task']), r['sample'])):
        src = code_block(r['text'])
        if src:
            programs[str(r['task'])].append(src)
    v37rows = {r['case_id']: r for r in json.loads((V37 / 'gate.json').read_text())['rows']}
    cases = flow_run.cohort('pilot20')
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(lambda c: analyse(c, heps, programs, v37rows), cases))
    s = lambda k: sum(bool(r[k]) for r in rows)
    det = sum(r['consensus_det_inputs'] for r in rows)
    summary = dict(tasks=len(rows), C=s('C'), H=s('H'), consensus_witness_tasks=s('consensus'),
                   consensus_det_inputs=det, consensus_det_precision=(sum(r['consensus_correct_det'] for r in rows) / det) if det else None,
                   tasks_with_det=sum(r['consensus_det_inputs'] > 0 for r in rows),
                   G1=s('C') >= 10, G2=s('H') >= 3)
    summary['verdict'] = 'go' if summary['G1'] and summary['G2'] else ('no-go: G1' if not summary['G1'] else 'no-go: G2')
    (OUT / 'gate.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1) + '\n')
    print(json.dumps(summary))
    for r in rows:
        print(r)


if __name__ == '__main__':
    sys.exit(main())
