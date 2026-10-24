"""v59: v34 fault concept as the only PUT information for a code-blind Sonnet generator (see PREREG.md). Repo root:
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v59_blind_concept/run.py prompts   # neutral job dirs + pending.json
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v59_blind_concept/run.py collect   # copy answers into out/.../answers
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v59_blind_concept/run.py freeze    # after every answer + audit.json
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v59_blind_concept/run.py score     # references only here
Sonnet subagents read ~/.local/state/ct_jobs/<hex>/r_<key>.txt and write a_<key>.txt (Amendment 1: neutral paths, no two
requests of one problem per writer); `collect` copies them to answers/<arm>/s<i>/<key>.txt.
"""
import ast
import hashlib
import json
import secrets
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O
from trickcatcher_linefacts.analysis.v49_defn_oracle import plan_rules as R
from trickcatcher_linefacts.analysis.v53_validity_smallscope import smallscope as S
from trickcatcher_linefacts.analysis.v53_validity_smallscope import validity as V
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run

E = O.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v59_blind_concept'
TOOLS = HERE.parents[1] / 'out' / 'pipelines' / 'v31_faulttemplate' / 'humaneval' / 'faulttemplate' / 'openrouter' / 'vibepass_half' / 'cases'
JOBS = Path.home() / '.local' / 'state' / 'ct_jobs'
TASKS = ('6', '39', '48', '58', '69', '70')
ARMS = ('blind', 'concept', 'placebo', 'code')
K = 3
HEAD = {'concept': 'Tool analysis of the program under test (its code is not shown):\n',
        'placebo': 'Tool output for the program under test (its code is not shown):\n',
        'code': 'Program under test (may be buggy):\n'}
SUBAGENT = (
    'You are one independent writer in a test-generation experiment. Use only two tools: Read (each request file '
    'below) and Write (each answer file below). Do not read, search or open anything else; no Bash, no Grep, no Glob, '
    'no web. For each request file: read it; it contains a SYSTEM part and a USER part; answer the USER part following '
    'the SYSTEM part exactly (one ```python code block and nothing else); write that answer, verbatim, to the paired '
    'answer file. Treat each request independently. When all answers are written, reply with the single word: done.\n\n')


def tool(cid):
    return json.loads((TOOLS / cid / 'tool.json').read_text())


def prompt(case, arm):
    """Stage 2 `plain` prompt (byte-identical for `blind`); other arms insert one block before the instruction."""
    head = S.message(E.task_view(case), 'plain')
    instr = S.INSTR['plain']
    assert head.endswith(instr)
    if arm == 'blind':
        return head
    if arm == 'code':
        block = f"```python\n{E.task_view(case)['source_masked'].strip()}\n```"
    else:
        g = ft_run.guidance(tool(case['case_id'])) if arm == 'concept' else ft_run.placebo_guidance(tool(case['case_id']))
        block = json.dumps(g, ensure_ascii=False, indent=1)
    return head[:-len(instr)] + HEAD[arm] + block + '\n\n' + instr


def key(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def cases():
    run, probs = V.problems()
    by_id = {c['case_id']: c for c in run.cases}
    pid_of = {c['case_id']: p for p, cs in probs.items() for c in cs}
    return run, probs, {cid: by_id[cid] for cid in TASKS}, pid_of


def prompts():
    """Neutral job dirs (Amendment 1 M1) and per-writer batches with at most one request per problem (M2)."""
    _, _, cs, pid_of = cases()
    old = json.loads((OUT / 'manifest.json').read_text()) if (OUT / 'manifest.json').is_file() else {}
    salt = old.get('salt') or secrets.token_hex(8)
    keys, jobs, pending = {}, {}, []
    for arm in ARMS:
        texts = {cid: f"SYSTEM:\n{V.SYSTEM}\n\nUSER:\n{prompt(cs[cid], arm)}\n" for cid in TASKS}
        keys[arm] = {cid: key(t) for cid, t in texts.items()}
        rank = {}
        for cid in TASKS:  # b-th distinct prompt of a problem goes to batch b
            k, p = keys[arm][cid], pid_of[cid]
            rank.setdefault(p, [])
            if k not in rank[p]:
                rank[p].append(k)
        batches = {}
        for p, ks in rank.items():
            for b, k in enumerate(ks):
                batches.setdefault(b, []).append(k)
        for i in range(K):
            for b, ks in sorted(batches.items()):
                job = hashlib.sha256(f'{salt}/{arm}/{i}/{b}'.encode()).hexdigest()[:10]
                jobs[job] = dict(arm=arm, sample=i, batch=b, keys=ks)
                (JOBS / job).mkdir(parents=True, exist_ok=True)
                files = []
                for k in ks:
                    (JOBS / job / f'r_{k}.txt').write_text(next(t for cid, t in texts.items() if keys[arm][cid] == k))
                    if not (OUT / 'answers' / arm / f's{i}' / f'{k}.txt').is_file():
                        files.append(dict(request=str(JOBS / job / f'r_{k}.txt'), answer=str(JOBS / job / f'a_{k}.txt')))
                if files:
                    pending.append(dict(job=job, n=len(files), files=files,
                                        prompt=SUBAGENT + '\n'.join(f"request: {f['request']}\nanswer: {f['answer']}" for f in files)))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'manifest.json').write_text(json.dumps(dict(salt=salt, keys=keys, jobs=jobs), indent=1))
    (OUT / 'subagent_prompt.txt').write_text(SUBAGENT)
    (OUT / 'pending.json').write_text(json.dumps(pending, indent=1))
    print(json.dumps({a: len(set(m.values())) for a, m in keys.items()}), 'jobs', len(jobs), 'pending', len(pending))


