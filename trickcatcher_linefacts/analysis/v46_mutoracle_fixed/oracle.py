"""v46 mutant-concept oracle with program variants + repaired judge (see PREREG.md). Usage (repo root):
  QWEN_BASE_URL=... PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v46_mutoracle_fixed/oracle.py generate
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v46_mutoracle_fixed/oracle.py score
The endpoint URL comes from the environment only and is never written to disk or printed.
"""
import ast
import collections
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trickcatcher_linefacts import tc_full
from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.analysis.v42_mutoracle import mutoracle
from trickcatcher_linefacts.pipelines.v7.oracle_b01 import code_block
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_concepts, ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.chain_inputs import parse_literal, typed_value
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, numbered, same
from trickcatcher_linefacts.pipelines.v34_ftplacebo.gen_inputs import sandbox
from trickcatcher_linefacts.pipelines.v34_ftplacebo.paths import CONFIG

HERE = Path(__file__).resolve().parent
LF = HERE.parents[1]
OUT = LF / 'out' / 'analysis' / 'v46_mutoracle_fixed'
QUESTIONS = LF / 'out' / 'analysis' / 'v45_mutjudge' / 'questions.json'
QUESTIONS_SHA256 = '3b4f48378d8c78cfae6f782715fd96681a22d9500cbb5ee9bf256a069b7cabca'
V39 = LF / 'out' / 'analysis' / 'v39_specalt_vibepass' / 'programs'
V39_TRANSPORT = ('NotFoundError', 'InternalServerError', 'APITimeoutError', 'APIConnectionError')
VIBEPASS = LF / 'out' / 'heldout_vibepass_real' / 'he' / 'humaneval_mbpp_plus.jsonl'
MODEL = 'qwen2.5-coder-32b-instruct'
NPROG = 10
MAX_CONCEPTS = 5
PROG_ARMS = ('dpp', 'tc', 'tc_concept')
JUDGE_ARMS = ('binary', 'code', 'concept')
JUDGE_SEED = 20261022
MAX_REPR = 1500
SYSTEM = 'Return exactly one JSON object matching the schema. No Markdown.'
ENDING = ('First work out the correct result of this call from the specification and the public tests, step by step, in '
          '"analysis". Then give that result in "expected" as a Python literal, and choose: the label whose result equals '
          'it, "neither" if neither result is correct, or "invalid" if the call violates the constraints of the '
          'specification.')
INSTR = {
    'binary': 'Two candidate implementations of the specification return different results on the call below. ' + ENDING,
    'code': ('The code below and the same code with one small edit both pass the public tests; on the call below they '
             'return different results (labels say which is which). ' + ENDING),
    'concept': ('The code below and the same code with one small edit (the fault concept below) both pass the public '
                'tests; on the call below they return different results. ' + ENDING),
}
SCHEMA = {'analysis': 'str: step-by-step computation of the correct result',
          'expected': 'the correct result as a Python literal (string), or null if the call is invalid',
          'choice': 'A|B|neither|invalid'}
CHOICES = ('A', 'B', 'neither', 'invalid')


# ---- frozen material --------------------------------------------------------------------------------------------
def load_questions():
    if hashlib.sha256(QUESTIONS.read_bytes()).hexdigest() != QUESTIONS_SHA256:
        raise SystemExit('questions.json differs from the registered hash')
    return json.loads(QUESTIONS.read_text())


def put_parts(case):
    """(preamble, entry wrapper, parameter names) of a VibePass PUT: preamble + Solution class + module wrapper.
    Preamble = every top-level statement before the first class/def (imports, setrecursionlimit) plus later imports."""
    src = case['source']
    tree = ast.parse(src)
    first = next(i for i, n in enumerate(tree.body) if isinstance(n, (ast.ClassDef, ast.FunctionDef)))
    pre = [n for i, n in enumerate(tree.body) if (i < first and not isinstance(n, ast.If))
           or (i >= first and isinstance(n, (ast.Import, ast.ImportFrom)))]
    header = '\n'.join(ast.get_source_segment(src, n) for n in pre)
    wrapper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == case['entry'])
    names = [a.arg for a in wrapper.args.args]
    return header, ast.get_source_segment(src, wrapper), names


