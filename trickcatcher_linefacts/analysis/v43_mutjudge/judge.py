"""v43 binary judge on v42 mutant-disagreement questions (see PREREG.md). Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v43_mutjudge/judge.py build
  QWEN_BASE_URL=... PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v43_mutjudge/judge.py generate
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v43_mutjudge/judge.py score
The endpoint URL comes from the environment only and is never written to disk or printed.
"""
import collections
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.analysis.v42_mutoracle import mutoracle
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_concepts, ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, numbered, same
from trickcatcher_linefacts.pipelines.v34_ftplacebo.v4_tools import enumerate_mutants

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v43_mutjudge'
MODEL = 'qwen2.5-coder-32b-instruct'
ARMS = ('binary', 'code', 'concept')
QUESTIONS_SHA256 = '3b4f48378d8c78cfae6f782715fd96681a22d9500cbb5ee9bf256a069b7cabca'
SEED = 20261021
MAX_REPR = 1500
CHOICES = ('A', 'B', 'neither', 'invalid', 'unsure')
SYSTEM = 'Return exactly one JSON object matching the schema. No Markdown.'
INSTR = {
    'binary': ('Two candidate implementations of the specification return different results on the input below. '
               'Decide from the specification and the public tests only which result is correct. Answer "neither" if '
               'both are wrong, "invalid" if the input violates the constraints of the specification, "unsure" if the '
               'specification does not decide it.'),
    'code': ('The code below and the same code with one small edit both pass the public tests; on the input below they '
             'return different results (labels say which is which). Decide from the specification and the public tests '
             'only which result is correct. Answer "neither" if both are wrong, "invalid" if the input violates the '
             'constraints of the specification, "unsure" if the specification does not decide it.'),
    'concept': ('The code below and the same code with one small edit (the fault concept below) both pass the public tests; '
                'on the input below they return different results. Decide from the specification and the public tests '
                'only which result is correct. Answer "neither" if both are wrong, "invalid" if the input violates the '
                'constraints of the specification, "unsure" if the specification does not decide it.'),
}
SCHEMA = {'choice': '|'.join(CHOICES), 'reason': 'str (at most 2 sentences)'}


def show(o):
    if o[0] == 'ok':
        return o[1] if len(o[1]) <= MAX_REPR else o[1][:MAX_REPR] + '...<truncated>'
    return f'raises {o[1]}' if o[0] == 'exception' else o[0]


def build():
    """Freeze the 607 v42 questions with PUT/mutant outcomes and the mutant edit + fault type (tool side only)."""
    run = ft_run.FTRun('vibepass_half')
    v41 = {r['case_id']: r for r in json.loads((iorel.OUT / 'ceiling.json').read_text())['rows']}
    out = []
    for case in run.cases:
        cid = case['case_id']
        t = mutoracle.tool(case, run, v41[cid])  # cached v42 batches
        if not t['questions']:
            continue
        job = json.loads((run.root / 'cases' / cid / 'tool' / 'phase2' / 'job.json').read_text())
        rows = {f"m{m['k']}": m for m in enumerate_mutants(case['source'], directory=OUT)}
        lines = case['source'].split('\n')
        raw = {}
        for c in range(0, len(job['order']) - 1, mutoracle.CHUNK):
            raw.update(json.loads((mutoracle.OUT / 'cases' / cid / f'chunk{c // mutoracle.CHUNK:03d}' / 'result.json').read_text()))
        for k, m in t['questions']:
            row = rows[m]
            if row['mutant_src'] != job['sources'][m]:
                raise SystemExit(f'{cid} {m}: re-enumerated mutant differs from v34')
            ftype = ft_concepts.fault_type(row, lines[row['line'] - 1] if row['line'] <= len(lines) else '')
            flip = int(hashlib.sha256(f'{cid}/{t["inputs"][k]}/{m}'.encode()).hexdigest(), 16) % 2
            out.append(dict(case_id=cid, k=k, input=t['inputs'][k], mutant=m, put=t['put'][k], mut=raw[m][k],
                            mutant_label='A' if flip else 'B', line=row['line'], before=row['before'], after=row['after'],
                            fault_type=ftype))
    OUT.mkdir(parents=True, exist_ok=True)
    immutable(OUT / 'questions.json', out)
    print(len(out), collections.Counter(q['fault_type'] for q in out))


def prompt(task, q, arm):
    put_label = 'B' if q['mutant_label'] == 'A' else 'A'
    results = {q['mutant_label']: show(q['mut']), put_label: show(q['put'])}
    ctx = dict(signature=task['signature'], spec=task['spec'], public_tests=task['base'], input=q['input'],
               results=dict(sorted(results.items())))
    if arm == 'code':
        ctx['code'] = numbered(task)
        ctx['labels'] = {put_label: 'the code as written', q['mutant_label']: 'the code with one small edit'}
    if arm == 'concept':
        ctx['code'] = numbered(task)
        ctx['fault_concept'] = dict(fault_type=q['fault_type'], meaning=ft_concepts.TYPE_TEXT[q['fault_type']],
                                    edit=f"line {q['line']}: `{q['before']}` -> `{q['after']}`",
                                    labels={put_label: 'the code as written', q['mutant_label']: 'the code with the edit'})
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': json.dumps(dict(instruction=INSTR[arm], context=ctx, schema=SCHEMA), ensure_ascii=False)}]


