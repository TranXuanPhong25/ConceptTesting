"""v39 spec-alternative gate on vibepass_half (see PREREG.md).
  source <qwen env>; PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v39_specalt_vibepass/gate.py generate|score
The endpoint URL comes from the environment only and is never written or printed.
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable
from trickcatcher_linefacts.pipelines.v7.oracle_b01 import code_block, dpp_templates

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v37_mokav_gate'))
from gate import same, value  # noqa: E402  (v37 comparison, unchanged)

HERE = Path(__file__).resolve().parent
LF = HERE.parents[1]
OUT = LF / 'out' / 'analysis' / 'v39_specalt_vibepass'
V35 = LF / 'out' / 'analysis' / 'v35_concept_ceiling' / 'ceiling.json'
ROOT = LF.parent / 'trickcatcher_linefacts/out/heldout_vibepass_real/he'
MODEL, NREF, SEED = 'qwen2.5-coder-32b-instruct', 10, 20261021


def tasks():
    run = ft_run.FTRun('vibepass_half')
    plus = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, (ROOT / 'humaneval_mbpp_plus.jsonl').read_text().splitlines())}
    return run.cases, plus


def generate():
    import openai
    client = openai.OpenAI(base_url=os.environ['QWEN_BASE_URL'], api_key=os.environ.get('QWEN_API_KEY', 'none'), timeout=300, max_retries=0)
    dsys, dusr = dpp_templates()
    cases, plus = tasks()
    questions = {}
    for c in cases:
        r = plus[int(c['case_id'])]
        questions.setdefault(r['question_id'], r['prompt'])
    jobs = [(q, s) for q in sorted(questions) for s in range(NREF)]

    def one(job):
        q, s = job
        path = OUT / 'programs' / f'{q}_{s}.json'
        if path.exists():
            return
        msgs = [dict(role='system', content=dsys), dict(role='user', content=dusr.replace('{signature_and_doctoring}', questions[q]))]
        try:
            r = client.chat.completions.create(model=MODEL, messages=msgs, temperature=0.8, top_p=0.95, max_tokens=2048,
                                               seed=SEED + 100 * int(q) + s)
            rec = dict(question=q, sample=s, text=r.choices[0].message.content, finish=r.choices[0].finish_reason,
                       usage=r.usage.model_dump() if r.usage else None)
        except Exception as exc:  # one attempt only (PREREG)
            rec = dict(question=q, sample=s, text=None, error=f'{type(exc).__name__}')
        immutable(path, rec)
    (OUT / 'programs').mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, jobs))
    recs = [json.loads(p.read_text()) for p in (OUT / 'programs').glob('*.json')]
    print(dict(calls=len(recs), failed=sum(r.get('text') is None for r in recs), length=sum(r.get('finish') == 'length' for r in recs)))


def analyse(case, r, programs, v35):
    atol = r.get('atol') or 0
    seeds = ft_run.base_inputs(case, 'vibepass_half')
    progs = {f'p{i}': src for i, src in enumerate(programs)}
    work = OUT / 'cases' / case['case_id']
    srcs = {'put': case['source'], **progs}
    base = ft_run.execute(work / 'base', srcs, list(srcs), case['entry'], seeds) if seeds else {k: [] for k in srcs}
    valid = [n for n in progs if base[n] and all(same(a, b, atol) for a, b in zip(base['put'], base[n]))]
    U = [list(x) for x in r['base_input']] + [list(x) for x in r['plus_input']]
    contract = r['prompt'] + r['contract'] + '\n    pass\n'
    srcs = {'put': case['source'], 'silver': r['prompt'] + r['canonical_solution'], 'contract': contract, **{n: progs[n] for n in valid}}
    res = ft_run.execute(work / 'U', srcs, list(srcs), case['entry'], U)
    keep = [i for i in range(len(U)) if res['contract'][i] and res['contract'][i][0] == 'ok']
    put, silver = res['put'], res['silver']
    exposed = [i for i in keep if same(put[i], silver[i], atol) is False]
    witness = [n for n in valid if any(same(res[n][i], silver[i], atol) for i in exposed)]
    memorized = [n for n in valid if keep and all(same(res[n][i], silver[i], atol) is not False for i in keep)]
    det = right = 0
    for i in keep:
        outs = [res[n][i] for n in valid]
        if len(valid) < 3 or any(same(outs[0], o, atol) is not True for o in outs[1:]):
            continue
        if same(outs[0], put[i], atol) is False:
            det += 1
            right += bool(same(outs[0], silver[i], atol))
    tmpl = v35[case['case_id']]['exposing_inputs']
    return dict(case_id=case['case_id'], question=r['question_id'], programs=len(progs), valid=len(valid), memorized=len(memorized),
                pool_valid=len(keep), exposed=len(exposed), witnesses=len(witness), consensus_det_inputs=det,
                consensus_correct_det=right, C=bool(witness), consensus=right > 0, template_exposing=tmpl,
                H=bool(witness) and tmpl == 0)


def score():
    cases, plus = tasks()
    by_q = {}
    for p in sorted((OUT / 'programs').glob('*.json'), key=lambda p: (p.stem.split('_')[0], int(p.stem.split('_')[1]))):
        rec = json.loads(p.read_text())
        src = code_block(rec['text']) if rec.get('text') else ''
        if src:
            by_q.setdefault(rec['question'], []).append(src)
    v35 = {r['case_id']: r for r in json.loads(V35.read_text())['rows']}
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(lambda c: analyse(c, plus[int(c['case_id'])], by_q.get(plus[int(c['case_id'])]['question_id'], []), v35), cases))
    s = lambda k: sum(bool(r[k]) for r in rows)
    valid = sum(r['valid'] for r in rows)
    det = sum(r['consensus_det_inputs'] for r in rows)
    mem = sum(r['memorized'] for r in rows) / valid if valid else None
    summary = dict(tasks=len(rows), exposed=sum(r['exposed'] > 0 for r in rows), valid_programs=valid, memorization_share=mem,
                   C=s('C'), H=s('H'), consensus_witness_tasks=s('consensus'), consensus_det_inputs=det,
                   consensus_precision=(sum(r['consensus_correct_det'] for r in rows) / det) if det else None,
                   tasks_without_3_valid=sum(r['valid'] < 3 for r in rows))
    if mem is None or mem >= 0.5:
        summary['verdict'] = 'untestable (memorized)'
    else:
        summary['verdict'] = 'go' if s('C') >= 17 and s('H') >= 3 else ('no-go: G1' if s('C') < 17 else 'no-go: G2')
    (OUT / 'gate.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1) + '\n')
    print(json.dumps(summary))
    for r in rows:
        print(r)


if __name__ == '__main__':
    {'generate': generate, 'score': score}[sys.argv[1]]()