def collect():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    copied, missing = 0, []
    for job, j in manifest['jobs'].items():
        for k in j['keys']:
            src, dst = JOBS / job / f'a_{k}.txt', OUT / 'answers' / j['arm'] / f"s{j['sample']}" / f'{k}.txt'
            if dst.is_file():
                if src.is_file() and src.read_bytes() != dst.read_bytes():
                    raise SystemExit(f'answer changed after collect: {job}/{k}')
                continue
            if not src.is_file():
                missing.append(f'{job}/{k}')
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            copied += 1
    print('copied', copied, 'missing', missing)


def answer_paths():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    return {f'{arm}/s{i}/{k}': OUT / 'answers' / arm / f's{i}' / f'{k}.txt'
            for arm in ARMS for i in range(K) for k in set(manifest['keys'][arm].values())}


def external_files():
    """Files outside this folder that `score` reads: v31 tool.json, Stage 1 `open` checks, Stage 2 / v52 oracle answers."""
    _, probs, _, pid_of = cases()
    files = [TOOLS / cid / 'tool.json' for cid in TASKS]
    for pid in dict.fromkeys(pid_of[cid] for cid in TASKS):
        files.append(V.OUT / 'answers' / f'{pid}_open.txt')
        old = S.v52_task([c['case_id'] for c in probs[pid]])
        files += [(S.P.OUT / 'programs' / 'defn' / old / f'{i}.txt') if old else S.OUT / 'answers' / 'oracle' / f'{pid}_{i}.txt'
                  for i in range(S.K)]
    return files


def frozen_state():
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    paths = answer_paths()
    return dict(answers={n: sha(p) for n, p in paths.items()},
                parse_ok={n: bool(p.is_file() and O.code_block(p.read_text())) for n, p in paths.items()},
                requests={f'{job}/{f.name}': sha(f) for job in sorted(json.loads((OUT / 'manifest.json').read_text())['jobs'])
                          for f in sorted((JOBS / job).glob('r_*.txt'))},
                sources={f: sha(HERE / f) for f in ('run.py', 'PREREG.md')},
                external={str(p.relative_to(HERE.parents[1])): sha(p) for p in external_files()},
                subagent_prompt=sha(OUT / 'subagent_prompt.txt'), manifest=sha(OUT / 'manifest.json'),
                audit=sha(OUT / 'audit.json'))


def freeze():
    frozen = frozen_state()
    missing = sorted(n for n, h in frozen['answers'].items() if h is None)
    bad = sorted(n for n, ok in frozen['parse_ok'].items() if not ok)
    audit = json.loads((OUT / 'audit.json').read_text()) if (OUT / 'audit.json').is_file() else None
    if missing or bad or audit is None or any(v not in ('ok', 'excluded') for v in audit.values()):
        raise SystemExit(f'not freezable: missing={missing} unparseable={bad} audit={audit}')
    O.immutable(OUT / 'frozen.json', frozen)
    print('frozen', len(frozen['answers']), 'answers')