def call(client, run, q, arm):
    path = OUT / 'calls' / q['case_id'] / f"{q['k']}_{q['mutant']}_{arm}.json"
    if path.exists():
        return json.loads(path.read_text())
    case = next(c for c in run.cases if c['case_id'] == q['case_id'])
    r = client.chat.completions.create(model=MODEL, messages=prompt(run.task(case), q, arm), temperature=0, max_tokens=300,
                                       seed=SEED, response_format={'type': 'json_object'})
    rec = dict(text=r.choices[0].message.content or '', finish_reason=r.choices[0].finish_reason,
               input_tokens=r.usage.prompt_tokens, output_tokens=r.usage.completion_tokens)
    immutable(path, rec)
    return rec


def choice(text):
    try:
        v = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.S)
        try:
            v = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            v = {}
    c = v.get('choice') if isinstance(v, dict) else None
    if not isinstance(c, str):
        m = re.search(r'"choice"\s*:\s*"([^"]+)"', text)  # truncated JSON
        c = m.group(1) if m else None
    if not isinstance(c, str):
        return None
    c = c.strip()
    return c.upper() if c.upper() in ('A', 'B') else c.lower() if c.lower() in CHOICES else None


def load_questions():
    path = OUT / 'questions.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != QUESTIONS_SHA256:
        raise SystemExit('questions.json differs from the registered hash')
    return json.loads(path.read_text())


def generate():
    import openai
    run = ft_run.FTRun('vibepass_half')
    qs = load_questions()
    client = openai.OpenAI(base_url=os.environ['QWEN_BASE_URL'], api_key='none', timeout=600, max_retries=3,
                           default_headers={'ngrok-skip-browser-warning': '1'})
    if MODEL not in [m.id for m in client.models.list().data]:
        raise SystemExit(f'{MODEL} not served')
    jobs = [(q, a) for q in qs for a in ARMS]

    def safe(j):
        try:
            call(client, run, *j)
            return None
        except Exception as exc:  # recorded; rerun resumes from the cache
            return f'{type(exc).__name__}: {str(exc)[:120]}'
    errors = collections.Counter()
    with ThreadPoolExecutor(8) as pool:
        for done, err in enumerate(pool.map(safe, jobs), 1):
            if err:
                errors[err] += 1
            if done % 100 == 0:
                print(done, '/', len(jobs), 'errors', sum(errors.values()), flush=True)
    print('done', len(jobs), dict(errors))
    if errors:
        raise SystemExit(1)


def score():
    run = ft_run.FTRun('vibepass_half')
    qs = load_questions()
    official = Reference(run)
    official.root = iorel.OUT / 'official'
    cases = {c['case_id']: c for c in run.cases}
    truth = {}
    for cid in sorted({q['case_id'] for q in qs}):
        job = json.loads((iorel.OUT / 'cases' / cid / 'put' / 'job.json').read_text())
        truth[cid] = (job['inputs'], mutoracle.load_ref(cases[cid], job['inputs']))
    stats = {}
    for arm in ARMS:
        s = dict(confirmed=set(), fa_tasks=set(), flags=0, fa_questions=0, true_flags=0, choices=collections.Counter(),
                 parse_failures=0, mutant_right=[0, 0], put_right=[0, 0], finish=collections.Counter())
        for q in qs:
            cid, k = q['case_id'], q['k']
            inputs, res = truth[cid]
            assert inputs[k] == q['input']
            valid = res['contract'][k][0] == 'ok'
            ref, put, mut = iorel.value(res['ref'][k]), iorel.value(q['put']), iorel.value(q['mut'])
            cat = ('invalid' if not valid or ref is None else 'mutant_right' if same(mut, ref) else
                   'put_right' if same(put, ref) else 'neither')
            rec = json.loads((OUT / 'calls' / cid / f"{k}_{q['mutant']}_{arm}.json").read_text())
            s['finish'][rec['finish_reason']] += 1
            c = choice(rec['text'])
            if c is None:
                s['parse_failures'] += 1
            put_label = 'B' if q['mutant_label'] == 'A' else 'A'
            named = 'mutant' if c == q['mutant_label'] else 'put' if c == put_label else c
            s['choices'][f'{cat}:{named}'] += 1
            if cat in ('mutant_right', 'put_right'):
                s[cat][1] += 1
                s[cat][0] += named == ('mutant' if cat == 'mutant_right' else 'put')
            if named != 'mutant':
                continue
            s['flags'] += 1
            if cat != 'mutant_right':
                s['fa_questions'] += 1
                s['fa_tasks'].add(cid)
            elif iorel.official_exposes(official, cases[cid], q['input']):  # batch-only exposure: neither true nor FA
                s['true_flags'] += 1
                s['confirmed'].add(cid)
        stats[arm] = dict(confirmed_tasks=len(s['confirmed']), confirmed=sorted(s['confirmed'], key=int),
                          fa_questions=s['fa_questions'], fa_tasks=len(s['fa_tasks']), flags=s['flags'],
                          true_flags=s['true_flags'], precision=round(s['true_flags'] / s['flags'], 3) if s['flags'] else None,
                          sensitivity=f"{s['mutant_right'][0]}/{s['mutant_right'][1]}",
                          specificity=f"{s['put_right'][0]}/{s['put_right'][1]}", parse_failures=s['parse_failures'],
                          finish=dict(s['finish']), choices=dict(sorted(s['choices'].items())))
    c = stats['concept']
    verdict = ('continue' if c['confirmed_tasks'] >= 8 and (c['precision'] or 0) >= 0.5
               and all(c['confirmed_tasks'] >= stats[a]['confirmed_tasks'] and c['fa_questions'] <= stats[a]['fa_questions']
                       for a in ('binary', 'code')) else 'close')
    summary = dict(questions=len(qs), arms=stats, verdict=verdict)
    (OUT / 'score.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    dict(build=build, generate=generate, score=score)[sys.argv[1]]()