def program_module(case, program):
    """Arm-neutral loading: PUT import header + program (+ PUT entry wrapper if the program has no module-level entry)."""
    header, wrapper, _ = put_parts(case)
    try:
        has_entry = any(isinstance(n, ast.FunctionDef) and n.name == case['entry'] for n in ast.parse(program).body)
    except SyntaxError:
        has_entry = True  # leave as is: it fails to load and the program is invalid
    return header + '\n\n' + ('' if has_entry else wrapper + '\n\n') + program + '\n'


def concepts(case, qs):
    """Distinct mutant edits of the task's questions, package order, <= MAX_CONCEPTS (tool side only)."""
    lines = case['source'].split('\n')
    out, seen = [], set()
    for q in qs:
        key = (q['line'], q['before'], q['after'])
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(fault_type=q['fault_type'], meaning=ft_concepts.TYPE_TEXT[q['fault_type']],
                        code_line=lines[q['line'] - 1].strip() if q['line'] <= len(lines) else '', before=q['before'], after=q['after']))
        if len(out) == MAX_CONCEPTS:
            break
    return out


def concept_block(cs):
    rows = [f"- {c['fault_type']} ({c['meaning']}): in `{c['code_line']}`, possible alternative: `{c['before']}` -> `{c['after']}`." for c in cs]
    return '\n\n**Possible fault concepts** (from automated analysis of this code; each may be wrong):\n' + '\n'.join(rows)


# ---- generation -------------------------------------------------------------------------------------------------
def tc_messages(case, arm, cs, templates):
    msgs = tc_full.messages(dict(put=case['source']), 'variant', templates)
    if arm == 'tc_concept':
        msgs[1] = dict(msgs[1], content=msgs[1]['content'] + concept_block(cs))
    return msgs


def show(o):
    if o[0] == 'ok':
        return o[1] if len(o[1]) <= MAX_REPR else o[1][:MAX_REPR] + '...<truncated>'
    return f'raises {o[1]}' if o[0] == 'exception' else o[0]


def call_text(case, literal):
    _, _, names = put_parts(case)
    args = ast.literal_eval(literal)
    return f"{case['entry']}(" + ', '.join(f'{n}={v!r}' for n, v in zip(names, args)) + ')'


def judge_messages(run, case, q, arm):
    task = run.task(case)
    put_label = 'B' if q['mutant_label'] == 'A' else 'A'
    results = {q['mutant_label']: show(q['mut']), put_label: show(q['put'])}
    ctx = dict(signature=task['signature'], spec=task['spec'], public_tests=task['base'], call=call_text(case, q['input']),
               results=dict(sorted(results.items())))
    if arm in ('code', 'concept'):
        ctx['code'] = numbered(task)
    if arm == 'code':
        ctx['labels'] = {put_label: 'the code as written', q['mutant_label']: 'the code with one small edit'}
    if arm == 'concept':
        ctx['fault_concept'] = dict(fault_type=q['fault_type'], meaning=ft_concepts.TYPE_TEXT[q['fault_type']],
                                    edit=f"line {q['line']}: `{q['before']}` -> `{q['after']}`",
                                    labels={put_label: 'the code as written', q['mutant_label']: 'the code with the edit'})
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': json.dumps(dict(instruction=INSTR[arm], context=ctx, schema=SCHEMA), ensure_ascii=False)}]


def digest(messages, params):
    return hashlib.sha256(json.dumps([messages, params], sort_keys=True).encode()).hexdigest()