def generated(case, arm, i, k):
    """smallscope.generated on this experiment's answer path and execution root: (literals <= CAP, info)."""
    code = O.code_block((OUT / 'answers' / arm / f's{i}' / f'{k}.txt').read_text())
    info = dict(status='ok', yielded=0, dropped=0, duplicates=0)
    if not code:
        return [], dict(info, status='parse_error')
    src, d = {'g': code + S.GEN_WRAP}, OUT / 'exec' / case['case_id'] / 'gen' / arm / f's{i}'
    try:
        n = O.batch(d / 'len', src, ['g'], '__gen__', ['(-1,)'], 20)['g'][0]
        count = int(n[1]) if n[0] == 'ok' else 0
        items = O.batch(d / 'items', src, ['g'], '__gen__', [f'({j},)' for j in range(count)], 20)['g'] if count else []
    except RuntimeError:
        return [], dict(info, status='sandbox_failed')
    if n[0] != 'ok':
        info['status'] = 'inputs_' + n[0] + ('' if len(n) < 2 else ':' + str(n[1]))
    out, arity = [], len(S.params(case))
    for o in items:
        info['yielded'] += 1
        try:
            lit = S.literal(ast.literal_eval(o[1]), arity) if o[0] == 'ok' and not o[1].endswith('<truncated>') else None
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            lit = None
        if lit is None:
            info['dropped'] += 1
        elif lit in out:
            info['duplicates'] += 1
        elif len(out) < S.CAP:
            out.append(lit)
    return out, info


def accept(case, rec, pid, inputs):
    """smallscope.accept with this experiment's execution root."""
    code, found, _ = V.checks((V.OUT / 'answers' / f'{pid}_open.txt').read_text())
    if not found or not inputs:
        return {lit: True for lit in inputs}
    srcs = [V.wrap(code, case['entry'], c['name']) for c in found]
    with E.execution_root(OUT):
        base = O.run_programs(case, 'chk_open', srcs, rec['base_inputs'], 'base', 2)
        ran = O.run_programs(case, 'chk_open', srcs, inputs, 'all')
    ok = lambda o: bool(o) and o[0] == 'ok' and o[1] == 'True'
    kept = [j for j in range(len(found)) if all(ok(o) for o in base[f'p{j}'])]
    return {lit: all(ok(ran[f'p{j}'][n]) for j in kept) for n, lit in enumerate(inputs)}


def truth_for(inv, case, rows, official):
    """smallscope.truth_for with this experiment's reference root."""
    view = dict(inputs={lit: dict(put=r['put'], vote=None, consensus=None) for lit, r in rows.items()})
    with O.reference_root(OUT):
        truth = E.reference_truth(inv, case, view, official, set())
    for lit, t in truth.items():
        put = E.iorel.value(rows[lit]['put'])
        cache = []

        def exposes(lit=lit, t=t, put=put, cache=cache):
            if not cache:
                cache.append(bool(t['valid'] and put is not None and t['ref'] is not None and not E.same(put, t['ref'])
                                  and E.iorel.official_exposes(official, case, lit)))
            return cache[0]
        t['exposes'] = exposes
    return truth


def norm(lit, arity):
    try:
        return S.literal(ast.literal_eval(lit), arity)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None


def mechanism(inputs, rows, truth, labels, templates):
    """Exposing (proxy, then official) and confirmed inputs, split into template inputs and others."""
    proxy = [l for l in E.ordered(inputs) if R.exposing(dict(truth[l], exposing=None), E.iorel.value(rows[l]['put']))]
    exposing = [l for l in proxy if truth[l]['exposes']()]
    confirmed = [l for l in E.emitted(set(inputs), rows, 'primary', 20) if labels[l]['primary'] == 'confirmed']
    split = lambda ls: dict(n=len(ls), template=sum(l in templates for l in ls), other=sum(l not in templates for l in ls))
    return dict(exposing=split(exposing), confirmed=split(confirmed), exposing_examples=exposing[:3])


