"""v60: behaviour-fact concept for a code-blind Qwen input generator (see PREREG.md). Repo root, PYTHONPATH=.:
  source <env with QWEN_BASE_URL>; $V4_PYTHON .../v60_behavior_fact/run.py generate [smoke]   # 1 worker, resumable
  $V4_PYTHON .../v60_behavior_fact/run.py freeze
  $V4_PYTHON .../v60_behavior_fact/run.py score                                              # references only here
The endpoint URL comes from the environment only; it is never written or printed.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v46_mutoracle_fixed.oracle import complete, digest
from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O
from trickcatcher_linefacts.analysis.v53_validity_smallscope import smallscope as S
from trickcatcher_linefacts.analysis.v53_validity_smallscope import validity as V
from trickcatcher_linefacts.analysis.v59_blind_concept import run as B
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable

E = O.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v60_behavior_fact'
B.OUT = OUT  # v59 helpers (generated, accept, truth_for, mechanism) read and write under this experiment's root
MODEL = 'qwen2.5-coder-32b-instruct'
ARMS = ('blind', 'concept', 'placebo', 'code')
K = 2
FACT_SYSTEM = 'You are an expert Python programmer. Reply only with the requested lines.'
FACT_INSTR = {
    'facts': ('List up to 5 BEHAVIOUR FACTS of this code: specific conditions on the inputs under which it takes a special '
              'path, uses a limit or constant, skips, caps or stops work, or treats an input class differently. One line '
              'each: `FACT: when <condition on the inputs>, the code <does what>`. Describe what the code does; do not '
              'judge whether it is correct; no other text.'),
    'specfacts': ('List up to 5 facts the problem statement implies about the answer: one line each `FACT: when <condition '
                  'on the inputs>, the answer <is what>`; no other text.'),
}
HEAD = {'concept': 'Facts about the program under test (its code is not shown):\n',
        'placebo': 'Facts about the problem:\n',
        'code': 'Program under test (may be buggy):\n'}
FACT_PARAMS = dict(temperature=0, max_tokens=512)


def tasks():
    run, probs = V.problems()
    pid_of = {c['case_id']: p for p, cs in probs.items() for c in cs}
    return run, probs, {c['case_id']: c for c in run.cases}, pid_of


def fact_messages(case, kind):
    t = E.task_view(case)
    body = f"Problem statement:\n{t['spec']}\n\nPublic tests (valid inputs):\n{t['base']}\n\nFunction signature:\ndef {t['signature']}:\n\n"
    if kind == 'facts':
        body += f"Code:\n```python\n{t['source_masked'].strip()}\n```\n\n"
    return [{'role': 'system', 'content': FACT_SYSTEM}, {'role': 'user', 'content': body + FACT_INSTR[kind]}]


def fact_lines(cid, kind):
    rec = json.loads((OUT / 'calls' / kind / f'{cid}.json').read_text())
    return [l.strip() for l in rec['text'].splitlines() if l.strip().startswith('FACT:')]


def gen_messages(case, arm):
    head = S.message(E.task_view(case), 'plain')
    instr = S.INSTR['plain']
    assert head.endswith(instr)
    if arm != 'blind':
        if arm == 'code':
            block = f"```python\n{E.task_view(case)['source_masked'].strip()}\n```"
        else:
            block = '\n'.join(fact_lines(case['case_id'], 'facts' if arm == 'concept' else 'specfacts'))
        head = head[:-len(instr)] + HEAD[arm] + block + '\n\n' + instr
    return [{'role': 'system', 'content': V.SYSTEM}, {'role': 'user', 'content': head}]


def key(msgs):
    return hashlib.sha256(json.dumps(msgs, sort_keys=True).encode()).hexdigest()[:16]


def gen_params(arm, k, i):
    seed = int(hashlib.sha256(f'v60/{arm}/{k}/{i}'.encode()).hexdigest()[:8], 16)
    return dict(temperature=0.8, top_p=0.95, max_tokens=1536, seed=seed)


def call(client, path, msgs, params):
    import openai
    try:
        return complete(client, path, msgs, **params)
    except openai.BadRequestError as exc:  # prompt + max_tokens over the 8192 context: recorded once, empty answer
        if 'context' not in str(exc).lower():
            raise
        rec = dict(text='', finish_reason='context_overflow', input_tokens=None, output_tokens=0, digest=digest(msgs, params))
        immutable(path, rec)
        return rec


def generate(smoke):
    import openai
    client = openai.OpenAI(base_url=os.environ['QWEN_BASE_URL'], api_key='none', timeout=900, max_retries=2,
                           default_headers={'ngrok-skip-browser-warning': '1'})
    served = {m.id: getattr(m, 'max_model_len', None) for m in client.models.list().data}
    if served.get(MODEL, 0) != 8192:
        raise SystemExit(f'{MODEL} not served with max_model_len 8192')
    _, _, cs, _ = tasks()
    ids = sorted(cs, key=int)[:1] if smoke else sorted(cs, key=int)
    errors = 0

    def run(path, msgs, params):
        nonlocal errors
        try:
            call(client, path, msgs, params)
        except Exception as exc:  # recorded; a rerun resumes from the cache
            errors += 1
            print(type(exc).__name__, path.relative_to(OUT), str(exc)[:120], flush=True)
    for kind in ('facts', 'specfacts'):  # stage 1: concept and placebo sources
        for cid in ids:
            run(OUT / 'calls' / kind / f'{cid}.json', fact_messages(cs[cid], kind), FACT_PARAMS)
    manifest = {}
    for arm in ARMS:  # stage 2: generator, one call per (arm, distinct prompt, sample)
        manifest[arm] = {}
        for cid in ids:
            if arm in ('concept', 'placebo') and not (OUT / 'calls' / ('facts' if arm == 'concept' else 'specfacts') / f'{cid}.json').is_file():
                continue
            msgs = gen_messages(cs[cid], arm)
            k = manifest[arm][cid] = key(msgs)
            for i in range(K):
                path = OUT / 'calls' / arm / f's{i}' / f'{k}.json'
                if not path.exists():
                    run(path, msgs, gen_params(arm, k, i))
                if path.exists():
                    ans = OUT / 'answers' / arm / f's{i}' / f'{k}.txt'
                    ans.parent.mkdir(parents=True, exist_ok=True)
                    ans.write_text(json.loads(path.read_text())['text'])
        print(arm, 'distinct prompts', len(set(manifest[arm].values())), 'errors so far', errors, flush=True)
    if not smoke:
        (OUT / 'manifest.json').write_text(json.dumps(dict(keys=manifest), indent=1))
    print('done', 'errors', errors, flush=True)
    if errors:
        raise SystemExit(1)


def external_files():
    """Everything outside this folder that `score` reads (Amendment 1, Codex M2): Stage 1 open checks, Stage 2 / v52
    oracle answers, v49 task records (PUT outcomes, universe), v41 PUT/reference caches, helper sources."""
    _, probs, cs, _ = tasks()
    files = []
    for pid, cases in probs.items():
        files.append(V.OUT / 'answers' / f'{pid}_open.txt')
        old = S.v52_task([c['case_id'] for c in cases])
        files += [(S.P.OUT / 'programs' / 'defn' / old / f'{i}.txt') if old else S.OUT / 'answers' / 'oracle' / f'{pid}_{i}.txt'
                  for i in range(S.K)]
    files += [O.OUT / 'tasks' / f'{cid}.json' for cid in cs]
    files += sorted(p for cid in cs for p in (E.iorel.OUT / 'cases' / cid).rglob('*.json'))
    files += [Path(m.__file__) for m in (O, S, V, B, E, E.iorel)]
    return files


def frozen_state():
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    calls = sorted((OUT / 'calls').rglob('*.json'))
    answers = sorted((OUT / 'answers').rglob('*.txt'))
    return dict(calls={str(p.relative_to(OUT)): sha(p) for p in calls},
                answers={str(p.relative_to(OUT)): sha(p) for p in answers},  # Amendment 1, Codex M1
                sources={f: sha(HERE / f) for f in ('run.py', 'PREREG.md')},
                external={str(p.relative_to(HERE.parents[2])): sha(p) for p in external_files()},
                manifest=sha(OUT / 'manifest.json'))


def freeze():
    if not (OUT / 'manifest.json').is_file():
        raise SystemExit('no manifest: run a full (non-smoke) generate first')
    manifest = json.loads((OUT / 'manifest.json').read_text())['keys']
    _, _, cs, _ = tasks()
    missing = [f'{a}/s{i}/{k}' for a in ARMS for k in set(manifest[a].values()) for i in range(K)
               if not (OUT / 'calls' / a / f's{i}' / f'{k}.json').is_file()]
    if missing or any(set(manifest[a]) != set(cs) for a in ARMS):
        raise SystemExit(f'incomplete: {missing[:5]} ... {len(missing)}')
    bad = []  # preflight (Codex S1, M1): every call matches its prompt/params; every answer equals its call text
    for kind in ('facts', 'specfacts'):
        for cid in cs:
            rec = json.loads((OUT / 'calls' / kind / f'{cid}.json').read_text())
            bad += [] if rec['digest'] == digest(fact_messages(cs[cid], kind), FACT_PARAMS) else [f'{kind}/{cid}']
    for a in ARMS:
        for cid, k in manifest[a].items():
            msgs = gen_messages(cs[cid], a)
            for i in range(K):
                rec = json.loads((OUT / 'calls' / a / f's{i}' / f'{k}.json').read_text())
                if key(msgs) != k or rec['digest'] != digest(msgs, gen_params(a, k, i)) \
                        or (OUT / 'answers' / a / f's{i}' / f'{k}.txt').read_text() != rec['text']:
                    bad.append(f'{a}/s{i}/{cid}')
    state = frozen_state()
    absent = [n for n, h in state['external'].items() if h is None]
    if bad or absent:
        raise SystemExit(f'preflight failed: {bad[:5]} absent {absent[:3]}')
    O.immutable(OUT / 'frozen.json', state)
    print('frozen', len(state['calls']), 'call records,', len(state['answers']), 'answers')


def score():
    frozen = json.loads((OUT / 'frozen.json').read_text())
    now = frozen_state()
    changed = sorted(f for f in frozen if frozen[f] != now[f])
    if changed:
        raise SystemExit(f'frozen state changed: {changed}')
    manifest = json.loads((OUT / 'manifest.json').read_text())['keys']
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    _, _, records, _ = ready
    run, probs, cs, pid_of = tasks()
    official = E.Reference(run)
    official.root = OUT / 'references' / 'official'
    res, gen_info = {}, {}
    for cid in sorted(cs, key=int):
        case, rec, pid = cs[cid], records[cid], pid_of[cid]
        samples = {}
        for arm in ARMS:
            for i in range(K):
                samples[arm, i], gen_info[f'{arm}/s{i}/{cid}'] = B.generated(case, arm, i, manifest[arm][cid])
        everything = list(dict.fromkeys(l for v in samples.values() for l in v))
        acc = B.accept(case, rec, pid, everything)
        arms = {}
        for arm in ARMS:
            for i in range(K):
                arms[f'{arm}#s{i}'] = [l for l in samples[arm, i] if acc[l]]
            arms[arm] = list(dict.fromkeys(l for i in range(K) for l in arms[f'{arm}#s{i}']))
        used = list(dict.fromkeys(l for a in arms.values() for l in a))
        new = [l for l in used if l not in rec['inputs']]
        srcs = S.oracle_sources(pid, [c['case_id'] for c in probs[pid]])
        with E.execution_root(OUT):
            put_new = O.run_programs(case, 'put', [case['source']], new, 'new')['p0'] if new else []
            base = O.run_programs(case, 'sonnet_defn', srcs, rec['base_inputs'], 'base', 2)
            reasons = {j: O.rejection(rec['base_put'], base[f'p{j}']) for j in range(S.K)}
            strict = [j for j in range(S.K) if srcs[j] and not reasons[j]]
            tolerant = [j for j in range(S.K) if srcs[j] and (not reasons[j] or (
                O.resource_only(reasons[j], base[f'p{j}']) and 'mismatch' not in reasons[j]
                and any(o and o[0] == 'ok' for o in base[f'p{j}'])))]
            ran = O.run_programs(case, 'sonnet_defn_valid', [srcs[j] for j in tolerant], used, 'used') if used else {}
        put = {l: rec['inputs'][l]['put'] for l in used if l in rec['inputs']} | dict(zip(new, put_new))
        rows = {}
        for name, ids in (('tolerant', tolerant), ('strict', strict)):
            rows[name] = {}
            for n, l in enumerate(used):
                outs = [ran[f'p{tolerant.index(j)}'][n] for j in ids]
                rows[name][l] = dict(put=put[l], programs=outs, **O.votes(put[l], outs))
        truth = B.truth_for(inv, case, rows['tolerant'], official)
        res[cid] = dict(problem=pid, facts=len(fact_lines(cid, 'facts')), specfacts=len(fact_lines(cid, 'specfacts')),
                        oracle=dict(strict=strict, tolerant=tolerant, reasons={str(j): reasons[j] for j in range(S.K)}),
                        arms={a: S.arm_metrics(ins, rows, truth, len(tolerant), len(strict)) for a, ins in arms.items()})
        print(cid, {a: (m['inputs'], m['confirmed_tasks'], m['fa_tests'], m['reach']) for a, m in res[cid]['arms'].items()
                    if '#' not in a}, flush=True)
    total = lambda a, f: sum(t['arms'][a][f] for t in res.values())
    totals = {a: dict(confirmed_tasks=total(a, 'confirmed_tasks'), reach=total(a, 'reach'),
                      strict_confirmed_tasks=sum(t['arms'][a]['strict']['confirmed_tasks'] for t in res.values()),
                      finishing_reach=total(a, 'finishing_reach'), confirmed_tests=total(a, 'confirmed_tests'),
                      tests=total(a, 'tests'), fa_tests=total(a, 'fa_tests'), inputs=total(a, 'inputs')) for a in ARMS}
    for t in totals.values():
        t['precision'] = t['confirmed_tests'] / t['tests'] if t['tests'] else None
    per_answer = {a: dict(reach=sum(t['arms'][f'{a}#s{i}']['reach'] for t in res.values() for i in range(K)),
                          confirmed=sum(t['arms'][f'{a}#s{i}']['confirmed_tasks'] for t in res.values() for i in range(K)),
                          of=len(res) * K) for a in ARMS}
    checks = {}
    for comp in ('placebo', 'blind'):
        net = {}
        for cid, t in res.items():
            net[t['problem']] = net.get(t['problem'], 0) + t['arms']['concept']['confirmed_tasks'] - t['arms'][comp]['confirmed_tasks']
        checks[comp] = dict(margin=totals['concept']['confirmed_tasks'] - totals[comp]['confirmed_tasks'],
                            positive_problems=sorted(p[:12] for p, v in net.items() if v > 0),
                            concept_only=sorted((c for c, t in res.items() if t['arms']['concept']['confirmed_tasks']
                                                 and not t['arms'][comp]['confirmed_tasks']), key=int),
                            comp_only=sorted((c for c, t in res.items() if t['arms'][comp]['confirmed_tasks']
                                              and not t['arms']['concept']['confirmed_tasks']), key=int))
        checks[comp]['ok'] = checks[comp]['margin'] >= 3 and len(checks[comp]['positive_problems']) >= 3
    fa_ok = totals['concept']['fa_tests'] <= min(totals['placebo']['fa_tests'], totals['blind']['fa_tests']) + 5
    precision_ok = (totals['concept']['precision'] or 0) >= 0.8
    signal = fa_ok and precision_ok and all(c['ok'] for c in checks.values())
    uninformative = totals['code']['confirmed_tasks'] <= totals['blind']['confirmed_tasks']
    verdict = 'uninformative' if uninformative else 'signal' if signal else 'no signal'  # Amendment 1, Codex M3
    per_problem = {}
    for t in res.values():
        p = per_problem.setdefault(t['problem'][:12], {a: 0 for a in ARMS})
        for a in ARMS:
            p[a] += t['arms'][a]['confirmed_tasks']
    gen_status = {a: {} for a in ARMS}  # Codex S3/NOTES: generation failures and finish reasons per arm
    for name, info in gen_info.items():
        a = name.split('/')[0]
        gen_status[a][info['status']] = gen_status[a].get(info['status'], 0) + 1
    finish = {a: {} for a in (*ARMS, 'facts', 'specfacts')}
    for p in (OUT / 'calls').rglob('*.json'):
        a, r = p.relative_to(OUT / 'calls').parts[0], json.loads(p.read_text())['finish_reason']
        finish[a][r] = finish[a].get(r, 0) + 1
    if frozen_state() != frozen:
        raise SystemExit('frozen state changed during score')
    out = dict(signal=verdict, signal_checks_passed=signal, checks=checks, fa_ok=fa_ok, precision_ok=precision_ok,
               totals=totals, per_answer=per_answer, per_problem=per_problem, generation_status=gen_status, finish=finish,
               concept_vs_code=totals['concept']['confirmed_tasks'] - totals['code']['confirmed_tasks'],
               tasks=res, generation=gen_info, frozen_sha256=hashlib.sha256((OUT / 'frozen.json').read_bytes()).hexdigest())
    O.immutable(OUT / 'score.json', out)
    print(json.dumps({k: out[k] for k in ('signal', 'signal_checks_passed', 'checks', 'totals', 'per_answer', 'concept_vs_code',
                                          'per_problem', 'generation_status', 'finish')}, indent=1))


if __name__ == '__main__':
    cmd = sys.argv[1]
    raise SystemExit({'generate': lambda: generate('smoke' in sys.argv[2:]), 'freeze': freeze, 'score': score}[cmd]() or 0)