def complete(client, path, messages, **params):
    if path.exists():
        rec = json.loads(path.read_text())
        if rec.get('digest') != digest(messages, params):
            raise SystemExit(f'{path}: cached call made with a different prompt/params')
        return rec
    r = client.chat.completions.create(model=MODEL, messages=messages, **params)
    rec = dict(text=r.choices[0].message.content or '', finish_reason=r.choices[0].finish_reason,
               input_tokens=r.usage.prompt_tokens, output_tokens=r.usage.completion_tokens, digest=digest(messages, params))
    immutable(path, rec)
    return rec


def jobs(run, qs):
    templates = tc_full.templates()
    by_case = collections.defaultdict(list)
    for q in qs:
        by_case[q['case_id']].append(q)
    cases = {c['case_id']: c for c in run.cases}
    out = []
    for cid, cq in by_case.items():
        cs = concepts(cases[cid], cq)
        for arm in ('tc', 'tc_concept'):
            msgs = tc_messages(cases[cid], arm, cs, templates)
            for i in range(NPROG):
                seed = int(hashlib.sha256(f'v46/{cid}/{arm}/{i}'.encode()).hexdigest()[:8], 16)
                out.append((OUT / 'programs' / arm / cid / f'{i}.json', msgs, dict(seed=seed, **tc_full.PARAMS)))
    for q in qs:
        for arm in JUDGE_ARMS:
            out.append((OUT / 'judge' / q['case_id'] / f"{q['k']}_{q['mutant']}_{arm}.json", judge_messages(run, cases[q['case_id']], q, arm),
                        dict(temperature=0, seed=JUDGE_SEED, max_tokens=2048, response_format={'type': 'json_object'})))
    return out


def generate():
    import openai
    run = ft_run.FTRun('vibepass_half')
    qs = load_questions()
    client = openai.OpenAI(base_url=os.environ['QWEN_BASE_URL'], api_key='none', timeout=1200, max_retries=3,
                           default_headers={'ngrok-skip-browser-warning': '1'})
    served = {m.id: getattr(m, 'max_model_len', None) for m in client.models.list().data}
    if served.get(MODEL, 0) != 8192:
        raise SystemExit(f'{MODEL} not served with max_model_len 8192: {served}')
    todo = jobs(run, qs)
    if 'smoke' in sys.argv[2:]:
        todo = [todo[0], todo[10], todo[-1]]

    def safe(job):
        try:
            complete(client, *job[:2], **job[2])
            return None
        except openai.BadRequestError as exc:  # prompt + max_tokens over the 8192 context: recorded once, no program
            if 'context' not in str(exc).lower():
                return f'BadRequestError: {str(exc)[:120]}'
            immutable(job[0], dict(text='', finish_reason='context_overflow', input_tokens=None, output_tokens=0,
                                   digest=digest(job[1], job[2])))
            return None
        except Exception as exc:  # recorded; a rerun resumes from the cache
            return f'{type(exc).__name__}: {str(exc)[:120]}'
    errors = collections.Counter()
    # the endpoint serves one request at a time; parallel clients only queue and time out (aborted, re-queued)
    with ThreadPoolExecutor(int(os.environ.get('V46_WORKERS', '1'))) as pool:
        for done, err in enumerate(pool.map(safe, todo), 1):
            if err:
                errors[err] += 1
            if done % 20 == 0:
                print(done, '/', len(todo), 'errors', sum(errors.values()), flush=True)
    print('done', len(todo), dict(errors))
    if errors:
        raise SystemExit(1)


# ---- scoring (references enter only here) -----------------------------------------------------------------------
def programs(case, arm, question_id):
    if arm == 'dpp':
        srcs = []
        for s in range(NPROG):
            p = V39 / f'{question_id}_{s}.json'
            if not p.exists():
                continue
            rec = json.loads(p.read_text())
            retry = p.with_name(p.stem + '.retry.json')
            if rec.get('error') in V39_TRANSPORT and retry.exists():
                rec = json.loads(retry.read_text())
            srcs.append(code_block(rec['text']) if rec.get('text') else '')
        return srcs
    return [tc_full.source(json.loads((OUT / 'programs' / arm / case['case_id'] / f'{i}.json').read_text())['text'])
            for i in range(NPROG)]