def score():
    frozen = json.loads((OUT / 'frozen.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    now = frozen_state()
    changed = sorted(f for f in frozen if frozen[f] != now[f])
    if changed or not all(frozen['parse_ok'].values()):
        raise SystemExit(f'frozen state changed or unparseable answers: {changed}')
    manifest = json.loads((OUT / 'manifest.json').read_text())['keys']
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    _, _, records, _ = ready
    run, probs, cs, pid_of = cases()
    official = E.Reference(run)
    official.root = OUT / 'references' / 'official'
    tasks, gen_info = {}, {}
    for cid in TASKS:
        case, rec, pid = cs[cid], records[cid], pid_of[cid]
        arity = len(S.params(case))
        samples = {}
        for arm in ARMS:
            for i in range(K):
                samples[arm, i], gen_info[f'{arm}/s{i}/{cid}'] = generated(case, arm, i, manifest[arm][cid])
        everything = list(dict.fromkeys(l for v in samples.values() for l in v))
        acc = accept(case, rec, pid, everything)
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
        truth = truth_for(inv, case, rows['tolerant'], official)
        labels = O.labels_for(rows['tolerant'], truth)
        templates = {norm(r['input'], arity) for c in tool(cid)['concepts'] for r in c['inputs']} - {None}
        tasks[cid] = dict(problem=pid, oracle=dict(strict=strict, tolerant=tolerant,
                                                    reasons={str(j): reasons[j] for j in range(S.K)}),
                          arms={a: dict(S.arm_metrics(ins, rows, truth, len(tolerant), len(strict)),
                                        **mechanism(ins, rows['tolerant'], truth, labels, templates)) for a, ins in arms.items()})
        print(cid, {a: (m['inputs'], m['confirmed_tasks'], m['fa_tests'], m['reach']) for a, m in tasks[cid]['arms'].items()
                    if '#' not in a}, flush=True)
    total = lambda a, f: sum(t['arms'][a][f] for t in tasks.values())
    totals = {a: dict(confirmed_tasks=total(a, 'confirmed_tasks'), reach=total(a, 'reach'),
                      strict_confirmed_tasks=sum(t['arms'][a]['strict']['confirmed_tasks'] for t in tasks.values()),
                      finishing_reach=total(a, 'finishing_reach'),
                      confirmed_tests=total(a, 'confirmed_tests'), tests=total(a, 'tests'), fa_tests=total(a, 'fa_tests'),
                      inputs=total(a, 'inputs'),
                      exposing_template=sum(t['arms'][a]['exposing']['template'] for t in tasks.values()),
                      exposing_other=sum(t['arms'][a]['exposing']['other'] for t in tasks.values()),
                      confirmed_template=sum(t['arms'][a]['confirmed']['template'] for t in tasks.values()),
                      confirmed_other=sum(t['arms'][a]['confirmed']['other'] for t in tasks.values()))
              for a in ARMS}
    for t in totals.values():
        t['precision'] = t['confirmed_tests'] / t['tests'] if t['tests'] else None
    per_answer = {a: dict(reach=sum(t['arms'][f'{a}#s{i}']['reach'] for t in tasks.values() for i in range(K)),
                          confirmed=sum(t['arms'][f'{a}#s{i}']['confirmed_tasks'] for t in tasks.values() for i in range(K)),
                          of=len(TASKS) * K) for a in ARMS}
    win = lambda a, b: sorted(c for c, t in tasks.items() if t['arms'][a]['confirmed_tasks'] and not t['arms'][b]['confirmed_tasks'])
    checks = {}
    for comp in ('placebo', 'blind'):
        extra = win('concept', comp)
        checks[comp] = dict(concept_only=extra, comp_only=win(comp, 'concept'),
                            margin=totals['concept']['confirmed_tasks'] - totals[comp]['confirmed_tasks'],
                            margin_ok=totals['concept']['confirmed_tasks'] >= totals[comp]['confirmed_tasks'] + 2,
                            span_ok=len({tasks[c]['problem'] for c in extra}) >= 2)
    fa_ok = totals['concept']['fa_tests'] <= min(totals['placebo']['fa_tests'], totals['blind']['fa_tests']) + 5
    precision_ok = (totals['concept']['precision'] or 0) >= 0.8
    signal = fa_ok and precision_ok and all(c['margin_ok'] and c['span_ok'] for c in checks.values())
    verdict = 'signal' if signal else 'uninformative' if totals['code']['reach'] == 0 else 'no signal'  # Amendment 1 S7
    out = dict(signal=verdict, checks=checks, fa_ok=fa_ok, precision_ok=precision_ok,
               totals=totals, per_answer=per_answer, tasks=tasks, generation=gen_info,
               frozen_sha256=sha(OUT / 'frozen.json'))
    O.immutable(OUT / 'score.json', out)
    print(json.dumps(dict(signal=out['signal'], checks=checks, totals=totals, per_answer=per_answer), indent=1))


if __name__ == '__main__':
    raise SystemExit(dict(prompts=prompts, collect=collect, freeze=freeze, score=score)[sys.argv[1]]() or 0)