def batch(d, sources, order, entry, inputs):
    """ft_worker process, cached by job content; tc-full semantics: every input gets its 1 s call, no timeout skipping."""
    d.mkdir(parents=True, exist_ok=True)
    jp, op = d / 'job.json', d / 'result.json'
    job = dict(sources={k: sources[k] for k in order}, order=order, entry=entry, inputs=inputs, per_call_timeout=1,
               max_timeouts=len(inputs) + 1)
    if op.exists() and jp.exists() and json.loads(jp.read_text()) == job:
        return json.loads(op.read_text())
    op.unlink(missing_ok=True)
    jp.write_text(json.dumps(job))
    return sandbox(CONFIG['V4_PYTHON'], iorel.WORKER, jp, op, mutoracle.CHUNK_TIMEOUT)


def run_programs(case, arm, srcs, inputs, tag):
    """All programs in one process; if it crashes, one process per program, and a program crashing alone is skipped."""
    names = [f'p{i}' for i in range(len(srcs))]
    sources = {n: program_module(case, s) for n, s in zip(names, srcs)}
    if not names:
        return {}
    d = OUT / 'exec' / case['case_id'] / arm / tag
    try:
        return batch(d, sources, names, case['entry'], inputs)
    except RuntimeError:
        out = {}
        for n in names:
            try:
                out.update(batch(d / n, sources, [n], case['entry'], inputs))
            except RuntimeError:
                out[n] = [['skipped']] * len(inputs)
        return out


def parse_expected(text, put_raw):
    """The judge's expected value -> ft_worker-style outcome, typed like the PUT output when ambiguous."""
    if text is None or (isinstance(text, str) and text.strip() in ('None', 'null', '')):
        return None
    cands = []
    if isinstance(text, str):
        try:
            cands.append(ast.literal_eval(text.strip()))
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            pass
        cands.append(text)
    else:
        cands.append(text)
    want = None
    if put_raw[0] == 'ok':
        try:
            want = type(parse_literal(put_raw[1], output=True))
        except (ValueError, TypeError, SyntaxError, RecursionError):
            want = None
    if want is bool and isinstance(text, str) and text.strip().lower() in ('true', 'false'):
        cands.insert(0, text.strip().lower() == 'true')
    pick = next((c for c in cands if want is not None and type(c) is want), cands[0])
    return iorel.value(['ok', repr(pick)])


def judge_reply(text):
    try:
        v = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.S)
        try:
            v = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            v = {}
    v = v if isinstance(v, dict) else {}
    c = v.get('choice')
    if not isinstance(c, str):
        m = re.search(r'"choice"\s*:\s*"([^"]+)"', text)
        c = m.group(1) if m else None
    if isinstance(c, str):
        c = c.strip()
        c = c.upper() if c.upper() in ('A', 'B') else c.lower() if c.lower() in CHOICES else None
    return c, v.get('expected')


def score():
    run = ft_run.FTRun('vibepass_half')
    qs = load_questions()
    cases = {c['case_id']: c for c in run.cases}
    plus = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, VIBEPASS.read_text().splitlines())}
    official = Reference(run)
    official.root = iorel.OUT / 'official'
    by_case = collections.defaultdict(list)
    for q in qs:
        by_case[q['case_id']].append(q)
    truth = {}
    for cid in by_case:
        inputs = json.loads((iorel.OUT / 'cases' / cid / 'put' / 'job.json').read_text())['inputs']
        put_raw = json.loads((iorel.OUT / 'cases' / cid / 'put' / 'result.json').read_text())['put']
        truth[cid] = (inputs, mutoracle.load_ref(cases[cid], inputs), put_raw)
    confirmed_cache = {}

    def judge_test(cid, k, value):
        """'confirmed', 'fa', or 'unconfirmed' (value = reference but the official path does not confirm PUT != reference;
        counted as a test, neither true nor FA) for a test asserting `value` on input k."""
        inputs, res, put_raw = truth[cid]
        ref = iorel.value(res['ref'][k])
        if res['contract'][k][0] != 'ok' or ref is None or value is None or not same(value, ref):
            return 'fa'
        if (cid, k) not in confirmed_cache:
            put = iorel.value(put_raw[k])
            confirmed_cache[(cid, k)] = put is not None and not same(put, ref) and iorel.official_exposes(official, cases[cid], inputs[k])
        return 'confirmed' if confirmed_cache[(cid, k)] else 'unconfirmed'  # scored as FA (PREREG), counted separately

    arms = {}
    # program oracles
    for arm in PROG_ARMS:
        s = dict(tests=0, confirmed=set(), fa=0, fa_tasks=set(), true=0, valid=[], consensus_tests=0, consensus_true=0,
                 consensus_tasks=set(), unconfirmed=0, invalid=collections.Counter(), overflow=0, empty=0)
        for cid, cq in by_case.items():
            case = cases[cid]
            srcs = programs(case, arm, plus[int(cid)]['question_id'])
            if arm != 'dpp':
                s['overflow'] += sum(json.loads((OUT / 'programs' / arm / cid / f'{i}.json').read_text())['finish_reason']
                                     == 'context_overflow' for i in range(NPROG))
            seeds = [repr(x) for x in ft_run.base_inputs(case, 'vibepass_half')]
            base = run_programs(case, arm, srcs, seeds, 'base')
            base_put = [iorel.value(o) for o in run_programs(case, 'put', [case['source']], seeds, 'base')['p0']] if seeds else []
            valid = []
            s['empty'] += sum(not x for x in srcs)
            for n in base:
                vals = [iorel.value(o) for o in base[n]]
                pairs = [(a, b) for a, b in zip(base_put, vals) if a is not None]
                if pairs and all(b is not None and same(a, b) for a, b in pairs):
                    valid.append(n)
                elif base[n] and base[n][0][0] == 'exception' and str(base[n][0][1]).startswith('load:'):
                    s['invalid']['load_error'] += 1
                elif any(b is not None and b[0] == 'exception' for _, b in pairs):
                    s['invalid']['exception'] += 1
                elif any(b is None for _, b in pairs):
                    s['invalid']['timeout_or_unparsable'] += 1
                else:
                    s['invalid']['mismatch'] += 1
            s['valid'].append(len(valid))
            ks = sorted({q['k'] for q in cq})
            inputs = truth[cid][0]
            outs = run_programs(case, arm, [srcs[int(n[1:])] for n in valid], [inputs[k] for k in ks], 'questions') if valid else {}
            for j, k in enumerate(ks):
                put = iorel.value(next(q['put'] for q in cq if q['k'] == k))
                if put is None or put[0] != 'ok':
                    continue  # tc-full: PUT failures give no comparison
                vals = [iorel.value(outs[f'p{i}'][j]) for i in range(len(valid))]
                groups = []
                for v in vals:
                    if v is None or v[0] != 'ok' or same(v, put):
                        continue
                    g = next((g for g in groups if same(g[0], v)), None)
                    if g:
                        g[1] += 1
                    else:
                        groups.append([v, 1])
                if groups:
                    value = max(groups, key=lambda g: g[1])[0]  # max keeps the first of ties
                    verdict = judge_test(cid, k, value)
                    s['tests'] += 1
                    if verdict == 'confirmed':
                        s['true'] += 1
                        s['confirmed'].add(cid)
                    else:
                        s['fa'] += 1
                        s['unconfirmed'] += verdict == 'unconfirmed'
                        s['fa_tasks'].add(cid)
                if len(vals) >= 3 and all(v is not None and v[0] == 'ok' for v in vals) and all(same(vals[0], v) for v in vals) \
                        and not same(vals[0], put):
                    s['consensus_tests'] += 1
                    if judge_test(cid, k, vals[0]) == 'confirmed':
                        s['consensus_true'] += 1
                        s['consensus_tasks'].add(cid)
        arms[arm] = dict(confirmed_tasks=len(s['confirmed']), confirmed=sorted(s['confirmed'], key=int), tests=s['tests'],
                         true_tests=s['true'], fa_tests=s['fa'], fa_tasks=len(s['fa_tasks']),
                         precision=round(s['true'] / s['tests'], 3) if s['tests'] else None,
                         valid_programs=sum(s['valid']), tasks_valid_ge1=sum(v >= 1 for v in s['valid']),
                         tasks_valid_ge3=sum(v >= 3 for v in s['valid']), invalid=dict(s['invalid']), empty_programs=s['empty'],
                         context_overflow=s['overflow'],
                         unconfirmed=s['unconfirmed'],
                         consensus=dict(tests=s['consensus_tests'], true=s['consensus_true'], tasks=len(s['consensus_tasks'])))
    # judge
    for arm in JUDGE_ARMS:
        s = dict(tests=0, confirmed=set(), fa=0, fa_tasks=set(), true=0, choices=collections.Counter(), parse_failures=0,
                 finish=collections.Counter(), neither_tests=0, neither_true=0, unconfirmed=0)
        for q in qs:
            cid, k = q['case_id'], q['k']
            rec = json.loads((OUT / 'judge' / cid / f"{k}_{q['mutant']}_{arm}.json").read_text())
            s['finish'][rec['finish_reason']] += 1
            c, expected = judge_reply(rec['text'])
            s['parse_failures'] += c is None
            put_label = 'B' if q['mutant_label'] == 'A' else 'A'
            named = 'mutant' if c == q['mutant_label'] else 'put' if c == put_label else c
            s['choices'][named] += 1
            value = None
            if named == 'mutant':
                value = iorel.value(q['mut'])
            elif named == 'neither':
                v = parse_expected(expected, q['put'])
                put = iorel.value(q['put'])
                value = v if v is not None and (put is None or not same(v, put)) else None
            if value is None:
                continue
            verdict = judge_test(cid, k, value)
            s['tests'] += 1
            s['neither_tests'] += named == 'neither'
            if verdict == 'confirmed':
                s['true'] += 1
                s['neither_true'] += named == 'neither'
                s['confirmed'].add(cid)
            else:
                s['fa'] += 1
                s['unconfirmed'] += verdict == 'unconfirmed'
                s['fa_tasks'].add(cid)
        arms[f'judge_{arm}'] = dict(confirmed_tasks=len(s['confirmed']), confirmed=sorted(s['confirmed'], key=int),
                                    tests=s['tests'], true_tests=s['true'], fa_tests=s['fa'], fa_tasks=len(s['fa_tasks']),
                                    precision=round(s['true'] / s['tests'], 3) if s['tests'] else None,
                                    neither=dict(tests=s['neither_tests'], true=s['neither_true']), unconfirmed=s['unconfirmed'],
                                    parse_failures=s['parse_failures'], finish=dict(s['finish']), choices=dict(s['choices']))

    def wins(a, others):
        x = arms[a]
        return (x['confirmed_tasks'] >= 8 and (x['precision'] or 0) >= 0.5
                and all(x['confirmed_tasks'] >= arms[o]['confirmed_tasks'] and x['fa_tests'] <= arms[o]['fa_tests']
                        and (x['confirmed_tasks'] > arms[o]['confirmed_tasks'] or x['fa_tests'] < arms[o]['fa_tests'])
                        and len(set(x['confirmed']) - set(arms[o]['confirmed'])) >= 2 for o in others))
    pairs = {'tc_concept vs tc': wins('tc_concept', ['tc']),
             'judge_concept vs judge_code+binary': wins('judge_concept', ['judge_code', 'judge_binary'])}
    summary = dict(questions=len(qs), tasks=len(by_case), arms=arms, pairs=pairs,
                   verdict='continue' if any(pairs.values()) else 'close')
    (OUT / 'score.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    dict(generate=generate, score=score)[sys.argv[1]]()
